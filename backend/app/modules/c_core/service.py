"""C orchestration, shared transactions and six concrete task handlers."""

from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select

from app.modules.ai.errors import AiFailure
from app.modules.ai.experience_schemas import ExperienceData
from app.modules.c_core.abilities import INTRODUCTION_VERSION
from app.modules.c_core.models import (
    FollowupTurn,
    RecommendationRun,
    RecommendedJob,
    Suggestion,
)
from app.modules.c_core.rewrite_policy import REWRITE_VERSION
from app.modules.c_core.validation import clone, read_target, revision, state
from app.modules.followups import service as followups
from app.modules.tasks.lifecycle import TaskOperationError
from app.modules.tasks.models import Task
from app.modules.tasks.registry import Handler, HandlerFailure, ResourceUnavailable
from app.modules.tasks.schemas import Kind, ResourceType, TaskError
from app.modules.tasks.service import create_task, resource_ref


def accepted(task):
    ref = resource_ref(task)
    return {
        "taskId": task.id,
        "resourceType": ref.resourceType.value,
        "resourceId": ref.resourceId,
        "status": task.status,
        "statusUrl": f"/api/tasks/{task.id}",
        "resourceUrl": ref.resourceUrl,
    }


def utc(value):
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


class CServices:
    def __init__(self, registry, a, b, abilities):
        self.registry, self.a, self.b, self.abilities = registry, a, b, abilities

    def register(self):
        for kind in (
            Kind.GENERATE_QUESTION,
            Kind.ANALYZE_ANSWER,
            Kind.GENERATE_RESUME,
            Kind.REWRITE_ITEM,
            Kind.GENERATE_PREPARATION,
            Kind.RECOMMEND_JOBS,
        ):
            self.registry.register(
                kind,
                Handler(
                    self.check,
                    self.compute,
                    self.save,
                    self.fail,
                    self.retry,
                    self.cancel,
                    self.invalidate,
                ),
            )

    def suggestion(self, db, user, identifier, lock=False):
        row = db.get(Suggestion, identifier)
        if row is None or row.user_id != user:
            raise ResourceUnavailable()
        # Parent before child across HTTP and worker paths.
        resume = self.b.resume(db, user, row.resume_id, lock)
        if lock:
            db.refresh(row, with_for_update=True)
        return row, resume

    def run(self, db, user, identifier, lock=False):
        row = db.get(RecommendationRun, identifier)
        if row is None or row.user_id != user:
            raise ResourceUnavailable()
        self.b.version(db, user, row.resume_version_id, lock)
        if lock:
            db.refresh(row, with_for_update=True)
        return row

    def job(self, db, user, identifier, lock=False):
        row = db.get(RecommendedJob, identifier)
        if row is None or row.user_id != user:
            raise ResourceUnavailable()
        self.run(db, user, row.run_id, lock)
        if lock:
            db.refresh(row, with_for_update=True)
        return row

    def create_generation(self, db, user, request):
        workspace = self.a.workspace(db, user, request.workspaceId, True)
        revision(workspace["revision"], request.baseWorkspaceRevision)
        values = self.a.facts(
            db,
            user,
            request.workspaceId,
            sorted(ref.id for ref in request.experienceRevisions),
            True,
        )
        mapping = {value["id"]: value for value in values}
        if set(mapping) != {ref.id for ref in request.experienceRevisions}:
            raise ResourceUnavailable()
        facts = []
        for ref in request.experienceRevisions:
            fact = mapping[ref.id]
            revision(fact["revision"], ref.revision)
            state(fact["status"] == "CONFIRMED" and not fact["excluded"])
            ExperienceData.model_validate(fact["data"])
            facts.append(clone(fact))
        template = self.b.template(
            db, request.templateId, request.templateVersion, request.sectionTypes
        )
        payload = {
            "workspaceId": request.workspaceId,
            "workspaceRevision": workspace["revision"],
            "profile": clone(workspace["profile"]),
            "direction": workspace.get("direction"),
            "jdSnapshot": clone(workspace.get("jdSnapshot")),
            "facts": facts,
            "request": request.model_dump(),
            "template": clone(template),
        }
        identifier = self.b.create_resume(db, user, payload, request.model_dump())
        return create_task(
            db,
            self.registry,
            user_id=user,
            kind=Kind.GENERATE_RESUME,
            resource_type=ResourceType.RESUME,
            resource_id=identifier,
            input_data=payload,
            prompt_version="resume-1.1.0",
            bind=lambda task: self.b.bind_task(db, user, "RESUME", identifier, task.id),
        )

    def create_suggestion(self, db, user, identifier, request):
        resume = self.b.resume(db, user, identifier, True)
        revision(resume["revision"], request.baseRevision)
        target = request.target.model_dump()
        profile_context = clone(resume['document']['profile'])
        profile_context.pop('photoData', None)
        original = read_target(resume["document"], target)
        self.b.validate_target(target, original)
        row = Suggestion(
            user_id=user,
            resume_id=identifier,
            base_revision=request.baseRevision,
            target_json=target,
            original_json=clone(original),
        )
        db.add(row)
        db.flush()
        return create_task(
            db,
            self.registry,
            user_id=user,
            kind=Kind.REWRITE_ITEM,
            resource_type=ResourceType.SUGGESTION,
            resource_id=row.id,
            input_data={
                "resumeId": identifier,
                "baseRevision": request.baseRevision,
                "target": target,
                "original": original,
                "instruction": request.instruction,
                "templateId": resume["templateId"],
                "rewritePromptVersion": REWRITE_VERSION,
                "profile": profile_context,
                "jdSnapshot": clone(resume.get('jdSnapshot')),
                "module": clone(next(s for s in resume['document']['sections'] if s['id'] == target['sectionId'])),
            },
            prompt_version=REWRITE_VERSION,
            bind=lambda task: setattr(row, "task_id", task.id),
        )

    def suggestion_view(self, db, user, identifier):
        row, resume = self.suggestion(db, user, identifier)
        status = (
            "STALE"
            if row.status == "READY" and resume["revision"] != row.base_revision
            else row.status
        )
        return {
            "id": row.id,
            "taskId": row.task_id,
            "resumeId": row.resume_id,
            "baseRevision": row.base_revision,
            "target": row.target_json,
            "original": row.original_json,
            "proposed": row.proposed_json,
            "explanation": row.explanation,
            "needsFactConfirmation": row.needs_fact_confirmation,
            "status": status,
            "appliedRevision": row.applied_revision,
            "createdAt": utc(row.created_at),
        }

    def apply(self, db, user, identifier, request):
        row, resume = self.suggestion(db, user, identifier, True)
        state(
            row.status == "READY"
            and not row.needs_fact_confirmation
            and row.proposed_json is not None
        )
        revision(resume["revision"], request.baseRevision)
        revision(resume["revision"], row.base_revision)
        state(read_target(resume["document"], row.target_json) == row.original_json)
        result = self.b.apply_target(
            db,
            user,
            row.resume_id,
            row.base_revision,
            row.target_json,
            row.original_json,
            row.proposed_json,
        )
        if result["id"] != row.resume_id or result["revision"] != row.base_revision + 1:
            raise RuntimeError("B did not advance the full document revision")
        row.status, row.applied_revision = "APPLIED", result["revision"]
        return result

    def reject(self, db, user, identifier):
        row, _ = self.suggestion(db, user, identifier, True)
        state(row.status in {"READY", "STALE"})
        row.status = "REJECTED"
        db.flush()
        return self.suggestion_view(db, user, identifier)

    def create_preparation(self, db, user, request):
        version = self.b.version(db, user, request.resumeVersionId, True)
        payload = {
            "request": request.model_dump(),
            "version": clone(version),
            "resumeVersionId": request.resumeVersionId,
        }
        prompt_version = "preparation-1.1.0"
        if request.type == "INTRODUCTION":
            prompt_version = INTRODUCTION_VERSION
            payload["preparationPromptVersion"] = prompt_version
        identifier = self.b.create_preparation(db, user, request.model_dump())
        return create_task(
            db,
            self.registry,
            user_id=user,
            kind=Kind.GENERATE_PREPARATION,
            resource_type=ResourceType.PREPARATION,
            resource_id=identifier,
            input_data=payload,
            prompt_version=prompt_version,
            bind=lambda task: self.b.bind_task(db, user, "PREPARATION", identifier, task.id),
        )

    def create_recommendation(self, db, user, request):
        version = self.b.version(db, user, request.resumeVersionId, True)
        if not self.abilities.source.available:
            from app.modules.tasks.lifecycle import TaskOperationError

            raise TaskOperationError("SOURCE_UNAVAILABLE", "真实岗位来源尚未启用", 503)
        row = RecommendationRun(
            user_id=user,
            resume_version_id=request.resumeVersionId,
            filters_json=request.model_dump(),
        )
        db.add(row)
        db.flush()
        return create_task(
            db,
            self.registry,
            user_id=user,
            kind=Kind.RECOMMEND_JOBS,
            resource_type=ResourceType.RECOMMENDATION_RUN,
            resource_id=row.id,
            input_data={
                "resumeVersionId": request.resumeVersionId,
                "version": clone(version),
                "filters": request.model_dump(),
                "sourceConfig": self.abilities.source.config_id,
            },
            prompt_version="recommendation-1.0.0",
            bind=lambda task: setattr(row, "task_id", task.id),
        )

    def run_view(self, db, user, identifier):
        row = self.run(db, user, identifier)
        task = db.get(Task, row.task_id)
        jobs = list(
            db.scalars(
                select(RecommendedJob)
                .where(RecommendedJob.run_id == row.id)
                .order_by(RecommendedJob.created_at, RecommendedJob.id)
            )
        )
        return {
            "id": row.id,
            "taskId": row.task_id,
            "resumeVersionId": row.resume_version_id,
            "status": task.status,
            "filters": row.filters_json,
            "error": task.error_json,
            "jobs": [
                {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "city": job.city,
                    "salaryText": job.salary_text,
                    "sourceUrl": job.source_url,
                    "fetchedAt": utc(job.fetched_at),
                    "publishedAt": utc(job.published_at) if job.published_at else None,
                    "availability": job.availability,
                    "reasons": job.reasons_json,
                    "gaps": job.gaps_json,
                }
                for job in jobs
            ],
        }

    def save_job(self, db, user, identifier, request):
        job = self.job(db, user, identifier, True)
        state(job.availability != "EXPIRED")
        return self.a.create_jd(
            db,
            user,
            {
                "sourceKey": job.source_key,
                "sourceJobId": job.source_job_id,
                "sourceUrl": job.source_url,
                "originalText": job.description_text,
                "title": job.title,
                "company": job.company,
                "fetchedAt": utc(job.fetched_at),
            },
            request.title,
        )

    def check(self, db, task, lock):
        if task.kind in {Kind.GENERATE_QUESTION, Kind.ANALYZE_ANSWER}:
            row = followups.owned(db, self.a, task.user_id, task.resource_id, lock)
            if lock:
                if (
                    row.last_task_id != task.id
                    or row.status == "COMPLETED"
                    or row.revision != task.data["baseSessionRevision"]
                ):
                    raise ResourceUnavailable()
                expected = (
                    "GENERATING" if task.kind == Kind.GENERATE_QUESTION else "ANALYZING_ANSWER"
                )
                if row.status not in {expected, "FAILED"}:
                    raise ResourceUnavailable()
                values = self.a.facts(
                    db,
                    task.user_id,
                    row.workspace_id,
                    sorted(v["id"] for v in task.data["facts"]),
                    True,
                )
                if {(v["id"], v["revision"]) for v in values} != {
                    (v["id"], v["revision"]) for v in task.data["facts"]
                } or any(v["excluded"] for v in values):
                    raise ResourceUnavailable()
                if task.kind == Kind.ANALYZE_ANSWER:
                    turn = followups.current_turn(db, row, task.data["turnId"])
                    if turn.status != "ANALYZING" or turn.answer != task.data["answer"]:
                        raise ResourceUnavailable()
        elif task.kind == Kind.REWRITE_ITEM:
            row, _ = self.suggestion(db, task.user_id, task.resource_id, lock)
            if lock and (row.task_id != task.id or row.status not in {"GENERATING", "FAILED"}):
                raise ResourceUnavailable()
        elif task.kind == Kind.RECOMMEND_JOBS:
            row = self.run(db, task.user_id, task.resource_id, lock)
            if row.task_id != task.id:
                raise ResourceUnavailable()
        else:
            self.b.check_task(db, task, lock)

    def compute(self, task):
        try:
            return self.abilities.compute(task)
        except AiFailure as error:
            raise HandlerFailure(
                error.error, retry_after_seconds=error.retry_after_seconds
            ) from None
        except (ValidationError, ValueError, TypeError, KeyError, TaskOperationError):
            raise HandlerFailure(
                TaskError(
                    code="MODEL_INVALID_OUTPUT",
                    message="模型结果未通过结构或内容校验",
                    canRetry=False,
                )
            ) from None

    def invalidate(self, db, task, error):
        try:
            if task.kind in {Kind.GENERATE_QUESTION, Kind.ANALYZE_ANSWER}:
                row = followups.owned(db, self.a, task.user_id, task.resource_id, True)
                if row.last_task_id == task.id and row.status != "COMPLETED":
                    row.status = "FAILED"
            elif task.kind == Kind.REWRITE_ITEM:
                row, _ = self.suggestion(db, task.user_id, task.resource_id, True)
                if row.task_id == task.id and row.status == "GENERATING":
                    row.status = "FAILED"
            elif task.kind != Kind.RECOMMEND_JOBS:
                self.b.invalidate_task(db, task)
        except ResourceUnavailable:
            pass  # Deleted/foreign resources must remain untouched.

    def save(self, db, task, computed):
        value = computed.value
        if computed.metadata:
            row = db.get(Task, task.id)
            row.prompt_version = computed.metadata.promptVersion
            row.model_identifier = computed.metadata.responseModel
        if task.kind == Kind.GENERATE_QUESTION:
            row = followups.owned(db, self.a, task.user_id, task.resource_id, True)
            if value is None:
                row.status, row.ended_reason = "COMPLETED", "达到轮次上限或暂无待补充主题"
            else:
                state(
                    row.rounds_shown < row.max_rounds
                    and value["topic"] not in row.asked_topics_json
                    and value["topic"] not in row.skipped_topics_json
                )
                turn = FollowupTurn(
                    user_id=task.user_id,
                    session_id=row.id,
                    ordinal=row.rounds_shown + 1,
                    status="AWAITING_ANSWER",
                    question=value["question"],
                    reason=value["reason"],
                    experience_id=value["experienceId"],
                    topic=value["topic"],
                )
                db.add(turn)
                db.flush()
                row.current_turn_id, row.status = turn.id, "AWAITING_ANSWER"
                row.rounds_shown += 1
                row.asked_topics_json = [*row.asked_topics_json, value["topic"]]
            row.revision += 1
        elif task.kind == Kind.ANALYZE_ANSWER:
            row = followups.owned(db, self.a, task.user_id, task.resource_id, True)
            turn = followups.current_turn(db, row, task.data["turnId"])
            state(turn.status == "ANALYZING")
            turn.candidate_updates_json, turn.status = value, "REVIEW_REQUIRED"
            row.status, row.revision = "REVIEW_REQUIRED", row.revision + 1
        elif task.kind == Kind.REWRITE_ITEM:
            row, resume = self.suggestion(db, task.user_id, task.resource_id, True)
            row.proposed_json, row.explanation = value["proposed"], value["explanation"]
            row.needs_fact_confirmation = value["needsFactConfirmation"]
            row.status = "READY" if resume["revision"] == row.base_revision else "STALE"
        elif task.kind == Kind.GENERATE_RESUME:
            self.b.save_generated(db, task, value)
        elif task.kind == Kind.GENERATE_PREPARATION:
            self.b.save_preparation(db, task, value)
        else:
            for item in value:
                fields = {
                    key: item[key]
                    for key in (
                        "source_key",
                        "source_job_id",
                        "source_url",
                        "title",
                        "company",
                        "city",
                        "salary_text",
                        "description_text",
                        "availability",
                        "reasons_json",
                        "gaps_json",
                    )
                }
                for key in ("published_at", "fetched_at"):
                    fields[key] = (
                        datetime.fromisoformat(item[key]).astimezone(UTC).replace(tzinfo=None)
                        if item[key]
                        else None
                    )
                db.add(RecommendedJob(user_id=task.user_id, run_id=task.resource_id, **fields))

    def fail(self, db, task, error):
        self._state(db, task, "FAILED")

    def cancel(self, db, task):
        self._state(db, task, "FAILED")

    def retry(self, db, task):
        self.check(db, task, True)
        if task.kind == Kind.REWRITE_ITEM:
            row, resume = self.suggestion(db, task.user_id, task.resource_id, True)
            revision(resume["revision"], row.base_revision)
        self._state(db, task, "GENERATING")

    def _state(self, db, task, status):
        if task.kind in {Kind.GENERATE_QUESTION, Kind.ANALYZE_ANSWER}:
            row = followups.owned(db, self.a, task.user_id, task.resource_id, True)
            if row.status == "COMPLETED" or row.last_task_id != task.id:
                return
            row.status = (
                "ANALYZING_ANSWER"
                if status == "GENERATING" and task.kind == Kind.ANALYZE_ANSWER
                else status
            )
        elif task.kind == Kind.REWRITE_ITEM:
            row, _ = self.suggestion(db, task.user_id, task.resource_id, True)
            row.status = status
        elif task.kind not in {Kind.RECOMMEND_JOBS}:
            self.b.task_state(db, task, status)
