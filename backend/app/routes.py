from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File as Upload, Form, Query, Request, Response, UploadFile
from sqlalchemy import func, select

from . import schemas as s
from .auth import CurrentUser, DB, verify_bearer
from .core import Problem, audit, claim, complete, conflict, invalid, missing, response, sha
from .models import Experience, File, JdVersion, JobDescription, Material, Segment, Workspace, now
from .services import (bump, create_experience, edit_experience, experience_json, file_json,
    jd_json, jd_version, material_json, merge_experiences, owned, paginate, replay_record,
    revision, segment_json, valid_file, version_json, workspace_json)
from .storage import MAX_SIZE, display_name, file_access, identify

router = APIRouter(prefix='/api', tags=['工作区、资料与JD'])
PageNo = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=20)]
WRITE = [Depends(verify_bearer)]


def intent(db, request, user, body):
    payload = body.model_dump(by_alias=True, exclude_unset=True) if isinstance(body, s.Model) else body
    record, replay = claim(db, request, payload, user_id=user.id)
    return record, replay_record(db, request, record, user.id) if replay else None


def saved(db, request, user, record, status, data, kind, obj):
    complete(record, status, data, kind, obj.id)
    audit(db, user.id, request.method, kind, obj.id, request.state.request_id,
          **({'revision': obj.revision} if hasattr(obj, 'revision') else {}))
    return Response(status_code=204) if status == 204 else response(request, data, status)


