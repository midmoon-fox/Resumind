"""Contract 1.1.0 boundary models. JSON integers and booleans are strict."""
import re
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic.alias_generators import to_camel

Id = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')]
Revision = Annotated[int, Field(ge=1)]
Title = Annotated[str, Field(min_length=1, max_length=200)]
Month = Annotated[str, StringConstraints(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]
ExperienceType = Literal['PROJECT', 'INTERNSHIP', 'CAMPUS', 'AWARD']
ExperienceStatus = Literal['CANDIDATE', 'CONFIRMED']
Step = Literal['JD', 'PROFILE', 'MATERIALS', 'FOLLOWUP', 'EDITOR']
ShortItems = Annotated[list[Annotated[str, Field(max_length=2000)]], Field(max_length=50)]


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra='forbid', strict=True)


def email_value(value: str, blank=False):
    if blank and value == '':
        return value
    if len(value) > 254 or not value.isascii() or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}", value):
        raise ValueError('邮箱格式不正确，例如 name@example.com。')
    return value.lower()


class Dates(Model):
    start_date: Month | None
    end_date: Month | None
    is_current: bool

    @model_validator(mode='after')
    def dates(self):
        if self.is_current and self.end_date is not None:
            raise ValueError('isCurrent=true 时 endDate 必须为 null')
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('结束日期不能早于开始日期')
        return self


class Education(Dates):
    id: Id
    school: str
    major: str
    degree: str


class Profile(Model):
    photoData: Annotated[str, Field(max_length=400000, pattern=r'^data:image/jpeg;base64,[A-Za-z0-9+/=]+$')] | None = None
    name: Annotated[str, Field(max_length=100)]
    phone: Annotated[str, Field(max_length=32)] | None
    email: Annotated[str, Field(max_length=254)]
    intention: Annotated[str, Field(max_length=100)]
    age: Annotated[int, Field(ge=16, le=100)] | None
    education: Annotated[list[Education], Field(max_length=50)]
    skills: list[str]

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        return email_value(value, blank=True)

    @model_validator(mode='after')
    def unique_ids(self):
        if len({e.id for e in self.education}) != len(self.education):
            raise ValueError('教育记录 ID 不得重复')
        return self


def empty_profile():
    return dict(name='', phone='', email='', intention='', age=None, education=[], skills=[])


class Login(Model):
    email: Annotated[str, Field(max_length=254)]
    password: Annotated[str, Field(min_length=1, max_length=128)]
    _email = field_validator('email')(email_value)


class Registration(Login):
    password: Annotated[str, Field(min_length=5, max_length=128, description='5～128 位，允许纯数字，例如 12345；不要求大小写或特殊符号。')]
    username: Annotated[str, Field(min_length=1, max_length=50)]


class PatchModel(Model):
    @model_validator(mode='after')
    def patch_valid(self):
        supplied = self.model_fields_set - {'base_revision'}
        if not supplied:
            raise ValueError('至少提供一个可修改字段')
        for field in supplied:
            if getattr(self, field) is None and field not in {'avatar_file_id', 'direction', 'jd_version_id'}:
                raise ValueError(f'{to_camel(field)} 不允许 null')
        return self


class MePatch(PatchModel):
    username: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    avatar_file_id: Id | None = None


class WorkspaceCreate(Model):
    title: Annotated[str, Field(min_length=1, max_length=100)] = '未命名简历任务'
    direction: Annotated[str, Field(max_length=100)] | None = None

    @model_validator(mode='after')
    def no_explicit_null(self):
        if 'direction' in self.model_fields_set and self.direction is None:
            raise ValueError('创建时 direction 必须是字符串或省略')
        return self


class WorkspacePatch(PatchModel):
    base_revision: Revision
    title: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    direction: Annotated[str, Field(max_length=100)] | None = None
    profile: Profile | None = None
    jd_version_id: Id | None = None
    step: Step | None = None


