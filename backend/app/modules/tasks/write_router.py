"""Interfaces 67/68: guarded, transactional and persistent-idempotency aware."""

import json
import logging
from collections.abc import Callable
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from .lifecycle import TaskOperationError, cancel_task, owned_task, retry_task
from .ports import StoredResponse, WritePorts
from .registry import Registry, ResourceUnavailable
from .schemas import AsyncAcceptedResponse, ErrorResponse, RetryRequest, TaskResponse
from .service import get_task, resource_ref
from app.core import Problem

CONTRACT_ERRORS = {
    status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 422, 429, 500, 503)
}


def error_response(status, code, request_id, message="操作失败", details=None):
    return JSONResponse(
        status_code=status,
        headers={"X-Contract-Version": "1.1.0"},
        content={
            "error": {"code": code, "message": message, "details": details or {}},
            "requestId": request_id,
        },
    )


def validation_path(location):
    parts = list(location[1:])
    if location[0] == "header":
        parts.insert(0, "headers")
    return "/" + "/".join(str(part) for part in parts)


class ContractRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                return await original(request)
            except RequestValidationError as error:
                malformed = any(item["type"] == "json_invalid" for item in error.errors())
                return error_response(
                    400 if malformed else 422,
                    "BAD_REQUEST" if malformed else "VALIDATION_ERROR",
                    getattr(request.state, "request_id", str(uuid4())),
                    "请求格式错误" if malformed else "字段校验失败",
                    {
                        "errors": [
                            {
                                "path": validation_path(item["loc"]),
                                "message": "字段不符合契约",
                            }
                            for item in error.errors()
                        ]
                    },
                )
            except Problem as error:
                response = error_response(error.status, error.code,
                    getattr(request.state, 'request_id', str(uuid4())), error.message, error.details)
                response.headers.update(error.headers)
                return response
            except TaskOperationError as error:
                return error_response(
                    error.status,
                    error.code,
                    getattr(request.state, "request_id", str(uuid4())),
                    error.message,
                    error.details,
                )
            except ResourceUnavailable:
                return error_response(
                    404,
                    "NOT_FOUND",
                    getattr(request.state, "request_id", str(uuid4())),
                    "资源不存在",
                )
            except HTTPException as error:
                code = {
                    400: "BAD_REQUEST",
                    401: "UNAUTHENTICATED",
                    403: "CSRF_INVALID",
                    404: "NOT_FOUND",
                    409: "STATE_CONFLICT",
                    422: "VALIDATION_ERROR",
                    429: "RATE_LIMITED",
                    503: "FEATURE_DISABLED",
                }.get(error.status_code, "INTERNAL_ERROR")
                response = error_response(
                    error.status_code,
                    code,
                    getattr(request.state, "request_id", str(uuid4())),
                    "请求未通过校验",
                )
                retry_after = (error.headers or {}).get("Retry-After", "")
                if error.status_code == 429 and retry_after.isascii() and retry_after.isdecimal():
                    response.headers["Retry-After"] = retry_after
                return response
            except Exception:
                logging.getLogger(__name__).exception('Request failed id=%s path=%s', getattr(request.state, 'request_id', 'unknown'), request.url.path)
                return error_response(
                    500,
                    "INTERNAL_ERROR",
                    getattr(request.state, "request_id", str(uuid4())),
                    "AI 帮助暂时无法完成，请重试；仍失败时请提供请求编号" if "/suggestions" in request.url.path else "请求处理失败",
                )

        return handle


