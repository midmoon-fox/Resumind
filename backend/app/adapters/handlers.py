"""把 A 的两类资料/JD 处理器与 B 的两类导出处理器注册成 C 的 Handler（合并方案 5.3）。

C 的 Registry 期望 Handler(check/compute/save/fail/retry/cancel/invalidate)，
其中 check/save/fail/retry/cancel/invalidate 在 SQL 事务内，compute 在事务外。
A 原 handlers.py 使用 prepare/execute/commit 旧协议，这里重写为 C 协议并复用其
extract_parts / check_parts 与 A 的服务函数。
"""
from copy import deepcopy

from sqlalchemy import select

from app.core import invalid
from app.handlers import check_parts, extract_parts
from app.models import (
    Experience,
    File,
    JobDescription,
    JdVersion,
    Material,
    Segment,
    uid,
)
from app.ports import JdAnalysis, MaterialAnalysis, TextPart
from app.services import add_source, leaves
from app.modules.tasks.registry import Handler, HandlerFailure, ResourceUnavailable, TaskInput
from app.modules.ai.errors import AiFailure
from app.modules.tasks.schemas import TaskError


def _get(db, cls, resource_id, user_id, lock=False):
    query = select(cls).where(cls.id == resource_id, cls.user_id == user_id)
    if hasattr(cls, "deleted_at"):
        query = query.where(cls.deleted_at.is_(None))
    if lock:
        query = query.with_for_update()
    obj = db.scalar(query.execution_options(populate_existing=True))
    if obj is None:
        raise ResourceUnavailable()
    return obj


class MaterialHandler:
    kind = "PARSE_MATERIAL"

    def __init__(self, storage, ai):
        self.storage, self.ai = storage, ai

    def check(self, db, task, lock):
        obj = _get(db, Material, task.resource_id, task.user_id, lock=lock)
        if task.data.get("materialId") != obj.id:
            raise ResourceUnavailable()
        if lock:
            if obj.status not in {"QUEUED", "PROCESSING", "FAILED"}:
                raise ResourceUnavailable()
            if obj.file_id:
                file = db.get(File, obj.file_id)
                if (
                    file is None
                    or file.user_id != task.user_id
                    or file.purpose != "MATERIAL"
                    or file.status != "READY"
                    or file.id != task.data.get("fileId")
                    or file.object_key != task.data.get("objectKey")
                ):
                    raise ResourceUnavailable()
            elif obj.input_text != task.data.get("text"):
                raise ResourceUnavailable()
        return obj

    def compute(self, task):
        snapshot = task.data
        if snapshot.get("fileId"):
            parts = extract_parts(self.storage.read(snapshot["objectKey"]), snapshot["mimeType"], self.ai)
        else:
            parts = [TextPart(text=snapshot["text"], page=None, extractionMethod="TEXT")]
        check_parts(parts)
        segments = []
        for part in parts:
            for offset in range(0, len(part.text), 4000):
                text = part.text[offset : offset + 4000]
                if text.strip():
                    segments.append(
                        dict(
                            id=uid(),
                            ordinal=len(segments) + 1,
                            page=part.page,
                            text=text,
                            extractionMethod=part.extraction_method,
                            materialId=snapshot["materialId"],
                            attribution="UNSPECIFIED",
                        )
                    )
        analysis = MaterialAnalysis.model_validate(self.ai.extract_experiences(deepcopy(segments)))
        if len({c.candidate_key for c in analysis.candidates}) != len(analysis.candidates):
            invalid("模型 candidateKey 重复")
        segment_ids = {p["id"] for p in segments}
        for candidate in analysis.candidates:
            fields = leaves(candidate.data.model_dump(by_alias=True))
            covered = set()
            for source in candidate.provenance:
                if (
                    source.origin != "MATERIAL"
                    or source.turn_ids
                    or not source.segment_ids
                    or not set(source.segment_ids) <= segment_ids
                    or source.json_pointer not in fields
                ):
                    invalid("模型返回不可信的字段来源")
                covered.add(source.json_pointer)
            required = {p for p, value in fields.items() if value not in ("", None, False)}
            if not required <= covered:
                invalid("模型经历事实缺少原材料来源")
        return dict(segments=segments, analysis=analysis)

    def save(self, db, task, result):
        obj = self.check(db, task, True)
        for part in result["segments"]:
            db.add(
                Segment(
                    id=part["id"],
                    user_id=task.user_id,
                    material_id=obj.id,
                    ordinal=part["ordinal"],
                    page_no=part["page"],
                    text=part["text"],
                    extraction_method=part["extractionMethod"],
                )
            )
        db.flush()
        for candidate in result["analysis"].candidates:
            exp = Experience(
                user_id=task.user_id,
                workspace_id=obj.workspace_id,
                generation_task_id=task.id,
                candidate_key=candidate.candidate_key,
                type=candidate.type,
                data_json=candidate.data.model_dump(by_alias=True),
                status="CANDIDATE",
                revision=1,
                excluded=False,
            )
            db.add(exp)
            db.flush()
            for source in candidate.provenance:
                for segment_id in set(source.segment_ids):
                    add_source(db, exp, source.json_pointer, origin="MATERIAL", segment_id=segment_id)
        obj.status, obj.error_json = "READY", None

    def fail(self, db, task, error):
        obj = _get(db, Material, task.resource_id, task.user_id, lock=True)
        obj.status, obj.error_json = "FAILED", TaskError.model_validate(error).model_dump(by_alias=True, exclude_none=True)

    def retry(self, db, task):
        obj = _get(db, Material, task.resource_id, task.user_id, lock=True)
        if obj.status != "FAILED":
            raise ResourceUnavailable()
        obj.status, obj.error_json = "QUEUED", None

    def cancel(self, db, task):
        query = select(Material).where(Material.id == task.resource_id, Material.user_id == task.user_id).with_for_update()
        obj = db.scalar(query.execution_options(populate_existing=True))
        if obj is None:
            raise ResourceUnavailable()
        if obj.deleted_at is None:
            obj.status = "FAILED"
            obj.error_json = dict(code="TASK_CANCELLED", message="任务已取消", canRetry=False)

    def invalidate(self, db, task, error):
        obj = _get(db, Material, task.resource_id, task.user_id, lock=True)
        obj.status, obj.error_json = "FAILED", TaskError.model_validate(error).model_dump(by_alias=True, exclude_none=True)