@router.post('/workspaces', status_code=201, response_model=s.Envelope[s.WorkspaceOut], dependencies=WRITE)
def create_workspace(body: s.WorkspaceCreate, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    obj = Workspace(user_id=user.id, title=body.title, direction=body.direction, profile_json=s.empty_profile(), step='JD', revision=1)
    db.add(obj)
    db.flush()
    return saved(db, request, user, record, 201, workspace_json(obj), 'WORKSPACE', obj)


@router.get('/workspaces', response_model=s.Envelope[s.Page[s.WorkspaceOut]])
def list_workspaces(request: Request, user: CurrentUser, db: DB, page: PageNo = 1, pageSize: PageSize = 20, q: Annotated[str | None, Query(max_length=100)] = None):
    query = select(Workspace).where(Workspace.user_id == user.id)
    if q is not None:
        query = query.where(Workspace.title.contains(q, autoescape=True))
    return response(request, paginate(db, query, Workspace, workspace_json, page, pageSize, updated=True))


@router.get('/workspaces/{workspaceId}', response_model=s.Envelope[s.WorkspaceOut])
def get_workspace(workspaceId: s.Id, request: Request, user: CurrentUser, db: DB):
    return response(request, workspace_json(owned(db, Workspace, workspaceId, user.id)))


@router.patch('/workspaces/{workspaceId}', response_model=s.Envelope[s.WorkspaceOut], dependencies=WRITE)
def patch_workspace(workspaceId: s.Id, body: s.WorkspacePatch, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    obj = owned(db, Workspace, workspaceId, user.id, lock=True)
    revision(obj, body.base_revision)
    if body.jd_version_id is not None:
        jd_version(db, body.jd_version_id, user.id, confirmed=True, lock=True)
    for key in body.model_fields_set - {'base_revision'}:
        value = getattr(body, key)
        setattr(obj, 'profile_json' if key == 'profile' else key, value.model_dump(by_alias=True) if key == 'profile' else value)
    bump(obj)
    db.flush()
    return saved(db, request, user, record, 200, workspace_json(obj), 'WORKSPACE', obj)


@router.post('/files', status_code=201, response_model=s.Envelope[s.FileOut], dependencies=WRITE)
async def upload_file(request: Request, user: CurrentUser, db: DB,
                      purpose: Annotated[Literal['MATERIAL', 'JD', 'AVATAR'], Form()],
                      file: Annotated[UploadFile, Upload()]):
    form = await request.form()
    if set(form.keys()) != {'purpose', 'file'} or len(form.getlist('purpose')) != 1 or len(form.getlist('file')) != 1:
        invalid('上传只允许唯一的 purpose 和 file 字段')
    content = await file.read(MAX_SIZE + 1)
    name = display_name(file.filename)
    mime = identify(content, name, purpose)
    record, replay = intent(db, request, user, dict(purpose=purpose, name=name, sha256=sha(content).hex(), size=len(content)))
    if replay is not None:
        return replay
    key = request.app.state.storage.put(user.id, content)
    obj = File(user_id=user.id, purpose=purpose, object_key=key, original_name=name, mime_type=mime,
               size_bytes=len(content), sha256=sha(content), status='READY')
    db.add(obj)
    db.flush()
    return saved(db, request, user, record, 201, file_json(obj), 'FILE', obj)


@router.get('/files/{fileId}/download', response_model=s.Envelope[s.DownloadOut])
def download_file(fileId: s.Id, request: Request, user: CurrentUser, db: DB):
    file = file_access(db, fileId, user.id, request.app.state.relations)
    return response(request, request.app.state.storage.sign(file, user.id))


def accepted(task, kind, obj, url):
    return dict(taskId=task.id, resourceType=kind, resourceId=obj.id, status=task.status,
                statusUrl='/api/tasks/' + task.id, resourceUrl=url)


@router.post('/materials', status_code=202, response_model=s.Envelope[s.Accepted], dependencies=WRITE)
def create_material(body: s.MaterialCreate, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    owned(db, Workspace, body.workspace_id, user.id, lock=True)
    if body.kind in {'URL', 'ZIP'}:
        raise Problem(503, 'FEATURE_DISABLED', 'URL/ZIP 导入首期未开启')
    file = valid_file(db, body.file_id, user.id, 'MATERIAL') if body.kind == 'FILE' else None
    obj = Material(user_id=user.id, workspace_id=body.workspace_id, kind=body.kind, file_id=file.id if file else None,
                   title=body.title or (file.original_name[:200] if file else body.text[:50]), input_text=body.text, status='QUEUED')
    db.add(obj)
    db.flush()
    snapshot = dict(materialId=obj.id, text=body.text, fileId=obj.file_id, objectKey=file.object_key if file else None,
                    mimeType=file.mime_type if file else None, protocolVersion='1.1.0')
    task = request.app.state.tasks.create_task(db, user_id=user.id, kind='PARSE_MATERIAL', resource_type='MATERIAL', resource_id=obj.id, input_json=snapshot)
    return saved(db, request, user, record, 202, accepted(task, 'MATERIAL', obj, '/api/materials/' + obj.id), 'MATERIAL', obj)


@router.get('/materials', response_model=s.Envelope[s.Page[s.MaterialOut]])
def list_materials(workspaceId: s.Id, request: Request, user: CurrentUser, db: DB, page: PageNo = 1, pageSize: PageSize = 20):
    owned(db, Workspace, workspaceId, user.id)
    query = select(Material).where(Material.user_id == user.id, Material.workspace_id == workspaceId, Material.deleted_at.is_(None))
    return response(request, paginate(db, query, Material, lambda o: material_json(o, request.app.state.tasks, db), page, pageSize))


@router.get('/materials/{materialId}', response_model=s.Envelope[s.MaterialOut])
def get_material(materialId: s.Id, request: Request, user: CurrentUser, db: DB):
    return response(request, material_json(owned(db, Material, materialId, user.id), request.app.state.tasks, db))


@router.get('/materials/{materialId}/segments', response_model=s.Envelope[s.Page[s.SegmentOut]])
def list_segments(materialId: s.Id, request: Request, user: CurrentUser, db: DB, page: PageNo = 1, pageSize: PageSize = 20):
    owned(db, Material, materialId, user.id)
    query = select(Segment).where(Segment.material_id == materialId, Segment.user_id == user.id)
    return response(request, paginate(db, query, Segment, segment_json, page, pageSize))


def revoke_unreferenced_file(db, request, file_id, user_id):
    if file_id:
        file = owned(db, File, file_id, user_id, lock=True, include_deleted=True)
        db.flush()
        if not request.app.state.relations.file_referenced(db, file):
            file.status, file.deleted_at = 'DELETING', now()


@router.delete('/materials/{materialId}', status_code=204, dependencies=WRITE)
def delete_material(materialId: s.Id, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, {})
    if replay is not None:
        return replay
    obj = owned(db, Material, materialId, user.id, lock=True)
    obj.deleted_at = now()
    request.app.state.tasks.cancel_resource(db, user.id, 'MATERIAL', obj.id)
    revoke_unreferenced_file(db, request, obj.file_id, user.id)
    return saved(db, request, user, record, 204, None, 'MATERIAL', obj)


@router.post('/experiences', status_code=201, response_model=s.Envelope[s.ExperienceOut], dependencies=WRITE)
def post_experience(body: s.ExperienceCreate, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    obj = create_experience(db, user.id, body.workspace_id, body.type, body.data.model_dump(by_alias=True))
    db.flush()
    return saved(db, request, user, record, 201, experience_json(db, obj), 'EXPERIENCE', obj)


@router.get('/experiences', response_model=s.Envelope[s.Page[s.ExperienceOut]])
def list_experiences(workspaceId: s.Id, request: Request, user: CurrentUser, db: DB, page: PageNo = 1, pageSize: PageSize = 20):
    owned(db, Workspace, workspaceId, user.id)
    query = select(Experience).where(Experience.user_id == user.id, Experience.workspace_id == workspaceId, Experience.deleted_at.is_(None))
    return response(request, paginate(db, query, Experience, lambda o: experience_json(db, o), page, pageSize))


@router.get('/experiences/{experienceId}', response_model=s.Envelope[s.ExperienceOut])
def get_experience(experienceId: s.Id, request: Request, user: CurrentUser, db: DB):
    return response(request, experience_json(db, owned(db, Experience, experienceId, user.id)))


@router.patch('/experiences/{experienceId}', response_model=s.Envelope[s.ExperienceOut], dependencies=WRITE)
def patch_experience(experienceId: s.Id, body: s.ExperiencePatch, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    obj = owned(db, Experience, experienceId, user.id, lock=True)
    revision(obj, body.base_revision)
    edit_experience(db, obj, data=body.data.model_dump(by_alias=True) if body.data else None,
                    kind=body.type, status=body.status, excluded=body.excluded)
    db.flush()
    return saved(db, request, user, record, 200, experience_json(db, obj), 'EXPERIENCE', obj)


@router.delete('/experiences/{experienceId}', status_code=204, dependencies=WRITE)
def delete_experience(experienceId: s.Id, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, {})
    if replay is not None:
        return replay
    obj = owned(db, Experience, experienceId, user.id, lock=True)
    obj.deleted_at = now()
    bump(obj)
    return saved(db, request, user, record, 204, None, 'EXPERIENCE', obj)


@router.post('/experience-merges', response_model=s.Envelope[s.ExperienceOut], dependencies=WRITE)
def merge(body: s.ExperienceMerge, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    obj = merge_experiences(db, user.id, body)
    return saved(db, request, user, record, 200, experience_json(db, obj), 'EXPERIENCE', obj)


def create_jd_version(db, tasks, user_id, jd, source_type, text=None, file_id=None, source_url=None):
    if source_type == 'URL':
        raise Problem(503, 'FEATURE_DISABLED', 'JD网址导入首期未开启')
    if db.scalar(select(JdVersion.id).where(JdVersion.jd_id == jd.id, JdVersion.status.in_(['QUEUED', 'ANALYZING'])).limit(1)):
        conflict('当前 JD 仍有进行中的分析')
    file = valid_file(db, file_id, user_id, 'JD') if source_type == 'IMAGE' else None
    number = (db.scalar(select(func.max(JdVersion.version_no)).where(JdVersion.jd_id == jd.id)) or 0) + 1
    obj = JdVersion(user_id=user_id, jd_id=jd.id, version_no=number, source_type=source_type,
                    original_text=text or '', file_id=file.id if file else None, source_url=source_url,
                    requirements_json=[], status='QUEUED')
    db.add(obj)
    db.flush()
    if jd.current_version_id is None:
        jd.current_version_id = obj.id
    task = tasks.create_task(db, user_id=user_id, kind='ANALYZE_JD', resource_type='JD_VERSION', resource_id=obj.id,
        input_json=dict(jdVersionId=obj.id, text=text, fileId=obj.file_id, objectKey=file.object_key if file else None,
                        mimeType=file.mime_type if file else None, protocolVersion='1.1.0'))
    return obj, task


def create_jd_from_job(db, tasks, user_id, title, description, source_url):
    """C71 must call this within its own transaction, with actual source data."""
    if not source_url.startswith('https://') or not 1 <= len(description) <= 100000:
        invalid('真实岗位来源或描述不合法')
    jd = JobDescription(user_id=user_id, title=title[:200], revision=1)
    db.add(jd)
    db.flush()
    version, task = create_jd_version(db, tasks, user_id, jd, 'RECOMMENDATION', description, source_url=source_url)
    return jd, version, task


@router.post('/job-descriptions', status_code=202, response_model=s.Envelope[s.Accepted], dependencies=WRITE)
def post_jd(body: s.JdCreate, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    jd = JobDescription(user_id=user.id, title=body.title or '未命名JD档案', revision=1)
    db.add(jd)
    db.flush()
    obj, task = create_jd_version(db, request.app.state.tasks, user.id, jd, body.source_type, body.text, body.file_id)
    return saved(db, request, user, record, 202, accepted(task, 'JD_VERSION', obj, f'/api/job-descriptions/{jd.id}/versions/{obj.id}'), 'JD_VERSION', obj)


@router.get('/job-descriptions', response_model=s.Envelope[s.Page[s.JdOut]])
def list_jds(request: Request, user: CurrentUser, db: DB, page: PageNo = 1, pageSize: PageSize = 20, q: Annotated[str | None, Query(max_length=100)] = None):
    query = select(JobDescription).where(JobDescription.user_id == user.id, JobDescription.deleted_at.is_(None))
    if q is not None:
        query = query.where(JobDescription.title.contains(q, autoescape=True))
    return response(request, paginate(db, query, JobDescription, jd_json, page, pageSize))


@router.get('/job-descriptions/{jdId}', response_model=s.Envelope[s.JdOut])
def get_jd(jdId: s.Id, request: Request, user: CurrentUser, db: DB):
    return response(request, jd_json(owned(db, JobDescription, jdId, user.id)))


@router.patch('/job-descriptions/{jdId}', response_model=s.Envelope[s.JdOut], dependencies=WRITE)
def patch_jd(jdId: s.Id, body: s.JdPatch, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    obj = owned(db, JobDescription, jdId, user.id, lock=True)
    revision(obj, body.base_revision)
    obj.title = body.title
    bump(obj)
    db.flush()
    return saved(db, request, user, record, 200, jd_json(obj), 'JD', obj)


@router.get('/job-descriptions/{jdId}/versions', response_model=s.Envelope[s.Page[s.JdVersionOut]])
def list_versions(jdId: s.Id, request: Request, user: CurrentUser, db: DB, page: PageNo = 1, pageSize: PageSize = 20):
    owned(db, JobDescription, jdId, user.id)
    query = select(JdVersion).where(JdVersion.jd_id == jdId, JdVersion.user_id == user.id)
    return response(request, paginate(db, query, JdVersion, lambda o: version_json(o, request.app.state.tasks, db), page, pageSize))


@router.get('/job-descriptions/{jdId}/versions/{versionId}', response_model=s.Envelope[s.JdVersionOut])
def get_version(jdId: s.Id, versionId: s.Id, request: Request, user: CurrentUser, db: DB):
    return response(request, version_json(jd_version(db, versionId, user.id, jdId), request.app.state.tasks, db))


@router.post('/job-descriptions/{jdId}/versions', status_code=202, response_model=s.Envelope[s.Accepted], dependencies=WRITE)
def new_version(jdId: s.Id, body: s.JdVersionCreate, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    jd = owned(db, JobDescription, jdId, user.id, lock=True)
    revision(jd, body.base_revision)
    obj, task = create_jd_version(db, request.app.state.tasks, user.id, jd, body.source_type, body.original_text, body.file_id)
    bump(jd)
    return saved(db, request, user, record, 202, accepted(task, 'JD_VERSION', obj, f'/api/job-descriptions/{jd.id}/versions/{obj.id}'), 'JD_VERSION', obj)


@router.post('/job-descriptions/{jdId}/confirmations', response_model=s.Envelope[s.JdVersionOut], dependencies=WRITE)
def confirm_jd(jdId: s.Id, body: s.JdConfirm, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, body)
    if replay is not None:
        return replay
    jd = owned(db, JobDescription, jdId, user.id, lock=True)
    revision(jd, body.base_revision)
    obj = jd_version(db, body.jd_version_id, user.id, jdId, lock=True)
    if obj.status != 'REVIEW_REQUIRED':
        conflict('只能确认待核对的 JD 版本')
    requirements = [r.model_dump(by_alias=True) for r in body.requirements]
    for req in requirements:
        if req['evidenceQuote'] and req['evidenceQuote'] not in body.original_text:
            invalid('要求依据必须来自核对后的原文', '/requirements')
    jd.title, jd.current_version_id = body.title, obj.id
    bump(jd)
    obj.original_text, obj.job_title, obj.company_name = body.original_text, body.job_title, body.company_name
    obj.requirements_json, obj.status, obj.confirmed_at = requirements, 'CONFIRMED', now()
    db.flush()
    return saved(db, request, user, record, 200, version_json(obj, request.app.state.tasks, db), 'JD_VERSION', obj)


@router.delete('/job-descriptions/{jdId}', status_code=204, dependencies=WRITE)
def delete_jd(jdId: s.Id, request: Request, user: CurrentUser, db: DB):
    record, replay = intent(db, request, user, {})
    if replay is not None:
        return replay
    jd = owned(db, JobDescription, jdId, user.id, lock=True)
    jd.deleted_at = now()
    bump(jd)
    versions = list(db.scalars(select(JdVersion).where(JdVersion.jd_id == jd.id, JdVersion.user_id == user.id).order_by(JdVersion.id).with_for_update()))
    for obj in versions:
        request.app.state.tasks.cancel_resource(db, user.id, 'JD_VERSION', obj.id)
    for file_id in sorted({v.file_id for v in versions if v.file_id}):
        revoke_unreferenced_file(db, request, file_id, user.id)
    return saved(db, request, user, record, 204, None, 'JD', jd)


@router.get('/job-descriptions/{jdId}/deletion-impact', response_model=s.Envelope[s.Impact])
def jd_impact(jdId: s.Id, request: Request, user: CurrentUser, db: DB):
    obj = owned(db, JobDescription, jdId, user.id)
    return response(request, dict(resourceType='JD', resourceId=obj.id, revision=obj.revision,
        affectedCounts=request.app.state.relations.counts(db, user.id, 'JD', obj.id),
        messages=['删除后原输入与图片引用将被清理；既有简历独立快照保留。关联工作区须重新选择JD或跳过后再生成。']))


@router.get('/materials/{materialId}/deletion-impact', response_model=s.Envelope[s.Impact])
def material_impact(materialId: s.Id, request: Request, user: CurrentUser, db: DB):
    obj = owned(db, Material, materialId, user.id)
    return response(request, dict(resourceType='MATERIAL', resourceId=obj.id, revision=None,
        affectedCounts=request.app.state.relations.counts(db, user.id, 'MATERIAL', obj.id),
        messages=['删除后撤销材料访问并清理原文；已确认事实、既有简历文字和来源墓碑保留。共用文件仍有有效引用时保留。']))
