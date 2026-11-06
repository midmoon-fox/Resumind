"""Reusable A services. Caller owns transaction; these functions never commit."""
from collections import defaultdict
from copy import deepcopy

from sqlalchemy import func, select

from .core import Problem, conflict, invalid, missing, response, stamp
from .models import (Experience, ExperienceSource, File, JdVersion, JobDescription,
                     Material, Segment, User, Workspace, now)
from .schemas import ExperienceData, Profile


def owned(db, cls, resource_id, user_id, lock=False, include_deleted=False):
    query = select(cls).where(cls.id == resource_id)
    query = query.where(cls.id == user_id) if cls is User else query.where(cls.user_id == user_id)
    if hasattr(cls, 'deleted_at') and not include_deleted:
        query = query.where(cls.deleted_at.is_(None))
    if lock:
        query = query.with_for_update()
    obj = db.scalar(query.execution_options(populate_existing=True))
    if obj is None:
        missing()
    return obj


def revision(obj, expected):
    if obj.revision != expected:
        raise Problem(409, 'REVISION_CONFLICT', '内容已更新，请核对后再保存', {'currentRevision': obj.revision})


def bump(obj):
    obj.revision += 1
    obj.updated_at = now()


def jd_version(db, version_id, user_id, jd_id=None, confirmed=False, lock=False):
    version = owned(db, JdVersion, version_id, user_id, lock)
    owned(db, JobDescription, version.jd_id, user_id, lock)
    if jd_id and version.jd_id != jd_id:
        missing()
    if confirmed and version.status != 'CONFIRMED':
        invalid('必须选择已确认的 JD 版本', '/jdVersionId')
    return version


def valid_file(db, file_id, user_id, purpose):
    file = owned(db, File, file_id, user_id, lock=True)
    if file.purpose != purpose or file.status != 'READY':
        invalid('文件用途或状态不合法', '/fileId')
    return file


def workspace_json(obj):
    return dict(id=obj.id, title=obj.title, direction=obj.direction, profile=obj.profile_json,
                jdVersionId=obj.jd_version_id, activeFollowupSessionId=obj.active_followup_session_id,
                step=obj.step, revision=obj.revision, createdAt=stamp(obj.created_at), updatedAt=stamp(obj.updated_at))


def file_json(obj):
    return dict(id=obj.id, purpose=obj.purpose, originalName=obj.original_name, mimeType=obj.mime_type,
                sizeBytes=obj.size_bytes, createdAt=stamp(obj.created_at))


def sources(db, experience, rev=None):
    return list(db.scalars(select(ExperienceSource).where(ExperienceSource.user_id == experience.user_id,
        ExperienceSource.experience_id == experience.id, ExperienceSource.experience_revision == (rev or experience.revision))))


def provenance_json(rows):
    groups = {}
    for row in rows:
        key = (row.json_pointer, row.origin)
        item = groups.setdefault(key, dict(jsonPointer=row.json_pointer, segmentIds=[], turnIds=[], origin=row.origin))
        for column, output in [('segment_id', 'segmentIds'), ('turn_id', 'turnIds')]:
            value = getattr(row, column)
            if value and value not in item[output]:
                item[output].append(value)
    return [groups[key] for key in sorted(groups)]


def experience_json(db, obj):
    return dict(id=obj.id, workspaceId=obj.workspace_id, type=obj.type, data=obj.data_json,
                provenance=provenance_json(sources(db, obj)), status=obj.status, excluded=obj.excluded,
                revision=obj.revision, createdAt=stamp(obj.created_at), updatedAt=stamp(obj.updated_at))


def jd_json(obj):
    return dict(id=obj.id, title=obj.title, currentVersionId=obj.current_version_id, revision=obj.revision,
                createdAt=stamp(obj.created_at), updatedAt=stamp(obj.updated_at))


def version_json(obj, tasks, db):
    return dict(id=obj.id, jdId=obj.jd_id, versionNo=obj.version_no, status=obj.status,
                taskId=tasks.latest_task_id(db, obj.user_id, 'JD_VERSION', obj.id), sourceType=obj.source_type,
                originalText=obj.original_text, fileId=obj.file_id, sourceUrl=obj.source_url,
                jobTitle=obj.job_title, companyName=obj.company_name, requirements=obj.requirements_json,
                createdAt=stamp(obj.created_at))


def material_json(obj, tasks, db):
    text = obj.input_text
    if text is None:
        text = db.scalar(select(Segment.text).where(Segment.material_id == obj.id, Segment.user_id == obj.user_id).order_by(Segment.ordinal).limit(1))
    return dict(id=obj.id, workspaceId=obj.workspace_id, kind=obj.kind, fileId=obj.file_id, title=obj.title,
                status=obj.status, taskId=tasks.latest_task_id(db, obj.user_id, 'MATERIAL', obj.id),
                textPreview=(text or '')[:500], error=obj.error_json, createdAt=stamp(obj.created_at))


def segment_json(obj):
    return dict(id=obj.id, materialId=obj.material_id, page=obj.page_no, ordinal=obj.ordinal, text=obj.text,
                extractionMethod=obj.extraction_method)