def create_write_router(
    registry: Registry,
    *,
    session_dependency: Callable,
    user_dependency: Callable,
    request_id_dependency: Callable,
    ports: WritePorts | None,
) -> APIRouter:
    router = APIRouter(route_class=ContractRoute, responses=CONTRACT_ERRORS)

    def unavailable():
        raise TaskOperationError("FEATURE_DISABLED", "公共写入能力尚未接入", 503)

    def perform(session, user_id, request_id, task_id, key, action, payload):
        if ports is None:
            raise TaskOperationError("FEATURE_DISABLED", "公共写入能力尚未接入", 503)
        operation = f"POST /api/tasks/{task_id}/{action}"
        with ports.transaction(session):
            replay = ports.idempotency.begin(
                session, user_id=user_id, operation=operation, key=key, request=payload
            )
            # Recheck ownership/parents even when replaying a previously completed request.
            owned_task(session, registry, task_id, user_id)
            if replay is not None:
                response = replay
            else:
                if action == "retries":
                    task = retry_task(
                        session, registry, task_id, user_id, payload["expectedAttempt"]
                    )
                    ref = resource_ref(task)
                    data = {
                        "taskId": task.id,
                        "resourceType": ref.resourceType.value,
                        "resourceId": ref.resourceId,
                        "status": "QUEUED",
                        "statusUrl": f"/api/tasks/{task.id}",
                        "resourceUrl": ref.resourceUrl,
                    }
                    status = 202
                else:
                    cancel_task(session, registry, task_id, user_id)
                    data = get_task(session, registry, task_id, user_id).model_dump(mode="json")
                    status = 200
                response_type = AsyncAcceptedResponse if status == 202 else TaskResponse
                body = response_type.model_validate_json(
                    json.dumps({"data": data, "requestId": request_id})
                ).model_dump(mode="json")
                response = StoredResponse(status, body)
                ports.idempotency.complete(
                    session, user_id=user_id, operation=operation, key=key, response=response
                )
        # Transaction exit/commit happens before any successful response is sent.
        return JSONResponse(
            status_code=response.status,
            content=response.body,
            headers={"X-Contract-Version": "1.1.0"},
        )

    def invalid(path, message):
        raise TaskOperationError(
            "VALIDATION_ERROR", message, 422, {"errors": [{"path": path, "message": message}]}
        )

    def validate(request, task_id, key):
        if request.query_params:
            invalid("/query", "不接受查询参数")
        try:
            parsed = UUID(task_id)
            if parsed.version != 4 or str(parsed) != task_id:
                raise ValueError()
        except ValueError:
            invalid("/taskId", "需要UUID v4")
        if key is None or not 8 <= len(key) <= 64 or not key.isascii():
            invalid("/headers/Idempotency-Key", "幂等键需要8至64个ASCII字符")

    guard = ports.csrf_dependency if ports is not None else unavailable

    @router.post(
        "/api/tasks/{taskId}/retries", status_code=202, response_model=AsyncAcceptedResponse
    )
    def retry(
        taskId: str,
        payload: RetryRequest,
        request: Request,
        session: Annotated[Session, Depends(session_dependency)],
        user_id: Annotated[str, Depends(user_dependency)],
        request_id: Annotated[str, Depends(request_id_dependency)],
        security: Annotated[None, Depends(guard)],
        key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
    ):
        request.state.request_id = request_id
        try:
            validate(request, taskId, key)
            return perform(
                session, user_id, request_id, taskId, key, "retries", payload.model_dump()
            )
        except ResourceUnavailable:
            return error_response(404, "NOT_FOUND", request_id, "资源不存在")

    @router.post("/api/tasks/{taskId}/cancellations", response_model=TaskResponse)
    async def cancel(
        taskId: str,
        request: Request,
        session: Annotated[Session, Depends(session_dependency)],
        user_id: Annotated[str, Depends(user_dependency)],
        request_id: Annotated[str, Depends(request_id_dependency)],
        security: Annotated[None, Depends(guard)],
        key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
    ):
        from starlette.concurrency import run_in_threadpool

        request.state.request_id = request_id
        try:
            validate(request, taskId, key)
            if await request.body():
                invalid("/body", "取消接口不接受请求体")
            return await run_in_threadpool(
                perform, session, user_id, request_id, taskId, key, "cancellations", {}
            )
        except ResourceUnavailable:
            return error_response(404, "NOT_FOUND", request_id, "资源不存在")

    return router
