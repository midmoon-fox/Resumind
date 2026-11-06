"""B 侧适配器：把 C 期望的 BServices 协议 + B 自己的 Dependencies/导出协调器接到 resume_b 服务。

覆盖合并方案 F07（导出先建 Task 后建记录 → 延后完整性检查）、F08（准备资料创建顺序）、
F10（统一幂等/事务/异常）、F16（统一 Profile 校验）与 5.3 的 BServicesAdapter/BExportHandlerAdapter。
"""
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from fastapi import Depends, Request
from sqlalchemy import func, select

from app.core import sha
from app.models import Experience, File, Idempotency, JdVersion, now
from app.modules.c_core.models import Suggestion
from app.modules.tasks.lifecycle import TaskOperationError
from app.modules.tasks.models import Task
from app.modules.tasks.registry import ResourceUnavailable
from app.modules.tasks.schemas import KIND_RESOURCE, Kind, ResourceId, ResourceType
from app.storage import display_name
from pydantic import TypeAdapter

from resume_b.ai_bridge import DocumentBridge, replace_target, target_value
from resume_b.api import Dependencies
from resume_b.deletion import DeletionService
from resume_b.documents import COLORS, DEFAULT_STYLE, dates, fields, string, uuid4 as _uuid4
from resume_b.documents import validate_document as b_validate_document
from resume_b.documents import validate_richtext
from resume_b.exports import ExportCoordinator, ExportDependencies, ExportResumeHandler
from resume_b.models import Export, Preparation, PreparationExport, Resume, ResumeVersion
from resume_b.preparations import PreparationService
from resume_b.preparation_exports import (
    ExportPreparationHandler,
    PreparationExportCoordinator,
    PreparationExportDependencies,
)
from resume_b.service import (
    ResourceNotFound,
    ResumeService,
    RevisionConflict,
    StateConflict,
)
from resume_b.templates import TemplateService

from app.adapters.write_ports import authenticate_user_id, verify_write as _verify_write
from resume_b.richtext import ContentError


def _stamp(value):
    return value.isoformat(timespec="microseconds") + "Z"


def _translate_b(method):
    from functools import wraps

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except ResourceNotFound:
            raise ResourceUnavailable() from None
        except RevisionConflict as e:
            raise TaskOperationError(
                "REVISION_CONFLICT", "内容已更新，请核对后再保存", 409,
                {"currentRevision": e.current_revision} if e.current_revision is not None else {},
            ) from None
        except StateConflict as e:
            raise TaskOperationError("STATE_CONFLICT", str(e) or "当前状态不允许该操作", 409) from None
        except ContentError as e:
            raise TaskOperationError(
                "VALIDATION_ERROR", str(e), 422, {"errors": [{"path": e.path, "message": str(e)}]}
            ) from None

    return wrapper


# --------------------------------------------------------------------------- #
# 纯模块级回调（无 ctx，签名固定，供 B/C 复用）
# --------------------------------------------------------------------------- #

def _owned(db, cls, resource_id, user_id, lock=False):
    query = select(cls).where(cls.id == resource_id, cls.user_id == user_id)
    if hasattr(cls, "deleted_at"):
        query = query.where(cls.deleted_at.is_(None))
    if lock:
        query = query.with_for_update()
    obj = db.scalar(query.execution_options(populate_existing=True))
    if obj is None:
        raise ResourceNotFound()
    return obj


def check_references(db, user, workspace_id, document, jd_snapshot):
    exp_ids = {
        item.get("experienceId")
        for section in document.get("sections", [])
        for item in section.get("items", [])
        if item.get("experienceId")
    }
    if workspace_id is not None:
        _owned(db, app_Workspace(), workspace_id, user)
    for eid in sorted(exp_ids):
        exp = _owned(db, Experience, eid, user)
        if exp.status != "CONFIRMED" or exp.excluded:
            raise TaskOperationError("STATE_CONFLICT", "经历必须是已确认且未排除的本人事实", 409)
        if workspace_id is not None and exp.workspace_id != workspace_id:
            raise ResourceNotFound()


def app_Workspace():
    from app.models import Workspace
    return Workspace