def paginate(db, query, cls, serializer, page, page_size, updated=False):
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    time = cls.updated_at if updated else cls.created_at
    rows = db.scalars(query.order_by(time.desc(), cls.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return dict(items=[serializer(r) for r in rows], page=page, pageSize=page_size, total=total)


RESOURCE_MODELS = {'USER': User, 'WORKSPACE': Workspace, 'FILE': File, 'MATERIAL': Material,
                   'EXPERIENCE': Experience, 'JD': JobDescription, 'JD_VERSION': JdVersion}


def replay_record(db, request, record, user_id):
    if record.resource_type and record.http_status != 204:
        if record.resource_type == 'JD_VERSION':
            jd_version(db, record.resource_id, user_id)
        else:
            owned(db, RESOURCE_MODELS[record.resource_type], record.resource_id, user_id)
    if record.http_status == 204:
        from fastapi import Response
        return Response(status_code=204)
    return response(request, record.response_json, record.http_status)


def leaves(data, prefix=''):
    result = {}
    if isinstance(data, dict):
        for key, value in data.items():
            result.update(leaves(value, prefix + '/' + key.replace('~', '~0').replace('/', '~1')))
    elif isinstance(data, list):
        for i, value in enumerate(data):
            result.update(leaves(value, prefix + '/' + str(i)))
    else:
        result[prefix] = data
    return result


def field_values(data):
    """Merge mappings may select a whole array or an individual fact."""
    values = leaves(data)
    values.update({'/' + key: value for key, value in data.items()})
    return values


def add_source(db, exp, pointer, original=None, origin='USER_INPUT', segment_id=None, turn_id=None):
    db.add(ExperienceSource(user_id=exp.user_id, experience_id=exp.id, experience_revision=exp.revision,
        json_pointer=pointer, origin=original.origin if original else origin,
        segment_id=original.segment_id if original else segment_id, turn_id=original.turn_id if original else turn_id))


def confirmable(kind, data, status):
    if status != 'CONFIRMED':
        return
    if not data['name'].strip():
        invalid('确认经历需要名称', '/data/name')
    if kind == 'AWARD':
        if not any(x.strip() for x in data['outcomes']):
            invalid('确认奖项需要获奖结果', '/data/outcomes')
    elif not data['personalRole'].strip() and not any(x.strip() for x in data['actions']):
        invalid('确认经历需要本人职责或具体行动', '/data/personalRole')


def create_experience(db, user_id, workspace_id, kind, data, status='CANDIDATE', turn_id=None):
    owned(db, Workspace, workspace_id, user_id, lock=True)
    data = ExperienceData.model_validate(data).model_dump(by_alias=True)
    confirmable(kind, data, status)
    exp = Experience(user_id=user_id, workspace_id=workspace_id, type=kind, data_json=data, status=status, excluded=False, revision=1)
    db.add(exp)
    db.flush()
    for pointer in leaves(data):
        add_source(db, exp, pointer, origin='FOLLOWUP' if turn_id else 'USER_INPUT', turn_id=turn_id)
    return exp


def edit_experience(db, exp, *, data=None, kind=None, status=None, excluded=None, turn_id=None):
    old_data = exp.data_json
    old_rows = sources(db, exp)
    new_data = data if data is not None else deepcopy(old_data)
    kind = kind or exp.type
    status = status or exp.status
    confirmable(kind, new_data, status)
    old_leaves, new_leaves = leaves(old_data), leaves(new_data)
    by_pointer = defaultdict(list)
    for row in old_rows:
        by_pointer[row.json_pointer].append(row)
    bump(exp)
    exp.type, exp.status, exp.data_json = kind, status, deepcopy(new_data)
    if excluded is not None:
        exp.excluded = excluded
    for pointer, value in new_leaves.items():
        parent = pointer.rsplit('/', 1)[0]
        # For array reordering match values within the same field, never by position.
        if pointer.rsplit('/', 1)[-1].isdigit():
            candidates = [p for p, v in old_leaves.items() if p.rsplit('/', 1)[0] == parent and v == value]
        else:
            candidates = [pointer] if pointer in old_leaves and old_leaves[pointer] == value else []
        originals = [row for p in candidates for row in by_pointer[p]]
        if originals:
            for row in originals:
                add_source(db, exp, pointer, row)
        else:
            add_source(db, exp, pointer, origin='FOLLOWUP' if turn_id else 'USER_INPUT', turn_id=turn_id)
    return exp


def merge_experiences(db, user_id, body):
    # Deterministic row lock order avoids two concurrent merges locking in reverse.
    cards = {ref.id: owned(db, Experience, ref.id, user_id, lock=True) for ref in sorted(body.sources, key=lambda x: x.id)}
    target = cards[body.target_experience_id]
    for ref in body.sources:
        card = cards[ref.id]
        revision(card, ref.revision)
        if card.workspace_id != target.workspace_id or card.type != target.type:
            invalid('只能合并同工作区同类型经历', '/sources')
    new_data = body.data.model_dump(by_alias=True)
    confirmable(target.type, new_data, body.status)
    new_leaves = leaves(new_data)
    new_fields = field_values(new_data)
    original_rows = {i: sources(db, card) for i, card in cards.items()}
    mapped = {}
    targets = [m.json_pointer for m in body.source_mappings]
    for i, pointer in enumerate(targets):
        if any(pointer.startswith(other + '/') or other.startswith(pointer + '/') for other in targets[i + 1:]):
            invalid('来源映射目标不能重叠', '/sourceMappings')
    for mapping in body.source_mappings:
        if mapping.json_pointer not in new_fields:
            invalid('映射目标不是有效事实字段', '/sourceMappings')
        for source in mapping.sources:
            card = cards.get(source.experience_id)
            values = field_values(card.data_json) if card else {}
            if source.json_pointer not in values or values[source.json_pointer] != new_fields[mapping.json_pointer]:
                invalid('映射来源必须属于选定修订且与目标值一致', '/sourceMappings')
            for row in original_rows[card.id]:
                if row.json_pointer == source.json_pointer or row.json_pointer.startswith(source.json_pointer + '/'):
                    destination = mapping.json_pointer + row.json_pointer[len(source.json_pointer):]
                    if destination in new_leaves:
                        mapped.setdefault(destination, []).append(row)
    bump(target)
    target.data_json, target.status, target.excluded = new_data, body.status, body.excluded
    for pointer in new_leaves:
        rows = mapped.get(pointer, [])
        if rows:
            seen = set()
            for row in rows:
                key = (row.origin, row.segment_id, row.turn_id)
                if key not in seen:
                    add_source(db, target, pointer, row)
                    seen.add(key)
        else:
            add_source(db, target, pointer)
    for card in cards.values():
        if card.id != target.id:
            card.deleted_at, card.merged_into_id = now(), target.id
            bump(card)
    db.flush()
    return target


def read_fixed_facts(db, user_id, workspace_id, workspace_revision, experience_refs):
    workspace = owned(db, Workspace, workspace_id, user_id, lock=True)
    revision(workspace, workspace_revision)
    if len({ref['id'] for ref in experience_refs}) != len(experience_refs):
        invalid('经历编号不得重复')
    facts = []
    for ref in sorted(experience_refs, key=lambda r: r['id']):
        exp = owned(db, Experience, ref['id'], user_id, lock=True)
        revision(exp, ref['revision'])
        if exp.workspace_id != workspace_id or exp.status != 'CONFIRMED' or exp.excluded:
            invalid('经历必须在当前工作区内、已确认且未排除')
        facts.append(dict(id=exp.id, revision=exp.revision, type=exp.type, data=deepcopy(exp.data_json)))
    jd = None
    if workspace.jd_version_id:
        version = jd_version(db, workspace.jd_version_id, user_id, confirmed=True, lock=True)
        jd = dict(sourceJdId=version.jd_id, sourceJdVersionId=version.id, jobTitle=version.job_title,
                  companyName=version.company_name, originalText=version.original_text,
                  requirements=deepcopy(version.requirements_json))
    return dict(workspaceRevision=workspace.revision, profile=deepcopy(workspace.profile_json),
                direction=workspace.direction, experiences=facts, jdSnapshot=jd)


def bind_followup_session(db, user_id, workspace_id, session_id, is_active):
    workspace = owned(db, Workspace, workspace_id, user_id, lock=True)
    if workspace.active_followup_session_id and is_active(db, user_id, workspace.active_followup_session_id):
        conflict('已有活动追问会话')
    workspace.active_followup_session_id = session_id
    bump(workspace)
    return workspace


def apply_followup_fact(db, relations, *, user_id, workspace_id, turn_id, kind, data,
                        experience_id=None, base_revision=None):
    """C35 calls after candidate selection/revision checks in its transaction; no commit here."""
    tables = relations.tables(db)
    if not {'followup_sessions', 'followup_turns'} <= tables.keys():
        conflict('追问模块尚未接入')
    turn, session = tables['followup_turns'], tables['followup_sessions']
    owner = db.execute(select(turn.c.id).join(session, session.c.id == turn.c.session_id).where(
        turn.c.id == turn_id, turn.c.user_id == user_id, session.c.user_id == user_id,
        session.c.workspace_id == workspace_id, turn.c.status == 'REVIEW_REQUIRED',
        session.c.status == 'REVIEW_REQUIRED').with_for_update()).first()
    if owner is None:
        conflict('追问轮次不是当前可确认的本人数据')
    data = ExperienceData.model_validate(data).model_dump(by_alias=True)
    if experience_id is None:
        if base_revision is not None:
            invalid('新增经历不接受旧修订号')
        return create_experience(db, user_id, workspace_id, kind, data, status='CONFIRMED', turn_id=turn_id)
    exp = owned(db, Experience, experience_id, user_id, lock=True)
    if exp.workspace_id != workspace_id or exp.excluded:
        invalid('追问目标必须属于本工作区且未排除')
    revision(exp, base_revision)
    return edit_experience(db, exp, kind=kind, data=data, status='CONFIRMED', turn_id=turn_id)
