"""Signed access tokens with server-side revocation; no bearer secrets stored in DB."""
import hmac
from datetime import timezone
from uuid import UUID

import jwt

ALGORITHM = 'HS256'
AUDIENCE = 'moneyai-api'
ACCESS_LIFETIME_DAYS = 7
REQUIRED_CLAIMS = ['sub', 'jti', 'iat', 'nbf', 'exp', 'iss', 'aud', 'token_type']


def signing_key(settings):
    return hmac.digest(settings.secret.encode(), b'moneyai:jwt-access:v1', 'sha256')


def epoch(value):
    return int(value.replace(tzinfo=timezone.utc).timestamp())


def issue_access_token(settings, session):
    issued = epoch(session.created_at)
    return jwt.encode(dict(sub=session.user_id, jti=session.id, iat=issued, nbf=issued,
                           exp=epoch(session.expires_at), iss=settings.origin,
                           aud=AUDIENCE, token_type='access'), signing_key(settings), algorithm=ALGORITHM)


def verify_access_token(settings, token):
    claims = jwt.decode(token, signing_key(settings), algorithms=[ALGORITHM],
                        audience=AUDIENCE, issuer=settings.origin,
                        options={'require': REQUIRED_CLAIMS, 'strict_aud': True})
    if claims['token_type'] != 'access':
        raise jwt.InvalidTokenError('Unexpected token type')
    for name in ['sub', 'jti']:
        value = claims[name]
        try:
            identifier = UUID(value)
            if identifier.version != 4 or str(identifier) != value:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise jwt.InvalidTokenError('Invalid identity') from None
    for name in ['iat', 'nbf', 'exp']:
        if type(claims[name]) is not int:
            raise jwt.InvalidTokenError('Invalid timestamp')
    if not claims['nbf'] == claims['iat'] < claims['exp']:
        raise jwt.InvalidTokenError('Invalid lifetime')
    return claims


def configure_openapi_security(schema):
    """One authentication contract for standalone A and integrated A/B/C routes."""
    schema.setdefault('components', {})['securitySchemes'] = {
        'bearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}}
    public = {'/api/auth/registrations', '/api/auth/sessions'}
    for path, methods in schema['paths'].items():
        for method, operation in methods.items():
            if method not in {'get', 'post', 'patch', 'delete'}:
                continue
            operation['security'] = [] if path in public else [{'bearerAuth': []}]
            parameters = [p for p in operation.get('parameters', [])
                          if not (p.get('in') == 'header' and p.get('name', '').lower()
                                  in {'origin', 'x-csrf-token'})]
            needs_key = method in {'post', 'patch', 'delete'} and path != '/api/auth/session' and not path.endswith('/preflights')
            if needs_key and not any(p.get('in') == 'header' and p.get('name', '').lower() == 'idempotency-key' for p in parameters):
                parameters.append({'name': 'Idempotency-Key', 'in': 'header', 'required': True,
                                   'schema': {'type': 'string', 'minLength': 8, 'maxLength': 64, 'pattern': '^[!-~]+$'}})
            operation['parameters'] = parameters
    return schema
