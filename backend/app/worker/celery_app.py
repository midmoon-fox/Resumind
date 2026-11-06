"""Broker messages contain only Task ID and attempt; MySQL holds the result."""

from celery import Celery

from app.modules.tasks.runtime import Runtime

TASK_NAME = "resume.tasks.execute"


def create_celery(broker_url: str, runtime: Runtime, *, queue: str = "resume_tasks") -> Celery:
    app = Celery("resume_c_tasks", broker=broker_url)
    app.conf.update(
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
        task_ignore_result=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        broker_transport_options={
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "visibility_timeout": 300,
        },
        task_default_queue=queue,
        task_publish_retry=False,
    )

    @app.task(name=TASK_NAME, ignore_result=True)
    def execute(task_id: str, attempt: int):
        runtime.run(task_id, attempt)

    return app


def publisher(app: Celery, *, queue: str = "resume_tasks"):
    def publish(task_id: str, attempt: int):
        app.send_task(TASK_NAME, args=[task_id, attempt], queue=queue, ignore_result=True)

    return publish
