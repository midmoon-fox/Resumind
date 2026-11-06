import hmac
import secrets
from datetime import timedelta
from uuid import uuid4
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.exc import IntegrityError

from . import schemas as s
from .core import (Problem, audit, claim, complete, get_db, invalid, response, sha, stamp)
from .models import Session, User, now
import jwt
from .jwt_auth import ACCESS_LIFETIME_DAYS, epoch, issue_access_token, verify_access_token

router = APIRouter(prefix='/api', tags=['账户与登录'])
DB = Annotated[DatabaseSession, Depends(get_db, scope='function')]
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))
def signature(settings, message):
    return hmac.new(settings.secret.encode(), message.encode(), 'sha256').hexdigest()


def optional_session(request, db):
    values = request.headers.getlist('Authorization')
    if len(values) != 1:
        return None
    parts = values[0].split(' ')
    if len(parts) != 2 or parts[0].lower() != 'bearer' or not parts[1] or len(parts[1]) > 4096:
        return None
    try:
        claims = verify_access_token(request.app.state.settings, parts[1])
    except (jwt.InvalidTokenError, TypeError, ValueError, OverflowError):
        return None
    session = db.get(Session, claims['jti'])
    if (session is None or session.user_id != claims['sub'] or session.revoked_at is not None
            or session.expires_at <= now() or not hmac.compare_digest(session.token_hash, sha(session.id))
            or epoch(session.created_at) != claims['iat'] or epoch(session.expires_at) != claims['exp']):
        return None
    return session


def unauthenticated():
    return Problem(401, 'UNAUTHENTICATED', '请先登录或重新登录', headers={'WWW-Authenticate': 'Bearer'})


def current_user(request: Request, db: DB):
    session = optional_session(request, db)
    if session is None:
        raise unauthenticated()
    user = db.get(User, session.user_id)
    if user is None:
        raise unauthenticated()
    if user.status != 'ACTIVE':
        raise Problem(403, 'ACCOUNT_DISABLED', '账户已禁用')
    request.state.session = session
    request.state.user = user
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def verify_bearer(request: Request, db: DB):
    """Writes require an explicit Bearer token; no ambient Cookie credentials."""
    current_user(request, db)


def auth_scope(request, email):
    # Cookie-free idempotency scope. A keyed digest avoids storing email in the scope.
    return bytes.fromhex(signature(request.app.state.settings, 'auth-intent:' + email))


def user_json(user):
    return dict(id=user.id, email=user.email, username=user.username, avatarFileId=user.avatar_file_id, createdAt=stamp(user.created_at))


class RedisRateLimiter:
    """Shared limit across API processes. IP comes from the trusted ASGI peer."""
    SCRIPT = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n"

    def __init__(self, url):
        from redis import Redis
        self.client = Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)

    def check(self, key):
        try:
            count = self.client.eval(self.SCRIPT, 1, 'auth-rate:' + key, 60)
        except Exception:
            raise Problem(503, 'FEATURE_DISABLED', '登录限流存储暂不可用') from None
        if count > 10:
            raise Problem(429, 'RATE_LIMITED', '请求过于频繁', headers={'Retry-After': '60'})


class MissingRateLimiter:
    def check(self, key):
        raise Problem(503, 'FEATURE_DISABLED', '尚未配置 REDIS_URL 登录限流存储')


def limit_auth(request, email):
    peer = request.client.host if request.client else 'unknown'
    for value in ('ip:' + peer, 'email:' + email):
        request.app.state.limiter.check(signature(request.app.state.settings, value))


@router.post('/auth/registrations', status_code=201, response_model=s.Envelope[s.UserOut])
def register(body: s.Registration, request: Request, db: DB):
    limit_auth(request, body.email)
    record, replay = claim(db, request, body.model_dump(by_alias=True), anonymous_hash=auth_scope(request, body.email))
    if replay:
        return response(request, record.response_json, record.http_status)
    user = User(email=body.email, username=body.username, password_hash=hasher.hash(body.password))
    try:
        with db.begin_nested():
            db.add(user)
            db.flush()
    except IntegrityError:
        raise Problem(409, 'EMAIL_UNAVAILABLE', '该邮箱不可用于注册') from None
    data = user_json(user)
    complete(record, 201, data)
    audit(db, user.id, 'REGISTER', 'USER', user.id, request.state.request_id)
    return response(request, data, 201)


