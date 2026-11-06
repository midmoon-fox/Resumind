"""Preparation export snapshots and handler; no AI call or resume layout reuse."""
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from sqlalchemy import select

from .documents import require, uuid4 as validate_uuid
from .exports import ExportDependencies, ExportNotReady, filename
from .models import PreparationExport
from .service import ResourceNotFound, RevisionConflict, StateConflict
from .export_lifecycle import ExportLifecycle


@dataclass(frozen=True)
class PreparationExportDependencies:
    common: ExportDependencies
    preparations: Callable  # Session -> PreparationService


class PreparationExportCoordinator:
    def __init__(self, deps):
        self.deps = deps

    def accept(self, user, preparation_id, payload, key):
        require(8 <= len(key) <= 64 and key.isascii(), "/headers/Idempotency-Key", "expected 8..64 ASCII characters")
        require(payload["format"] in {"PDF", "DOCX"}, "/format", "preparation exports support PDF/DOCX only")
        operation = f"POST /api/preparations/{preparation_id}/exports"
        common = self.deps.common
        with common.unit_of_work() as session:
            # Recheck parent before any replay to avoid exposing deleted content.
            self.deps.preparations(session).get(user, preparation_id)
            def action():
                preparation = self.deps.preparations(session).get(user, preparation_id, lock=True)
                if preparation.status != "READY":
                    raise StateConflict("preparation is not ready")
                if preparation.revision != payload["baseRevision"]:
                    raise RevisionConflict(preparation.revision)
                identifier = str(uuid4())
                task = common.create_task(session, user, "EXPORT_PREPARATION", "PREPARATION_EXPORT", identifier,
                                          {"preparationExportId": identifier, "format": payload["format"]})
                validate_uuid(task, "/taskId")
                record = PreparationExport(id=identifier, user_id=user, task_id=task, preparation_id=preparation_id,
                    source_revision=preparation.revision, content_snapshot_json=deepcopy(preparation.content_json),
                    format=payload["format"], file_name=filename(payload.get("fileName") or "面试准备", payload["format"]))
                session.add(record)
                session.flush()
                return {"taskId": task, "resourceType": "PREPARATION_EXPORT", "resourceId": identifier, "status": "QUEUED",
                    "statusUrl": f"/api/tasks/{task}", "resourceUrl": f"/api/preparation-exports/{identifier}"}
            return common.execute_write(session, user, operation, key, payload, action)

    def accessible(self, session, user, export_id, *, lock=False):
        statement = select(PreparationExport).where(PreparationExport.id == export_id, PreparationExport.user_id == user)
        record = session.scalar(statement.execution_options(populate_existing=True))
        if record is None:
            raise ResourceNotFound()
        preparation = self.deps.preparations(session).get(user, record.preparation_id, lock=lock)
        if lock:
            record = session.scalar(statement.with_for_update().execution_options(populate_existing=True))
        return record, preparation

    def detail(self, user, export_id):
        with self.deps.common.unit_of_work() as session:
            record, _ = self.accessible(session, user, export_id)
            task = self.deps.common.task_info(session, user, record.task_id)
            return {"id": record.id, "taskId": record.task_id, "preparationId": record.preparation_id,
                    "sourceRevision": record.source_revision, "format": record.format, "fileName": record.file_name,
                    "status": task["status"], "fileId": record.file_id, "error": task["error"]}

    def download(self, user, export_id):
        with self.deps.common.unit_of_work() as session:
            record, _ = self.accessible(session, user, export_id)
            task = self.deps.common.task_info(session, user, record.task_id)
            if task["status"] != "SUCCEEDED" or record.file_id is None:
                raise ExportNotReady()
            return self.deps.common.download_file(session, user, record.file_id, record.file_name)


class ExportPreparationHandler(ExportLifecycle):
    def __init__(self, coordinator, *, render, verify_lease, register_file):
        self.coordinator, self.render = coordinator, render
        self.verify_lease, self.register_file = verify_lease, register_file

    def load(self, user, export_id):
        with self.coordinator.deps.common.unit_of_work() as session:
            record, preparation = self.coordinator.accessible(session, user, export_id)
            return deepcopy({"type": preparation.type, "content": record.content_snapshot_json, "format": record.format, "fileName": record.file_name,
                             "renderContext": {"userId": user, "preparationId": preparation.id, "sourceRevision": record.source_revision,
                                               "exportId": record.id, "taskId": record.task_id, "resumeVersionId": preparation.resume_version_id}})

    def execute(self, user, export_id):
        return self.render(self.load(user, export_id))

    def _lock_record(self, session, user, export_id):
        record, _ = self.coordinator.accessible(session, user, export_id, lock=True)
        return record

    def commit_result(self, session, user, export_id, lease, artifact):
        record = self._lock_record(session, user, export_id)
        self.verify_lease(session, user, record.task_id, lease)
        if record.file_id is None:
            identifier = self.register_file(session, user, "PREPARATION_EXPORT", artifact)
            validate_uuid(identifier, "/fileId")
            record.file_id = identifier
            session.flush()
        return record.file_id