def resolve_workspace_snapshot(db, user, workspace_id, base_revision):
    from app.services import jd_version, revision

    if workspace_id is None and base_revision is None:
        return None
    ws = _owned(db, app_Workspace(), workspace_id, user, lock=True)
    if ws.revision != base_revision:
        raise RevisionConflict(ws.revision)
    if not ws.jd_version_id:
        return None
    version = jd_version(db, ws.jd_version_id, user, confirmed=True, lock=True)
    return dict(
        sourceJdId=version.jd_id,
        sourceJdVersionId=version.id,
        jobTitle=version.job_title,
        companyName=version.company_name,
        originalText=version.original_text,
        requirements=deepcopy(version.requirements_json),
    )


def generation_status(db, user, task_id):
    if not task_id:
        return None
    task = db.get(Task, task_id)
    if task is None or task.user_id != user:
        return None
    return task.status


def verify_task(db, user, task_id, resource_id, kind):
    task = db.get(Task, task_id)
    if task is None or task.user_id != user or task.resource_id != resource_id or task.kind != kind:
        raise StateConflict("task binding mismatch")


def verify_lease(db, user, task_id, lease):
    # C Runtime._finish 在 save/commit_result 前已锁定 Task 并核验租约，无需重复。
    return None


def verify_fact_preservation(db, user, target, original, proposed):
    # 事实保全由 C 的 fact_risk（compute）与 B 的 replace_target（身份/日期不变）共同保证。
    return None


def load_suggestion(db, user, suggestion_id):
    row = db.get(Suggestion, suggestion_id)
    if row is None or row.user_id != user:
        raise StateConflict("suggestion unavailable")
    return {
        "resumeId": row.resume_id,
        "status": row.status,
        "needsFactConfirmation": row.needs_fact_confirmation,
        "baseRevision": row.base_revision,
        "target": row.target_json,
        "original": row.original_json,
        "proposed": row.proposed_json,
    }


def count_sources(db, user, workspace_id, experience_ids):
    experiences = db.scalar(
        select(func.count())
        .select_from(Experience)
        .where(
            Experience.user_id == user,
            Experience.workspace_id == workspace_id,
            Experience.id.in_(experience_ids),
            Experience.deleted_at.is_(None),
        )
    )
    return {"workspaces": 1, "experiences": experiences or 0}


def count_tasks(db, user, references):
    total = 0
    for resource_type, ids in (
        ("RESUME", [references["resumeId"]]),
        ("EXPORT", references["exportIds"]),
        ("PREPARATION", references["preparationIds"]),
        ("PREPARATION_EXPORT", references["preparationExportIds"]),
    ):
        if not ids:
            continue
        total += (
            db.scalar(
                select(func.count())
                .select_from(Task)
                .where(Task.user_id == user, Task.resource_type == resource_type, Task.resource_id.in_(ids))
            )
            or 0
        )
    return total


def task_info(db, user, task_id):
    task = db.get(Task, task_id)
    if task is None or task.user_id != user:
        raise ResourceNotFound()
    return {"status": task.status, "error": task.error_json}


def _mime_for(file_name):
    name = (file_name or "").lower()
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if name.endswith(".html") or name.endswith(".htm"):
        return "text/html"
    return "application/octet-stream"


# --------------------------------------------------------------------------- #
# BContext 与 BServicesAdapter
# --------------------------------------------------------------------------- #

class BContext:
    def __init__(self, registry, storage, relations, idempotency, tasks):
        self.registry = registry
        self.storage = storage
        self.relations = relations
        self.idempotency = idempotency
        self.tasks = tasks