class MaterialCreate(Model):
    workspace_id: Id
    kind: Literal['TEXT', 'FILE', 'URL', 'ZIP']
    file_id: Id | None = None
    text: Annotated[str, Field(min_length=1, max_length=100000)] | None = None
    url: Annotated[str, Field(min_length=1, max_length=2048)] | None = None
    title: Title | None = None

    @model_validator(mode='after')
    def exclusive(self):
        check_input(self, self.kind, 'text')
        if 'title' in self.model_fields_set and self.title is None:
            raise ValueError('title 不允许 null')
        return self


def check_input(obj, kind, text_field):
    selected = {'TEXT': text_field, 'FILE': 'file_id', 'ZIP': 'file_id', 'IMAGE': 'file_id', 'URL': 'url'}[kind]
    for field in (text_field, 'file_id', 'url'):
        if field == selected:
            if field not in obj.model_fields_set or getattr(obj, field) is None:
                raise ValueError(f'{to_camel(field)} 必填且不允许 null')
        elif field in obj.model_fields_set:
            raise ValueError(f'当前输入类型必须省略 {to_camel(field)}')


class ExperienceData(Dates):
    name: Annotated[str, Field(max_length=200)]
    background: Annotated[str, Field(max_length=5000)]
    personal_role: Annotated[str, Field(max_length=2000)]
    actions: ShortItems
    outcomes: ShortItems
    technologies: ShortItems


class ExperienceCreate(Model):
    workspace_id: Id
    type: ExperienceType
    data: ExperienceData


class ExperiencePatch(PatchModel):
    base_revision: Revision
    type: ExperienceType | None = None
    excluded: bool | None = None
    data: ExperienceData | None = None
    status: ExperienceStatus | None = None


class Requirement(Model):
    id: Id
    category: str  # No closed enum is defined by contract 1.1.0.
    text: Annotated[str, Field(max_length=2000)]
    necessity: Literal['REQUIRED', 'PREFERRED', 'UNSPECIFIED']
    evidence_quote: Annotated[str, Field(max_length=4000)]


def check_jd_input(obj, text_field):
    text = getattr(obj, text_field)
    if text is not None:
        text = text.strip()
        setattr(obj, text_field, text or None)
    if obj.source_type == 'URL':
        check_input(obj, 'URL', text_field)
        return
    if obj.url is not None:
        raise ValueError('请直接填写 JD 原文或上传 TXT、JPG、PNG 文件，暂不支持网址导入')
    if not text and not obj.file_id:
        raise ValueError('请填写 JD 原文或选择文件，至少提供一项')
    # Preserve IMAGE as the existing file-source contract; it also accepts TXT.
    obj.source_type = 'IMAGE' if obj.file_id else 'TEXT'


class JdCreate(Model):
    title: Title | None = None
    source_type: Literal['TEXT', 'IMAGE', 'URL'] | None = None
    text: Annotated[str, Field(min_length=1, max_length=100000)] | None = None
    file_id: Id | None = None
    url: Annotated[str, Field(min_length=1, max_length=2048)] | None = None

    @model_validator(mode='after')
    def exclusive(self):
        check_jd_input(self, 'text')
        if 'title' in self.model_fields_set and self.title is None:
            raise ValueError('title 不允许 null')
        return self


class JdVersionCreate(Model):
    base_revision: Revision
    source_type: Literal['TEXT', 'IMAGE', 'URL'] | None = None
    original_text: Annotated[str, Field(min_length=1, max_length=100000)] | None = None
    file_id: Id | None = None
    url: Annotated[str, Field(min_length=1, max_length=2048)] | None = None

    @model_validator(mode='after')
    def exclusive(self):
        check_jd_input(self, 'original_text')
        return self


class JdPatch(Model):
    base_revision: Revision
    title: Title


