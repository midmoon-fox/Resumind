"""唯一装配入口：把 A（账户/资料）、B（文档/导出）、C（AI/任务）组装成单 FastAPI 应用。

- A 提供 JWT 鉴权/幂等/异常骨架与 33 条路由；
- B 的 resume_b 通过 TeamAdapters 注入，23 条操作（含模板预览）挂到同一应用；
- C 的 build() 注册 6 个 handler + 19 条路由，A/B 的 4 个 handler 注册到同一 Registry。
"""
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.adapters.a_ai import AAIAdapter
from app.adapters.a_services import AServicesAdapter
from app.adapters.a_tasks import ATaskPort
from app.adapters.b_services import BContext, BServicesAdapter, build_b_integration
from app.adapters.handlers import export_handler, jd_handler, material_handler
from app.adapters.write_ports import (
    IdempotencyService,
    make_write_ports,
    request_id_dependency,
    session_dependency,
    user_id_dependency,
    verify_write,
)
from app.auth import MissingRateLimiter, RedisRateLimiter, router as auth_router
from app.core import Problem, Settings, database, reject_unknown_query
from app.modules.ai.config import create_model_client, load_model_configuration
from app.modules.c_core.integration import build
from app.modules.tasks.registry import Registry
from app.modules.tasks.schemas import Kind
from app.modules.recommendations.config import JobSourceSettings


def _job_configuration(settings):
    configuration = JobSourceSettings.from_mapping(os.environ)
    cache = None
    if configuration.enable_live_calls:
        if not settings.redis_url:
            raise RuntimeError('真实岗位源需要配置 REDIS_URL')
        from redis import Redis
        cache = Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=5)
    return configuration, cache


class _UnavailableRenderer:
    """渲染依赖（Playwright/docxtpl/字体/打印页）未就绪时的明确降级，而不是静默失败。"""

    def __init__(self, reason):
        self.reason = reason

    def _fail(self):
        from resume_b.preflight import PreflightUnavailable

        raise PreflightUnavailable(self.reason)

    def inspect(self, snapshot, format):
        self._fail()

    def render(self, snapshot):
        self._fail()


def _find_font():
    for candidate in (
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ):
        if Path(candidate).is_file():
            return candidate
    return "C:/Windows/Fonts/simsun.ttc"


def _build_renderers(settings, assets_dir):
    from resume_b.preflight import PreflightUnavailable

    word_dir = assets_dir / "word"

    def word_loader(key, version):
        path = word_dir / f"{key}-{version}.docx"
        if not path.is_file():
            raise PreflightUnavailable("缺少 Word 模板资产 " + path.name)
        return path.read_bytes()

    try:
        from resume_b.word_renderer import WordRenderer

        word = WordRenderer(word_loader)
    except ImportError as e:
        word = _UnavailableRenderer("DOCX 渲染依赖未安装（docxtpl/lxml）：" + str(e))

    try:
        from resume_b.local_pdf import LocalPdfRenderer
        from resume_b.local_templates import StaticHtmlRenderer

        html = StaticHtmlRenderer()
        pdf = LocalPdfRenderer()
    except (ImportError, ValueError) as e:
        pdf = _UnavailableRenderer("PDF/HTML 渲染未配置（需 Playwright/Chromium 与前端打印页）：" + str(e))
        html = _UnavailableRenderer("HTML 渲染未配置")

    from resume_b.render_dispatch import ResumeRenderers

    resume = ResumeRenderers(pdf=pdf, word=word, html=html)

    try:
        from resume_b.preparation_renderer import PreparationRenderer

        def preparation_loader():
            path = word_dir / "preparation-1.0.0.docx"
            if not path.is_file():
                raise PreflightUnavailable("缺少准备资料模板资产 " + path.name)
            return path.read_bytes()

        preparation = PreparationRenderer(
            docx_template_loader=preparation_loader,
            pdf_font_file=_find_font(),
        )
    except (ImportError, ValueError, OSError) as e:
        preparation = _UnavailableRenderer("准备资料渲染未配置（需 reportlab/字体）：" + str(e))

    return resume, preparation