class BServicesAdapter:
    def __init__(self, ctx: BContext):
        self.ctx = ctx

    def _resumes(self, db):
        return ResumeService(
            db,
            check_references=check_references,
            generation_complete=lambda s, u, t: generation_status(s, u, t) == "SUCCEEDED",
        )

    def _bridge(self, db):
        return DocumentBridge(
            self._resumes(db),
            verify_task=verify_task,
            verify_lease=verify_lease,
            load_suggestion=load_suggestion,
            verify_fact_preservation=verify_fact_preservation,
        )

    def _preparations(self, db):
        return PreparationService(self._resumes(db), verify_task=verify_task, verify_lease=verify_lease)

    @_translate_b
    def resume(self, db, user, resume_id, lock):
        resume = self._resumes(db).get(user, resume_id, lock=lock)
        return dict(
            id=resume.id,
            workspaceId=resume.workspace_id,
            title=resume.title,
            revision=resume.revision,
            generationTaskId=resume.generation_task_id,
            generationStatus=generation_status(db, user, resume.generation_task_id)
            if resume.generation_task_id
            else None,
            document=deepcopy(resume.document_json),
            style=deepcopy(resume.style_json),
            templateId=resume.template_key,
            templateVersion=resume.template_version,
            jdSnapshot=deepcopy(resume.jd_snapshot_json),
            createdAt=_stamp(resume.created_at),
            updatedAt=_stamp(resume.updated_at),
        )

    @_translate_b
    def version(self, db, user, version_id, lock):
        version = db.scalar(
            select(ResumeVersion).where(ResumeVersion.id == version_id, ResumeVersion.user_id == user)
        )
        if version is None:
            raise ResourceUnavailable()
        self._resumes(db).get(user, version.resume_id, lock=lock)
        return dict(
            id=version.id,
            resumeId=version.resume_id,
            sourceRevision=version.source_revision,
            document=deepcopy(version.document_json),
            style=deepcopy(version.style_json),
            templateId=version.template_key,
            templateVersion=version.template_version,
            jdSnapshot=deepcopy(version.jd_snapshot_json),
        )

    @_translate_b
    def template(self, db, key, version, section_types):
        row = TemplateService(db).definition(key, version)
        for section in section_types:
            if section not in row.section_types_json:
                raise TaskOperationError(
                    "VALIDATION_ERROR", "模板不支持所选模块", 422,
                    {"errors": [{"path": "/sectionTypes", "message": "模板不支持所选模块"}]},
                )
        return dict(
            id=key,
            version=version,
            name=row.name,
            allowedSectionTypes=list(row.section_types_json),
            defaultStyle=DEFAULT_STYLE,
        )

    @_translate_b
    def create_resume(self, db, user, snapshot, request):
        draft = self._bridge(db).create_draft(
            user,
            title=request["title"],
            template_key=request["templateId"],
            template_version=request["templateVersion"],
            workspace_id=snapshot["workspaceId"],
            jd_snapshot=snapshot.get("jdSnapshot"),
        )
        return draft.id

    @_translate_b
    def create_preparation(self, db, user, request):
        version_id = request["resumeVersionId"]
        self.version(db, user, version_id, True)
        identifier = str(uuid4())
        options = {"tone": request["tone"]} if "tone" in request else {}
        if request["type"] == "INTERVIEW_QUESTIONS":
            options["questionCount"] = request.get("questionCount", 5)
        db.info.setdefault('pending_preparations', {})[identifier] = (version_id, request["type"], options)
        return identifier

    @_translate_b
    def bind_task(self, db, user, resource_type, resource, task):
        if resource_type == "RESUME":
            self._bridge(db).bind_generation(user, resource, task)
        elif resource_type == "PREPARATION":
            version_id, kind, request = db.info['pending_preparations'].pop(resource)
            self._preparations(db).create_generation(user, version_id, task, kind, request, identifier=resource)
        else:
            raise ValueError("unsupported bind resource type")

    @_translate_b
    def check_task(self, db, task, lock):
        if task.kind == Kind.GENERATE_RESUME:
            resume = self._resumes(db).get(task.user_id, task.resource_id, lock=lock)
            if resume.generation_task_id != task.id:
                raise ResourceUnavailable()
            if lock and resume.revision != 1:
                raise ResourceUnavailable()
        elif task.kind == Kind.GENERATE_PREPARATION:
            prep = db.get(Preparation, task.resource_id)
            if prep is None or prep.user_id != task.user_id or prep.task_id != task.id:
                raise ResourceUnavailable()
            self._preparations(db).version(task.user_id, prep.resume_version_id, lock=lock)
        else:
            raise ResourceUnavailable()

    @_translate_b
    def save_generated(self, db, task, document):
        self._bridge(db).complete_generation(task.user_id, task.resource_id, task.id, None, document, DEFAULT_STYLE)

    @_translate_b
    def save_preparation(self, db, task, content):
        self._preparations(db).complete_generation(task.user_id, task.resource_id, task.id, None, content)

    @_translate_b
    def task_state(self, db, task, state):
        if task.kind == Kind.GENERATE_PREPARATION:
            prep = self._preparations(db)
            if state == "FAILED":
                prep.fail_generation(task.user_id, task.resource_id, task.id, None)
            elif state == "GENERATING":
                prep.retry_generation(task.user_id, task.resource_id, task.id)

    @_translate_b
    def invalidate_task(self, db, task):
        if task.kind == Kind.GENERATE_PREPARATION:
            try:
                self._preparations(db).fail_generation(task.user_id, task.resource_id, task.id, None)
            except StateConflict:
                pass

    def validate_document(self, document, snapshot):
        b_validate_document(document)

    def validate_target(self, target, value):
        kind = target["kind"]
        if kind == "ITEM_DESCRIPTION":
            validate_richtext(value, allowed_colors=COLORS)
        elif kind == "SECTION_CONTENT":
            fields(value, "items", "/proposed")
            for item in value["items"]:
                fields(item, "itemId description", "/proposed/items")
                _uuid4(item["itemId"], "/proposed/items/itemId")
                validate_richtext(item["description"], allowed_colors=COLORS)
        elif kind == "SECTION_FIELD":
            validate_richtext(value, allowed_colors=COLORS)
        else:
            field = target["field"]
            fields(value, field, "/proposed")
            items = value[field]
            if field == "education":
                for e in items:
                    fields(e, "id school major degree startDate endDate isCurrent", "/proposed/education")
                    _uuid4(e["id"], "/proposed/education/id")
                    for key in ("school", "major", "degree"):
                        string(e[key], "/proposed/education/" + key)
                    dates(e, "/proposed/education")
            else:
                for s in items:
                    string(s, "/proposed/skills")

    @_translate_b
    def apply_target(self, db, user, resume_id, revision, target, original, proposed):
        svc = self._resumes(db)
        resume = svc.get(user, resume_id, lock=True)
        svc.editable(resume)
        if resume.revision != revision:
            raise RevisionConflict(resume.revision)
        if target_value(resume.document_json, target) != original:
            raise StateConflict("suggestion target is stale")
        result = replace_target(resume.document_json, target, proposed)
        svc.check_references(db, user, resume.workspace_id, result, resume.jd_snapshot_json)
        svc._cas(resume, revision, document_json=result)
        return self.resume(db, user, resume_id, lock=False)


