"""API contract 1.1.0. Do not expose input snapshots or provider metadata."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_serializer

ResourceId = Annotated[
    str,
    StringConstraints(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    ),
]


class Kind(StrEnum):
    PARSE_MATERIAL = "PARSE_MATERIAL"
    ANALYZE_JD = "ANALYZE_JD"
    GENERATE_QUESTION = "GENERATE_QUESTION"
    ANALYZE_ANSWER = "ANALYZE_ANSWER"
    GENERATE_RESUME = "GENERATE_RESUME"
    REWRITE_ITEM = "REWRITE_ITEM"
    EXPORT_RESUME = "EXPORT_RESUME"
    GENERATE_PREPARATION = "GENERATE_PREPARATION"
    EXPORT_PREPARATION = "EXPORT_PREPARATION"
    RECOMMEND_JOBS = "RECOMMEND_JOBS"


class Status(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class ResourceType(StrEnum):
    MATERIAL = "MATERIAL"
    JD_VERSION = "JD_VERSION"
    FOLLOWUP_SESSION = "FOLLOWUP_SESSION"
    RESUME = "RESUME"
    SUGGESTION = "SUGGESTION"
    EXPORT = "EXPORT"
    PREPARATION = "PREPARATION"
    PREPARATION_EXPORT = "PREPARATION_EXPORT"
    RECOMMENDATION_RUN = "RECOMMENDATION_RUN"


KIND_RESOURCE = dict(
    zip(
        Kind,
        (
            ResourceType.MATERIAL,
            ResourceType.JD_VERSION,
            ResourceType.FOLLOWUP_SESSION,
            ResourceType.FOLLOWUP_SESSION,
            ResourceType.RESUME,
            ResourceType.SUGGESTION,
            ResourceType.EXPORT,
            ResourceType.PREPARATION,
            ResourceType.PREPARATION_EXPORT,
            ResourceType.RECOMMENDATION_RUN,
        ),
        strict=True,
    )
)

RESOURCE_PATHS = {
    ResourceType.MATERIAL: "materials",
    ResourceType.FOLLOWUP_SESSION: "followup-sessions",
    ResourceType.RESUME: "resumes",
    ResourceType.SUGGESTION: "suggestions",
    ResourceType.EXPORT: "exports",
    ResourceType.PREPARATION: "preparations",
    ResourceType.PREPARATION_EXPORT: "preparation-exports",
    ResourceType.RECOMMENDATION_RUN: "recommendation-runs",
}


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ErrorDetail(ContractModel):
    code: str
    message: str
    details: dict


class ErrorResponse(ContractModel):
    error: ErrorDetail
    requestId: ResourceId


class Issue(ContractModel):
    code: str
    severity: str
    path: str
    message: str


class TaskError(ContractModel):
    code: str
    message: str
    canRetry: bool
    issues: list[Issue] | None = None


class ResourceRef(ContractModel):
    resourceType: ResourceType
    resourceId: ResourceId
    resourceUrl: str


class TaskView(ContractModel):
    id: ResourceId
    kind: Kind
    status: Status
    stage: str
    attempt: int = Field(ge=0)
    result: ResourceRef | None
    error: TaskError | None
    createdAt: datetime
    updatedAt: datetime

    @field_serializer("error")
    def error_json(self, value: TaskError | None):
        return value.model_dump(mode="json", exclude_none=True) if value else None

    @field_serializer("createdAt", "updatedAt")
    def utc_string(self, value: datetime) -> str:
        return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


class TaskResponse(ContractModel):
    data: TaskView
    requestId: ResourceId


class RetryRequest(ContractModel):
    expectedAttempt: int = Field(ge=0)


class AsyncAccepted(ContractModel):
    taskId: ResourceId
    resourceType: ResourceType
    resourceId: ResourceId
    status: str
    statusUrl: str
    resourceUrl: str


class AsyncAcceptedResponse(ContractModel):
    data: AsyncAccepted
    requestId: ResourceId
