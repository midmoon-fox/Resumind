"""Resume export orchestration with explicit short transaction boundaries."""
from copy import deepcopy
from dataclasses import dataclass
import re
from types import SimpleNamespace
from typing import Callable
from uuid import uuid4

from sqlalchemy import select

from .documents import require, uuid4 as validate_uuid
from .models import Export, ResumeVersion
from .preflight import preflight, PreflightFailed
from .service import ResourceNotFound, RevisionConflict
from .templates import TemplateService
from .export_lifecycle import ExportLifecycle


class ExportNotReady(Exception):
    pass


def filename(value, format):
    require(format in {"PDF", "DOCX", "HTML"}, "/format", "unsupported export format")
    require(value is None or isinstance(value, str), "/fileName", "expected string")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value or "简历")
    name = name.strip(" .") or "简历"
    name = re.sub(r"\.(pdf|docx|html)$", "", name, flags=re.I).rstrip(" .") or "简历"
    if name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        name = "_" + name
    suffix = "." + format.lower()
    return name[:150 - len(suffix)].rstrip(" .") + suffix


@dataclass(frozen=True)
class ExportDependencies:
    unit_of_work: Callable  # context manager yielding Session; commits on success, rolls back on failure
    service: Callable  # Session -> ResumeService
    inspect_layout: Callable
    find_replay: Callable  # session,user,operation,key,payload -> data or None; mismatch raises
    execute_write: Callable  # same A atomic service as document writes
    create_task: Callable  # session,user,kind,resourceType,resourceId,input -> task UUID; no commit
    task_info: Callable  # session,user,taskId -> {status,error}; validates task ownership
    download_file: Callable  # session,user,fileId,fileName -> Download JSON


class ExportCoordinator:
    def __init__(self, deps: ExportDependencies):
        self.deps = deps

    def read_fixed(self, user, resume_id, revision):
        with self.deps.unit_of_work() as session:
            svc = self.deps.service(session)
            resume = svc.get(user, resume_id)
            svc.editable(resume)
            if resume.revision != revision:
                raise RevisionConflict(resume.revision)
            template = TemplateService(session).definition(resume.template_key, resume.template_version, allow_retired=True)
            return SimpleNamespace(document_json=deepcopy(resume.document_json), style_json=deepcopy(resume.style_json), template_key=resume.template_key, template_version=resume.template_version, allowed_formats=deepcopy(template.formats_json), render_context={"userId": user, "resumeId": resume.id, "sourceRevision": resume.revision})

    def preflight(self, user, resume_id, revision, format):
        fixed = self.read_fixed(user, resume_id, revision)
        require(format in fixed.allowed_formats, "/format", "format is not supported by this template version")
        # No database session or row lock survives into trial rendering.
        return preflight(fixed, format, self.deps.inspect_layout, render_context=fixed.render_context)

    def accept(self, user, payload, key):
        require(8 <= len(key) <= 64 and key.isascii(), "/headers/Idempotency-Key", "expected 8..64 ASCII characters")
        resume_id, revision, format = payload["resumeId"], payload["baseRevision"], payload["format"]
        validate_uuid(resume_id, "/resumeId")
        name = filename(payload.get("fileName"), format)
        operation = "POST /api/exports"
        with self.deps.unit_of_work() as session:
            self.deps.service(session).get(user, resume_id)
            replay = self.deps.find_replay(session, user, operation, key, payload)
            if replay is not None:
                return replay
        report = self.preflight(user, resume_id, revision, format)
        if not report["canExport"]:
            raise PreflightFailed(report["issues"])
        with self.deps.unit_of_work() as session:
            def action():
                svc = self.deps.service(session)
                # Rechecks revision after slow rendering; concurrent changes cannot leak in.
                version = svc.snapshot(user, resume_id, revision, reason="EXPORT")
                identifier = str(uuid4())
                task = self.deps.create_task(session, user, "EXPORT_RESUME", "EXPORT", identifier,
                                             {"resumeVersionId": version.id, "format": format, "templateId": version.template_key, "templateVersion": version.template_version})
                validate_uuid(task, "/taskId")
                session.add(Export(id=identifier, user_id=user, task_id=task, resume_version_id=version.id, format=format, file_name=name,
                                   warnings_json=[issue["message"] for issue in report["issues"] if issue["severity"] == "WARNING"]))
                session.flush()
                return {"taskId": task, "resourceType": "EXPORT", "resourceId": identifier, "status": "QUEUED",
                        "statusUrl": f"/api/tasks/{task}", "resourceUrl": f"/api/exports/{identifier}"}
            return self.deps.execute_write(session, user, operation, key, payload, action)

    def accessible(self, session, user, export_id):
        record = session.scalar(select(Export).where(Export.id == export_id, Export.user_id == user))
        if record is None:
            raise ResourceNotFound()
        version = session.scalar(select(ResumeVersion).where(ResumeVersion.id == record.resume_version_id, ResumeVersion.user_id == user))
        if version is None:
            raise ResourceNotFound()
        self.deps.service(session).get(user, version.resume_id)
        return record, version

    def detail(self, user, export_id):
        with self.deps.unit_of_work() as session:
            record, _ = self.accessible(session, user, export_id)
            task = self.deps.task_info(session, user, record.task_id)
            return {"id": record.id, "taskId": record.task_id, "resumeVersionId": record.resume_version_id,
                    "format": record.format, "fileName": record.file_name, "status": task["status"], "fileId": record.file_id,
                    "warnings": record.warnings_json, "error": task["error"], "createdAt": record.created_at.isoformat(timespec="microseconds") + "Z"}

    def download(self, user, export_id):
        with self.deps.unit_of_work() as session:
            record, _ = self.accessible(session, user, export_id)
            task = self.deps.task_info(session, user, record.task_id)
            if task["status"] != "SUCCEEDED" or record.file_id is None:
                raise ExportNotReady("export is not ready")
            return self.deps.download_file(session, user, record.file_id, record.file_name)


