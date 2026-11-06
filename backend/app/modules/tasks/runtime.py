"""Short SQL transactions surround computation; stale workers cannot save."""

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from .lifecycle import terminal
from .models import OutboxEvent, Task, new_id, utcnow
from .registry import HandlerFailure, Registry, ResourceUnavailable, TaskInput
from .schemas import TaskError
from .service import snapshot


@dataclass(frozen=True)
class Lease:
    task: TaskInput
    token: str


class LeaseExpired(Exception):
    """Abort business writes if the lease expires while acquiring business locks."""


class Runtime:
    def __init__(self, sessions: sessionmaker, registry: Registry, *, lease_seconds: int = 60):
        if lease_seconds < 3:
            raise ValueError("Lease must be at least three seconds")
        self.sessions, self.registry, self.lease_seconds = sessions, registry, lease_seconds

    def claim(self, task_id: str, attempt: int) -> Lease | None:
        if type(attempt) is not int or attempt < 0:
            raise ValueError("Invalid attempt")
        with self.sessions.begin() as session:
            task = session.get(Task, task_id, with_for_update=True)
            if task is None or task.status != "QUEUED" or task.attempt != attempt:
                return None
            event = session.scalar(
                select(OutboxEvent).where(
                    OutboxEvent.task_id == task_id, OutboxEvent.attempt == attempt
                )
            )
            if event is None or event.next_attempt_at > utcnow():
                return None
            handler = self.registry.get(task.kind)
            data = snapshot(task)
            try:
                handler.check(session, data, True)
            except ResourceUnavailable:
                self.invalidate(session, handler, task, data)
                return None
            token = new_id()
            task.status, task.stage = "RUNNING", "处理中"
            task.lease_token = token
            task.lease_expires_at = utcnow() + timedelta(seconds=self.lease_seconds)
            return Lease(data, token)

    def renew(self, lease: Lease) -> bool:
        with self.sessions.begin() as session:
            result = session.execute(
                update(Task)
                .where(
                    Task.id == lease.task.id,
                    Task.attempt == lease.task.attempt,
                    Task.lease_token == lease.token,
                    Task.status == "RUNNING",
                    Task.lease_expires_at > utcnow(),
                )
                .values(lease_expires_at=utcnow() + timedelta(seconds=self.lease_seconds))
            )
            return result.rowcount == 1

    @contextmanager
    def heartbeat(self, lease: Lease):
        stop = threading.Event()

        def pulse():
            while not stop.wait(self.lease_seconds / 3):
                try:
                    if not self.renew(lease):
                        return
                except Exception:
                    # Final submission still checks the lease in MySQL.
                    return

        thread = threading.Thread(target=pulse, daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=5)

    def finish(
        self,
        lease: Lease,
        result=None,
        error: TaskError | None = None,
        retry_after_seconds: int | None = None,
    ) -> bool:
        try:
            return self._finish(lease, result, error, retry_after_seconds)
        except LeaseExpired:
            return False

    def _finish(self, lease: Lease, result, error: TaskError | None, retry_after_seconds) -> bool:
        with self.sessions.begin() as session:
            task = session.get(Task, lease.task.id, with_for_update=True)
            if (
                task is None
                or task.attempt != lease.task.attempt
                or task.lease_token != lease.token
                or task.status != "RUNNING"
                or task.lease_expires_at is None
                or task.lease_expires_at <= utcnow()
            ):
                return False
            handler = self.registry.get(task.kind)
            current_input = snapshot(task)
            try:
                handler.check(session, current_input, True)
            except ResourceUnavailable:
                self.invalidate(session, handler, task, current_input)
                return False
            if error is None:
                handler.save(session, current_input, result)
            else:
                handler.fail(session, current_input, error)
            session.flush()
            if task.lease_expires_at <= utcnow():
                raise LeaseExpired()
            self._terminal(task, "SUCCEEDED" if error is None else "FAILED", error)
            if error is not None and retry_after_seconds is not None and retry_after_seconds > 0:
                try:
                    task.retry_not_before = utcnow() + timedelta(seconds=retry_after_seconds)
                except OverflowError:
                    task.retry_not_before = datetime.max
            return True

    _terminal = staticmethod(terminal)

    def invalidate(self, session, handler, task, data):
        error = TaskError(code="TASK_INPUT_INVALID", message="任务依据已失效", canRetry=False)
        if handler.invalidate is not None:
            with session.begin_nested():
                handler.invalidate(session, data, error)
        self._terminal(task, "FAILED", error)

    def run(self, task_id: str, attempt: int) -> bool:
        lease = self.claim(task_id, attempt)
        if lease is None:
            return False
        try:
            with self.heartbeat(lease):
                result = self.registry.get(lease.task.kind).compute(lease.task)
                return self.finish(lease, result=result)
        except HandlerFailure as failure:
            return self.finish(
                lease, error=failure.error, retry_after_seconds=failure.retry_after_seconds
            )
        except Exception:
            # Never expose exception strings, DB URLs, private inputs or provider responses.
            return self.finish(
                lease,
                error=TaskError(
                    code="TASK_EXECUTION_FAILED", message="任务处理失败", canRetry=True
                ),
            )