def _register_b_error_handlers(app):
    from resume_b.api import ApiError
    from resume_b.exports import ExportNotReady
    from resume_b.preflight import PreflightFailed, PreflightUnavailable
    from resume_b.richtext import ContentError
    from resume_b.service import ResourceNotFound, RevisionConflict, StateConflict
    from app.modules.tasks.lifecycle import TaskOperationError
    from app.modules.tasks.registry import ResourceUnavailable

    def _error(request, status, code, message, details=None, headers=None):
        response_headers = {"X-Contract-Version": "2.0.0"}
        retry_after = (headers or {}).get("Retry-After")
        if status == 429 and isinstance(retry_after, str) and retry_after.isascii() and retry_after.isdecimal():
            response_headers["Retry-After"] = retry_after
        return JSONResponse(
            status_code=status,
            headers=response_headers,
            content={
                "error": {"code": code, "message": message, "details": details or {}},
                "requestId": getattr(request.state, "request_id", str(uuid4())),
            },
        )

    @app.exception_handler(ResourceNotFound)
    async def _rn(request, e):
        return _error(request, 404, "NOT_FOUND", "资源不存在")

    @app.exception_handler(ResourceUnavailable)
    async def _resource_unavailable(request, e):
        return _error(request, 404, 'NOT_FOUND', '资源不存在')

    @app.exception_handler(TaskOperationError)
    async def _task_operation(request, e):
        return _error(request, e.status, e.code, e.message, e.details)

    @app.exception_handler(RevisionConflict)
    async def _rc(request, e):
        return _error(request, 409, "REVISION_CONFLICT", "内容已更新，请核对后再保存",
                      {"currentRevision": e.current_revision} if e.current_revision is not None else {})

    @app.exception_handler(StateConflict)
    async def _sc(request, e):
        return _error(request, 409, "STATE_CONFLICT", "当前状态不允许该操作")

    @app.exception_handler(ContentError)
    async def _ce(request, e):
        return _error(request, 422, "VALIDATION_ERROR", "输入字段不合法",
                      {"errors": [{"path": e.path, "message": str(e)}]})

    @app.exception_handler(PreflightFailed)
    async def _pf(request, e):
        return _error(request, 422, "PREFLIGHT_FAILED", "请先修正导出问题", {"issues": e.issues})

    @app.exception_handler(PreflightUnavailable)
    async def _pu(request, e):
        return _error(request, 503, "SOURCE_UNAVAILABLE", "导出试渲染未完成，请重试")

    @app.exception_handler(ExportNotReady)
    async def _en(request, e):
        return _error(request, 409, "NOT_READY", "导出文件尚未就绪")

    @app.exception_handler(ApiError)
    async def _ae(request, e):
        return _error(request, e.status, e.code, e.message, e.details, e.headers)


