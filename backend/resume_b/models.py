"""B-owned mappings. A/C must register their tables in Base.metadata at integration."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, CHAR, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

UUID = CHAR(36).with_variant(mysql.CHAR(36, charset="ascii", collation="ascii_bin"), "mysql")
KEY50 = String(50).with_variant(mysql.VARCHAR(50, charset="ascii", collation="ascii_bin"), "mysql")
KEY20 = String(20).with_variant(mysql.VARCHAR(20, charset="ascii", collation="ascii_bin"), "mysql")
TIME = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")
UINT = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fk(target):
    return ForeignKey(target, ondelete="RESTRICT", onupdate="RESTRICT")


from app.shared.base import Base


class Entity:
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(TIME, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIME, default=utcnow)


class Owned(Entity):
    user_id: Mapped[str] = mapped_column(UUID, fk("users.id"))


class Template(Entity, Base):
    __tablename__ = "templates"
    template_key: Mapped[str] = mapped_column(KEY50)
    version: Mapped[str] = mapped_column(KEY20)
    name: Mapped[str] = mapped_column(String(100))
    formats_json: Mapped[list] = mapped_column(JSON)
    section_types_json: Mapped[list] = mapped_column(JSON)
    style_policy_json: Mapped[dict] = mapped_column(JSON)
    vue_asset_version: Mapped[str] = mapped_column(String(100))
    docx_object_key: Mapped[str] = mapped_column(String(512))
    preview_file_id: Mapped[str | None] = mapped_column(UUID, fk("files.id"))
    status: Mapped[str] = mapped_column(String(20))
    __table_args__ = (UniqueConstraint("template_key", "version"),)


def template_fk():
    return ForeignKeyConstraint(["template_key", "template_version"], ["templates.template_key", "templates.version"], ondelete="RESTRICT", onupdate="RESTRICT")


class Resume(Owned, Base):
    __tablename__ = "resumes"
    workspace_id: Mapped[str | None] = mapped_column(UUID, fk("workspaces.id"))
    title: Mapped[str] = mapped_column(String(200))
    revision: Mapped[int] = mapped_column(UINT, default=1)
    document_json: Mapped[dict] = mapped_column(JSON)
    style_json: Mapped[dict] = mapped_column(JSON)
    template_key: Mapped[str] = mapped_column(KEY50)
    template_version: Mapped[str] = mapped_column(KEY20)
    jd_snapshot_json: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    generation_task_id: Mapped[str | None] = mapped_column(UUID, fk("ai_tasks.id"), unique=True)
    deleted_at: Mapped[datetime | None] = mapped_column(TIME)
    __table_args__ = (template_fk(), Index("ix_resumes_user_updated_id", "user_id", "updated_at", "id"), Index("ix_resumes_workspace", "workspace_id"))


class ResumeVersion(Owned, Base):
    __tablename__ = "resume_versions"
    resume_id: Mapped[str] = mapped_column(UUID, fk("resumes.id"))
    source_revision: Mapped[int] = mapped_column(UINT)
    label: Mapped[str | None] = mapped_column(String(100))
    document_json: Mapped[dict] = mapped_column(JSON)
    style_json: Mapped[dict] = mapped_column(JSON)
    template_key: Mapped[str] = mapped_column(KEY50)
    template_version: Mapped[str] = mapped_column(KEY20)
    jd_snapshot_json: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    reason: Mapped[str] = mapped_column(String(32))
    content_sha256: Mapped[bytes] = mapped_column(LargeBinary(32).with_variant(mysql.BINARY(32), "mysql"))
    __table_args__ = (template_fk(), Index("ix_versions_resume_created_id", "resume_id", "created_at", "id"))


class Export(Owned, Base):
    __tablename__ = "exports"
    task_id: Mapped[str] = mapped_column(UUID, fk("ai_tasks.id"), unique=True)
    resume_version_id: Mapped[str] = mapped_column(UUID, fk("resume_versions.id"))
    format: Mapped[str] = mapped_column(String(12))
    file_name: Mapped[str] = mapped_column(String(150))
    file_id: Mapped[str | None] = mapped_column(UUID, fk("files.id"))
    warnings_json: Mapped[list] = mapped_column(JSON)
    __table_args__ = (Index("ix_exports_version_created_id", "resume_version_id", "created_at", "id"),)


class Preparation(Owned, Base):
    __tablename__ = "preparations"
    task_id: Mapped[str] = mapped_column(UUID, fk("ai_tasks.id"), unique=True)
    resume_version_id: Mapped[str] = mapped_column(UUID, fk("resume_versions.id"))
    type: Mapped[str] = mapped_column(String(32))
    revision: Mapped[int] = mapped_column(UINT, default=1)
    status: Mapped[str] = mapped_column(String(24))
    content_json: Mapped[dict] = mapped_column(JSON)
    generation_options_json: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (Index("ix_preparations_version_type_created_id", "resume_version_id", "type", "created_at", "id"),)


class PreparationExport(Owned, Base):
    __tablename__ = "preparation_exports"
    task_id: Mapped[str] = mapped_column(UUID, fk("ai_tasks.id"), unique=True)
    preparation_id: Mapped[str] = mapped_column(UUID, fk("preparations.id"))
    source_revision: Mapped[int] = mapped_column(UINT)
    content_snapshot_json: Mapped[dict] = mapped_column(JSON)
    format: Mapped[str] = mapped_column(String(12))
    file_name: Mapped[str] = mapped_column(String(150))
    file_id: Mapped[str | None] = mapped_column(UUID, fk("files.id"))
    __table_args__ = (Index("ix_preparation_exports_parent_created_id", "preparation_id", "created_at", "id"),)


OWNED_TABLES = (Template.__table__, Resume.__table__, ResumeVersion.__table__, Export.__table__, Preparation.__table__, PreparationExport.__table__)
for _table in OWNED_TABLES:
    _table.dialect_options["mysql"].update(engine="InnoDB", charset="utf8mb4", collate="utf8mb4_0900_ai_ci")
