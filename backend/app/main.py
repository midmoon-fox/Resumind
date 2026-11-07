import logging
import sys
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException
from .cors import configure_cors

from .auth import MissingRateLimiter, RedisRateLimiter, router as auth_router
from .core import Problem, Settings, database, reject_unknown_query


def create_app(settings=None, *, tasks=None, ai=None, storage=None, limiter=None, relations=None):
    from .ports import MissingAI, MissingTasks, SqlRelations
    from .storage import LocalStorage
    from .schemas import ErrorEnvelope
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError('本项目要求 Python >=3.13,<3.14')
    settings = settings or Settings.load()
    error_responses = {code: {'model': ErrorEnvelope} for code in [400, 401, 403, 404, 409, 413, 415, 422, 429, 500, 503]}
    app = FastAPI(title='账户与资料后端 A', version='2.0.0', dependencies=[Depends(reject_unknown_query)], responses=error_responses)
    app.state.settings = settings
    app.state.engine, app.state.sessions = database(settings.database_url)
    app.state.tasks = tasks or MissingTasks()
    app.state.ai = ai or MissingAI()
    app.state.storage = storage or LocalStorage(settings)
    app.state.relations = relations or SqlRelations()
    app.state.limiter = limiter or (RedisRateLimiter(settings.redis_url) if settings.redis_url else MissingRateLimiter())

    @app.middleware('http')
    async def common(request: Request, call_next):
        request.state.request_id = str(uuid4())
        received = 0
        original_receive = request._receive
        async def bounded_receive():
            nonlocal received
            message = await original_receive()
            received += len(message.get('body', b''))
            if received > 21 * 1024 * 1024:
                raise Problem(413, 'FILE_TOO_LARGE', '请求体超过21MiB')
            return message
        request._receive = bounded_receive
        try:
            if int(request.headers.get('Content-Length', '0')) > 21 * 1024 * 1024:
                result = await problem(request, Problem(413, 'FILE_TOO_LARGE', '请求体超过21MiB'))
            else:
                result = await call_next(request)
        except Problem as exc:
            result = await problem(request, exc)
        except Exception:
            logging.getLogger('backend').error('unhandled_error request_id=%s', request.state.request_id)
            result = JSONResponse({'error': {'code': 'INTERNAL_ERROR', 'message': '服务暂时无法完成请求', 'details': {}}, 'requestId': request.state.request_id}, status_code=500)
        result.headers['X-Contract-Version'] = '2.0.0'
        result.headers['Cache-Control'] = 'no-store'
        result.headers['X-Request-Id'] = request.state.request_id
        result.headers['X-Content-Type-Options'] = 'nosniff'
        result.headers['X-Frame-Options'] = 'DENY'
        return result

    @app.exception_handler(Problem)
    async def problem(request, exc):
        return JSONResponse({'error': {'code': exc.code, 'message': exc.message, 'details': exc.details}, 'requestId': request.state.request_id}, status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        from .core import validation_problem
        return await problem(request, validation_problem(request, exc.errors()))

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return await problem(request, Problem(exc.status_code, 'NOT_FOUND' if exc.status_code == 404 else 'BAD_REQUEST', '请求无法处理'))

    app.include_router(auth_router)
    from .routes import router
    app.include_router(router)
    from .storage import download_router
    app.include_router(download_router)

    def contract_openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        from .jwt_auth import configure_openapi_security
        configure_openapi_security(schema)
        app.openapi_schema = schema
        return schema

    app.openapi = contract_openapi
    configure_cors(app, settings.origin)
    return app
