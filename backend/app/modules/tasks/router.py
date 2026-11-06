"""Interface 66, composed into A's app with A's session and auth dependencies."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .ports import WritePorts
from .registry import Registry, ResourceUnavailable
from .schemas import TaskResponse
from .service import get_task
from .write_router import CONTRACT_ERRORS, ContractRoute, create_write_router


def create_router(
    registry: Registry,
    *,
    session_dependency: Callable,
    user_dependency: Callable,
    request_id_dependency: Callable,
    write_ports: WritePorts | None = None,
) -> APIRouter:
    """user_dependency returns A-verified user UUID; never trust a user header/body."""
    router = APIRouter(route_class=ContractRoute, responses=CONTRACT_ERRORS)

    @router.get(
        "/api/tasks/{taskId}", response_model=TaskResponse, response_model_exclude_none=False
    )
    def read_task(
        taskId: str,
        request: Request,
        session: Annotated[Session, Depends(session_dependency)],
        user_id: Annotated[str, Depends(user_dependency)],
        request_id: Annotated[str, Depends(request_id_dependency)],
    ):
        headers = {"X-Contract-Version": "1.1.0"}
        if request.query_params:
            return JSONResponse(
                status_code=422,
                headers=headers,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "字段校验失败",
                        "details": {"errors": [{"path": "/query", "message": "不接受查询参数"}]},
                    },
                    "requestId": request_id,
                },
            )
        try:
            parsed = UUID(taskId)
            if parsed.version != 4 or str(parsed) != taskId:
                raise ValueError()
        except ValueError:
            return JSONResponse(
                status_code=422,
                headers=headers,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "字段校验失败",
                        "details": {"errors": [{"path": "/taskId", "message": "需要UUID v4"}]},
                    },
                    "requestId": request_id,
                },
            )
        try:
            data = get_task(session, registry, taskId, user_id)
        except ResourceUnavailable:
            return JSONResponse(
                status_code=404,
                headers=headers,
                content={
                    "error": {"code": "NOT_FOUND", "message": "资源不存在", "details": {}},
                    "requestId": request_id,
                },
            )
        response = TaskResponse(data=data, requestId=request_id)
        return JSONResponse(
            content=response.model_dump(mode="json", exclude_none=False), headers=headers
        )

    router.include_router(
        create_write_router(
            registry,
            session_dependency=session_dependency,
            user_dependency=user_dependency,
            request_id_dependency=request_id_dependency,
            ports=write_ports,
        )
    )
    return router


def request_id() -> str:
    """Optional request ID generator; A may instead inject its middleware request ID."""
    return str(uuid4())
