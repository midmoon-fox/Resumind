"""Preparation content and caller-transaction services owned by B."""
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select, update

from .documents import fields, require, string, uuid4 as validate_uuid
from .models import Preparation, ResumeVersion, utcnow
from .service import ResourceNotFound, RevisionConflict, StateConflict


from .preparation_content import validate_content


class PreparationService:
    def __init__(self, resume_service, *, verify_task, verify_lease):
        self.resumes = resume_service
        self.session = resume_service.session
        self.verify_task, self.verify_lease = verify_task, verify_lease

    def version(self, user, version_id, *, lock=False):
        version = self.session.scalar(select(ResumeVersion).where(ResumeVersion.id == version_id, ResumeVersion.user_id == user))
        if version is None:
            raise ResourceNotFound()
        resume = self.resumes.get(user, version.resume_id, lock=lock)
        return version, resume

    def get(self, user, preparation_id, *, lock=False):
        statement = select(Preparation).where(Preparation.id == preparation_id, Preparation.user_id == user)
        record = self.session.scalar(statement.execution_options(populate_existing=True))
        if record is None:
            raise ResourceNotFound()
        self.version(user, record.resume_version_id, lock=lock)
        if lock:
            record = self.session.scalar(statement.with_for_update().execution_options(populate_existing=True))
        return record

    def create_generation(self, user, version_id, task_id, kind, options, *, identifier=None):
        self.version(user, version_id, lock=True)
        require(kind in {"INTRODUCTION", "INTERVIEW_QUESTIONS"}, "/type", "unsupported preparation type")
        require(isinstance(options, dict) and not set(options) - {"tone", "questionCount"}, "/options", "unsupported options")
        if "tone" in options:
            string(options["tone"], "/options/tone", 100)
        if "questionCount" in options:
            require(kind == "INTERVIEW_QUESTIONS" and type(options["questionCount"]) is int and 5 <= options["questionCount"] <= 10, "/options/questionCount", "expected question count 5..10 for question set")
        identifier = identifier or str(uuid4())
        validate_uuid(identifier, "/id")
        self.verify_task(self.session, user, task_id, identifier, "GENERATE_PREPARATION")
        record = Preparation(id=identifier, user_id=user, task_id=task_id, resume_version_id=version_id, type=kind, status="GENERATING", content_json={"introduction": None, "questions": []}, generation_options_json=deepcopy(options))
        self.session.add(record)
        self.session.flush()
        return record

    def complete_generation(self, user, preparation_id, task_id, lease, content):
        record = self.get(user, preparation_id, lock=True)
        if record.status != "GENERATING" or record.task_id != task_id:
            raise StateConflict("preparation is not accepting generation results")
        self.verify_task(self.session, user, task_id, preparation_id, "GENERATE_PREPARATION")
        self.verify_lease(self.session, user, task_id, lease)
        version, _ = self.version(user, record.resume_version_id)
        validate_content(content, record.type, version.document_json)
        if record.type == "INTERVIEW_QUESTIONS":
            require(len(content["questions"]) == record.generation_options_json.get("questionCount", 5), "/content/questions", "generated count differs from accepted options")
        result = deepcopy(content)
        for question in result["questions"]:
            question["id"] = str(uuid4())
        record.content_json = result
        record.status = "READY"
        record.revision += 1
        record.updated_at = utcnow()
        self.session.flush()
        return record

    def _generation_record(self, user, preparation_id, task_id):
        record = self.get(user, preparation_id, lock=True)
        self.verify_task(self.session, user, task_id, preparation_id, "GENERATE_PREPARATION")
        if record.task_id != task_id or record.status == "READY":
            raise StateConflict("preparation cannot change generation state")
        return record

    def _generation_status(self, record, status):
        if record.status != status:
            record.status = status
            record.revision += 1
            record.updated_at = utcnow()
            self.session.flush()
        return record

    def fail_generation(self, user, preparation_id, task_id, lease):
        record = self._generation_record(user, preparation_id, task_id)
        self.verify_lease(self.session, user, task_id, lease)
        return self._generation_status(record, "FAILED")

    def retry_generation(self, user, preparation_id, task_id):
        record = self._generation_record(user, preparation_id, task_id)
        if record.status != "FAILED":
            raise StateConflict("preparation is not waiting for retry")
        # Caller C locks Task, increments attempt and writes Outbox in the same transaction.
        return self._generation_status(record, "GENERATING")

    def cancel_generation(self, user, preparation_id, task_id):
        record = self._generation_record(user, preparation_id, task_id)
        # Preparation has no CANCELLED enum; C's Task retains the cancellation reason/status.
        return self._generation_status(record, "FAILED")

    def patch(self, user, preparation_id, revision, content):
        record = self.get(user, preparation_id, lock=True)
        if record.status != "READY":
            raise StateConflict("preparation is not ready for editing")
        if type(revision) is not int or record.revision != revision:
            raise RevisionConflict(record.revision)
        version, _ = self.version(user, record.resume_version_id)
        validate_content(content, record.type, version.document_json)
        result = self.session.execute(update(Preparation).where(Preparation.id == record.id, Preparation.user_id == user, Preparation.revision == revision, Preparation.status == "READY").values(content_json=deepcopy(content), revision=revision + 1, updated_at=utcnow()).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise RevisionConflict()
        self.session.expire(record)
        return self.get(user, preparation_id)

    def outdated(self, user, record):
        version, resume = self.version(user, record.resume_version_id)
        return resume.revision != version.source_revision

    def list(self, user, version_id, *, page=1, page_size=20):
        self.version(user, version_id)
        require(type(page) is int and page >= 1 and type(page_size) is int and 1 <= page_size <= 20, "/query", "invalid pagination")
        return list(self.session.scalars(select(Preparation).where(Preparation.user_id == user, Preparation.resume_version_id == version_id).order_by(Preparation.created_at.desc(), Preparation.id.desc()).offset((page - 1) * page_size).limit(page_size)))
