"""Transactional document operations; caller owns commit/rollback and idempotency."""
from copy import deepcopy
import hashlib
import json
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .documents import require, string, validate_document, validate_style, validate_template
from .models import Resume, ResumeVersion, utcnow
from .templates import TemplateService


class ResourceNotFound(Exception):
    pass


class RevisionConflict(Exception):
    def __init__(self, current_revision=None):
        self.current_revision = current_revision
        super().__init__("revision conflict")


class StateConflict(Exception):
    pass


class ResumeService:
    def __init__(self, session: Session, *, check_references, generation_complete):
        self.session = session
        # A checks workspace, JD and experience ownership/fact revisions in this transaction.
        self.check_references = check_references
        # C checks task state; a missing/failed/running task never counts as completed.
        self.generation_complete = generation_complete

    def get(self, user_id, resume_id, *, lock=False):
        statement = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id, Resume.deleted_at.is_(None))
        if lock:
            statement = statement.with_for_update()
        resume = self.session.scalar(statement.execution_options(populate_existing=True))
        if resume is None:
            raise ResourceNotFound()
        return resume

    def editable(self, resume):
        if resume.generation_task_id and not self.generation_complete(self.session, resume.user_id, resume.generation_task_id):
            raise StateConflict("generation has not completed")

    def create(self, user_id, *, title, document, style, template_key, template_version, workspace_id=None, jd_snapshot=None, _allow_retired_template=False):
        string(title, "/title", 200)
        require(bool(title), "/title", "title is required")
        validate_template(template_key, template_version)
        validate_document(document)
        validate_style(style)
        TemplateService(self.session).validate(template_key, template_version, document, style, allow_retired=_allow_retired_template)
        self.check_references(self.session, user_id, workspace_id, document, jd_snapshot)
        resume = Resume(user_id=user_id, title=title, document_json=deepcopy(document), style_json=deepcopy(style), template_key=template_key, template_version=template_version, workspace_id=workspace_id, jd_snapshot_json=deepcopy(jd_snapshot))
        self.session.add(resume)
        self.session.flush()
        return resume

    def list(self, user_id, *, page=1, page_size=20):
        require(type(page) is int and page >= 1, "/page", "expected positive page")
        require(type(page_size) is int and 1 <= page_size <= 20, "/pageSize", "expected 1..20")
        return list(self.session.scalars(select(Resume).where(Resume.user_id == user_id, Resume.deleted_at.is_(None)).order_by(Resume.updated_at.desc(), Resume.id.desc()).offset((page - 1) * page_size).limit(page_size)))

    def patch(self, user_id, resume_id, base_revision, changes):
        require(type(base_revision) is int and base_revision >= 1, "/baseRevision", "expected positive revision")
        require(isinstance(changes, dict) and not set(changes) - {"title", "document", "style", "templateId", "templateVersion"}, "", "unsupported patch fields")
        require(("templateId" in changes) == ("templateVersion" in changes), "/templateId", "template key and version must be provided together")
        current = self.get(user_id, resume_id, lock=True)
        self.editable(current)
        if current.revision != base_revision:
            raise RevisionConflict(current.revision)
        document = changes.get("document", current.document_json)
        style = changes.get("style", current.style_json)
        title = changes.get("title", current.title)
        key = changes.get("templateId", current.template_key)
        version = changes.get("templateVersion", current.template_version)
        string(title, "/title", 200)
        require(bool(title), "/title", "title is required")
        validate_template(key, version)
        validate_document(document, previous=current.document_json)
        validate_style(style)
        TemplateService(self.session).validate(key, version, document, style, allow_retired=(key, version) == (current.template_key, current.template_version))
        self.check_references(self.session, user_id, current.workspace_id, document, current.jd_snapshot_json)
        self._cas(current, base_revision, title=title, document_json=deepcopy(document), style_json=deepcopy(style), template_key=key, template_version=version)
        return self.get(user_id, resume_id)

    def _cas(self, resume, base_revision, **values):
        result = self.session.execute(update(Resume).where(Resume.id == resume.id, Resume.user_id == resume.user_id, Resume.revision == base_revision, Resume.deleted_at.is_(None)).values(**values, revision=base_revision + 1, updated_at=utcnow()).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise RevisionConflict(self.get(resume.user_id, resume.id).revision)
        self.session.expire(resume)

    def snapshot(self, user_id, resume_id, base_revision, *, reason="MANUAL", label=None):
        require(reason in {"MANUAL", "EXPORT", "BEFORE_RESTORE"}, "/reason", "invalid snapshot reason")
        if label is not None:
            string(label, "/label", 100)
        resume = self.get(user_id, resume_id, lock=True)
        self.editable(resume)
        if type(base_revision) is not int or resume.revision != base_revision:
            raise RevisionConflict(resume.revision)
        content = dict(document=resume.document_json, style=resume.style_json, templateId=resume.template_key, templateVersion=resume.template_version, jdSnapshot=resume.jd_snapshot_json)
        digest = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).digest()
        version = ResumeVersion(user_id=user_id, resume_id=resume_id, source_revision=base_revision, label=label, document_json=deepcopy(resume.document_json), style_json=deepcopy(resume.style_json), template_key=resume.template_key, template_version=resume.template_version, jd_snapshot_json=deepcopy(resume.jd_snapshot_json), reason=reason, content_sha256=digest)
        self.session.add(version)
        self.session.flush()
        return version

    def version(self, user_id, resume_id, version_id):
        self.get(user_id, resume_id)
        version = self.session.scalar(select(ResumeVersion).where(ResumeVersion.id == version_id, ResumeVersion.resume_id == resume_id, ResumeVersion.user_id == user_id))
        if version is None:
            raise ResourceNotFound()
        return version

    def versions(self, user_id, resume_id, *, page=1, page_size=20):
        self.get(user_id, resume_id)
        require(type(page) is int and page >= 1, "/page", "expected positive page")
        require(type(page_size) is int and 1 <= page_size <= 20, "/pageSize", "expected 1..20")
        return list(self.session.scalars(select(ResumeVersion).where(ResumeVersion.user_id == user_id, ResumeVersion.resume_id == resume_id).order_by(ResumeVersion.created_at.desc(), ResumeVersion.id.desc()).offset((page - 1) * page_size).limit(page_size)))

    def restore(self, user_id, resume_id, version_id, base_revision):
        current = self.get(user_id, resume_id, lock=True)
        version = self.version(user_id, resume_id, version_id)
        self.snapshot(user_id, resume_id, base_revision, reason="BEFORE_RESTORE")
        self._cas(current, base_revision, document_json=deepcopy(version.document_json), style_json=deepcopy(version.style_json), template_key=version.template_key, template_version=version.template_version, jd_snapshot_json=deepcopy(version.jd_snapshot_json))
        return self.get(user_id, resume_id)

    def copy(self, user_id, resume_id, *, title, version_id=None):
        current = self.get(user_id, resume_id, lock=True)
        self.editable(current)
        source = self.version(user_id, resume_id, version_id) if version_id else current
        document = deepcopy(source.document_json)
        for education in document["profile"]["education"]:
            education["id"] = str(uuid4())
        for section in document["sections"]:
            section["id"] = str(uuid4())
            for item in section["items"]:
                item["id"] = str(uuid4())
        # Historical sources are independently frozen; A must not re-resolve mutable JD.
        return self.create(user_id, title=title, document=document, style=source.style_json, template_key=source.template_key, template_version=source.template_version, workspace_id=current.workspace_id, jd_snapshot=source.jd_snapshot_json, _allow_retired_template=True)

    def delete(self, user_id, resume_id):
        current = self.get(user_id, resume_id, lock=True)
        self._cas(current, current.revision, deleted_at=utcnow())