# --------------------------------------------------------------------------- #
# 组装 B 的 Dependencies / 导出协调器 / 处理器 / 文档桥
# --------------------------------------------------------------------------- #

_RESOURCE_MODELS = {
    "RESUME": Resume,
    "RESUME_VERSION": ResumeVersion,
    "EXPORT": Export,
    "PREPARATION": Preparation,
    "PREPARATION_EXPORT": PreparationExport,
}


def _resource_for(operation):
    if operation == "POST /api/resumes":
        return "RESUME"
    if operation.startswith("PATCH /api/resumes/"):
        return "RESUME"
    if operation.startswith("DELETE /api/resumes/"):
        return "RESUME"
    if operation.endswith("/copies") and operation.startswith("POST /api/resumes/"):
        return "RESUME"
    if operation.endswith("/versions") and operation.startswith("POST /api/resumes/"):
        return "RESUME_VERSION"
    if operation.endswith("/restorations") and operation.startswith("POST /api/resumes/"):
        return "RESUME"
    if operation == "POST /api/exports":
        return "EXPORT"
    if operation.startswith("PATCH /api/preparations/"):
        return "PREPARATION"
    if operation.endswith("/exports") and operation.startswith("POST /api/preparations/"):
        return "PREPARATION_EXPORT"
    return None


