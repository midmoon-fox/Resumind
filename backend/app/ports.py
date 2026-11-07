"""Proposed internal integration protocol; no extra public endpoints or C-owned tables."""
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.orm import Session

from .core import Problem
from .models import Experience, ExperienceSource, JdVersion, JobDescription, Material, Segment, User, Workspace
from .schemas import ExperienceData, ExperienceType, Model, Provenance, Requirement
from pydantic import Field
from typing import Annotated


@dataclass(frozen=True)
class TaskRef:
    id: str
    status: str = 'QUEUED'


@dataclass(frozen=True)
class TaskContext:
    task_id: str
    user_id: str
    resource_id: str
    attempt: int
    lease_token: str
    input_json: dict


class TaskPort(Protocol):
    def create_task(self, db: Session, *, user_id: str, kind: str, resource_type: str,
                    resource_id: str, input_json: dict) -> TaskRef:
        """Insert C Task+Outbox in caller transaction, attempt=0, protocolVersion=1.1.0."""

    def latest_task_id(self, db: Session, user_id: str, resource_type: str, resource_id: str) -> str: ...
    def cancel_resource(self, db: Session, user_id: str, resource_type: str, resource_id: str) -> None: ...
    def assert_lease(self, db: Session, context: TaskContext) -> None:
        """Lock Task and verify owner, RUNNING, attempt, lease token and expiry."""
    def purge_resource_input(self, db: Session, user_id: str, resource_type: str, resource_id: str) -> None:
        """Remove private raw inputs from terminal tasks after access revocation; retain tombstones."""


class TextPart(Model):
    text: Annotated[str, Field(max_length=100000)]
    page: Annotated[int, Field(ge=1)] | None
    extraction_method: str


class ExperienceCandidate(Model):
    candidate_key: Annotated[str, Field(min_length=1, max_length=100)]
    type: ExperienceType
    data: ExperienceData
    provenance: list[Provenance]


class MaterialAnalysis(Model):
    candidates: Annotated[list[ExperienceCandidate], Field(max_length=50)]


class JdAnalysis(Model):
    job_title: Annotated[str, Field(max_length=200)] | None
    company_name: Annotated[str, Field(max_length=200)] | None
    requirements: Annotated[list[Requirement], Field(max_length=100)]


class AIPort(Protocol):
    def recognize(self, content: bytes, mime_type: str) -> list[TextPart]: ...
    def extract_experiences(self, segments: list[dict]) -> MaterialAnalysis: ...
    def analyze_jd(self, text: str) -> JdAnalysis: ...


class MissingTasks:
    def __getattr__(self, name):
        def missing(*args, **kwargs):
            raise Problem(503, 'FEATURE_DISABLED', '尚未接入 C 的统一任务框架')
        return missing


class MissingAI:
    def __getattr__(self, name):
        def missing(*args, **kwargs):
            raise Problem(503, 'FEATURE_DISABLED', '尚未接入 C 的模型/OCR 能力')
        return missing