class JdHandler(MaterialHandler):
    kind = "ANALYZE_JD"

    def check(self, db, task, lock):
        version = _get(db, JdVersion, task.resource_id, task.user_id, lock=lock)
        _get(db, JobDescription, version.jd_id, task.user_id, lock=lock)
        if task.data.get("jdVersionId") != version.id:
            raise ResourceUnavailable()
        if lock:
            if version.status not in {"QUEUED", "ANALYZING", "FAILED"}:
                raise ResourceUnavailable()
            if version.file_id:
                file = db.get(File, version.file_id)
                if (
                    file is None
                    or file.user_id != task.user_id
                    or file.status != 'READY'
                    or file.purpose != 'JD'
                    or file.object_key != task.data.get("objectKey")
                    or file.id != task.data.get("fileId")
                ):
                    raise ResourceUnavailable()
            elif version.original_text != task.data.get("text"):
                raise ResourceUnavailable()
        return version

    def compute(self, task):
        snapshot = task.data
        if snapshot.get("fileId"):
            parts = extract_parts(self.storage.read(snapshot["objectKey"]), snapshot["mimeType"], self.ai)
            check_parts(parts)
            text = "\n".join(p.text for p in parts)
        else:
            text = snapshot["text"]
        analysis = JdAnalysis.model_validate(self.ai.analyze_jd(text))
        ids = [r.id for r in analysis.requirements]
        if len(set(ids)) != len(ids):
            invalid("模型要求 ID 重复")
        for r in analysis.requirements:
            if not r.evidence_quote or r.evidence_quote not in text:
                invalid("模型JD分析缺少原文依据")
        return dict(text=text, analysis=analysis)

    def save(self, db, task, result):
        version = self.check(db, task, True)
        version.original_text = result["text"]
        version.job_title, version.company_name = result["analysis"].job_title, result["analysis"].company_name
        version.requirements_json = [r.model_dump(by_alias=True) for r in result["analysis"].requirements]
        version.status = "REVIEW_REQUIRED"

    def fail(self, db, task, error):
        version = _get(db, JdVersion, task.resource_id, task.user_id, lock=True)
        version.status = "FAILED"

    def retry(self, db, task):
        version = _get(db, JdVersion, task.resource_id, task.user_id, lock=True)
        if version.status != "FAILED":
            raise ResourceUnavailable()
        version.status = "QUEUED"

    def cancel(self, db, task):
        version = _get(db, JdVersion, task.resource_id, task.user_id, lock=True)
        jd = db.get(JobDescription, version.jd_id)
        if jd is not None and jd.deleted_at is None and version.status != "CONFIRMED":
            version.status = "FAILED"

    def invalidate(self, db, task, error):
        version = _get(db, JdVersion, task.resource_id, task.user_id, lock=True)
        version.status = "FAILED"


def _ai_compute(compute):
    def execute(task):
        try:
            return compute(task)
        except AiFailure as error:
            raise HandlerFailure(error.error, retry_after_seconds=error.retry_after_seconds) from None
    return execute


def material_handler(storage, ai) -> Handler:
    h = MaterialHandler(storage, ai)
    return Handler(
        check=h.check,
        compute=_ai_compute(h.compute),
        save=h.save,
        fail=h.fail,
        retry=h.retry,
        cancel=h.cancel,
        invalidate=h.invalidate,
    )


def jd_handler(storage, ai) -> Handler:
    h = JdHandler(storage, ai)
    return Handler(
        check=h.check,
        compute=_ai_compute(h.compute),
        save=h.save,
        fail=h.fail,
        retry=h.retry,
        cancel=h.cancel,
        invalidate=h.invalidate,
    )


def export_handler(b_handler, coordinator, resource_model) -> Handler:
    """把 B 的 ExportResumeHandler/ExportPreparationHandler 适配成 C 的 Handler。"""

    def check(db, task, lock):
        record, version = coordinator.accessible(db, task.user_id, task.resource_id)
        if record.task_id != task.id:
            raise ResourceUnavailable()
        if lock:
            if resource_model.__name__ == 'PreparationExport':
                coordinator.accessible(db, task.user_id, task.resource_id, lock=True)
            else:
                coordinator.deps.service(db).get(task.user_id, version.resume_id, lock=True)
            row = db.scalar(
                select(resource_model)
                .where(resource_model.id == task.resource_id, resource_model.user_id == task.user_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if row is None or row.file_id is not None:
                raise ResourceUnavailable()

    def compute(task):
        return b_handler.execute(task.user_id, task.resource_id)

    def save(db, task, artifact):
        b_handler.commit_result(db, task.user_id, task.resource_id, None, artifact)

    def fail(db, task, error):
        return None

    def retry(db, task):
        b_handler.check_retry(db, task.user_id, task.resource_id, task.id)

    def cancel(db, task):
        b_handler.check_cancel(db, task.user_id, task.resource_id, task.id)

    def invalidate(db, task, error):
        return None

    return Handler(
        check=check,
        compute=compute,
        save=save,
        fail=fail,
        retry=retry,
        cancel=cancel,
        invalidate=invalidate,
    )