class JdConfirm(Model):
    base_revision: Revision
    jd_version_id: Id
    title: Title
    original_text: Annotated[str, Field(min_length=1, max_length=100000)]
    job_title: Annotated[str, Field(max_length=200)] | None
    company_name: Annotated[str, Field(max_length=200)] | None
    requirements: Annotated[list[Requirement], Field(max_length=100)]

    @model_validator(mode='after')
    def ids(self):
        if len({r.id for r in self.requirements}) != len(self.requirements):
            raise ValueError('requirement ID 不得重复')
        return self


class SourceRevision(Model):
    id: Id
    revision: Revision


class FieldSource(Model):
    experience_id: Id
    json_pointer: Annotated[str, Field(max_length=500)]


class SourceMapping(Model):
    json_pointer: Annotated[str, Field(max_length=500)]
    sources: Annotated[list[FieldSource], Field(min_length=1)]


class ExperienceMerge(Model):
    target_experience_id: Id
    sources: Annotated[list[SourceRevision], Field(min_length=2, max_length=20)]
    data: ExperienceData
    status: ExperienceStatus
    excluded: bool
    source_mappings: list[SourceMapping]

    @model_validator(mode='after')
    def ids(self):
        ids = [s.id for s in self.sources]
        if len(set(ids)) != len(ids) or self.target_experience_id not in ids:
            raise ValueError('sources 必须唯一并包含目标')
        if len({m.json_pointer for m in self.source_mappings}) != len(self.source_mappings):
            raise ValueError('映射目标不得重复')
        return self


class UserOut(Model):
    id: Id
    email: str
    username: str
    avatar_file_id: Id | None
    created_at: str


class WorkspaceOut(Model):
    id: Id
    title: str
    direction: str | None
    profile: Profile
    jd_version_id: Id | None
    active_followup_session_id: Id | None
    step: Step
    revision: Revision
    created_at: str
    updated_at: str


class FileOut(Model):
    id: Id
    purpose: str
    original_name: str
    mime_type: str
    size_bytes: int
    created_at: str


class DownloadOut(Model):
    url: str
    expires_at: str
    file_name: str


class TaskError(Model):
    code: str
    message: str
    can_retry: bool


class MaterialOut(Model):
    id: Id
    workspace_id: Id
    kind: str
    file_id: Id | None
    title: str
    status: str
    task_id: Id
    text_preview: str
    error: TaskError | None
    created_at: str


class SegmentOut(Model):
    id: Id
    material_id: Id
    page: int | None
    ordinal: int
    text: str
    extraction_method: str


class Provenance(Model):
    json_pointer: str
    segment_ids: list[Id]
    turn_ids: list[Id]
    origin: Literal['MATERIAL', 'USER_INPUT', 'FOLLOWUP']


class ExperienceOut(Model):
    id: Id
    workspace_id: Id
    type: ExperienceType
    data: ExperienceData
    provenance: list[Provenance]
    status: ExperienceStatus
    excluded: bool
    revision: Revision
    created_at: str
    updated_at: str


class JdOut(Model):
    id: Id
    title: str
    current_version_id: Id
    revision: Revision
    created_at: str
    updated_at: str


class JdVersionOut(Model):
    id: Id
    jd_id: Id
    version_no: int
    status: str
    task_id: Id
    source_type: str
    original_text: str
    file_id: Id | None
    source_url: str | None
    job_title: str | None
    company_name: str | None
    requirements: list[Requirement]
    created_at: str


class Accepted(Model):
    task_id: Id
    resource_type: str
    resource_id: Id
    status: str
    status_url: str
    resource_url: str


class Impact(Model):
    resource_type: str
    resource_id: Id
    revision: int | None
    affected_counts: dict[str, int]
    messages: list[str]


class LoginOut(Model):
    user: UserOut
    expires_at: str
    access_token: str
    token_type: Literal['Bearer']


T = TypeVar('T')


class Envelope(Model, Generic[T]):
    data: T
    request_id: Id


class ErrorBody(Model):
    code: str
    message: str
    details: dict


class ErrorEnvelope(Model):
    error: ErrorBody
    request_id: Id


class Page(Model, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
