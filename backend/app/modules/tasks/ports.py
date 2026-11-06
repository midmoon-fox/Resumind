"""A owns the shared transaction, CSRF and persistent idempotency implementation."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class StoredResponse:
    status: int
    body: dict


class IdempotencyPort(Protocol):
    def begin(
        self, session: Session, *, user_id: str, operation: str, key: str, request: dict
    ) -> StoredResponse | None:
        """Atomic unique-key claim; mismatch/in-progress raise TaskOperationError.

        Existing response is returned without modifying it. No commit or credentials.
        """
        ...

    def complete(
        self, session: Session, *, user_id: str, operation: str, key: str, response: StoredResponse
    ) -> None:
        """Save the response in the SAME business transaction, without commit."""
        ...


@dataclass(frozen=True)
class WritePorts:
    csrf_dependency: Callable
    transaction: Callable[[Session], AbstractContextManager]
    idempotency: IdempotencyPort
