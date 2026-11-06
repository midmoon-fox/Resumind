import hashlib
import hmac
import io
import re
import time
import warnings
import zipfile
from datetime import timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from .auth import CurrentUser, DB
from .core import Problem, invalid, missing, sha, stamp
from .models import File, now
from .services import owned

MAX_SIZE = 20 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000
download_router = APIRouter()


def display_name(name, limit=255):
    name = re.split(r'[/\\]', name or '')[-1]
    name = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', '_', name).strip(' .')
    return (name or 'file')[:limit]


def checked_docx(content):
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
        entries = archive.infolist()
        if len(entries) > 2000 or sum(e.file_size for e in entries) > 100 * 1024 * 1024:
            raise ValueError('DOCX 展开规模超限')
        for e in entries:
            path = Path(e.filename.replace('\\', '/'))
            if path.is_absolute() or '..' in path.parts or e.flag_bits & 1 or e.file_size > max(1024 * 1024, e.compress_size * 200):
                raise ValueError('DOCX 压缩结构不安全')
        if '[Content_Types].xml' not in archive.namelist() or 'word/document.xml' not in archive.namelist():
            raise ValueError('不是 DOCX 文档')
        if any('vbaProject' in e.filename for e in entries):
            raise ValueError('不接受包含宏的文档')
        return archive
    except (zipfile.BadZipFile, ValueError) as exc:
        raise Problem(415, 'UNSUPPORTED_FILE_TYPE', str(exc)) from None


def identify(content, name, purpose):
    if len(content) > MAX_SIZE:
        raise Problem(413, 'FILE_TOO_LARGE', '上传文件不能超过20MiB')
    if not content:
        invalid('不接受空文件', '/file')
    suffix = Path(name).suffix.lower()
    if content.startswith(b'\x89PNG\r\n\x1a\n') or content.startswith(b'\xff\xd8\xff'):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    if image.width * image.height > 20_000_000:
                        invalid('图片不能超过2000万像素', '/file')
                    fmt = image.format
                    image.verify()
            return {'PNG': 'image/png', 'JPEG': 'image/jpeg'}[fmt]
        except Problem:
            raise
        except Exception:
            raise Problem(415, 'UNSUPPORTED_FILE_TYPE', '图片格式损坏或规模超限') from None
    if purpose == 'AVATAR':
        raise Problem(415, 'UNSUPPORTED_FILE_TYPE', '头像仅支持 PNG、JPG 图片')
    if purpose == 'JD' and suffix != '.txt':
        raise Problem(415, 'UNSUPPORTED_FILE_TYPE', '岗位 JD 仅支持 TXT、JPG、PNG 文件；也可以直接粘贴 JD 原文')
    if purpose == 'JD' and (content.startswith(b'%PDF-') or content.startswith(b'PK\x03\x04')):
        raise Problem(415, 'UNSUPPORTED_FILE_TYPE', '岗位 JD 仅支持 TXT、JPG、PNG 文件')
    if content.startswith(b'%PDF-'):
        try:
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted or len(reader.pages) > 50:
                invalid('PDF必须未加密且不超过50页', '/file')
        except Problem:
            raise
        except Exception:
            raise Problem(415, 'UNSUPPORTED_FILE_TYPE', 'PDF格式不合法') from None
        return 'application/pdf'
    if content.startswith(b'PK\x03\x04'):
        checked_docx(content).close()
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    if suffix in {'.txt', '.md', '.markdown'}:
        try:
            text = content.decode('utf-8-sig')
            if any(ord(c) < 32 and c not in '\r\n\t' for c in text):
                raise ValueError()
        except (UnicodeError, ValueError):
            raise Problem(415, 'UNSUPPORTED_FILE_TYPE', '文本文件需要有效UTF-8文本') from None
        return 'text/plain' if suffix == '.txt' else 'text/markdown'
    raise Problem(415, 'UNSUPPORTED_FILE_TYPE', '不支持的实际文件类型')


class LocalStorage:
    """Private development storage. Production can inject an object-store adapter."""
    def __init__(self, settings):
        self.settings = settings
        self.root = Path(settings.object_root).resolve()

    def path(self, key):
        if not re.fullmatch(r'[a-f0-9-]{36}/[a-f0-9-]{36}', key):
            raise ValueError('Invalid server object key')
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Object path escaped storage root')
        return path

    def put(self, user_id, content):
        key = user_id + '/' + str(uuid4())
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)
        return key

    def read(self, key):
        return self.path(key).read_bytes()

    def delete(self, key):
        self.path(key).unlink(missing_ok=True)

    def sign(self, file, user_id):
        expires = now() + timedelta(seconds=300)
        epoch = int(expires.replace(tzinfo=timezone.utc).timestamp())
        message = f'{file.id}:{user_id}:{epoch}'
        sig = hmac.new(self.settings.secret.encode(), message.encode(), 'sha256').hexdigest()
        url = self.settings.download_base.rstrip('/') + '/internal/files/' + file.id + '?' + urlencode({'expires': epoch, 'signature': sig})
        if not url.startswith('https://'):
            raise RuntimeError('Download URLs require HTTPS')
        return dict(url=url, expiresAt=stamp(expires), fileName=display_name(file.original_name, 150))


def file_access(db, file_id, user_id, relations):
    file = owned(db, File, file_id, user_id)
    if file.status != 'READY':
        missing()
    if file.purpose in {'EXPORT', 'PREPARATION_EXPORT'} and not relations.output_accessible(db, file):
        missing()
    return file


def register_output_file(db, storage, user_id, purpose, content, name, mime):
    if purpose not in {'EXPORT', 'PREPARATION_EXPORT'}:
        raise ValueError('Output purpose required')
    key = storage.put(user_id, content)
    file = File(user_id=user_id, purpose=purpose, object_key=key, original_name=display_name(name),
                mime_type=mime, size_bytes=len(content), sha256=sha(content), status='READY')
    db.add(file)
    db.flush()
    return file


@download_router.get('/internal/files/{file_id}', include_in_schema=False)
def private_download(file_id: str, request: Request, user: CurrentUser, db: DB, expires: int, signature: str):
    # Local adapter implementation route, not an additional public API contract.
    if not time.time() <= expires <= time.time() + 301:
        missing()
    expected = hmac.new(request.app.state.settings.secret.encode(), f'{file_id}:{user.id}:{expires}'.encode(), 'sha256').hexdigest()
    if not hmac.compare_digest(signature, expected):
        missing()
    file = file_access(db, file_id, user.id, request.app.state.relations)
    storage = request.app.state.storage
    path = storage.path(file.object_key)
    if not path.is_file():
        missing()
    return FileResponse(path, media_type=file.mime_type, filename=display_name(file.original_name, 150), headers={'X-Content-Type-Options': 'nosniff'})
