"""Bounded automatic retries and stale lease recovery using MySQL row locks."""

import logging
from datetime import timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import sessionmaker

from .lifecycle import TaskOperationError, cancel_locked, requeue, terminal
from .models import Task, utcnow
from .registry import Registry, ResourceUnavailable
from .schemas import TaskError
from .service import snapshot

MAX_AUTOMATIC_ATTEMPTS = 3


def _recover_one(session, registry, handler, task):
    is_expired = task.status == "RUNNING" and (
        task.lease_expires_at is None or task.lease_expires_at <= utcnow()
    )
    if task.status == "CANCEL_REQUESTED":
        if handler.cancel is None:
            return "skipped"
        cancel_locked(session, registry, task)
        return "cancelled"
    if task.retry_not_before is not None and task.retry_not_before > utcnow():
        return "skipped"
    if not is_expired and not (
        task.status == "FAILED"
        and task.error_json
        and task.error_json.get("canRetry") is True
        and task.attempt < MAX_AUTOMATIC_ATTEMPTS - 1
        and task.finished_at is not None
        and task.finished_at + timedelta(seconds=2 ** (task.attempt + 1)) <= utcnow()
    ):
        return "skipped"
    if handler.retry is None:
        return "skipped"
    handler.check(session, snapshot(task), False)
    if is_expired and task.attempt >= MAX_AUTOMATIC_ATTEMPTS - 1:
        # Validate applicability before touching a potentially completed business resource.
        handler.retry(session, snapshot(task))
        error = TaskError(code="WORKER_LEASE_EXPIRED", message="任务执行租约已失效", canRetry=True)
        handler.fail(session, snapshot(task), error)
        terminal(task, "FAILED", error)
        return "failed"
    requeue(session, registry, task, delay=2 ** (task.attempt + 1) if is_expired else 0)
    return "requeued"


def recover_due(sessions: sessionmaker, registry: Registry, *, limit: int = 100) -> dict:
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Invalid recovery batch limit")
    now = utcnow()
    due = or_(
        Task.status == "CANCEL_REQUESTED",
        and_(
            Task.status == "RUNNING",
            or_(Task.lease_expires_at <= now, Task.lease_expires_at.is_(None)),
        ),
        and_(
            Task.status == "FAILED",
            Task.attempt < MAX_AUTOMATIC_ATTEMPTS - 1,
            Task.error_json["canRetry"].as_boolean().is_(True),
            Task.finished_at <= now - timedelta(seconds=2),
            or_(Task.retry_not_before.is_(None), Task.retry_not_before <= now),
        ),
    )
    # IDs only: each recovery has its own fresh transaction and current locking read.
    with sessions() as session:
        ids = list(
            session.scalars(
                select(Task.id).where(due).order_by(Task.updated_at, Task.id).limit(limit)
            )
        )
    counts = {"requeued": 0, "cancelled": 0, "failed": 0, "skipped": 0}
    for task_id in ids:
        with sessions.begin() as session:
            task = session.scalar(
                select(Task).where(Task.id == task_id).with_for_update(skip_locked=True)
            )
            if task is None:
                counts["skipped"] += 1
                continue
            try:
                handler = registry.get(task.kind)
            except ResourceUnavailable:
                counts["skipped"] += 1
                continue
            was_cancelling = task.status == "CANCEL_REQUESTED"
            try:
                with session.begin_nested():
                    outcome = _recover_one(session, registry, handler, task)
                counts[outcome] += 1
            except (ResourceUnavailable, TaskOperationError):
                # Savepoint rolls back even a callback which changed rows before rejecting.
                terminal(
                    task,
                    "CANCELLED" if was_cancelling else "FAILED",
                    TaskError(
                        code="TASK_CANCELLED" if was_cancelling else "TASK_INPUT_INVALID",
                        message="任务已取消" if was_cancelling else "任务依据或业务状态已失效",
                        canRetry=False,
                    ),
                )
                counts["cancelled" if was_cancelling else "failed"] += 1
            except Exception:
                logging.getLogger(__name__).error("TASK_RECOVERY_CALLBACK_FAILED")
                counts["skipped"] += 1
    return counts
