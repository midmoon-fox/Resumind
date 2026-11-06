"""Sixteen C business routes plus the existing three task routes, all dependency injected."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.modules.c_core import schemas
from app.modules.c_core.service import accepted
from app.modules.c_core.validation import invalid
from app.modules.c_core.views import Envelope, FollowupView, RunView, SuggestionView
from app.modules.followups import service as followups
from app.modules.tasks.lifecycle import TaskOperationError
from app.modules.tasks.models import Task
from app.modules.tasks.ports import StoredResponse
from app.modules.tasks.registry import ResourceUnavailable
from app.modules.tasks.router import create_router as create_task_router
from app.modules.tasks.schemas import AsyncAccepted, ResourceId
from app.modules.tasks.write_router import CONTRACT_ERRORS, ContractRoute


def create_router(
    services,
    *,
    registry,
    session_dependency,
    user_dependency,
    request_id_dependency,
    write_ports,
    resume_schema: type[BaseModel],
    suggestion_value_schema,
):
    router = APIRouter(route_class=ContractRoute, responses=CONTRACT_ERRORS)

    def disabled():
        raise TaskOperationError("FEATURE_DISABLED", "A/B 公共服务尚未接入", 503)

    guard = (
        write_ports.csrf_dependency
        if write_ports is not None and services is not None
        else disabled
    )

    def identifier(request):
        if request.query_params:
            invalid("/query", "不接受查询参数")
        values = list(request.path_params.values())
        if not values:
            return None
        value = values[0]
        try:
            TypeAdapter(ResourceId).validate_python(value)
        except ValidationError:
            invalid("/" + next(iter(request.path_params)), "需要UUID v4")
        return value

    def access(db, user, op, value, response=None):
        # Replays recheck live parents, including the resource created by the original request.
        if op in {"answer", "confirm", "skip", "next", "complete", "get_followup"}:
            followups.owned(db, services.a, user, value)
        elif op in {"apply", "reject", "get_suggestion"}:
            services.suggestion(db, user, value)
        elif op == "suggest":
            services.b.resume(db, user, value, False)
        elif op in {"save_job"}:
            services.job(db, user, value)
        if response:
            data = response.body["data"]
            resource_type = data.get("resourceType")
            if resource_type == "FOLLOWUP_SESSION":
                followups.owned(db, services.a, user, data["resourceId"])
            elif resource_type == "RESUME":
                services.b.resume(db, user, data["resourceId"], False)
            elif resource_type == "SUGGESTION":
                services.suggestion(db, user, data["resourceId"])
            elif resource_type == "RECOMMENDATION_RUN":
                services.run(db, user, data["resourceId"])
            elif resource_type == "PREPARATION":
                task = db.get(Task, data["taskId"])
                if task is None or task.user_id != user:
                    raise ResourceUnavailable()
                from app.modules.tasks.service import snapshot

                services.b.check_task(db, snapshot(task), False)
            elif resource_type == "JD_VERSION":
                services.a.jd_access(db, user, data["resourceId"])

    def invoke(db, user, op, value, payload):
        operations = {
            "create_followup": lambda: followups.create(db, registry, services.a, user, payload),
            "answer": lambda: followups.answer(db, registry, services.a, user, value, payload),
            "confirm": lambda: followups.confirm(db, services.a, user, value, payload),
            "skip": lambda: followups.skip(db, services.a, user, value, payload),
            "next": lambda: followups.next_question(db, registry, services.a, user, value, payload),
            "complete": lambda: followups.complete(db, services.a, user, value, payload),
            "generate": lambda: services.create_generation(db, user, payload),
            "suggest": lambda: services.create_suggestion(db, user, value, payload),
            "apply": lambda: services.apply(db, user, value, payload),
            "reject": lambda: services.reject(db, user, value),
            "prepare": lambda: services.create_preparation(db, user, payload),
            "recommend": lambda: services.create_recommendation(db, user, payload),
            "save_job": lambda: services.save_job(db, user, value, payload),
        }
        result = operations[op]()
        return accepted(result) if isinstance(result, Task) else result

    def perform(request, db, user, request_id, key, op, payload, output, status):
        if services is None or write_ports is None:
            disabled()
        value = identifier(request)
        if key is None or not 8 <= len(key) <= 64 or not key.isascii():
            invalid("/headers/Idempotency-Key", "幂等键需要8至64个ASCII字符")
        operation = "POST " + request.url.path
        with write_ports.transaction(db):
            replay = write_ports.idempotency.begin(
                db,
                user_id=user,
                operation=operation,
                key=key,
                request=payload.model_dump(mode="json") if payload is not None else {},
            )
            access(db, user, op, value, replay)
            if replay is not None:
                response = replay
            else:
                data = invoke(db, user, op, value, payload)
                body = (
                    Envelope[output]
                    .model_validate_json(json.dumps({"data": data, "requestId": request_id}))
                    .model_dump(mode="json", exclude_none=False)
                )
                response = StoredResponse(status, body)
                write_ports.idempotency.complete(
                    db, user_id=user, operation=operation, key=key, response=response
                )
        return JSONResponse(
            content=response.body,
            status_code=response.status,
            headers={"X-Contract-Version": "1.1.0"},
        )

    def parameters(path):
        import re

        return [
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": {"type": "string", "format": "uuid"},
            }
            for name in re.findall(r"{([^}]+)}", path)
        ]

    def post(path, schema, op, output, status=200):
        if schema is None:

            async def endpoint(
                request: Request,
                db: Annotated[Session, Depends(session_dependency)],
                user: Annotated[str, Depends(user_dependency)],
                request_id: Annotated[str, Depends(request_id_dependency)],
                security: Annotated[None, Depends(guard)],
                key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
            ):
                request.state.request_id = request_id
                if await request.body():
                    invalid("/body", "本接口不接受请求体")
                return perform(request, db, user, request_id, key, op, None, output, status)
        else:

            async def endpoint(
                request: Request,
                payload: schema,
                db: Annotated[Session, Depends(session_dependency)],
                user: Annotated[str, Depends(user_dependency)],
                request_id: Annotated[str, Depends(request_id_dependency)],
                security: Annotated[None, Depends(guard)],
                key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
            ):
                request.state.request_id = request_id
                return perform(request, db, user, request_id, key, op, payload, output, status)

        router.add_api_route(
            path,
            endpoint,
            methods=["POST"],
            status_code=status,
            response_model=Envelope[output],
            operation_id="c_" + op,
            openapi_extra={"parameters": parameters(path)},
        )

    def get(path, op, output):
        async def endpoint(
            request: Request,
            db: Annotated[Session, Depends(session_dependency)],
            user: Annotated[str, Depends(user_dependency)],
            request_id: Annotated[str, Depends(request_id_dependency)],
        ):
            request.state.request_id = request_id
            if services is None:
                disabled()
            value = identifier(request)
            if await request.body():
                invalid("/body", "读接口不接受请求体")
            if op == "get_followup":
                data = followups.view(db, followups.owned(db, services.a, user, value))
            elif op == "get_suggestion":
                data = services.suggestion_view(db, user, value)
            else:
                data = services.run_view(db, user, value)
            body = (
                Envelope[output]
                .model_validate_json(json.dumps({"data": data, "requestId": request_id}))
                .model_dump(mode="json")
            )
            return JSONResponse(content=body, headers={"X-Contract-Version": "1.1.0"})

        router.add_api_route(
            path,
            endpoint,
            methods=["GET"],
            response_model=Envelope[output],
            operation_id="c_" + op,
            openapi_extra={"parameters": parameters(path)},
        )

    post("/api/followup-sessions", schemas.CreateFollowup, "create_followup", AsyncAccepted, 202)
    get("/api/followup-sessions/{sessionId}", "get_followup", FollowupView)
    for suffix, schema, op, status in (
        ("answers", schemas.AnswerRequest, "answer", 202),
        ("answer-confirmations", schemas.ConfirmRequest, "confirm", 200),
        ("skips", schemas.TurnRequest, "skip", 200),
        ("next-questions", schemas.RevisionRequest, "next", 202),
        ("completions", schemas.CompleteRequest, "complete", 200),
    ):
        post(
            "/api/followup-sessions/{sessionId}/" + suffix,
            schema,
            op,
            AsyncAccepted if status == 202 else FollowupView,
            status,
        )
    post("/api/resume-generations", schemas.GenerateRequest, "generate", AsyncAccepted, 202)
    post(
        "/api/resumes/{resumeId}/suggestions", schemas.SuggestRequest, "suggest", AsyncAccepted, 202
    )
    get(
        "/api/suggestions/{suggestionId}", "get_suggestion", SuggestionView[suggestion_value_schema]
    )
    post(
        "/api/suggestions/{suggestionId}/applications",
        schemas.RevisionRequest,
        "apply",
        resume_schema,
    )
    post(
        "/api/suggestions/{suggestionId}/rejections",
        None,
        "reject",
        SuggestionView[suggestion_value_schema],
    )
    post("/api/preparations", schemas.PreparationRequest, "prepare", AsyncAccepted, 202)
    post("/api/recommendation-runs", schemas.RecommendRequest, "recommend", AsyncAccepted, 202)
    get("/api/recommendation-runs/{runId}", "get_run", RunView)
    post(
        "/api/recommended-jobs/{jobId}/job-descriptions",
        schemas.SaveJobRequest,
        "save_job",
        AsyncAccepted,
        202,
    )
    router.include_router(
        create_task_router(
            registry,
            session_dependency=session_dependency,
            user_dependency=user_dependency,
            request_id_dependency=request_id_dependency,
            write_ports=write_ports,
        )
    )
    return router
