"""Explicit origins for the public frontend; JWT requests never use cookies."""
import os
from urllib.parse import urlsplit
from starlette.middleware.cors import CORSMiddleware


def configure_cors(app, app_origin):
    origins = [app_origin, 'http://127.0.0.1:5173', 'http://localhost:5173']
    origins += [value.strip() for value in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if value.strip()]
    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or '*' in origin:
            raise RuntimeError('CORS_ALLOWED_ORIGINS 必须为明确的域名来源，不包含路径或通配符')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(dict.fromkeys(origins)),
        allow_credentials=False,
        allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'Idempotency-Key'],
        expose_headers=['X-Request-Id', 'X-Contract-Version', 'Content-Disposition'],
    )
