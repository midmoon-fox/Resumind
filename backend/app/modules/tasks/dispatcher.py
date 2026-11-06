"""At-least-once delivery. Broker acknowledgement precedes Outbox SENT."""

from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from .models import OutboxEvent, utcnow


def dispatch_pending(
    sessions: sessionmaker, publish: Callable[[str, int], None], *, limit: int = 100
) -> int:
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Invalid dispatcher batch limit")
    delivered = 0
    for _ in range(limit):
        with sessions.begin() as session:
            event = session.scalar(
                select(OutboxEvent)
                .where(OutboxEvent.state == "PENDING", OutboxEvent.next_attempt_at <= utcnow())
                .order_by(OutboxEvent.next_attempt_at, OutboxEvent.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if event is None:
                break
            event.attempts += 1
            try:
                # Configure broker connect/socket timeouts; no model or rendering here.
                publish(event.task_id, event.attempt)
            except Exception:
                event.last_error_code = "BROKER_UNAVAILABLE"
                event.next_attempt_at = utcnow() + timedelta(
                    seconds=min(2 ** min(event.attempts, 8), 300)
                )
            else:
                event.state = "SENT"
                event.last_error_code = None
                delivered += 1
    return delivered
