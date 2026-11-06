"""C public response envelopes. B validates and supplies its Resume response model."""

from typing import Literal

from pydantic import Field, field_serializer

from app.modules.ai.experience_schemas import ExperienceData, ExperienceType
from app.modules.c_core.schemas import Revision, Target
from app.modules.tasks.schemas import ContractModel, ResourceId, TaskError


class Provenance(ContractModel):
    jsonPointer: str
    segmentIds: list[ResourceId]
    turnIds: list[ResourceId]
    origin: Literal["MATERIAL", "USER_INPUT", "FOLLOWUP"]


class Candidate(ContractModel):
    candidateId: ResourceId
    type: ExperienceType
    experienceId: ResourceId | None
    baseExperienceRevision: Revision | None
    proposedData: ExperienceData
    provenance: list[Provenance]
    conflicts: list[str]


class TurnView(ContractModel):
    id: ResourceId
    ordinal: int = Field(ge=1, le=4)
    status: Literal[
        "AWAITING_ANSWER", "ANALYZING", "REVIEW_REQUIRED", "CONFIRMED", "SKIPPED", "ABANDONED"
    ]
    question: str
    reason: str
    experienceId: ResourceId | None
    answer: str | None
    candidateUpdates: list[Candidate]
    createdAt: str


class ErrorView(ContractModel):
    @field_serializer("error", check_fields=False)
    def sanitized_error(self, value):
        return value.model_dump(mode="json", exclude_none=True) if value else None


class FollowupView(ErrorView):
    id: ResourceId
    workspaceId: ResourceId
    status: Literal[
        "GENERATING",
        "AWAITING_ANSWER",
        "ANALYZING_ANSWER",
        "REVIEW_REQUIRED",
        "READY_NEXT",
        "COMPLETED",
        "FAILED",
    ]
    revision: Revision
    roundsShown: int = Field(ge=0, le=4)
    maxRounds: int = Field(ge=2, le=4)
    pendingTaskId: ResourceId | None
    lastTaskId: ResourceId | None
    error: TaskError | None
    currentTurnId: ResourceId | None
    endedReason: str | None
    turns: list[TurnView]


class SuggestionView[V](ContractModel):
    id: ResourceId
    taskId: ResourceId
    resumeId: ResourceId
    baseRevision: Revision
    target: Target
    original: V
    proposed: V | None
    explanation: str
    needsFactConfirmation: bool
    status: Literal["GENERATING", "READY", "APPLIED", "REJECTED", "STALE", "FAILED"]
    appliedRevision: Revision | None
    createdAt: str


class JobView(ContractModel):
    id: ResourceId
    title: str
    company: str
    city: str
    salaryText: str | None
    sourceUrl: str
    fetchedAt: str
    publishedAt: str | None
    availability: Literal["UNKNOWN", "ACTIVE", "EXPIRED"]
    reasons: list[str]
    gaps: list[str]


class RunView(ErrorView):
    id: ResourceId
    taskId: ResourceId
    resumeVersionId: ResourceId
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCEL_REQUESTED", "CANCELLED"]
    filters: dict
    jobs: list[JobView]
    error: TaskError | None


class Envelope[T](ContractModel):
    data: T
    requestId: ResourceId
