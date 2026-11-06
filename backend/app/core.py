import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from .models import AuditEvent, AuthIdempotency, Idempotency


class Problem(Exception):
    def __init__(self, status, code, message, details=None, headers=None):
        self.status, self.code, self.message = status, code, message
        self.details, self.headers = details or {}, headers or {}


def invalid(message, path=''):
    raise Problem(422, 'VALIDATION_ERROR', message, {'errors': [{'path': path, 'message': message}]})


def validation_problem(request, errors):
    """Keep structured field paths, with readable Chinese for account form errors."""
    account = request.url.path in {'/api/auth/registrations', '/api/auth/sessions'}
    bad_json = any(error['type'] == 'json_invalid' for error in errors)
    details = []
    labels = {'email': '邮箱', 'password': '密码', 'username': '昵称'}
    for error in errors:
        location = [str(part) for part in error['loc'] if part != 'body']
        field = location[-1] if location else ''
        message = error['msg']
        if account:
            label = labels.get(field, field or '请求内容')
            kind = error['type']
            if kind == 'json_invalid':
                message = '请求内容不是有效的 JSON，请检查逗号、引号和括号。'
            elif kind == 'missing':
                message = f'请输入{label}。'
            elif field == 'email' and kind == 'value_error':
                message = '邮箱格式不正确，例如 name@example.com。'
            elif kind == 'string_too_short':
                minimum = error['ctx']['min_length']
                message = f'{label}至少需要 {minimum} 位。' if minimum > 1 else f'请输入{label}。'
                if field == 'password' and minimum == 5:
                    message = '密码至少需要 5 位，例如 12345。'
            elif kind == 'string_too_long':
                message = f'{label}最多允许 {error["ctx"]["max_length"]} 位。'
            elif kind == 'string_type':
                message = f'{label}请填写文字，并在 JSON 中使用双引号。'
            elif kind == 'extra_forbidden':
                message = f'不支持字段 {field}，请删除后重试。'
        details.append({'path': '/' + '/'.join(location), 'message': message})
    message = ' '.join(dict.fromkeys(item['message'] for item in details)) if account else '请求数据不合法'
    return Problem(400 if bad_json else 422, 'BAD_REQUEST' if bad_json else 'VALIDATION_ERROR',
                   message, {'errors': details})


def reject_unknown_query(request: Request):
    route = request.scope.get('route')
    root = getattr(route, 'dependant', None)
    if root is None:
        return
    allowed, seen = set(), set()
    def collect(dependant):
        if id(dependant) in seen:
            return
        seen.add(id(dependant))
        allowed.update(field.alias for field in dependant.query_params)
        for child in dependant.dependencies:
            collect(child)
    collect(root)
    # B validates its manually-read query fields itself; declarations are trusted route metadata.
    for parameter in (getattr(route, 'openapi_extra', None) or {}).get('parameters', []):
        if parameter.get('in') == 'query':
            allowed.add(parameter['name'])
    unknown = set(request.query_params) - allowed
    if unknown:
        invalid('未知查询字段：' + ','.join(sorted(unknown)), '/query')


def missing():
    raise Problem(404, 'NOT_FOUND', '资源不存在或不可访问')


def conflict(message='当前状态不允许此操作'):
    raise Problem(409, 'STATE_CONFLICT', message)


def stamp(value):
    return value.replace(tzinfo=timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).digest()


@dataclass
class Settings:
    database_url: str
    secret: str
    origin: str = 'https://localhost:8443'
    object_root: str = '.data/objects'
    download_base: str = 'https://localhost:8443'
    redis_url: str | None = None

    @classmethod
    def load(cls):
        secret = os.environ.get('APP_SECRET', '')
        if len(secret) < 32:
            raise RuntimeError('APP_SECRET 必须配置为至少32字符的随机密钥')
        origin = os.environ.get('APP_ORIGIN', 'https://localhost:8443').rstrip('/')
        if not origin.startswith('https://'):
            raise RuntimeError('APP_ORIGIN 必须为 HTTPS，确保认证与文件下载经加密连接传输')
        return cls(os.environ.get('DATABASE_URL', 'mysql+pymysql://resume:resume@localhost:3306/resume_assistant?charset=utf8mb4'), secret, origin, os.environ.get('OBJECT_ROOT', '.data/objects'), os.environ.get('DOWNLOAD_BASE', origin), os.environ.get('REDIS_URL'))


