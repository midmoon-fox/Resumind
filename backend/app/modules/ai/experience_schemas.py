"""Internal material extraction DTOs matching the contract's ExperienceData fields."""

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.modules.tasks.schemas import ResourceId

from .schemas import AbilityModel, Evidence, ShortText, SourceSegment

YearMonth = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")]
ExperienceType = Literal["PROJECT", "INTERNSHIP", "CAMPUS", "AWARD"]


class MaterialSegment(SourceSegment):
    materialId: ResourceId
    # Trusted A-side source metadata, never supplied by the model or inferred as confirmation.
    attribution: Literal["PERSONAL", "TEAM", "DEPENDENCY", "UNSPECIFIED"] = "UNSPECIFIED"


class ExperienceData(AbilityModel):
    name: Annotated[str, StringConstraints(max_length=200)] = Field(repr=False)
    startDate: YearMonth | None
    endDate: YearMonth | None
    isCurrent: bool
    background: Annotated[str, StringConstraints(max_length=5000)] = Field(repr=False)
    personalRole: Annotated[str, StringConstraints(max_length=2000)] = Field(repr=False)
    actions: list[ShortText] = Field(max_length=50, repr=False)
    outcomes: list[ShortText] = Field(max_length=50, repr=False)
    technologies: list[ShortText] = Field(max_length=50, repr=False)

    @model_validator(mode="after")
    def coherent_dates_and_text(self):
        for value in (self.startDate, self.endDate):
            if value is not None:
                date.fromisoformat(value + "-01")
        if self.isCurrent and self.endDate is not None:
            raise ValueError("Current experience cannot have an end date")
        if self.startDate and self.endDate and self.startDate > self.endDate:
            raise ValueError("Experience dates are reversed")
        for value in (
            self.name,
            self.background,
            self.personalRole,
            *self.actions,
            *self.outcomes,
            *self.technologies,
        ):
            if value and not value.strip():
                raise ValueError("Whitespace is not an experience field")
        return self


class FieldEvidence(Evidence):
    jsonPointer: Annotated[str, StringConstraints(min_length=1, max_length=80)]


class ExperienceDraft(AbilityModel):
    type: ExperienceType
    data: ExperienceData
    evidence: list[FieldEvidence] = Field(max_length=1000, repr=False)
    conflicts: list[ShortText] = Field(max_length=50, repr=False)

    @model_validator(mode="after")
    def has_identifiable_experience(self):
        if not (
            self.data.name
            or self.data.background
            or self.data.personalRole
            or self.data.actions
            or self.data.outcomes
        ):
            raise ValueError("Dates or technology names alone do not identify an experience")
        return self


class MaterialDraft(AbilityModel):
    experiences: list[ExperienceDraft] = Field(max_length=50)
    warnings: list[ShortText] = Field(max_length=20, repr=False)


class MaterialProvenance(AbilityModel):
    jsonPointer: str
    segmentIds: list[ResourceId]
    turnIds: list[ResourceId] = Field(default_factory=list)
    origin: Literal["MATERIAL"] = "MATERIAL"


class ExperienceReview(AbilityModel):
    # This path refers to the original model proposal, not the sanitized arrays.
    proposedPath: str
    proposedValue: str | bool = Field(repr=False)
    reason: Literal[
        "PERSONAL_CONTRIBUTION_UNCONFIRMED",
        "TEAM_CONTEXT",
        "DEPENDENCY_ONLY",
        "MIXED_ATTRIBUTION",
        "DATE_NOT_IN_SOURCE",
        "CURRENT_STATUS_UNSUPPORTED",
    ]
    evidence: list[FieldEvidence] = Field(repr=False)


class ExperienceCandidate(AbilityModel):
    type: ExperienceType
    data: ExperienceData
    provenance: list[MaterialProvenance]
    reviewItems: list[ExperienceReview]
    conflicts: list[ShortText] = Field(repr=False)
    status: Literal["CANDIDATE"] = "CANDIDATE"
    needsReview: Literal[True] = True
    reviewOnly: bool


class MaterialExtraction(AbilityModel):
    materialId: ResourceId
    candidates: list[ExperienceCandidate]
    warnings: list[ShortText] = Field(repr=False)