@router.post('/auth/sessions', status_code=201, response_model=s.Envelope[s.LoginOut])
def login(body: s.Login, request: Request, db: DB):
    limit_auth(request, body.email)
    user = db.scalar(select(User).where(User.email == body.email).with_for_update())
    try:
        hasher.verify(user.password_hash if user else DUMMY_HASH, body.password)
    except VerificationError:
        raise Problem(401, 'INVALID_CREDENTIALS', '邮箱或密码错误') from None
    if not user:
        raise Problem(401, 'INVALID_CREDENTIALS', '邮箱或密码错误')
    if user.status != 'ACTIVE':
        raise Problem(403, 'ACCOUNT_DISABLED', '账户已禁用')
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(body.password)
    record, replay = claim(db, request, body.model_dump(by_alias=True), anonymous_hash=auth_scope(request, body.email))
    if replay:
        active = db.get(Session, record.response_json.get('_jwtSessionId', ''))
        if (active is None or active.user_id != user.id or active.revoked_at is not None
                or active.expires_at <= now()):
            raise Problem(409, 'SESSION_REAUTH_REQUIRED', '此登录已失效，请使用新请求编号重新登录')
        return response(request, login_json(request, user, active), record.http_status)
    previous = optional_session(request, db)
    if previous:
        previous.revoked_at = now()
    identifier = str(uuid4())
    session = Session(id=identifier, user_id=user.id, token_hash=sha(identifier),
                      csrf_hash=b'\0' * 32,  # Legacy NOT NULL column, no longer used.
                      expires_at=now() + timedelta(days=ACCESS_LIFETIME_DAYS))
    db.add(session)
    db.flush()
    data = login_json(request, user, session)
    complete(record, 201, {'user': data['user'], 'expiresAt': data['expiresAt'], '_jwtSessionId': session.id})
    audit(db, user.id, 'LOGIN', 'USER', user.id, request.state.request_id)
    return response(request, data, 201)


def login_json(request, user, session):
    return dict(user=user_json(user), expiresAt=stamp(session.expires_at), tokenType='Bearer',
                accessToken=issue_access_token(request.app.state.settings, session))


@router.delete('/auth/session', status_code=204, dependencies=[Depends(verify_bearer)])
def logout(request: Request, user: CurrentUser, db: DB):
    request.state.session.revoked_at = now()
    audit(db, user.id, 'LOGOUT', 'USER', user.id, request.state.request_id)
    return Response(status_code=204)


@router.get('/me', response_model=s.Envelope[s.UserOut])
def me(request: Request, user: CurrentUser):
    return response(request, user_json(user))


@router.patch('/me', response_model=s.Envelope[s.UserOut], dependencies=[Depends(verify_bearer)])
def patch_me(body: s.MePatch, request: Request, user: CurrentUser, db: DB):
    from .services import owned, replay_record
    from .models import File
    record, replay = claim(db, request, body.model_dump(by_alias=True, exclude_unset=True), user_id=user.id)
    if replay:
        return replay_record(db, request, record, user.id)
    if 'username' in body.model_fields_set:
        user.username = body.username
    if 'avatar_file_id' in body.model_fields_set:
        if body.avatar_file_id:
            file = owned(db, File, body.avatar_file_id, user.id, lock=True)
            if file.status != 'READY' or file.purpose != 'AVATAR':
                invalid('头像文件用途或状态不合法', '/avatarFileId')
        user.avatar_file_id = body.avatar_file_id
    db.flush()
    data = user_json(user)
    complete(record, 200, data, 'USER', user.id)
    audit(db, user.id, 'UPDATE', 'USER', user.id, request.state.request_id)
    return response(request, data)
