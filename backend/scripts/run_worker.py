"""启动 worker：消费 Outbox 投递的 Celery 任务（同一套 Registry/Runtime）。"""
import os

if __name__ == "__main__":
    from app.bootstrap import create_app_for_worker
    from app.worker.celery_app import create_celery

    broker = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    runtime, _model_client, _components = create_app_for_worker()
    app = create_celery(broker, runtime)
    app.worker_main(["worker", "--loglevel=INFO", "--pool=solo"])
