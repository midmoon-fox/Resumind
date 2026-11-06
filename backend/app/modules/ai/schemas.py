"""Internal A/C ability DTOs, not a replacement for A/B public resource schemas."""

from dataclasses import dataclass, field
from typing import Annotated, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.modules.tasks.schemas import ResourceId, TaskError

MiB = 1024 * 1024
Text = Annotated[str, StringConstraints(max_length=100_000)]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=2000)]


class AbilityModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class ModelSettings(AbilityModel):
    model: Literal["deepseek-flash"] = "deepseek-flash"
    enable_live_calls: bool = False
    timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    max_output_tokens: int = Field(default=4096, ge=1, le=8192)
    max_request_bytes: int = Field(default=32 * MiB, ge=1024, le=48 * MiB)
    max_response_bytes: int = Field(default=MiB, ge=1024, le=4 * MiB)


class Usage(AbilityModel):
    promptTokens: int = Field(ge=0)
    completionTokens: int = Field(ge=0)
    totalTokens: int = Field(ge=0)


class ModelMetadata(AbilityModel):
    provider: Literal["deepseek"] = "deepseek"
    requestedModel: str
    responseModel: str
    responseId: str
    promptVersion: str
    protocolVersion: Literal["1.1.0"] = "1.1.0"
    offline: bool
    usage: Usage | None


T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class AbilityResult[T: BaseModel]:
    value: T = field(repr=False)
    metadata: ModelMetadata


class SourceSegment(AbilityModel):
    id: ResourceId
    text: Text = Field(repr=False, min_length=1)
    page: int | None = Field(default=None, ge=1, le=50)


class Evidence(AbilityModel):
    segmentId: ResourceId
    quote: Annotated[str, StringConstraints(min_length=1, max_length=4000)] = Field(repr=False)


class RequirementCandidate(AbilityModel):
    category: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    text: ShortText = Field(repr=False)
    necessity: Literal["REQUIRED", "PREFERRED", "UNSPECIFIED"]
    evidence: list[Evidence] = Field(min_length=1, max_length=1)


class JdAnalysis(AbilityModel):
    requirements: list[RequirementCandidate] = Field(max_length=100)
    missingInformation: list[ShortText] = Field(max_length=20)
    needsReview: Literal[True] = True


class ImagePage(AbilityModel):
    """A supplies authorized, fully validated image bytes; no URL or path input."""

    sourceId: ResourceId
    page: int = Field(ge=1, le=50)
    mimeType: Literal["image/png", "image/jpeg"]
    content: bytes = Field(min_length=1, max_length=20 * MiB, repr=False, exclude=True)


class Uncertainty(AbilityModel):
    blockIndex: int | None = Field(ge=1)
    reason: ShortText


class OcrDraft(AbilityModel):
    # Model cannot supply IDs, pages, confidence scores or pixel boxes.
    blocks: list[Annotated[str, StringConstraints(min_length=1, max_length=10_000)]] = Field(
        max_length=1000, repr=False
    )
    uncertainties: list[Uncertainty] = Field(max_length=100)
    warnings: list[ShortText] = Field(max_length=20)

    @model_validator(mode="after")
    def bounded_content(self):
        if sum(len(block) for block in self.blocks) + max(0, len(self.blocks) - 1) > 100_000:
            raise ValueError("OCR text exceeds project limit")
        if any(
            item.blockIndex is not None and item.blockIndex > len(self.blocks)
            for item in self.uncertainties
        ):
            raise ValueError("Unknown OCR block reference")
        return self


class OcrBlock(AbilityModel):
    ordinal: int = Field(ge=1)
    text: Text = Field(repr=False)


class OcrPageResult(AbilityModel):
    sourceId: ResourceId
    page: int
    status: Literal["READY", "EMPTY", "FAILED", "NOT_ATTEMPTED"]
    text: Text | None = Field(repr=False)
    blocks: list[OcrBlock]
    uncertainties: list[Uncertainty]
    warnings: list[str]
    needsReview: Literal[True] = True
    error: TaskError | None
    retryAfterSeconds: int | None = None  # Internal A/C metadata, never a new TaskError field.
    metadata: ModelMetadata | None


class OcrBatchResult(AbilityModel):
    status: Literal["READY", "PARTIAL", "FAILED"]
    pages: list[OcrPageResult]