class SqlRelations:
    """Inspect existing B/C tables; never invent rows, create their schema or cache counts."""
    def tables(self, db):
        names = set(inspect(db.connection()).get_table_names())
        wanted = {'resumes', 'resume_versions', 'exports', 'preparations', 'preparation_exports', 'ai_tasks', 'followup_turns', 'followup_sessions'}
        meta = MetaData()
        return {name: Table(name, meta, autoload_with=db.connection(), resolve_fks=False) for name in names & wanted}

    def counts(self, db, user_id, kind, resource_id):
        tables = self.tables(db)
        result = dict(versions=0, exports=0, preparations=0, preparationExports=0, workspaces=0, experiences=0, tasks=0)
        count = lambda query: db.scalar(select(func.count()).select_from(query.subquery())) or 0
        if kind == 'MATERIAL':
            mat = db.get(Material, resource_id)
            result['workspaces'] = 1 if mat else 0
            exp_ids = select(ExperienceSource.experience_id).join(Segment, Segment.id == ExperienceSource.segment_id).where(Segment.material_id == resource_id, ExperienceSource.user_id == user_id)
            result['experiences'] = count(select(Experience.id).where(Experience.user_id == user_id, Experience.deleted_at.is_(None), Experience.id.in_(exp_ids)))
            if 'resume_versions' in tables:
                # Snapshot documents may refer to source experience IDs in JSON. Inspect actual JSON.
                versions = tables['resume_versions']
                experience_ids = set(db.scalars(exp_ids))
                result['versions'] = self._json_count(db, versions, user_id, experience_ids, 'document_json')
        else:
            version_ids = select(JdVersion.id).where(JdVersion.jd_id == resource_id, JdVersion.user_id == user_id)
            result['workspaces'] = count(select(Workspace.id).where(Workspace.user_id == user_id, Workspace.jd_version_id.in_(version_ids)))
            ids = set(db.scalars(version_ids))
            if 'resume_versions' in tables:
                result['versions'] = self._json_count(db, tables['resume_versions'], user_id, ids, 'jd_snapshot_json')
        task = tables.get('ai_tasks')
        if task is not None:
            types = ['MATERIAL'] if kind == 'MATERIAL' else ['JD_VERSION']
            ids = [resource_id] if kind == 'MATERIAL' else list(db.scalars(select(JdVersion.id).where(JdVersion.jd_id == resource_id, JdVersion.user_id == user_id)))
            result['tasks'] = count(select(task.c.id).where(task.c.user_id == user_id, task.c.resource_type.in_(types), task.c.resource_id.in_(ids)))
        # Derive downstream counts from actual matching snapshot IDs, including read-only retained links.
        snapshots = tables.get('resume_versions')
        if snapshots is not None:
            column = 'document_json' if kind == 'MATERIAL' else 'jd_snapshot_json'
            values = set(db.scalars(exp_ids)) if kind == 'MATERIAL' else ids if task is not None else set(db.scalars(version_ids))
            matched = self._json_ids(db, snapshots, user_id, set(values), column)
            for name, key in [('exports', 'exports'), ('preparations', 'preparations')]:
                t = tables.get(name)
                if t is not None:
                    result[key] = count(select(t.c.id).where(t.c.user_id == user_id, t.c.resume_version_id.in_(matched)))
            if 'preparations' in tables and 'preparation_exports' in tables:
                p, e = tables['preparations'], tables['preparation_exports']
                pids = select(p.c.id).where(p.c.user_id == user_id, p.c.resume_version_id.in_(matched))
                result['preparationExports'] = count(select(e.c.id).where(e.c.user_id == user_id, e.c.preparation_id.in_(pids)))
        return result

    def _json_ids(self, db, table, user_id, ids, column):
        def contains(value):
            if isinstance(value, dict):
                return any(contains(v) for v in value.values())
            if isinstance(value, list):
                return any(contains(v) for v in value)
            return isinstance(value, str) and value in ids
        return [r.id for r in db.execute(select(table.c.id, table.c[column]).where(table.c.user_id == user_id)) if contains(r[1])]

    def _json_count(self, *args):
        return len(self._json_ids(*args))

    def output_accessible(self, db, file):
        t = self.tables(db)
        if not {'resumes', 'resume_versions'} <= t.keys():
            return False
        r, v = t['resumes'], t['resume_versions']
        if file.purpose == 'EXPORT' and 'exports' in t:
            e = t['exports']
            query = select(e.c.id).join(v, v.c.id == e.c.resume_version_id).join(r, r.c.id == v.c.resume_id).where(e.c.file_id == file.id, e.c.user_id == file.user_id, v.c.user_id == file.user_id, r.c.user_id == file.user_id, r.c.deleted_at.is_(None))
            return db.scalar(query.limit(1)) is not None
        if file.purpose == 'PREPARATION_EXPORT' and {'preparations', 'preparation_exports'} <= t.keys():
            p, e = t['preparations'], t['preparation_exports']
            query = select(e.c.id).join(p, p.c.id == e.c.preparation_id).join(v, v.c.id == p.c.resume_version_id).join(r, r.c.id == v.c.resume_id).where(e.c.file_id == file.id, e.c.user_id == file.user_id, p.c.user_id == file.user_id, p.c.deleted_at.is_(None), v.c.user_id == file.user_id, r.c.user_id == file.user_id, r.c.deleted_at.is_(None))
            return db.scalar(query.limit(1)) is not None
        return False

    def file_referenced(self, db, file):
        if db.scalar(select(User.id).where(User.id == file.user_id, User.avatar_file_id == file.id)):
            return True
        if db.scalar(select(Material.id).where(Material.user_id == file.user_id, Material.file_id == file.id, Material.deleted_at.is_(None))):
            return True
        if db.scalar(select(JdVersion.id).join(JobDescription, JobDescription.id == JdVersion.jd_id).where(JdVersion.user_id == file.user_id, JdVersion.file_id == file.id, JobDescription.user_id == file.user_id, JobDescription.deleted_at.is_(None))):
            return True
        return self.output_accessible(db, file)
