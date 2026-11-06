"""worker / supervisor 共用的运行时与发布器工厂。

supervisor 通过 `python -m app.worker.supervisor --factory app.worker.entrypoint:factory` 动态导入；
celery worker 通过 scripts/run_worker.py 启动。
"""
import os


def factory(broker_url: str):
    """返回 (runtime, publish)，供 C 的 supervisor run_loop 使用。"""
    from app.bootstrap import create_app_for_worker
    from app.worker.celery_app import create_celery, publisher

    runtime, _model_client, _components = create_app_for_worker()
    celery = create_celery(broker_url, runtime)
    publish = publisher(celery)
    return runtime, publish
