"""No handler is registered implicitly; resource checks fail closed."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from .schemas import Kind, ResourceType, TaskError


class ResourceUnavailable(Exception):
    """Missing, deleted, foreign-owned or otherwise invalid business input."""


class HandlerFailure(Exception):
    def __init__(self, error: TaskError, *, retry_after_seconds: int | None = None):
        self.error = error
        self.retry_after_seconds = retry_after_seconds
        super().__init__(error.code)


@dataclass(frozen=True)
class TaskInput:
    id: str
    user_id: str
    kind: Kind
    resource_type: ResourceType
    resource_id: str
    attempt: int
    data: dict


@dataclass(frozen=True)
class Handler:
    # Checks must lock the business/parent rows when lock=True and recheck ownership.
    check: Callable[[Session, TaskInput, bool], None]
    compute: Callable[[TaskInput], Any]
    save: Callable[[Session, TaskInput, Any], None]
    fail: Callable[[Session, TaskInput, TaskError], None]
    retry: Callable[[Session, TaskInput], None] | None = None
    cancel: Callable[[Session, TaskInput], None] | None = None
    invalidate: Callable[[Session, TaskInput, TaskError], None] | None = None


class Registry:
    def __init__(self) -> None:
        self._handlers: dict[Kind, Handler] = {}

    def register(self, kind: Kind, handler: Handler) -> None:
        kind = Kind(kind)
        if kind in self._handlers:
            raise ValueError(f"Handler already registered: {kind}")
        self._handlers[kind] = handler

    def get(self, kind: Kind) -> Handler:
        try:
            return self._handlers[Kind(kind)]
        except KeyError:
            raise ResourceUnavailable("Handler is not configured") from None
