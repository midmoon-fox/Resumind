"""AServices 适配器：把 C 期望的 AServices 协议接到 A 的账户/工作区/经历/JD 服务。

异常翻译（合并方案 F10）：A 用 Problem（404/409/422），C 路由只识别
ResourceUnavailable(404) / TaskOperationError(状态码+code+details)，这里统一转换，
避免 A 的 Problem 掉进 ContractRoute 的兜底 500。
"""
from copy import deepcopy

from app.core import Problem
from app.models import Experience, JdVersion, Workspace
from app.modules.tasks.lifecycle import TaskOperationError
from app.modules.tasks.registry import ResourceUnavailable
from app.services import (
    bump,
    create_experience,
    edit_experience,
    jd_version,
    owned,
    provenance_json,
    revision,
    sources,
)


def translate(exc: Problem):
    if exc.status == 404:
        raise ResourceUnavailable() from None
    raise TaskOperationError(exc.code, exc.message, exc.status, exc.details) from None


class AServicesAdapter:
    def __init__(self, tasks):
        # tasks 是 ATaskPort，供 create_jd 复用 A 的 create_jd_from_job。
        self.tasks = tasks

    def workspace(self, db, user, workspace_id, lock):
        try:
            ws = owned(db, Workspace, workspace_id, user, lock)
        except Problem as e:
            translate(e)
        jd = None
        if ws.jd_version_id:
            try:
                version = jd_version(db, ws.jd_version_id, user, confirmed=True, lock=lock)
            except Problem as e:
                translate(e)
            jd = dict(
                sourceJdId=version.jd_id,
                sourceJdVersionId=version.id,
                jobTitle=version.job_title,
                companyName=version.company_name,
                originalText=version.original_text,
                requirements=deepcopy(version.requirements_json),
            )
        return dict(
            id=ws.id,
            revision=ws.revision,
            profile=deepcopy(ws.profile_json),
            direction=ws.direction,
            jdSnapshot=jd,
            activeFollowupSessionId=ws.active_followup_session_id,
        )

    def facts(self, db, user, workspace_id, ids, lock):
        result = []
        for eid in sorted(set(ids)):
            try:
                exp = owned(db, Experience, eid, user, lock)
            except Problem as e:
                translate(e)
            if exp.workspace_id != workspace_id:
                raise ResourceUnavailable()
            result.append(
                dict(
                    id=exp.id,
                    revision=exp.revision,
                    type=exp.type,
                    data=deepcopy(exp.data_json),
                    provenance=provenance_json(sources(db, exp)),
                    status=exp.status,
                    excluded=exp.excluded,
                )
            )
        return result

    def set_active_followup(self, db, user, workspace_id, followup_id):
        try:
            ws = owned(db, Workspace, workspace_id, user, lock=True)
        except Problem as e:
            translate(e)
        ws.active_followup_session_id = followup_id
        bump(ws)

    def confirm(self, db, user, workspace_id, turn_id, updates):
        saved = []
        for u in updates:
            kind, data = u["type"], u["data"]
            experience_id = u["experienceId"]
            base_revision = u["baseExperienceRevision"]
            try:
                if experience_id is None:
                    exp = create_experience(
                        db, user, workspace_id, kind, data, status="CONFIRMED", turn_id=turn_id
                    )
                else:
                    exp = owned(db, Experience, experience_id, user, lock=True)
                    if exp.workspace_id != workspace_id or exp.excluded:
                        raise ResourceUnavailable()
                    revision(exp, base_revision)
                    exp = edit_experience(
                        db, exp, kind=kind, data=data, status="CONFIRMED", turn_id=turn_id
                    )
            except Problem as e:
                translate(e)
            saved.append(dict(id=exp.id, revision=exp.revision, type=exp.type, status=exp.status))
        return saved

    def create_jd(self, db, user, job, title):
        from app.routes import create_jd_from_job

        try:
            jd, version, task = create_jd_from_job(
                db, self.tasks, user, title, job["originalText"], job["sourceUrl"]
            )
        except Problem as e:
            translate(e)
        return dict(
            taskId=task.id,
            resourceType="JD_VERSION",
            resourceId=version.id,
            status=task.status,
            statusUrl=f"/api/tasks/{task.id}",
            resourceUrl=f"/api/job-descriptions/{jd.id}/versions/{version.id}",
        )

    def jd_access(self, db, user, version_id):
        try:
            jd_version(db, version_id, user)
        except Problem as e:
            translate(e)
