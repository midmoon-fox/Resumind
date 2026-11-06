"""A-owned tables only. External foreign keys are installed by the integration migration."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (JSON, BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index,
                        Integer, LargeBinary, SmallInteger, String, Text, UniqueConstraint)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid():
    return str(uuid4())


UUID_TYPE = String(36).with_variant(mysql.CHAR(36, charset='ascii', collation='ascii_bin'), 'mysql')
UTC_TYPE = mysql.DATETIME(fsp=6).with_variant(DateTime(), 'sqlite')
UINT = Integer().with_variant(mysql.INTEGER(unsigned=True), 'mysql')
MEDIUM = Text().with_variant(mysql.MEDIUMTEXT(), 'mysql')
HASH = LargeBinary(32).with_variant(mysql.BINARY(32), 'mysql')


def ascii_key(length):
    return String(length).with_variant(mysql.VARCHAR(length, charset='ascii', collation='ascii_bin'), 'mysql')


def fk(target, **kwargs):
    return mapped_column(UUID_TYPE, ForeignKey(target, ondelete='RESTRICT', onupdate='RESTRICT', **kwargs))


from .shared.base import Base


class Row:
    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(UTC_TYPE, default=now)
    updated_at: Mapped[datetime] = mapped_column(UTC_TYPE, default=now, onupdate=now)


class Owned(Row):
    @declared_attr
    def user_id(cls) -> Mapped[str]:
        return fk('users.id')


class User(Row, Base):
    __tablename__ = 'users'
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(50))
    avatar_file_id: Mapped[str | None] = fk('files.id', use_alter=True, name='fk_users_avatar')
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')


class Session(Owned, Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[bytes] = mapped_column(HASH, unique=True)
    csrf_hash: Mapped[bytes] = mapped_column(HASH)
    expires_at: Mapped[datetime] = mapped_column(UTC_TYPE)
    revoked_at: Mapped[datetime | None] = mapped_column(UTC_TYPE)
    __table_args__ = (Index('ix_sessions_expiry', 'expires_at'), Index('ix_sessions_owner_time', 'user_id', 'created_at'))


class File(Owned, Base):
    __tablename__ = 'files'
    purpose: Mapped[str] = mapped_column(String(32))
    object_key: Mapped[str] = mapped_column(String(512).with_variant(mysql.VARCHAR(512, collation='utf8mb4_bin'), 'mysql'), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger().with_variant(mysql.BIGINT(unsigned=True), 'mysql'))
    sha256: Mapped[bytes] = mapped_column(HASH)
    status: Mapped[str] = mapped_column(String(24), default='READY')
    deleted_at: Mapped[datetime | None] = mapped_column(UTC_TYPE)
    __table_args__ = (Index('ix_files_owner_time', 'user_id', 'created_at', 'id'),)


class Workspace(Owned, Base):
    __tablename__ = 'workspaces'
    title: Mapped[str] = mapped_column(String(100))
    direction: Mapped[str | None] = mapped_column(String(100))
    profile_json: Mapped[dict] = mapped_column(JSON)
    jd_version_id: Mapped[str | None] = fk('jd_versions.id')
    active_followup_session_id: Mapped[str | None] = mapped_column(UUID_TYPE)  # C integration FK
    step: Mapped[str] = mapped_column(String(24), default='JD')
    revision: Mapped[int] = mapped_column(UINT, default=1)
    __table_args__ = (CheckConstraint('revision >= 1', name='ck_workspace_revision'), Index('ix_workspace_owner_time', 'user_id', 'updated_at', 'id'))


class Material(Owned, Base):
    __tablename__ = 'materials'
    workspace_id: Mapped[str] = fk('workspaces.id')
    file_id: Mapped[str | None] = fk('files.id')
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    input_text: Mapped[str | None] = mapped_column(MEDIUM)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(24), default='QUEUED')
    error_json: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    deleted_at: Mapped[datetime | None] = mapped_column(UTC_TYPE)
    __table_args__ = (Index('ix_material_workspace_time', 'workspace_id', 'created_at', 'id'), Index('ix_material_owner_time', 'user_id', 'created_at', 'id'))


class Segment(Owned, Base):
    __tablename__ = 'material_segments'
    material_id: Mapped[str] = fk('materials.id')
    ordinal: Mapped[int] = mapped_column(UINT)
    page_no: Mapped[int | None] = mapped_column(UINT)
    text: Mapped[str] = mapped_column(MEDIUM)
    extraction_method: Mapped[str] = mapped_column(String(32))
    __table_args__ = (UniqueConstraint('material_id', 'ordinal', name='uq_segment_ordinal'),)


class Experience(Owned, Base):
    __tablename__ = 'experiences'
    workspace_id: Mapped[str] = fk('workspaces.id')
    generation_task_id: Mapped[str | None] = mapped_column(UUID_TYPE)  # C integration FK
    candidate_key: Mapped[str | None] = mapped_column(String(100).with_variant(mysql.VARCHAR(100, collation='utf8mb4_bin'), 'mysql'))
    type: Mapped[str] = mapped_column(String(24))
    data_json: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default='CANDIDATE')
    revision: Mapped[int] = mapped_column(UINT, default=1)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    merged_into_id: Mapped[str | None] = fk('experiences.id')
    deleted_at: Mapped[datetime | None] = mapped_column(UTC_TYPE)
    __table_args__ = (CheckConstraint('revision >= 1', name='ck_experience_revision'), CheckConstraint('merged_into_id IS NULL OR merged_into_id <> id', name='ck_experience_not_self'), Index('ix_experience_workspace_status', 'workspace_id', 'status', 'id'), UniqueConstraint('generation_task_id', 'candidate_key', name='uq_experience_candidate'))


class ExperienceSource(Owned, Base):
    __tablename__ = 'experience_sources'
    experience_id: Mapped[str] = fk('experiences.id')
    experience_revision: Mapped[int] = mapped_column(UINT)
    json_pointer: Mapped[str] = mapped_column(String(500))
    segment_id: Mapped[str | None] = fk('material_segments.id')
    turn_id: Mapped[str | None] = mapped_column(UUID_TYPE)  # C integration FK
    origin: Mapped[str] = mapped_column(String(24))
    __table_args__ = (Index('ix_source_experience_revision', 'experience_id', 'experience_revision'), CheckConstraint("(origin='MATERIAL' AND segment_id IS NOT NULL AND turn_id IS NULL) OR (origin='FOLLOWUP' AND turn_id IS NOT NULL AND segment_id IS NULL) OR (origin='USER_INPUT' AND segment_id IS NULL AND turn_id IS NULL)", name='ck_source_origin'))


class JobDescription(Owned, Base):
    __tablename__ = 'job_descriptions'
    title: Mapped[str] = mapped_column(String(200))
    current_version_id: Mapped[str | None] = fk('jd_versions.id', use_alter=True, name='fk_jd_current_version')
    revision: Mapped[int] = mapped_column(UINT, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(UTC_TYPE)
    __table_args__ = (CheckConstraint('revision >= 1', name='ck_jd_revision'), Index('ix_jd_owner_time', 'user_id', 'created_at', 'id'))


class JdVersion(Owned, Base):
    __tablename__ = 'jd_versions'
    jd_id: Mapped[str] = fk('job_descriptions.id')
    version_no: Mapped[int] = mapped_column(UINT)
    status: Mapped[str] = mapped_column(String(32), default='QUEUED')
    source_type: Mapped[str] = mapped_column(String(24))
    original_text: Mapped[str] = mapped_column(MEDIUM)
    file_id: Mapped[str | None] = fk('files.id')
    source_url: Mapped[str | None] = mapped_column(String(2048))
    job_title: Mapped[str | None] = mapped_column(String(200))
    company_name: Mapped[str | None] = mapped_column(String(200))
    requirements_json: Mapped[list] = mapped_column(JSON)
    confirmed_at: Mapped[datetime | None] = mapped_column(UTC_TYPE)
    purged_at: Mapped[datetime | None] = mapped_column(UTC_TYPE)
    __table_args__ = (UniqueConstraint('jd_id', 'version_no', name='uq_jd_version_no'),)


class Idempotency(Owned, Base):
    __tablename__ = 'idempotency_records'
    operation_key: Mapped[str] = mapped_column(ascii_key(200))
    client_key: Mapped[str] = mapped_column(ascii_key(64))
    request_sha256: Mapped[bytes] = mapped_column(HASH)
    state: Mapped[str] = mapped_column(String(24), default='IN_PROGRESS')
    http_status: Mapped[int | None] = mapped_column(SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), 'mysql'))
    response_json: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[str | None] = mapped_column(UUID_TYPE)
    __table_args__ = (UniqueConstraint('user_id', 'operation_key', 'client_key', name='uq_idempotency_intent'),)


class AuthIdempotency(Row, Base):
    __tablename__ = 'auth_idempotency'
    anonymous_session_hash: Mapped[bytes] = mapped_column(HASH)
    operation_key: Mapped[str] = mapped_column(ascii_key(200))
    client_key: Mapped[str] = mapped_column(ascii_key(64))
    request_sha256: Mapped[bytes] = mapped_column(HASH)
    state: Mapped[str] = mapped_column(String(24), default='IN_PROGRESS')
    http_status: Mapped[int | None] = mapped_column(SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), 'mysql'))
    response_json: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    __table_args__ = (UniqueConstraint('anonymous_session_hash', 'operation_key', 'client_key', name='uq_auth_intent'),)


class AuditEvent(Owned, Base):
    __tablename__ = 'audit_events'
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(UUID_TYPE)
    request_id: Mapped[str] = mapped_column(UUID_TYPE)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (Index('ix_audit_owner_time', 'user_id', 'created_at', 'id'),)


for table in Base.metadata.tables.values():
    table.dialect_options['mysql'].update(engine='InnoDB', charset='utf8mb4', collate='utf8mb4_0900_ai_ci')