class ExportResumeHandler(ExportLifecycle):
    """C runner calls load -> render outside transaction -> commit_result in its final transaction."""
    def __init__(self, coordinator, *, render, verify_lease, register_file):
        self.coordinator, self.render = coordinator, render
        self.verify_lease, self.register_file = verify_lease, register_file

    def load(self, user, export_id):
        with self.coordinator.deps.unit_of_work() as session:
            record, version = self.coordinator.accessible(session, user, export_id)
            return deepcopy({"document": version.document_json, "style": version.style_json, "templateId": version.template_key,
                             "templateVersion": version.template_version, "format": record.format, "fileName": record.file_name,
                             "renderContext": {"userId": user, "resumeId": version.resume_id, "resumeVersionId": version.id,
                                               "sourceRevision": version.source_revision, "exportId": record.id, "taskId": record.task_id}})

    def execute(self, user, export_id):
        snapshot = self.load(user, export_id)
        fixed = SimpleNamespace(document_json=snapshot["document"], style_json=snapshot["style"],
                                template_key=snapshot["templateId"], template_version=snapshot["templateVersion"])
        report = preflight(fixed, snapshot["format"], self.coordinator.deps.inspect_layout, render_context=snapshot["renderContext"])
        if not report["canExport"]:
            raise PreflightFailed(report["issues"])
        return self.render(snapshot)

    def _lock_record(self, session, user, export_id):
        record, version = self.coordinator.accessible(session, user, export_id)
        self.coordinator.deps.service(session).get(user, version.resume_id, lock=True)
        # Refresh after the parent lock: another worker may have committed while we waited.
        record = session.scalar(select(Export).where(Export.id == export_id, Export.user_id == user).with_for_update().execution_options(populate_existing=True))
        return record

    def commit_result(self, session, user, export_id, lease, artifact):
        record = self._lock_record(session, user, export_id)
        self.verify_lease(session, user, record.task_id, lease)
        if record.file_id is None:
            file_id = self.register_file(session, user, "EXPORT", artifact)
            validate_uuid(file_id, "/fileId")
            record.file_id = file_id
            session.flush()
        return record.file_id
