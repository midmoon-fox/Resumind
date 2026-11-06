"""FastAPI adapter. All A/C dependencies are explicit and mandatory."""
from dataclasses import dataclass
from typing import Callable, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Request, Response, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.exceptions import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select

from .documents import require, uuid4 as check_uuid
from .models import Preparation, Resume, ResumeVersion, Template
from .richtext import ContentError
from .service import ResourceNotFound, ResumeService, RevisionConflict, StateConflict
from .templates import get_template
from .schemas import Document, Style, Envelope, Page, ResumeOutput, VersionOutput
from .schemas import Accepted, DeletionImpact, Download, ErrorOutput, ExportFormat, ExportOutput, PreparationContent, PreparationExportOutput, PreparationOutput, PreflightOutput, TemplateList
from .preflight import preflight, PreflightUnavailable
from .exports import ExportNotReady, PreflightFailed


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @model_validator(mode="after")
    def reject_explicit_null(self):
        for key in self.model_fields_set:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null when supplied")
        return self


class CreateResume(Input):
    workspaceId: str | None = None
    baseWorkspaceRevision: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=1, max_length=200)
    templateId: str
    templateVersion: str
    document: Document
    style: Style


class PatchResume(Input):
    baseRevision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    document: Document | None = None
    style: Style | None = None
    templateId: str | None = None
    templateVersion: str | None = None


class CopyResume(Input):
    versionId: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)


class Snapshot(Input):
    baseRevision: int = Field(ge=1)
    label: str | None = Field(default=None, max_length=100)


class Restore(Input):
    baseRevision: int = Field(ge=1)
    versionId: str


class Preflight(Input):
    baseRevision: int = Field(ge=1)
    format: ExportFormat


class ExportRequest(Input):
    resumeId: str
    baseRevision: int = Field(ge=1)
    format: ExportFormat
    fileName: str | None = Field(default=None, max_length=150)


class PatchPreparation(Input):
    baseRevision: int = Field(ge=1)
    content: PreparationContent


class PreparationExportRequest(Input):
    baseRevision: int = Field(ge=1)
    format: Literal["PDF", "DOCX"]
    fileName: str | None = Field(default=None, max_length=150)


@dataclass(frozen=True)
class Dependencies:
    # context is a FastAPI dependency yielding (SQLAlchemy Session, authenticated userId).
    context: Callable
    verify_write: Callable  # dependency validates CSRF and Origin, must raise on failure
    execute_write: Callable  # (session,user,operation,key,payload,action) -> replayable data
    check_references: Callable
    generation_complete: Callable
    generation_status: Callable
    resolve_workspace_snapshot: Callable  # (session,user,workspaceId,baseWorkspaceRevision) -> JD snapshot
    inspect_layout: Callable  # (fixed snapshot, format) -> {completed:bool,issues:list}; bounded rendering
    authenticated_user: Callable  # independent authentication dependency; closes its read transaction
    exports: object  # ExportCoordinator with its own short-lived transactions
    preparations: Callable  # (Session) -> PreparationService
    preparation_exports: object  # PreparationExportCoordinator
    deletion: Callable  # Session -> DeletionService with A/C cleanup/count callbacks
    templates: Callable  # Session -> TemplateService reading actual published definitions


def timestamp(value):
    return value.isoformat(timespec="microseconds") + "Z"


def resume_json(resume, status):
    return {"id": resume.id, "workspaceId": resume.workspace_id, "title": resume.title, "revision": resume.revision,
            "generationTaskId": resume.generation_task_id, "generationStatus": status,
            "document": resume.document_json, "style": resume.style_json,
            "templateId": resume.template_key, "templateVersion": resume.template_version,
            "jdSnapshot": resume.jd_snapshot_json, "createdAt": timestamp(resume.created_at), "updatedAt": timestamp(resume.updated_at)}


def version_json(version):
    return {"id": version.id, "resumeId": version.resume_id, "sourceRevision": version.source_revision,
            "label": version.label or f"版本 {version.source_revision}", "document": version.document_json,
            "style": version.style_json, "templateId": version.template_key, "templateVersion": version.template_version,
            "jdSnapshot": version.jd_snapshot_json, "reason": version.reason, "createdAt": timestamp(version.created_at)}


