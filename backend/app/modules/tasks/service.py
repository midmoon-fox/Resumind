"""Caller owns the transaction, idempotency claim and resource persistence."""

import json
from collections.abc import Callable
from datetime import UTC

from sqlalchemy.orm import Session

from .models import OutboxEvent, Task
from .registry import Registry, ResourceUnavailable, TaskInput
from .schemas import (
    KIND_RESOURCE,
    RESOURCE_PATHS,
    Kind,
    ResourceId,
    ResourceRef,
    ResourceType,
    Status,
    TaskError,
    TaskView,
)


def snapshot(task: Task) -> TaskInput:
    return TaskInput(
        task.id,
        task.user_id,
        Kind(task.kind),
        ResourceType(task.resource_type),
        task.resource_id,
        task.attempt,
        json.loads(json.dumps(task.input_json, allow_nan=False)),
    )


def create_task(
    session: Session,
    registry: Registry,
    *,
    user_id: ResourceId,
    kind: Kind,
    resource_type: ResourceType,
    resource_id: ResourceId,
    input_data: dict,
    prompt_version: str | None = None,
    bind: Callable[[Task], None] | None = None,
) -> Task:
    from pydantic import TypeAdapter

    for identifier in (user_id, resource_id):
        TypeAdapter(ResourceId).validate_python(identifier)
    kind, resource_type = Kind(kind), ResourceType(resource_type)
    if KIND_RESOURCE[kind] != resource_type:
        raise ValueError("Task kind does not match resource type")
    if not isinstance(input_data, dict):
        raise ValueError("Input snapshot must be a JSON object")
    if resource_type == ResourceType.JD_VERSION:
        TypeAdapter(ResourceId).validate_python(input_data.get("jdId"))
    if prompt_version is not None and not 1 <= len(prompt_version) <= 50:
        raise ValueError("Invalid prompt version")
    frozen_input = json.loads(json.dumps(input_data, allow_nan=False))
    task = Task(
        user_id=user_id,
        kind=kind.value,
        resource_type=resource_type.value,
        resource_id=resource_id,
        input_json=frozen_input,
        prompt_version=prompt_version,
    )
    session.add(task)
    session.flush()
    if bind is not None:
        bind(task)
        session.flush()
    registry.get(kind).check(session, snapshot(task), True)
    session.add(OutboxEvent(user_id=user_id, task_id=task.id, attempt=task.attempt))
    session.flush()
    return task


def resource_ref(task: Task) -> ResourceRef:
    resource_type = ResourceType(task.resource_type)
    if resource_type == ResourceType.JD_VERSION:
        # Immutable input must carry the A-owned parent JD identifier.
        from pydantic import TypeAdapter

        jd_id = TypeAdapter(ResourceId).validate_python(task.input_json.get("jdId"))
        url = f"/api/job-descriptions/{jd_id}/versions/{task.resource_id}"
    else:
        url = f"/api/{RESOURCE_PATHS[resource_type]}/{task.resource_id}"
    return ResourceRef(resourceType=resource_type, resourceId=task.resource_id, resourceUrl=url)


def get_task(session: Session, registry: Registry, task_id: str, user_id: str) -> TaskView:
    task = session.get(Task, task_id)
    if task is None or task.user_id != user_id:
        raise ResourceUnavailable()
    registry.get(Kind(task.kind)).check(session, snapshot(task), False)
    return TaskView(
        id=task.id,
        kind=Kind(task.kind),
        status=Status(task.status),
        stage=task.stage,
        attempt=task.attempt,
        result=resource_ref(task) if task.status == "SUCCEEDED" else None,
        error=TaskError.model_validate(task.error_json) if task.error_json else None,
        createdAt=task.created_at.replace(tzinfo=UTC),
        updatedAt=task.updated_at.replace(tzinfo=UTC),
    )
