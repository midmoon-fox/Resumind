"""OpenAPI structures for the document contract; semantic validation is shared."""
from typing import Annotated, Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .documents import validate_document, validate_style

TaskStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCEL_REQUESTED", "CANCELLED"]
ExportFormat = Literal["PDF", "DOCX", "HTML"]
Uid = Annotated[str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SimpleMark(Contract):
    type: Literal["bold", "italic", "underline"]


class LinkAttrs(Contract):
    href: str = Field(max_length=2048, pattern=r"^(https?://|mailto:)")


class LinkMark(Contract):
    type: Literal["link"]
    attrs: LinkAttrs


class ColorAttrs(Contract):
    color: Literal["#333333", "#1F2937", "#2563EB"]


class ColorMark(Contract):
    type: Literal["textStyle"]
    attrs: ColorAttrs


Mark = Annotated[SimpleMark | LinkMark | ColorMark, Field(discriminator="type")]


class TextNode(Contract):
    type: Literal["text"]
    text: str = Field(min_length=1)
    marks: list[Mark] = Field(default_factory=list)


class BreakNode(Contract):
    type: Literal["hardBreak"]


class ParagraphNode(Contract):
    type: Literal["paragraph"]
    content: list[Annotated[TextNode | BreakNode, Field(discriminator="type")]] = Field(default_factory=list)


class ListItemNode(Contract):
    type: Literal["listItem"]
    content: list["BlockNode"] = Field(min_length=1, description="The first block must be a paragraph")


class BulletNode(Contract):
    type: Literal["bulletList"]
    content: list[ListItemNode] = Field(min_length=1)


class ListAttrs(Contract):
    start: int = Field(default=1, ge=1, le=999)


class OrderedNode(Contract):
    type: Literal["orderedList"]
    content: list[ListItemNode] = Field(min_length=1)
    attrs: ListAttrs = Field(default_factory=ListAttrs)


BlockNode = Annotated[ParagraphNode | BulletNode | OrderedNode, Field(discriminator="type")]
ListItemNode.model_rebuild()
BulletNode.model_rebuild()
OrderedNode.model_rebuild()


class RichNode(Contract):
    type: Literal["doc"]
    content: list[BlockNode]


class Education(Contract):
    id: Uid
    school: str
    major: str
    degree: str
    startDate: str | None
    endDate: str | None
    isCurrent: bool


class Profile(Contract):
    photoData: str | None = Field(default=None, max_length=400000, pattern=r'^data:image/jpeg;base64,[A-Za-z0-9+/=]+$')
    name: str = Field(max_length=100)
    phone: str | None = Field(max_length=32)
    email: str = Field(max_length=254)
    intention: str = Field(max_length=100)
    age: int | None = Field(ge=16, le=100)
    education: list[Education]
    skills: list[str]


class Item(Contract):
    id: Uid
    title: str
    subtitle: str
    startDate: str | None
    endDate: str | None
    isCurrent: bool
    description: RichNode
    experienceId: Uid | None
    sourceRevision: int | None = Field(ge=1)


class ChartDatum(Contract):
    label: str = Field(max_length=80)
    value: int = Field(ge=0, le=100)
    unit: str = Field(default="", max_length=20)


class SocialLink(Contract):
    platform: str = Field(max_length=40)
    label: str = Field(default="", max_length=80)
    url: str = Field(max_length=500)


class Section(Contract):
    id: Uid
    type: Literal["EDUCATION", "PROJECTS", "INTERNSHIPS", "CAMPUS", "AWARDS", "SKILLS", "ACHIEVEMENTS", "CERTIFICATES", "GOAL", "CHARTS", "HOBBIES", "PUBLICATIONS", "REFERENCES", "SOCIAL_LINKS", "STRENGTHS", "TEXT", "VOLUNTEERING", "WORK_EXPERIENCE"]
    title: str
    visible: bool
    items: list[Item] = Field(default_factory=list, max_length=50)
    chartData: list[ChartDatum] | None = Field(default=None, max_length=20)
    links: list[SocialLink] | None = Field(default=None, max_length=20)
    text: RichNode | None = Field(default=None)


class Document(Contract):
    schemaVersion: Literal["1.0.0"]
    profile: Profile
    sections: list[Section] = Field(max_length=50)

    @model_validator(mode="before")
    @classmethod
    def semantics(cls, value):
        # Validate the raw mapping so explicit null/unknown attributes cannot be erased.
        if isinstance(value, dict):
            validate_document(value)
        return value


class SuggestionItemContent(Contract):
    itemId: Uid
    description: RichNode


class SuggestionSectionContent(Contract):
    items: list[SuggestionItemContent] = Field(max_length=50)


class SuggestionEducationContent(Contract):
    education: list[Education] = Field(max_length=50)


class SuggestionSkillsContent(Contract):
    skills: list[str]


SuggestionValue = RichNode | SuggestionSectionContent | SuggestionEducationContent | SuggestionSkillsContent


class Style(Contract):
    fontFamily: Literal["Microsoft YaHei", "SimSun"]
    fontSize: int = Field(ge=10, le=20)
    lineHeight: float = Field(ge=1.1, le=2)
    accentColor: Literal["#333333", "#1F2937", "#2563EB"]
    sectionGap: int = Field(ge=0, le=32)

    @model_validator(mode="before")
    @classmethod
    def semantics(cls, value):
        if isinstance(value, dict):
            validate_style(value)
        return value


T = TypeVar("T")


class Envelope(Contract, Generic[T]):
    data: T
    requestId: str


class Page(Contract, Generic[T]):
    items: list[T]
    page: int
    pageSize: int
    total: int


class ResumeOutput(Contract):
    id: str
    workspaceId: str | None
    title: str
    revision: int
    generationTaskId: str | None
    generationStatus: str | None
    document: Document
    style: Style
    templateId: str
    templateVersion: str
    jdSnapshot: "JdSnapshot | None"
    createdAt: str
    updatedAt: str


class VersionOutput(Contract):
    id: str
    resumeId: str
    sourceRevision: int
    label: str
    document: Document
    style: Style
    templateId: str
    templateVersion: str
    jdSnapshot: "JdSnapshot | None"
    reason: Literal["MANUAL", "EXPORT", "BEFORE_RESTORE"]
    createdAt: str


class Requirement(Contract):
    id: str
    category: str
    text: str = Field(max_length=2000)
    necessity: Literal["REQUIRED", "PREFERRED", "UNSPECIFIED"]
    evidenceQuote: str = Field(max_length=4000)


class JdSnapshot(Contract):
    sourceJdId: str | None
    sourceJdVersionId: str | None
    jobTitle: str | None
    companyName: str | None
    originalText: str
    requirements: list[Requirement] = Field(max_length=100)


class StylePolicy(Contract):
    fontFamilies: list[str]
    colors: list[str]
    fontSizeMin: int
    fontSizeMax: int
    lineHeightMin: float
    lineHeightMax: float


class TemplateOutput(Contract):
    id: str
    version: str
    name: str
    supportedFormats: list[ExportFormat]
    allowedSectionTypes: list[str]
    stylePolicy: StylePolicy
    previewUrl: str | None


class TemplateList(Page[TemplateOutput]):
    pass


class Issue(Contract):
    code: str
    severity: Literal["ERROR", "WARNING"]
    path: str
    message: str


class PreflightOutput(Contract):
    canExport: bool
    issues: list[Issue]


class TaskError(Contract):
    code: str
    message: str
    canRetry: bool
    issues: list[Issue] | None = None


class Accepted(Contract):
    taskId: str
    resourceType: Literal["EXPORT", "PREPARATION_EXPORT"]
    resourceId: str
    status: TaskStatus
    statusUrl: str
    resourceUrl: str


class ExportOutput(Contract):
    id: str
    taskId: str
    resumeVersionId: str
    format: ExportFormat
    fileName: str
    status: TaskStatus
    fileId: str | None
    warnings: list[str]
    error: TaskError | None
    createdAt: str


class Download(Contract):
    url: str
    expiresAt: str
    fileName: str


class Question(Contract):
    id: Uid
    number: int = Field(ge=1, le=10)
    question: str
    referenceAnswer: str
    basisItemIds: list[Uid]
    missingFacts: list[str]


class PreparationContent(Contract):
    introduction: str | None
    questions: list[Question] = Field(max_length=10)


class PreparationOutput(Contract):
    id: str
    taskId: str
    resumeVersionId: str
    type: Literal["INTRODUCTION", "INTERVIEW_QUESTIONS"]
    revision: int
    status: Literal["GENERATING", "READY", "FAILED"]
    content: PreparationContent
    isOutdated: bool
    createdAt: str
    updatedAt: str


class PreparationExportOutput(Contract):
    id: str
    taskId: str
    preparationId: str
    sourceRevision: int
    format: Literal["PDF", "DOCX"]
    fileName: str
    status: TaskStatus
    fileId: str | None
    error: TaskError | None


class AffectedCounts(Contract):
    versions: int = Field(ge=0)
    exports: int = Field(ge=0)
    preparations: int = Field(ge=0)
    preparationExports: int = Field(ge=0)
    workspaces: int = Field(ge=0)
    experiences: int = Field(ge=0)
    tasks: int = Field(ge=0)


class DeletionImpact(Contract):
    resourceType: Literal["RESUME"]
    resourceId: str
    revision: int
    affectedCounts: AffectedCounts
    messages: list[str]


class ErrorPayload(Contract):
    code: str
    message: str
    details: dict


class ErrorOutput(Contract):
    error: ErrorPayload
    requestId: str


ResumeOutput.model_rebuild()
VersionOutput.model_rebuild()