def create_router(deps: Dependencies):
    errors = {status: {"model": ErrorOutput} for status in (400, 401, 403, 404, 409, 422, 429, 500, 503)}
    def check_query(request: Request):
        path = request.scope["route"].path
        allowed = {"page", "pageSize"} if request.method == "GET" and path in {"/api/templates", "/api/resumes", "/api/resumes/{resumeId}/versions", "/api/preparations"} else set()
        if path == "/api/preparations" and request.method == "GET":
            allowed.add("resumeVersionId")
        if path == "/api/resumes/{resumeId}/preview" and request.method == "GET":
            allowed.update({"edit", "channel"})
        require(not set(request.query_params) - allowed, "/query", "unsupported query parameter")
        require(all(len(request.query_params.getlist(key)) == 1 for key in request.query_params), "/query", "duplicate query parameter")
    router = APIRouter(prefix="/api", responses=errors, dependencies=[Depends(check_query)])

    def service(context):
        return ResumeService(context[0], check_references=deps.check_references, generation_complete=deps.generation_complete)

    def render(context, resume):
        status = deps.generation_status(context[0], context[1], resume.generation_task_id) if resume.generation_task_id else None
        return resume_json(resume, status)

    def envelope(request, data):
        return {"data": data, "requestId": request.state.request_id}

    def write(request, context, payload, action):
        key = request.headers.get("Idempotency-Key", "")
        require(8 <= len(key) <= 64 and key.isascii(), "/headers/Idempotency-Key", "expected 8..64 ASCII characters")
        operation = request.method + " " + request.url.path
        data = deps.execute_write(context[0], context[1], operation, key, payload, action)
        return envelope(request, data)

    def path_id(value):
        check_uuid(value, "/path/id")
        return value

    def pagination(request, allowed=()):
        require(not set(request.query_params) - {"page", "pageSize", *allowed}, "/query", "unsupported query parameter")
        page, size = request.query_params.get("page", "1"), request.query_params.get("pageSize", "20")
        require(page.isascii() and page.isdecimal() and size.isascii() and size.isdecimal(), "/query", "expected integer pagination")
        page, size = int(page), int(size)
        require(page >= 1 and 1 <= size <= 20, "/query", "invalid pagination range")
        return page, size

    @router.get("/templates", response_model=Envelope[TemplateList])
    def templates(request: Request, context=Depends(deps.context, scope="function")):
        page, size = pagination(request)
        items = deps.templates(context[0]).list(page=page, page_size=size)
        total = context[0].scalar(select(func.count()).select_from(Template).where(Template.status == 'ACTIVE'))
        return envelope(request, {"items": items, "page": page, "pageSize": size, "total": total})

    @router.post("/resumes", status_code=201, dependencies=[Depends(deps.verify_write)], response_model=Envelope[ResumeOutput], response_model_exclude_unset=True)
    def create(request: Request, body: CreateResume, context=Depends(deps.context, scope="function")):
        def action():
            require((body.workspaceId is None) == (body.baseWorkspaceRevision is None), "/baseWorkspaceRevision", "workspace and revision must be provided together")
            if body.workspaceId is not None:
                path_id(body.workspaceId)
            snapshot = deps.resolve_workspace_snapshot(context[0], context[1], body.workspaceId, body.baseWorkspaceRevision)
            result = service(context).create(context[1], title=body.title, document=body.document.model_dump(exclude_unset=True), style=body.style.model_dump(), template_key=body.templateId, template_version=body.templateVersion, workspace_id=body.workspaceId, jd_snapshot=snapshot)
            return render(context, result)
        return write(request, context, body.model_dump(exclude_unset=True), action)

    @router.get("/resumes", response_model=Envelope[Page[ResumeOutput]], response_model_exclude_unset=True)
    def listing(request: Request, context=Depends(deps.context, scope="function")):
        page, size = pagination(request)
        items = service(context).list(context[1], page=page, page_size=size)
        total = context[0].scalar(select(func.count()).select_from(Resume).where(Resume.user_id == context[1], Resume.deleted_at.is_(None)))
        return envelope(request, {"items": [render(context, item) for item in items], "page": page, "pageSize": size, "total": total})

    @router.get("/resumes/{resumeId}", response_model=Envelope[ResumeOutput], response_model_exclude_unset=True)
    def detail(resumeId: str, request: Request, context=Depends(deps.context, scope="function")):
        return envelope(request, render(context, service(context).get(context[1], path_id(resumeId))))

    @router.get("/resumes/{resumeId}/preview", response_class=Response,
                responses={200: {"description": "HTML 预览", "content": {"text/html": {"schema": {"type": "string"}}}}},
                summary="预览简历（与 HTML/PDF 导出共用模板）")
    def preview(resumeId: str, request: Request, edit: Literal["0", "1"] = "0", channel: str = Query(default="", max_length=64, pattern=r"^[A-Za-z0-9_-]*$"), context=Depends(deps.context, scope="function")):
        from .local_templates import StaticHtmlRenderer
        resume = service(context).get(context[1], path_id(resumeId))
        deps.templates(context[0]).definition(resume.template_key, resume.template_version, allow_retired=True)
        snapshot = {"document": resume.document_json, "style": resume.style_json,
                    "templateId": resume.template_key, "templateVersion": resume.template_version}
        # ?edit=1 提供编辑器定位与桥接
        editable = request.query_params.get("edit") == "1"
        if editable:
            channel = request.query_params.get("channel", "")
            require(8 <= len(channel) <= 64 and channel.isascii(), "/query", "invalid preview channel")
            data = StaticHtmlRenderer().render_editable(snapshot, resume.id, resume.revision, channel)
        else:
            data = StaticHtmlRenderer().render(snapshot)
        return HTMLResponse(data, headers={"X-Frame-Options": "SAMEORIGIN", "Cache-Control": "no-store",
                            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'"})

    @router.patch("/resumes/{resumeId}", dependencies=[Depends(deps.verify_write)], response_model=Envelope[ResumeOutput], response_model_exclude_unset=True)
    def patch(resumeId: str, request: Request, body: PatchResume, context=Depends(deps.context, scope="function")):
        path_id(resumeId)
        def action():
            svc = service(context)
            current = svc.get(context[1], resumeId, lock=True)
            if current.revision != body.baseRevision:
                raise ApiError(409, "REVISION_CONFLICT", "内容已更新，请核对后再保存", {"currentRevision": current.revision})
            return render(context, svc.patch(context[1], resumeId, body.baseRevision, body.model_dump(exclude_unset=True, exclude={"baseRevision"})))
        return write(request, context, body.model_dump(exclude_unset=True), action)

    @router.delete("/resumes/{resumeId}", status_code=204, dependencies=[Depends(deps.verify_write)])
    def delete(resumeId: str, request: Request, context=Depends(deps.context, scope="function")):
        path_id(resumeId)
        write(request, context, {}, lambda: deps.deletion(context[0]).delete(context[1], resumeId))
        return Response(status_code=204)

    @router.post("/resumes/{resumeId}/copies", status_code=201, dependencies=[Depends(deps.verify_write)], response_model=Envelope[ResumeOutput], response_model_exclude_unset=True)
    def copy(resumeId: str, request: Request, body: CopyResume, context=Depends(deps.context, scope="function")):
        path_id(resumeId)
        if body.versionId:
            path_id(body.versionId)
        def action():
            svc = service(context)
            current = svc.get(context[1], resumeId)
            return render(context, svc.copy(context[1], resumeId, title=body.title or current.title, version_id=body.versionId))
        return write(request, context, body.model_dump(exclude_unset=True), action)

    @router.post("/resumes/{resumeId}/versions", status_code=201, dependencies=[Depends(deps.verify_write)], response_model=Envelope[VersionOutput], response_model_exclude_unset=True)
    def snapshot(resumeId: str, request: Request, body: Snapshot, context=Depends(deps.context, scope="function")):
        path_id(resumeId)
        return write(request, context, body.model_dump(exclude_unset=True), lambda: version_json(service(context).snapshot(context[1], resumeId, body.baseRevision, label=body.label)))

    @router.get("/resumes/{resumeId}/versions", response_model=Envelope[Page[VersionOutput]], response_model_exclude_unset=True)
    def versions(resumeId: str, request: Request, context=Depends(deps.context, scope="function")):
        path_id(resumeId)
        page, size = pagination(request)
        items = service(context).versions(context[1], resumeId, page=page, page_size=size)
        total = context[0].scalar(select(func.count()).select_from(ResumeVersion).where(ResumeVersion.user_id == context[1], ResumeVersion.resume_id == resumeId))
        return envelope(request, {"items": [version_json(item) for item in items], "page": page, "pageSize": size, "total": total})

    @router.get("/resumes/{resumeId}/versions/{versionId}", response_model=Envelope[VersionOutput], response_model_exclude_unset=True)
    def version(resumeId: str, versionId: str, request: Request, context=Depends(deps.context, scope="function")):
        return envelope(request, version_json(service(context).version(context[1], path_id(resumeId), path_id(versionId))))

    @router.post("/resumes/{resumeId}/restorations", dependencies=[Depends(deps.verify_write)], response_model=Envelope[ResumeOutput], response_model_exclude_unset=True)
    def restore(resumeId: str, request: Request, body: Restore, context=Depends(deps.context, scope="function")):
        path_id(resumeId)
        path_id(body.versionId)
        return write(request, context, body.model_dump(), lambda: render(context, service(context).restore(context[1], resumeId, body.versionId, body.baseRevision)))

    @router.post("/resumes/{resumeId}/preflights", dependencies=[Depends(deps.verify_write)], response_model=Envelope[PreflightOutput])
    def check_export(resumeId: str, request: Request, body: Preflight, user=Depends(deps.authenticated_user)):
        return envelope(request, deps.exports.preflight(user, path_id(resumeId), body.baseRevision, body.format))

    @router.post("/exports", status_code=202, dependencies=[Depends(deps.verify_write)], response_model=Envelope[Accepted])
    def export(request: Request, body: ExportRequest, user=Depends(deps.authenticated_user)):
        return envelope(request, deps.exports.accept(user, body.model_dump(exclude_unset=True), request.headers.get("Idempotency-Key", "")))

    @router.get("/exports/{exportId}", response_model=Envelope[ExportOutput], response_model_exclude_unset=True)
    def export_detail(exportId: str, request: Request, user=Depends(deps.authenticated_user)):
        return envelope(request, deps.exports.detail(user, path_id(exportId)))

    @router.get("/exports/{exportId}/download", response_model=Envelope[Download])
    def export_download(exportId: str, request: Request, user=Depends(deps.authenticated_user)):
        return envelope(request, deps.exports.download(user, path_id(exportId)))

    def preparation_json(context, record):
        return {"id": record.id, "taskId": record.task_id, "resumeVersionId": record.resume_version_id, "type": record.type,
                "revision": record.revision, "status": record.status, "content": record.content_json,
                "isOutdated": deps.preparations(context[0]).outdated(context[1], record), "createdAt": timestamp(record.created_at), "updatedAt": timestamp(record.updated_at)}

    @router.get("/preparations", response_model=Envelope[Page[PreparationOutput]])
    def preparations(request: Request, context=Depends(deps.context, scope="function")):
        versionId = request.query_params.get("resumeVersionId", "")
        path_id(versionId)
        page, size = pagination(request, {"resumeVersionId"})
        records = deps.preparations(context[0]).list(context[1], versionId, page=page, page_size=size)
        total = context[0].scalar(select(func.count()).select_from(Preparation).where(Preparation.user_id == context[1], Preparation.resume_version_id == versionId))
        return envelope(request, {"items": [preparation_json(context, item) for item in records], "page": page, "pageSize": size, "total": total})

    @router.get("/preparations/{preparationId}", response_model=Envelope[PreparationOutput])
    def preparation(preparationId: str, request: Request, context=Depends(deps.context, scope="function")):
        return envelope(request, preparation_json(context, deps.preparations(context[0]).get(context[1], path_id(preparationId))))

    @router.patch("/preparations/{preparationId}", dependencies=[Depends(deps.verify_write)], response_model=Envelope[PreparationOutput])
    def edit_preparation(preparationId: str, request: Request, body: PatchPreparation, context=Depends(deps.context, scope="function")):
        path_id(preparationId)
        return write(request, context, body.model_dump(), lambda: preparation_json(context, deps.preparations(context[0]).patch(context[1], preparationId, body.baseRevision, body.content.model_dump())))

    @router.post("/preparations/{preparationId}/exports", status_code=202, dependencies=[Depends(deps.verify_write)], response_model=Envelope[Accepted])
    def export_preparation(preparationId: str, request: Request, body: PreparationExportRequest, user=Depends(deps.authenticated_user)):
        return envelope(request, deps.preparation_exports.accept(user, path_id(preparationId), body.model_dump(exclude_unset=True), request.headers.get("Idempotency-Key", "")))

    @router.get("/preparation-exports/{exportId}", response_model=Envelope[PreparationExportOutput], response_model_exclude_unset=True)
    def preparation_export_detail(exportId: str, request: Request, user=Depends(deps.authenticated_user)):
        return envelope(request, deps.preparation_exports.detail(user, path_id(exportId)))

    @router.get("/preparation-exports/{exportId}/download", response_model=Envelope[Download])
    def preparation_export_download(exportId: str, request: Request, user=Depends(deps.authenticated_user)):
        return envelope(request, deps.preparation_exports.download(user, path_id(exportId)))

    @router.get("/resumes/{resumeId}/deletion-impact", response_model=Envelope[DeletionImpact])
    def deletion_impact(resumeId: str, request: Request, context=Depends(deps.context, scope="function")):
        return envelope(request, deps.deletion(context[0]).impact(context[1], path_id(resumeId)))

    for route in router.routes:
        parameters = []
        if "GET" in route.methods and route.path in {"/api/templates", "/api/resumes", "/api/resumes/{resumeId}/versions", "/api/preparations"}:
            parameters.extend([
                {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1, "default": 1}},
                {"name": "pageSize", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 20, "default": 20}},
            ])
        if "GET" in route.methods and route.path == "/api/preparations":
            parameters.append({"name": "resumeVersionId", "in": "query", "required": True, "schema": {"type": "string", "format": "uuid"}})
        if route.methods & {"POST", "PATCH", "DELETE"}:
            parameters.extend([
                {"name": "X-CSRF-Token", "in": "header", "required": True, "schema": {"type": "string"}},
                {"name": "Origin", "in": "header", "required": True, "schema": {"type": "string"}},
            ])
            if not route.path.endswith("/preflights"):
                parameters.append({"name": "Idempotency-Key", "in": "header", "required": True, "schema": {"type": "string", "minLength": 8, "maxLength": 64}})
        route.openapi_extra = {"security": [{"SessionAuth": []}], "parameters": parameters}
    return router


