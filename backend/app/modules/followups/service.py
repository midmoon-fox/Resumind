"""Follow-up state transitions. Caller provides transaction and A's fact services."""

from datetime import UTC

from sqlalchemy import select

from app.modules.c_core.models import FollowupSession, FollowupTurn
from app.modules.c_core.validation import clone, invalid, revision, state
from app.modules.tasks.models import Task
from app.modules.tasks.registry import ResourceUnavailable
from app.modules.tasks.schemas import Kind, ResourceType
from app.modules.tasks.service import create_task


def owned(db, a, user, identifier, lock=False):
    row = db.get(FollowupSession, identifier)
    if row is None or row.user_id != user:
        raise ResourceUnavailable()
    # Parent -> session lock order is shared with worker and workspace creation.
    a.workspace(db, user, row.workspace_id, lock)
    if lock:
        db.refresh(row, with_for_update=True)
    return row


def facts(db, a, user, row):
    refs = row.experience_refs_json
    values = a.facts(db, user, row.workspace_id, sorted(v["id"] for v in refs), True)
    indexed = {value["id"]: value for value in values}
    if set(indexed) != {ref["id"] for ref in refs}:
        raise ResourceUnavailable()
    result = []
    for ref in refs:
        value = indexed[ref["id"]]
        revision(value["revision"], ref["revision"])
        if value["excluded"]:
            raise ResourceUnavailable()
        result.append(clone(value))
    return result


def queue(db, registry, a, row, kind, *, turn=None):
    current = facts(db, a, row.user_id, row)
    payload = {
        "sessionId": row.id,
        "workspaceId": row.workspace_id,
        "baseSessionRevision": row.revision,
        "profile": clone(row.profile_snapshot_json),
        "direction": row.direction_snapshot,
        "jdSnapshot": clone(row.jd_snapshot_json),
        "facts": current,
        "askedTopics": clone(row.asked_topics_json),
        "skippedTopics": clone(row.skipped_topics_json),
        "roundsShown": row.rounds_shown,
        "maxRounds": row.max_rounds,
    }
    if turn:
        payload.update(turnId=turn.id, answer=turn.answer, experienceId=turn.experience_id)
    row.status = "ANALYZING_ANSWER" if turn else "GENERATING"
    return create_task(
        db,
        registry,
        user_id=row.user_id,
        kind=kind,
        resource_type=ResourceType.FOLLOWUP_SESSION,
        resource_id=row.id,
        input_data=payload,
        prompt_version="answer-1.0.0" if turn else "question-1.1.0",
        bind=lambda task: setattr(row, "last_task_id", task.id),
    )


def create(db, registry, a, user, request):
    workspace = a.workspace(db, user, request.workspaceId, True)
    revision(workspace["revision"], request.baseWorkspaceRevision)
    active = workspace.get("activeFollowupSessionId")
    if active:
        old = db.get(FollowupSession, active, with_for_update=True, populate_existing=True)
        if old is not None and old.status != "COMPLETED":
            from app.modules.tasks.lifecycle import TaskOperationError

            raise TaskOperationError(details={"existingSessionId": old.id})
    values = a.facts(db, user, request.workspaceId, sorted(request.experienceIds), True)
    if {v["id"] for v in values} != set(request.experienceIds) or any(
        v["excluded"] for v in values
    ):
        raise ResourceUnavailable()
    row = FollowupSession(
        user_id=user,
        workspace_id=request.workspaceId,
        profile_snapshot_json=clone(workspace["profile"]),
        direction_snapshot=workspace.get("direction"),
        jd_snapshot_json=clone(workspace.get("jdSnapshot")),
        experience_refs_json=[{"id": v["id"], "revision": v["revision"]} for v in values],
        max_rounds=request.maxRounds,
    )
    db.add(row)
    db.flush()
    a.set_active_followup(db, user, request.workspaceId, row.id)
    return queue(db, registry, a, row, Kind.GENERATE_QUESTION)


def current_turn(db, row, identifier):
    if row.current_turn_id != identifier:
        invalid("/turnId", "需要当前轮次")
    turn = db.get(FollowupTurn, identifier, with_for_update=True, populate_existing=True)
    if turn is None or turn.session_id != row.id:
        raise ResourceUnavailable()
    return turn


def answer(db, registry, a, user, identifier, request):
    row = owned(db, a, user, identifier, True)
    revision(row.revision, request.baseRevision)
    state(row.status == "AWAITING_ANSWER")
    turn = current_turn(db, row, request.turnId)
    state(turn.status == "AWAITING_ANSWER")
    turn.answer, turn.status = request.answer, "ANALYZING"
    row.revision += 1
    return queue(db, registry, a, row, Kind.ANALYZE_ANSWER, turn=turn)