def create_app(settings=None):
    from app.ports import SqlRelations
    from app.schemas import ErrorEnvelope
    from app.storage import LocalStorage

    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("本项目要求 Python >=3.13,<3.14")

    settings = settings or Settings.load()

    # ---- 基础设施 ----
    engine, sessions = database(settings.database_url)
    storage = LocalStorage(settings)
    relations = SqlRelations()
    limiter = RedisRateLimiter(settings.redis_url) if settings.redis_url else MissingRateLimiter()
    idempotency = IdempotencyService(settings.secret)

    # ---- 任务框架与适配器 ----
    registry = Registry()
    model_client = create_model_client(load_model_configuration())
    ai = AAIAdapter(model_client)
    tasks = ATaskPort(registry)
    a_services = AServicesAdapter(tasks)
    b_ctx = BContext(registry, storage, relations, idempotency, tasks)
    b_services = BServicesAdapter(b_ctx)

    registry.register(Kind.PARSE_MATERIAL, material_handler(storage, ai))
    registry.register(Kind.ANALYZE_JD, jd_handler(storage, ai))

    # ---- B 集成（渲染器 + 导出协调器 + 文档桥）----
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    resume_renderers, preparation_renderer = _build_renderers(settings, assets_dir)
    b_int = build_b_integration(
        b_ctx, session_factory=sessions, resume_renderers=resume_renderers, preparation_renderer=preparation_renderer
    )
    from resume_b.models import Export, PreparationExport

    registry.register(
        Kind.EXPORT_RESUME,
        export_handler(b_int.resume_export_handler, b_int.resume_export_handler.coordinator, Export),
    )
    registry.register(
        Kind.EXPORT_PREPARATION,
        export_handler(b_int.preparation_export_handler, b_int.preparation_export_handler.coordinator, PreparationExport),
    )

    # ---- C 集成（6 个 handler + 19 条路由）----
    job_settings, job_cache = _job_configuration(settings)
    write_ports = make_write_ports(idempotency, csrf_dependency=verify_write)
    from resume_b.schemas import ResumeOutput, SuggestionValue

    c_components = build(
        sessions=sessions,
        registry=registry,
        a=a_services,
        b=b_services,
        session_dependency=session_dependency,
        user_dependency=user_id_dependency,
        request_id_dependency=request_id_dependency,
        write_ports=write_ports,
        resume_schema=ResumeOutput,
        suggestion_value_schema=SuggestionValue,
        model_client=model_client,
        job_settings=job_settings,
        job_cache=job_cache,
    )

    # ---- FastAPI 应用骨架（沿用 A 的中间件与异常处理）----
    error_responses = {code: {"model": ErrorEnvelope} for code in [400, 401, 403, 404, 409, 413, 415, 422, 429, 500, 503]}
    app = FastAPI(
        title="Agent 简历求职助手后端",
        version="2.0.0",
        dependencies=[Depends(reject_unknown_query)],
        responses=error_responses,
    )
    app.state.settings = settings
    app.state.engine, app.state.sessions = engine, sessions
    app.state.tasks, app.state.ai = tasks, ai
    app.state.storage, app.state.relations, app.state.limiter = storage, relations, limiter
    app.state.registry = registry
    app.state.runtime = c_components.runtime

    @app.middleware("http")
    async def common(request: Request, call_next):
        request.state.request_id = str(uuid4())
        received = 0
        original_receive = request._receive

        async def bounded_receive():
            nonlocal received
            message = await original_receive()
            received += len(message.get("body", b""))
            if received > 21 * 1024 * 1024:
                raise Problem(413, "FILE_TOO_LARGE", "请求体超过21MiB")
            return message

        request._receive = bounded_receive
        try:
            if int(request.headers.get("Content-Length", "0")) > 21 * 1024 * 1024:
                result = await problem(request, Problem(413, "FILE_TOO_LARGE", "请求体超过21MiB"))
            else:
                result = await call_next(request)
        except Problem as exc:
            result = await problem(request, exc)
        except Exception:
            logging.getLogger("backend").error("unhandled_error request_id=%s", request.state.request_id)
            result = JSONResponse(
                {"error": {"code": "INTERNAL_ERROR", "message": "服务暂时无法完成请求", "details": {}},
                 "requestId": request.state.request_id},
                status_code=500,
            )
        result.headers["X-Contract-Version"] = "2.0.0"
        result.headers["Cache-Control"] = "no-store"
        result.headers["X-Request-Id"] = request.state.request_id
        result.headers["X-Content-Type-Options"] = "nosniff"
        result.headers.setdefault("X-Frame-Options", "DENY")
        return result

    @app.exception_handler(Problem)
    async def problem(request, exc):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message, "details": exc.details},
             "requestId": request.state.request_id},
            status_code=exc.status,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        from .core import validation_problem
        return await problem(request, validation_problem(request, exc.errors()))

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return await problem(request, Problem(exc.status_code, "NOT_FOUND" if exc.status_code == 404 else "BAD_REQUEST", "请求无法处理"))

    _register_b_error_handlers(app)

    # ---- 挂载路由（A 33 + B 23 + C 19 = 75 公开操作）----
    app.include_router(auth_router)
    from app.routes import router as a_router

    app.include_router(a_router)
    from app.storage import download_router

    app.include_router(download_router)
    from resume_b.api import create_router as create_b_router

    app.include_router(create_b_router(b_int.dependencies))
    app.include_router(c_components.router)

    # ---- 统一 OpenAPI ----
    def contract_openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        from .jwt_auth import configure_openapi_security
        configure_openapi_security(schema)
        for path, methods in schema['paths'].items():
            for method, operation in methods.items():
                if method not in {'get', 'post', 'patch', 'delete'}:
                    continue
                # Router extras and explicit dependencies may declare the same parameter.
                # Keep one authoritative declaration while preserving stricter schema constraints.
                unique = {}
                for parameter in operation.get('parameters', []):
                    if parameter.get('in') == 'path':
                        parameter.setdefault('schema', {}).update({
                            'type': 'string', 'format': 'uuid',
                            'pattern': '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'})
                    identity = (parameter.get('in'), parameter.get('name'))
                    if identity not in unique:
                        unique[identity] = parameter
                    else:
                        current = unique[identity]
                        current['required'] = current.get('required', False) or parameter.get('required', False)
                        current.setdefault('schema', {}).update(parameter.get('schema', {}))
                operation['parameters'] = list(unique.values())
        app.openapi_schema = schema
        return schema

    app.openapi = contract_openapi

    # ---- 生命周期 ----
    app.state._owned_clients = (model_client, *c_components._owned_clients, *((job_cache,) if job_cache else ()))

    from app.cors import configure_cors
    configure_cors(app, settings.origin)
    return app