def _recheck_replay(session, user, resource_type, resource_id):
    if not resource_type or not resource_id:
        return
    model = _RESOURCE_MODELS.get(resource_type)
    if model is None:
        return
    row = session.get(model, resource_id)
    if row is None or row.user_id != user or getattr(row, "deleted_at", None) is not None:
        raise ResourceNotFound()
    parents = {
        'RESUME_VERSION': ('RESUME', 'resume_id'),
        'PREPARATION': ('RESUME_VERSION', 'resume_version_id'),
        'EXPORT': ('RESUME_VERSION', 'resume_version_id'),
        'PREPARATION_EXPORT': ('PREPARATION', 'preparation_id'),
    }
    if resource_type in parents:
        parent_type, field = parents[resource_type]
        _recheck_replay(session, user, parent_type, getattr(row, field))


@dataclass
class BIntegration:
    dependencies: Dependencies
    resume_export_handler: ExportResumeHandler
    preparation_export_handler: ExportPreparationHandler
    document_bridge: Callable
    preparations: Callable
    templates: Callable


def build_b_integration(ctx: BContext, *, session_factory, resume_renderers, preparation_renderer) -> BIntegration:
    """session_factory 返回一个裸 SQLAlchemy Session；这里不开服务器、不 commit。"""

    def unit_of_work():
        class _Uow:
            def __enter__(self):
                self.session = session_factory()
                self.tx = self.session.begin()
                return self.session

            def __exit__(self, exc_type, exc, tb):
                try:
                    if exc_type is None:
                        self.tx.commit()
                    else:
                        self.tx.rollback()
                finally:
                    self.session.close()

        return _Uow()

    async def authenticated_user(request: Request):
        return authenticate_user_id(request)

    async def verify_write(request: Request):
        _verify_write(request)

    def context(user=Depends(authenticated_user)):
        with unit_of_work() as session:
            yield session, user

    # 幂等回调
    def find_replay(session, user, operation, key, payload):
        import hmac

        digest = ctx.idempotency._digest(payload)
        old = session.scalar(
            select(Idempotency).filter_by(user_id=user, operation_key=operation, client_key=key)
        )
        if old is None:
            return None
        if not hmac.compare_digest(old.request_sha256, digest):
            raise TaskOperationError("IDEMPOTENCY_MISMATCH", "相同幂等键对应的参数不同", 409)
        if old.state != "COMPLETED":
            raise TaskOperationError("REQUEST_IN_PROGRESS", "请求仍在提交，请稍后重试", 409)
        _recheck_replay(session, user, old.resource_type, old.resource_id)
        return old.response_json

    def execute_write(session, user, operation, key, payload, action):
        from app.modules.tasks.ports import StoredResponse

        replay = ctx.idempotency.begin(session, user_id=user, operation=operation, key=key, request=payload)
        if replay is not None:
            record = session.scalar(
                select(Idempotency).filter_by(user_id=user, operation_key=operation, client_key=key)
            )
            if record is not None:
                _recheck_replay(session, user, record.resource_type, record.resource_id)
            return replay.body
        data = action()
        resource_type = _resource_for(operation)
        resource_id = (data.get("id") or data.get("resourceId")) if isinstance(data, dict) else None
        ctx.idempotency.complete(
            session, user_id=user, operation=operation, key=key,
            response=StoredResponse(200, data), resource_type=resource_type, resource_id=resource_id,
        )
        return data

    # 任务/文件回调
    def create_task(session, user, kind, resource_type, resource_id, input_data):
        from app.adapters.b_services import create_task_deferred  # 见下方函数

        return create_task_deferred(session, ctx.registry, user_id=user, kind=kind,
                                    resource_type=resource_type, resource_id=resource_id, input_data=input_data)

    def download_file(session, user, file_id, file_name):
        from app.storage import file_access

        file = file_access(session, file_id, user, ctx.relations)
        return ctx.storage.sign(file, user)

    def stage_artifact(user, purpose, data, file_name):
        key = ctx.storage.put(user, data)
        return {
            "objectKey": key,
            "size": len(data),
            "sha256": sha(data),
            "mime": _mime_for(file_name),
            "fileName": file_name,
        }

    def register_file(session, user, purpose, artifact):
        file = File(
            user_id=user,
            purpose=purpose,
            object_key=artifact["objectKey"],
            original_name=display_name(artifact["fileName"]),
            mime_type=artifact["mime"],
            size_bytes=artifact["size"],
            sha256=artifact["sha256"],
            status="READY",
        )
        session.add(file)
        session.flush()
        return file.id

    def cleanup_artifact(artifact):
        try:
            ctx.storage.delete(artifact["objectKey"])
        except Exception:
            pass

    def on_deleted(session, user, resume_id, file_ids, impact):
        for file_id in file_ids:
            if not file_id:
                continue
            file = session.get(File, file_id)
            if file is None or file.user_id != user:
                continue
            if not ctx.relations.file_referenced(session, file):
                file.status, file.deleted_at = "DELETING", now()

    def resumes(session):
        return ResumeService(
            session,
            check_references=check_references,
            generation_complete=lambda s, u, t: generation_status(s, u, t) == "SUCCEEDED",
        )

    def preparations(session):
        return PreparationService(resumes(session), verify_task=verify_task, verify_lease=verify_lease)

    common = ExportDependencies(
        unit_of_work=unit_of_work,
        service=resumes,
        inspect_layout=resume_renderers.inspect,
        find_replay=find_replay,
        execute_write=execute_write,
        create_task=create_task,
        task_info=task_info,
        download_file=download_file,
    )
    exports = ExportCoordinator(common)
    preparation_exports = PreparationExportCoordinator(
        PreparationExportDependencies(common=common, preparations=preparations)
    )

    def stage(renderer, purpose, snapshot):
        data = renderer.render(snapshot)
        return stage_artifact(snapshot["renderContext"]["userId"], purpose, data, snapshot["fileName"])

    resume_handler = ExportResumeHandler(
        exports,
        render=lambda snapshot: stage(resume_renderers, "EXPORT", snapshot),
        verify_lease=verify_lease,
        register_file=register_file,
    )
    preparation_handler = ExportPreparationHandler(
        preparation_exports,
        render=lambda snapshot: stage(preparation_renderer, "PREPARATION_EXPORT", snapshot),
        verify_lease=verify_lease,
        register_file=register_file,
    )

    def bridge(session):
        return DocumentBridge(
            resumes(session),
            verify_task=verify_task,
            verify_lease=verify_lease,
            load_suggestion=load_suggestion,
            verify_fact_preservation=verify_fact_preservation,
        )

    def deletion(session):
        return DeletionService(
            resumes(session),
            count_sources=count_sources,
            count_tasks=count_tasks,
            on_deleted=on_deleted,
        )

    def templates(session):
        return TemplateService(session, preview_url=None)

    dependencies = Dependencies(
        context=context,
        verify_write=verify_write,
        execute_write=execute_write,
        check_references=check_references,
        generation_complete=lambda s, u, t: generation_status(s, u, t) == "SUCCEEDED",
        generation_status=generation_status,
        resolve_workspace_snapshot=resolve_workspace_snapshot,
        inspect_layout=resume_renderers.inspect,
        authenticated_user=authenticated_user,
        exports=exports,
        preparations=preparations,
        preparation_exports=preparation_exports,
        deletion=deletion,
        templates=templates,
    )
    return BIntegration(dependencies, resume_handler, preparation_handler, bridge, preparations, templates)


def create_task_deferred(session, registry, *, user_id, kind, resource_type, resource_id, input_data):
    """F07：B 的导出先建 Task 再插入 Export 记录，故跳过 handler.check，
    把完整性检查延后到 worker 领取（Runtime.claim 会再跑 check）。"""
    from app.modules.tasks.models import OutboxEvent

    for identifier in (user_id, resource_id):
        TypeAdapter(ResourceId).validate_python(identifier)
    kind, resource_type = Kind(kind), ResourceType(resource_type)
    if KIND_RESOURCE[kind] != resource_type:
        raise ValueError("Task kind does not match resource type")
    task = Task(
        user_id=user_id,
        kind=kind.value,
        resource_type=resource_type.value,
        resource_id=resource_id,
        input_json=deepcopy(input_data),
    )
    session.add(task)
    session.flush()
    session.add(OutboxEvent(user_id=user_id, task_id=task.id, attempt=task.attempt))
    session.flush()
    return task.id
