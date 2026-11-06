"""启动 supervisor：Outbox 投递 + 失败恢复 + 租约回收的周期调度。"""
import os

if __name__ == "__main__":
    from app.bootstrap import create_app_for_worker
    from app.worker.celery_app import create_celery, publisher
    from app.worker.supervisor import run_loop

    broker = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    runtime, _model_client, _components = create_app_for_worker()
    app = create_celery(broker, runtime)
    run_loop(runtime, publisher(app))