def create_app_for_worker():
    """worker/supervisor 复用同一配置工厂，但不启动 HTTP（由 scripts/run_worker.py 使用）。"""
    from app.adapters.a_ai import AAIAdapter
    from app.adapters.a_services import AServicesAdapter
    from app.adapters.a_tasks import ATaskPort
    from app.adapters.b_services import BContext, BServicesAdapter, build_b_integration
    from app.adapters.handlers import export_handler, jd_handler, material_handler
    from app.adapters.write_ports import IdempotencyService
    from app.auth import RedisRateLimiter
    from app.core import Settings, database
    from app.modules.c_core.integration import build
    from app.ports import SqlRelations
    from app.storage import LocalStorage

    settings = Settings.load()
    engine, sessions = database(settings.database_url)
    storage = LocalStorage(settings)
    relations = SqlRelations()
    idempotency = IdempotencyService(settings.secret)
    registry = Registry()
    model_client = create_model_client(load_model_configuration())
    ai = AAIAdapter(model_client)
    tasks = ATaskPort(registry)
    b_ctx = BContext(registry, storage, relations, idempotency, tasks)
    registry.register(Kind.PARSE_MATERIAL, material_handler(storage, ai))
    registry.register(Kind.ANALYZE_JD, jd_handler(storage, ai))
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    resume_renderers, preparation_renderer = _build_renderers(settings, assets_dir)
    b_int = build_b_integration(b_ctx, session_factory=sessions, resume_renderers=resume_renderers, preparation_renderer=preparation_renderer)
    from resume_b.models import Export, PreparationExport

    registry.register(Kind.EXPORT_RESUME, export_handler(b_int.resume_export_handler, b_int.resume_export_handler.coordinator, Export))
    registry.register(Kind.EXPORT_PREPARATION, export_handler(b_int.preparation_export_handler, b_int.preparation_export_handler.coordinator, PreparationExport))
    a_services = AServicesAdapter(tasks)
    b_services = BServicesAdapter(b_ctx)
    from app.adapters.write_ports import make_write_ports, verify_write
    from resume_b.schemas import ResumeOutput, SuggestionValue

    job_settings, job_cache = _job_configuration(settings)
    c_components = build(
        sessions=sessions,
        registry=registry,
        a=a_services,
        b=b_services,
        session_dependency=session_dependency,
        user_dependency=user_id_dependency,
        request_id_dependency=request_id_dependency,
        write_ports=make_write_ports(idempotency, csrf_dependency=verify_write),
        resume_schema=ResumeOutput,
        suggestion_value_schema=SuggestionValue,
        model_client=model_client,
        job_settings=job_settings,
        job_cache=job_cache,
    )
    if job_cache is not None:
        from dataclasses import replace
        c_components = replace(c_components, _owned_clients=(*c_components._owned_clients, job_cache))
    return c_components.runtime, model_client, c_components
