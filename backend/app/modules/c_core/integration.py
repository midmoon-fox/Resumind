"""One composition point for A's app and Linux worker, with no import-time side effects."""

from dataclasses import dataclass, field

from app.modules.ai.config import ModelConfiguration, create_model_client
from app.modules.c_core.abilities import ModelAbilities
from app.modules.c_core.router import create_router
from app.modules.c_core.service import CServices
from app.modules.recommendations.config import JobSourceSettings, create_source
from app.modules.tasks.runtime import Runtime


@dataclass(frozen=True)
class Components:
    services: CServices
    runtime: Runtime
    router: object
    _owned_clients: tuple = field(default=(), repr=False)

    def close(self):
        """Close only clients created here. Supplied clients remain caller-owned."""
        for client in self._owned_clients:
            client.close()


def build(
    *,
    sessions,
    registry,
    a,
    b,
    session_dependency,
    user_dependency,
    request_id_dependency,
    write_ports,
    resume_schema,
    suggestion_value_schema,
    model_client=None,
    model_configuration: ModelConfiguration | None = None,
    source=None,
    job_settings: JobSourceSettings | None = None,
    job_cache=None,
):
    """A/B register their four handlers on the SAME registry; C registers six more.
    Resources are owned by the caller; close explicit HTTP/source clients on shutdown.
    Default model and real-source clients are disabled and never read environment keys.
    """
    if source is not None and (job_settings is not None or job_cache is not None):
        raise ValueError("Pass a source instance OR source settings/cache")
    if model_client is not None and model_configuration is not None:
        raise ValueError("Pass a model client OR model configuration")
    if model_configuration is not None and not isinstance(model_configuration, ModelConfiguration):
        raise TypeError("Expected ModelConfiguration")
    selected = (
        source
        if source is not None
        else create_source(job_settings or JobSourceSettings(), cache=job_cache)
    )
    owned = [selected] if source is None else []
    try:
        client = model_client
        if client is None:
            client = create_model_client(model_configuration or ModelConfiguration())
            owned.append(client)
        abilities = ModelAbilities(client, b, selected)
        services = CServices(registry, a, b, abilities)
        services.register()
        router = create_router(
            services,
            registry=registry,
            session_dependency=session_dependency,
            user_dependency=user_dependency,
            request_id_dependency=request_id_dependency,
            write_ports=write_ports,
            resume_schema=resume_schema,
            suggestion_value_schema=suggestion_value_schema,
        )
        return Components(services, Runtime(sessions, registry), router, tuple(owned))
    except Exception:
        for client in owned:
            client.close()
        raise