def database(url):
    options = {'connect_args': {'autocommit': False}} if url.startswith('sqlite:') else {}
    engine = create_engine(url, pool_pre_ping=True, **options)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def sqlite_fk(connection, _):
            connection.autocommit = True
            connection.execute('PRAGMA foreign_keys=ON')
            connection.autocommit = False
    elif engine.dialect.name == 'mysql':
        @event.listens_for(engine, 'connect')
        def mysql_utc(connection, _):
            with connection.cursor() as cursor:
                cursor.execute('SELECT VERSION()')
                version = str(cursor.fetchone()[0])
                if not mysql_version_allowed(version, url):
                    raise RuntimeError('支持 MySQL 8.4 或 26.7，实际为 ' + version)
                cursor.execute("SET time_zone = '+00:00'")
    return engine, sessionmaker(engine, expire_on_commit=False)


def mysql_version_allowed(version, url):
    """Explicitly supported lines: original 8.4 and the user's verified 26.7 server."""
    return version.startswith(('8.4.', '26.7.'))


def get_db(request: Request):
    with request.app.state.sessions() as session:
        with session.begin():
            yield session


def envelope(request, data):
    return {'data': data, 'requestId': request.state.request_id}


def response(request, data, status=200):
    return JSONResponse(envelope(request, data), status_code=status)


def audit(db, user_id, action, resource_type, resource_id, request_id, **metadata):
    allowed = {'revision', 'sourceCount', 'errorCode'}
    if not metadata.keys() <= allowed:
        raise ValueError('审计元数据只允许修订、计数及错误类别')
    db.add(AuditEvent(user_id=user_id, action=action, resource_type=resource_type,
                      resource_id=resource_id, request_id=request_id, metadata_json=metadata))


def claim(db, request, payload, user_id=None, anonymous_hash=None):
    key = request.headers.get('Idempotency-Key', '')
    if not key:
        invalid('缺少请求编号。请在 Headers 中添加 Idempotency-Key，例如 register-test-0001；每次新的操作换一个编号。', '/headers/Idempotency-Key')
    if not 8 <= len(key) <= 64 or not key.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in key):
        invalid('请求编号格式不正确：Idempotency-Key 需要 8～64 位，可使用英文字母、数字和英文符号，不能包含空格或中文。例如 register-test-0001。', '/headers/Idempotency-Key')
    operation = f'{request.method} {request.url.path}'
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    # HMAC avoids an offline dictionary attack against stored login-password digests.
    digest = hmac.digest(request.app.state.settings.secret.encode(), canonical, 'sha256')
    cls = Idempotency if user_id else AuthIdempotency
    scope = {'user_id': user_id} if user_id else {'anonymous_session_hash': anonymous_hash}
    record = cls(**scope, operation_key=operation, client_key=key, request_sha256=digest)
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
        return record, False
    except IntegrityError:
        query = select(cls).filter_by(**scope, operation_key=operation, client_key=key).with_for_update()
        old = db.scalar(query)
        if old is None:
            raise Problem(409, 'REQUEST_IN_PROGRESS', '请求仍在提交，请稍后重试')
        if not hmac.compare_digest(old.request_sha256, digest):
            raise Problem(409, 'IDEMPOTENCY_MISMATCH', '相同幂等键对应的参数不同')
        if old.state != 'COMPLETED':
            raise Problem(409, 'REQUEST_IN_PROGRESS', '请求仍在提交，请稍后重试')
        return old, True


def complete(record, status, data, resource_type=None, resource_id=None):
    record.state, record.http_status = 'COMPLETED', status
    record.response_json = data
    if isinstance(record, Idempotency):
        record.resource_type, record.resource_id = resource_type, resource_id
