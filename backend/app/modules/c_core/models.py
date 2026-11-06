"""Remaining five C tables. External and circular FKs are staged in migration drafts.

列类型同 tasks/models.py：MySQL 精确类型 + SQLite 通用回退。
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON as SAJSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.tasks.models import OwnedRow, TaskBase

UUID_COLUMN = String(36).with_variant(mysql.CHAR(36, charset="ascii", collation="ascii_bin"), "mysql")
TIME = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")
UINT = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
JSON_T = SAJSON().with_variant(mysql.JSON(), "mysql")
JSON_NN = SAJSON(none_as_null=True).with_variant(mysql.JSON(none_as_null=True), "mysql")
MEDIUM = Text().with_variant(mysql.MEDIUMTEXT(), "mysql")
ASCII_KEY = String(100).with_variant(mysql.VARCHAR(100, charset="ascii", collation="ascii_bin"), "mysql")
BIN_KEY = String(200).with_variant(mysql.VARCHAR(200, collation="utf8mb4_bin"), "mysql")

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


class FollowupSession(OwnedRow, TaskBase):
    __tablename__ = "followup_sessions"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_followup_revision"),
        CheckConstraint(
            "max_rounds BETWEEN 2 AND 4 AND rounds_shown <= max_rounds", name="ck_followup_rounds"
        ),
        Index("ix_followup_workspace_time", "workspace_id", "created_at", "id"),
        TABLE_OPTIONS,
    )
    workspace_id: Mapped[str] = mapped_column(UUID_COLUMN)
    profile_snapshot_json: Mapped[dict] = mapped_column(JSON_T)
    direction_snapshot: Mapped[str | None] = mapped_column(String(100))
    jd_snapshot_json: Mapped[dict | None] = mapped_column(JSON_NN)
    experience_refs_json: Mapped[list] = mapped_column(JSON_T, default=list)
    status: Mapped[str] = mapped_column(String(32), default="GENERATING")
    revision: Mapped[int] = mapped_column(UINT, default=1)
    rounds_shown: Mapped[int] = mapped_column(UINT, default=0)
    max_rounds: Mapped[int] = mapped_column(UINT, default=4)
    last_task_id: Mapped[str | None] = mapped_column(UUID_COLUMN, ForeignKey("ai_tasks.id"))
    current_turn_id: Mapped[str | None] = mapped_column(UUID_COLUMN)
    asked_topics_json: Mapped[list] = mapped_column(JSON_T, default=list)
    skipped_topics_json: Mapped[list] = mapped_column(JSON_T, default=list)
    ended_reason: Mapped[str | None] = mapped_column(String(200))


class FollowupTurn(OwnedRow, TaskBase):
    __tablename__ = "followup_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_followup_turn_ordinal"),
        CheckConstraint("ordinal BETWEEN 1 AND 4", name="ck_followup_turn_ordinal"),
        TABLE_OPTIONS,
    )
    session_id: Mapped[str] = mapped_column(UUID_COLUMN, ForeignKey("followup_sessions.id"))
    ordinal: Mapped[int] = mapped_column(UINT)
    status: Mapped[str] = mapped_column(String(32))
    question: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    experience_id: Mapped[str | None] = mapped_column(UUID_COLUMN)
    topic: Mapped[str] = mapped_column(String(100))
    answer: Mapped[str | None] = mapped_column(Text)
    candidate_updates_json: Mapped[list] = mapped_column(JSON_T, default=list)
    created_experience_ids_json: Mapped[list] = mapped_column(JSON_T, default=list)
    confirmed_updates_json: Mapped[list | None] = mapped_column(JSON_NN)


class Suggestion(OwnedRow, TaskBase):
    __tablename__ = "ai_suggestions"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_suggestion_task"),
        CheckConstraint("base_revision >= 1", name="ck_suggestion_revision"),
        Index("ix_suggestion_resume_time", "resume_id", "created_at", "id"),
        TABLE_OPTIONS,
    )
    # Nullable only while linking resource and task in the SAME uncommitted transaction.
    task_id: Mapped[str | None] = mapped_column(UUID_COLUMN, ForeignKey("ai_tasks.id"))
    resume_id: Mapped[str] = mapped_column(UUID_COLUMN)
    base_revision: Mapped[int] = mapped_column(UINT)
    target_json: Mapped[dict] = mapped_column(JSON_T)
    original_json: Mapped[dict] = mapped_column(JSON_T)
    proposed_json: Mapped[dict | None] = mapped_column(JSON_NN)
    explanation: Mapped[str] = mapped_column(Text, default="")
    needs_fact_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(24), default="GENERATING")
    applied_revision: Mapped[int | None] = mapped_column(UINT)


class RecommendationRun(OwnedRow, TaskBase):
    __tablename__ = "recommendation_runs"
    __table_args__ = (UniqueConstraint("task_id", name="uq_recommendation_task"), TABLE_OPTIONS)
    task_id: Mapped[str | None] = mapped_column(UUID_COLUMN, ForeignKey("ai_tasks.id"))
    resume_version_id: Mapped[str] = mapped_column(UUID_COLUMN)
    filters_json: Mapped[dict] = mapped_column(JSON_T)


class RecommendedJob(OwnedRow, TaskBase):
    __tablename__ = "recommended_jobs"
    __table_args__ = (
        UniqueConstraint("run_id", "source_key", "source_job_id", name="uq_recommendation_source"),
        TABLE_OPTIONS,
    )
    run_id: Mapped[str] = mapped_column(UUID_COLUMN, ForeignKey("recommendation_runs.id"))
    source_key: Mapped[str] = mapped_column(ASCII_KEY)
    source_job_id: Mapped[str] = mapped_column(BIN_KEY)
    source_url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    salary_text: Mapped[str | None] = mapped_column(String(200))
    description_text: Mapped[str] = mapped_column(MEDIUM)
    published_at: Mapped[object | None] = mapped_column(TIME)
    fetched_at: Mapped[object] = mapped_column(TIME)
    availability: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    reasons_json: Mapped[list] = mapped_column(JSON_T, default=list)
    gaps_json: Mapped[list] = mapped_column(JSON_T, default=list)