class ApiError(Exception):
    def __init__(self, status, code, message, details=None, headers=None):
        self.status, self.code, self.message, self.details = status, code, message, details or {}
        self.headers = headers or {}


def install_api(app: FastAPI, deps: Dependencies):
    """Standalone composition helper; A may reuse handlers in its shared application."""
    @app.middleware("http")
    async def headers(request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Contract-Version"] = "1.1.0"
        return response

    def error_response(request, status, code, message, details=None, headers=None):
        response_headers = {"X-Contract-Version": "1.1.0"}
        retry_after = (headers or {}).get("Retry-After") or (headers or {}).get("retry-after")
        if status == 429 and isinstance(retry_after, str) and retry_after.isascii() and retry_after.isdecimal():
            response_headers["Retry-After"] = retry_after
        return JSONResponse(status_code=status, headers=response_headers, content={"error": {"code": code, "message": message, "details": details or {}}, "requestId": getattr(request.state, "request_id", str(uuid4()))})

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        codes = {400: "BAD_REQUEST", 401: "UNAUTHENTICATED", 403: "CSRF_INVALID", 404: "NOT_FOUND", 405: "BAD_REQUEST", 429: "RATE_LIMITED", 503: "SOURCE_UNAVAILABLE"}
        return error_response(request, error.status_code, codes.get(error.status_code, "BAD_REQUEST"), "请求未能完成", headers=error.headers)

    @app.exception_handler(Exception)
    async def internal_error(request, error):
        return error_response(request, 500, "INTERNAL_ERROR", "服务暂时无法完成请求")

    @app.exception_handler(ApiError)
    async def api_error(request, error):
        return error_response(request, error.status, error.code, error.message, error.details, error.headers)

    @app.exception_handler(ContentError)
    async def content_error(request, error):
        return error_response(request, 422, "VALIDATION_ERROR", "输入字段不合法", {"errors": [{"path": error.path, "message": str(error)}]})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        errors = error.errors()
        invalid_json = any(item["type"] == "json_invalid" for item in errors)
        details = {"errors": [{"path": "/" + "/".join(str(part) for part in item["loc"] if part != "body"), "message": item["msg"]} for item in errors]}
        return error_response(request, 400 if invalid_json else 422, "BAD_REQUEST" if invalid_json else "VALIDATION_ERROR", "请求格式不合法", details)

    @app.exception_handler(PreflightFailed)
    async def preflight_failed(request, error):
        return error_response(request, 422, "PREFLIGHT_FAILED", "请先修正导出问题", {"issues": error.issues})

    for exception, status, code, message in (
        (ResourceNotFound, 404, "NOT_FOUND", "资源不存在"),
        (RevisionConflict, 409, "REVISION_CONFLICT", "内容已更新，请核对后再保存"),
        (StateConflict, 409, "STATE_CONFLICT", "当前状态不允许该操作"),
        (PreflightUnavailable, 503, "SOURCE_UNAVAILABLE", "导出试渲染未完成，请重试"),
        (ExportNotReady, 409, "NOT_READY", "导出文件尚未就绪"),
    ):
        def handler(request, error, status=status, code=code, message=message):
            details = {"currentRevision": error.current_revision} if isinstance(error, RevisionConflict) and error.current_revision is not None else {}
            return error_response(request, status, code, message, details)
        app.add_exception_handler(exception, handler)
    app.include_router(create_router(deps))
    original_openapi = app.openapi
    def contract_openapi():
        schema = original_openapi()
        schema.setdefault("components", {}).setdefault("securitySchemes", {}).setdefault("SessionAuth", {"type": "apiKey", "in": "cookie", "name": "__Host-session"})
        return schema
    app.openapi = contract_openapi
