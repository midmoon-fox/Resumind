"""Lifecycle transitions within the caller's transaction; no autonomous commits."""

from datetime import timedelta

from sqlalchemy.orm import Session

from .models import OutboxEvent, Task, utcnow
from .registry import Registry, ResourceUnavailable
from .schemas import TaskError
from .service import can_retry_manually, snapshot

TERMINAL = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})
CANCEL_ERROR = TaskError(code="TASK_CANCELLED", message="任务已取消", canRetry=False)


class TaskOperationError(Exception):
    def __init__(
        self, code="STATE_CONFLICT", message="当前状态不允许此操作", status=409, details=None
    ):
        self.code, self.message, self.status = code, message, status
        self.details = details
        super().__init__(code)


def terminal(task: Task, status: str, error: TaskError | None = None) -> None:
    task.status = status
    task.stage = {"SUCCEEDED": "已完成", "CANCELLED": "已取消"}.get(status, "处理失败")
    task.error_json = error.model_dump(exclude_none=True) if error else None
    task.finished_at = utcnow()
    task.lease_token = task.lease_expires_at = None


def owned_task(session: Session, registry: Registry, task_id: str, user_id: str) -> Task:
    task = session.get(Task, task_id, with_for_update=True, populate_existing=True)
    if task is None or task.user_id != user_id:
        raise ResourceUnavailable()
    registry.get(task.kind).check(session, snapshot(task), False)
    return task


def requeue(session: Session, registry: Registry, task: Task, *, delay: int = 0) -> None:
    handler = registry.get(task.kind)
    if handler.retry is None:
        raise TaskOperationError(message="业务恢复能力尚未接入")
    # Callback locks and checks current turn/state/revisions and restores business status.
    # It sees the OLD attempt and the original fixed input.
    handler.retry(session, snapshot(task))
    task.attempt += 1
    task.status, task.stage = "QUEUED", "等待重试"
    task.error_json = task.finished_at = None
    task.lease_token = task.lease_expires_at = None
    session.add(
        OutboxEvent(
            user_id=task.user_id,
            task_id=task.id,
            attempt=task.attempt,
            next_attempt_at=max(
                utcnow() + timedelta(seconds=delay), task.retry_not_before or utcnow()
            ),
        )
    )
    session.flush()


def retry_task(
    session: Session, registry: Registry, task_id: str, user_id: str, expected_attempt: int
) -> Task:
    if type(expected_attempt) is not int or expected_attempt < 0:
        raise ValueError("Expected attempt must be a nonnegative integer")
    task = owned_task(session, registry, task_id, user_id)
    if task.attempt != expected_attempt or not can_retry_manually(task):
        raise TaskOperationError()
    requeue(session, registry, task)
    return task


def cancel_locked(session: Session, registry: Registry, task: Task) -> None:
    if task.status in TERMINAL:
        return
    handler = registry.get(task.kind)
    if handler.cancel is None:
        raise TaskOperationError(message="业务取消能力尚未接入")
    task.status, task.stage = "CANCEL_REQUESTED", "正在取消"
    # Invalidates the worker; logical cancellation does not guarantee stopping billing.
    task.lease_token = task.lease_expires_at = None
    handler.cancel(session, snapshot(task))
    terminal(task, "CANCELLED", CANCEL_ERROR)
    session.flush()


def cancel_task(session: Session, registry: Registry, task_id: str, user_id: str) -> Task:
    task = owned_task(session, registry, task_id, user_id)
    cancel_locked(session, registry, task)
    return task
