"""A 的 TaskPort 协议 → C 的统一任务框架（合并方案 F03/F04/F13）。

A 的路由通过 app.state.tasks 调用 create_task / latest_task_id / cancel_resource /
purge_resource_input；本适配器把它们落到 C 的 ai_tasks / outbox_events 与 Registry。
"""
from sqlalchemy import select

from app.core import conflict
from app.models import JdVersion
from app.modules.tasks.lifecycle import TERMINAL, cancel_locked
from app.modules.tasks.models import Task
from app.modules.tasks.registry import Registry
from app.modules.tasks.service import create_task as c_create_task
from app.ports import TaskRef


class ATaskPort:
    def __init__(self, registry: Registry):
        self.registry = registry

    def create_task(self, db, *, user_id, kind, resource_type, resource_id, input_json):
        data = dict(input_json)
        # F04：C 的 create_task 对 JD_VERSION 强制要求 input_data['jdId']，
        # A 的 ANALYZE_JD 输入只带 jdVersionId，这里从本人 JdVersion 读取父 jdId。
        if kind == "ANALYZE_JD":
            version = db.get(JdVersion, resource_id)
            if version is None or version.user_id != user_id:
                from app.core import missing
                missing()
            data["jdId"] = version.jd_id
        task = c_create_task(
            db,
            self.registry,
            user_id=user_id,
            kind=kind,
            resource_type=resource_type,
            resource_id=resource_id,
            input_data=data,
        )
        return TaskRef(task.id, task.status)

    def latest_task_id(self, db, user_id, resource_type, resource_id):
        return db.scalar(
            select(Task.id)
            .where(
                Task.user_id == user_id,
                Task.resource_type == resource_type,
                Task.resource_id == resource_id,
            )
            .order_by(Task.created_at.desc(), Task.id.desc())
            .limit(1)
        )

    def cancel_resource(self, db, user_id, resource_type, resource_id):
        # 删除父资源时，按稳定 ID 顺序锁定并取消所有未终态任务（锁序与 worker 一致，F13）。
        tasks = list(
            db.scalars(
                select(Task)
                .where(
                    Task.user_id == user_id,
                    Task.resource_type == resource_type,
                    Task.resource_id == resource_id,
                    Task.status.notin_(TERMINAL),
                )
                .order_by(Task.id)
                .with_for_update()
            )
        )
        for task in tasks:
            cancel_locked(db, self.registry, task)

    def purge_resource_input(self, db, user_id, resource_type, resource_id):
        # F20：终态任务的原始输入清理，保留墓碑（不含业务正文，仅清掉私有原文）。
        for task in db.scalars(
            select(Task).where(
                Task.user_id == user_id,
                Task.resource_type == resource_type,
                Task.resource_id == resource_id,
                Task.status.in_(TERMINAL),
            )
        ):
            task.input_json = {"purged": True}

    def assert_lease(self, db, ctx):
        # 兼容 A 旧 handler 的协议；新 handler 由 C Runtime._finish 统一核验租约。
        task = db.get(Task, ctx.task_id, with_for_update=True)
        if (
            task is None
            or task.user_id != ctx.user_id
            or task.status != "RUNNING"
            or task.attempt != ctx.attempt
            or task.lease_token != ctx.lease_token
        ):
            conflict("任务租约失效")
