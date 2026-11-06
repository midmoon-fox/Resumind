"""C-owned tables. A adds users foreign keys when merging the shared metadata.

列类型遵循 A/B 的既有约定：MySQL 用精确类型（CHAR ascii_bin / DATETIME(6) / unsigned），
SQLite 用通用回退（String / DateTime / Integer / JSON），使整合应用可本地隔离测试。
"""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON as SAJSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base import Base as TaskBase

UUID = String(36).with_variant(mysql.CHAR(36, charset="ascii", collation="ascii_bin"), "mysql")
TIME = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")
UINT = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
JSON_T = SAJSON().with_variant(mysql.JSON(), "mysql")
JSON_NN = SAJSON(none_as_null=True).with_variant(mysql.JSON(none_as_null=True), "mysql")


def utcnow() -> datetime:
    """MySQL DATETIME stores naive UTC, never local wall time."""
    return datetime.now(UTC).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid4())


class OwnedRow:
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(UUID)
    created_at: Mapped[datetime] = mapped_column(TIME, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIME, default=utcnow, onupdate=utcnow)


class Task(OwnedRow, TaskBase):
    __tablename__ = "ai_tasks"
    __table_args__ = (
        CheckConstraint("attempt >= 0", name="ck_ai_tasks_attempt"),
        Index("ix_ai_tasks_owner_time", "user_id", "created_at", "id"),
        Index("ix_ai_tasks_status_lease", "status", "lease_expires_at"),
        Index("ix_ai_tasks_resource", "resource_type", "resource_id", "created_at", "id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), default="QUEUED")
    stage: Mapped[str] = mapped_column(String(100), default="等待处理")
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(UUID)
    input_json: Mapped[dict] = mapped_column(JSON_T)
    attempt: Mapped[int] = mapped_column(UINT, default=0)
    lease_token: Mapped[str | None] = mapped_column(UUID)
    lease_expires_at: Mapped[datetime | None] = mapped_column(TIME)
    protocol_version: Mapped[str] = mapped_column(String(20), default="1.1.0")
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    model_identifier: Mapped[str | None] = mapped_column(String(200))
    error_json: Mapped[dict | None] = mapped_column(JSON_NN)
    finished_at: Mapped[datetime | None] = mapped_column(TIME)
    retry_not_before: Mapped[datetime | None] = mapped_column(TIME)


class OutboxEvent(OwnedRow, TaskBase):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("task_id", "attempt", name="uq_outbox_task_attempt"),
        Index("ix_outbox_pending", "state", "next_attempt_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )
    task_id: Mapped[str] = mapped_column(
        UUID, ForeignKey("ai_tasks.id", ondelete="RESTRICT", onupdate="RESTRICT")
    )
    attempt: Mapped[int] = mapped_column(UINT, default=0)
    state: Mapped[str] = mapped_column(String(20), default="PENDING")
    attempts: Mapped[int] = mapped_column(UINT, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(TIME, default=utcnow)
    last_error_code: Mapped[str | None] = mapped_column(String(100))
