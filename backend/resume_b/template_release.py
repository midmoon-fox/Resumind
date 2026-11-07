"""Explicit, repeatable publication after DB migration; no startup database mutation."""
import hashlib
from pathlib import Path

from .templates import TemplateService, get_template
from .documents import TEMPLATE_NAMES

ROOT = Path(__file__).resolve().parents[1]


def publish_templates(session, *, keys=None):
    published = []
    for key in TEMPLATE_NAMES if keys is None else keys:
        definition = get_template(key)
        names = ((key + '.html.j2', 'sections.html.j2', 'base.css', key + '.css')
                 if key in {'ribbon', 'sidebar'} else ('resume.html.j2', 'base.css', key + '.css'))
        paths = [ROOT / 'assets/templates/1.0.0' / name for name in names]
        word = ROOT / 'assets/word' / f'{key}-1.0.0.docx'
        digest = hashlib.sha256(b''.join(p.read_bytes() for p in paths) + word.read_bytes()).hexdigest()
        asset_version = 'html-1.0.0:' + digest
        object_key = word.relative_to(ROOT).as_posix()
        def verify(db, template_key, version, layout, docx, preview):
            return (template_key == key and version == '1.0.0' and layout == asset_version
                    and docx == object_key and preview is None and all(p.is_file() for p in paths))
        TemplateService(session).publish(definition, vue_asset_version=asset_version,
                                         docx_object_key=object_key, verify_assets=verify)
        published.append({'id': key, 'version': '1.0.0', 'name': definition['name']})
    return published