def confirm(db, a, user, identifier, request):
    row = owned(db, a, user, identifier, True)
    revision(row.revision, request.baseRevision)
    state(row.status == "REVIEW_REQUIRED")
    turn = current_turn(db, row, request.turnId)
    state(turn.status == "REVIEW_REQUIRED" and turn.confirmed_updates_json is None)
    candidates = {value["candidateId"]: value for value in turn.candidate_updates_json}
    writes = []
    for update in request.updates:
        candidate = candidates.get(update.candidateId)
        if candidate is None or any(
            candidate[key] != getattr(update, key)
            for key in ("experienceId", "baseExperienceRevision")
        ):
            invalid("/updates", "确认项必须匹配当前轮候选")
        # Explicitly edited user data is their new statement, never falsely attributed to material.
        data = update.data.model_dump()
        provenance = [
            {
                "jsonPointer": "/" + key + (f"/{i}" if isinstance(value, list) else ""),
                "segmentIds": [],
                "turnIds": [turn.id],
                "origin": "FOLLOWUP",
            }
            for key, value in data.items()
            if value
            for i in (range(len(value)) if isinstance(value, list) else [0])
        ]
        writes.append({**update.model_dump(), "type": candidate["type"], "provenance": provenance})
    saved = a.confirm(db, user, row.workspace_id, turn.id, writes) if writes else []
    if len(saved) != len(writes):
        raise RuntimeError("A confirmation returned an inconsistent result")
    refs = {value["id"]: value for value in row.experience_refs_json}
    created = []
    for write, value in zip(writes, saved, strict=True):
        if value["status"] != "CONFIRMED" or value["type"] != write["type"]:
            raise RuntimeError("A must return confirmed facts")
        if write["experienceId"] is not None and value["id"] != write["experienceId"]:
            raise RuntimeError("A changed the experience identity")
        refs[value["id"]] = {"id": value["id"], "revision": value["revision"]}
        if write["experienceId"] is None:
            created.append(value["id"])
    turn.created_experience_ids_json = created
    turn.confirmed_updates_json = [value.model_dump() for value in request.updates]
    turn.status, row.status = "CONFIRMED", "READY_NEXT"
    row.experience_refs_json = list(refs.values())
    row.revision += 1
    db.flush()
    return view(db, row)


def skip(db, a, user, identifier, request):
    row = owned(db, a, user, identifier, True)
    revision(row.revision, request.baseRevision)
    state(row.status in {"AWAITING_ANSWER", "REVIEW_REQUIRED"})
    turn = current_turn(db, row, request.turnId)
    state(turn.status in {"AWAITING_ANSWER", "REVIEW_REQUIRED"})
    turn.status, turn.candidate_updates_json = "SKIPPED", []
    row.skipped_topics_json = [*row.skipped_topics_json, turn.topic]
    row.status, row.revision = "READY_NEXT", row.revision + 1
    db.flush()
    return view(db, row)


def next_question(db, registry, a, user, identifier, request):
    row = owned(db, a, user, identifier, True)
    revision(row.revision, request.baseRevision)
    state(row.status == "READY_NEXT")
    row.revision += 1
    # Even at the cap enqueue a deterministic completion task: contract remains 202.
    return queue(db, registry, a, row, Kind.GENERATE_QUESTION)


def complete(db, a, user, identifier, request):
    row = owned(db, a, user, identifier, True)
    revision(row.revision, request.baseRevision)
    state(row.status != "COMPLETED")
    if row.current_turn_id:
        turn = current_turn(db, row, row.current_turn_id)
        if turn.status not in {"CONFIRMED", "SKIPPED", "ABANDONED"}:
            turn.status, turn.candidate_updates_json = "ABANDONED", []
    row.status, row.ended_reason = "COMPLETED", request.reason
    row.revision += 1
    db.flush()
    return view(db, row)


def view(db, row):
    task = db.get(Task, row.last_task_id) if row.last_task_id else None
    turns = list(
        db.scalars(
            select(FollowupTurn)
            .where(FollowupTurn.session_id == row.id)
            .order_by(FollowupTurn.ordinal)
        )
    )
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "status": row.status,
        "revision": row.revision,
        "roundsShown": row.rounds_shown,
        "maxRounds": row.max_rounds,
        "pendingTaskId": task.id
        if task
        and task.status in {"QUEUED", "RUNNING", "CANCEL_REQUESTED"}
        and row.status != "COMPLETED"
        else None,
        "lastTaskId": row.last_task_id,
        "error": task.error_json if task else None,
        "currentTurnId": row.current_turn_id,
        "endedReason": row.ended_reason,
        "turns": [
            {
                "id": turn.id,
                "ordinal": turn.ordinal,
                "status": turn.status,
                "question": turn.question,
                "reason": turn.reason,
                "experienceId": turn.experience_id,
                "answer": turn.answer,
                "candidateUpdates": turn.candidate_updates_json,
                "createdAt": turn.created_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
            }
            for turn in turns
        ],
    }
