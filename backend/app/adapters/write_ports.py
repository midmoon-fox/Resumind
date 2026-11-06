"""A 拥有的公共写入能力，供 C/B 复用：幂等认领、事务边界与 Bearer JWT 鉴权。

合并方案 F10：唯一 requestId/错误映射与提交边界；A 的幂等表是唯一实现，
B 的 execute_write 与 C 的 IdempotencyPort 都落到同一张 idempotency_records。
"""
import hmac
import json

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import Problem
from app.models import Idempotency
from app.modules.tasks.lifecycle import TaskOperationError
from app.modules.tasks.ports import StoredResponse, WritePorts


def _valid_key(key) -> bool:
    return (
        isinstance(key, str)
        and 8 <= len(key) <= 64
        and key.isascii()
        and all(32 <= ord(c) <= 126 for c in key)
    )


class IdempotencyService:
    """共享幂等服务：A/B/C 各自持有实例，使用同一个 settings.secret 与同一张表。"""

    def __init__(self, secret: str):
        self.secret = secret

    def _digest(self, payload) -> bytes:
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        return hmac.digest(self.secret.encode(), canonical, "sha256")

    def begin(self, session: Session, *, user_id: str, operation: str, key: str, request: dict) -> StoredResponse | None:
        if not _valid_key(key):
            raise TaskOperationError(
                "VALIDATION_ERROR", "幂等键需要8至64个ASCII字符", 422,
                {"errors": [{"path": "/headers/Idempotency-Key", "message": "幂等键需要8至64个ASCII字符"}]},
            )
        digest = self._digest(request)
        record = Idempotency(
            user_id=user_id, operation_key=operation, client_key=key, request_sha256=digest
        )
        try:
            with session.begin_nested():
                session.add(record)
                session.flush()
            return None  # 新意图，已以 IN_PROGRESS 原子认领
        except IntegrityError:
            query = (
                select(Idempotency)
                .filter_by(user_id=user_id, operation_key=operation, client_key=key)
                .with_for_update()
            )
            old = session.scalar(query)
            if old is None:
                raise TaskOperationError("REQUEST_IN_PROGRESS", "请求仍在提交，请稍后重试", 409)
            if not hmac.compare_digest(old.request_sha256, digest):
                raise TaskOperationError("IDEMPOTENCY_MISMATCH", "相同幂等键对应的参数不同", 409)
            if old.state != "COMPLETED":
                raise TaskOperationError("REQUEST_IN_PROGRESS", "请求仍在提交，请稍后重试", 409)
            return StoredResponse(old.http_status, old.response_json)

    def complete(
        self,
        session: Session,
        *,
        user_id: str,
        operation: str,
        key: str,
        response: StoredResponse,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        record = session.scalar(
            select(Idempotency)
            .filter_by(user_id=user_id, operation_key=operation, client_key=key, state="IN_PROGRESS")
            .with_for_update()
        )
        if record is None:
            raise RuntimeError("幂等记录缺失")
        record.state, record.http_status, record.response_json = "COMPLETED", response.status, response.body
        if resource_type is not None:
            record.resource_type, record.resource_id = resource_type, resource_id
        session.flush()


class IdempotencyPortAdapter:
    """实现 C 的 IdempotencyPort Protocol。"""

    def __init__(self, service: IdempotencyService):
        self.service = service

    def begin(self, session, *, user_id, operation, key, request):
        return self.service.begin(session, user_id=user_id, operation=operation, key=key, request=request)

    def complete(self, session, *, user_id, operation, key, response):
        self.service.complete(session, user_id=user_id, operation=operation, key=key, response=response)


def make_write_ports(service: IdempotencyService, csrf_dependency) -> WritePorts:
    return WritePorts(
        csrf_dependency=csrf_dependency,
        transaction=lambda session: session.begin(),
        idempotency=IdempotencyPortAdapter(service),
    )


def authenticate_user_id(request) -> str:
    """独立只读鉴权：读完即关闭事务，返回当前用户 UUID 字符串。"""
    from app.auth import current_user

    with request.app.state.sessions() as db:
        return current_user(request, db).id


def verify_write(request: Request) -> None:
    """Validate Bearer JWT and its revocation record in a short-lived DB session."""
    from app.auth import verify_bearer

    with request.app.state.sessions() as db:
        verify_bearer(request, db)


def session_dependency(request: Request):
    """供 C/B 路由使用的裸 Session（无活动事务）；事务由 WritePorts.transaction 或 B 的 unit_of_work 负责。"""
    with request.app.state.sessions() as session:
        yield session


def user_id_dependency(request: Request):
    return authenticate_user_id(request)


def request_id_dependency(request: Request):
    return request.state.request_id
