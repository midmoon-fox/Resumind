"""Strict public requests; A/B continue to own their public document schemas."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.modules.ai.experience_schemas import ExperienceData
from app.modules.tasks.schemas import ContractModel, ResourceId

Revision = Annotated[int, Field(ge=1)]
Name = Annotated[str, StringConstraints(min_length=1, max_length=200)]
FilterText = Annotated[str, StringConstraints(min_length=1, max_length=100)]
SectionType = Literal["PROJECTS", "INTERNSHIPS", "CAMPUS", "AWARDS", "EDUCATION", "SKILLS", "ACHIEVEMENTS", "CERTIFICATES", "GOAL", "CHARTS", "HOBBIES", "PUBLICATIONS", "REFERENCES", "SOCIAL_LINKS", "STRENGTHS", "TEXT", "VOLUNTEERING", "WORK_EXPERIENCE"]


def unique(values):
    if len(values) != len(set(values)):
        raise ValueError("Duplicate references")


class CreateFollowup(ContractModel):
    workspaceId: ResourceId
    baseWorkspaceRevision: Revision
    experienceIds: list[ResourceId] = Field(max_length=50)
    maxRounds: int = Field(default=4, ge=2, le=4)

    @model_validator(mode="after")
    def distinct(self):
        unique(self.experienceIds)
        return self


class RevisionRequest(ContractModel):
    baseRevision: Revision


class TurnRequest(RevisionRequest):
    turnId: ResourceId


class AnswerRequest(TurnRequest):
    answer: Annotated[str, StringConstraints(min_length=1, max_length=10000)]


class Confirmation(ContractModel):
    candidateId: ResourceId
    experienceId: ResourceId | None
    baseExperienceRevision: Revision | None
    data: ExperienceData


class ConfirmRequest(TurnRequest):
    updates: list[Confirmation] = Field(max_length=50)

    @model_validator(mode="after")
    def distinct(self):
        unique([value.candidateId for value in self.updates])
        unique([value.experienceId for value in self.updates if value.experienceId])
        return self


class CompleteRequest(RevisionRequest):
    reason: Annotated[str, StringConstraints(max_length=200)] = "用户主动结束"


class ExperienceRef(ContractModel):
    id: ResourceId
    revision: Revision


class GenerateRequest(ContractModel):
    workspaceId: ResourceId
    baseWorkspaceRevision: Revision
    experienceRevisions: list[ExperienceRef] = Field(max_length=50)
    templateId: Literal["simple", "project"]
    templateVersion: Literal["1.0.0"]
    sectionTypes: list[SectionType] = Field(min_length=1, max_length=18)
    title: Name = "我的简历"

    @model_validator(mode="after")
    def distinct(self):
        unique([value.id for value in self.experienceRevisions])
        unique(self.sectionTypes)
        return self


class ItemTarget(ContractModel):
    kind: Literal["ITEM_DESCRIPTION"]
    sectionId: ResourceId
    itemId: ResourceId


class SectionTarget(ContractModel):
    kind: Literal["SECTION_CONTENT"]
    sectionId: ResourceId


class ProfileTarget(ContractModel):
    kind: Literal["PROFILE_FIELD"]
    sectionId: ResourceId
    field: Literal["education", "skills"]


class SectionFieldTarget(ContractModel):
    kind: Literal["SECTION_FIELD"]
    sectionId: ResourceId
    field: Literal["text"]


Target = Annotated[ItemTarget | SectionTarget | ProfileTarget | SectionFieldTarget, Field(discriminator="kind")]


class SuggestRequest(RevisionRequest):
    target: Target
    instruction: Annotated[str, StringConstraints(min_length=1, max_length=4000)]


class PreparationRequest(ContractModel):
    resumeVersionId: ResourceId
    type: Literal["INTRODUCTION", "INTERVIEW_QUESTIONS"]
    questionCount: int = Field(default=5, ge=5, le=10)
    tone: Annotated[str, StringConstraints(max_length=100)] = "自然简洁"

    @model_validator(mode="after")
    def type_options(self):
        if self.type == "INTRODUCTION" and "questionCount" in self.model_fields_set:
            raise ValueError("questionCount applies only to interview questions")
        return self


class RecommendRequest(ContractModel):
    resumeVersionId: ResourceId
    city: FilterText
    direction: FilterText
    experienceLevel: FilterText


class SaveJobRequest(ContractModel):
    title: Name = "推荐岗位"
