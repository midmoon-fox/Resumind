"""Internal Python integration contracts. Every write shares the caller's Session."""

from typing import Protocol

from sqlalchemy.orm import Session

from app.modules.tasks.registry import TaskInput


class AServices(Protocol):
    def workspace(self, db: Session, user: str, workspace: str, lock: bool) -> dict:
        """Owned live workspace, revision, profile, direction, JD and active follow-up pointer."""
        ...

    def facts(
        self, db: Session, user: str, workspace: str, ids: list[str], lock: bool
    ) -> list[dict]:
        """Owned live facts: id/revision/type/data/provenance/status/excluded.
        Same workspace, nonexcluded; lock sorted IDs.
        Missing/foreign/deleted -> ResourceUnavailable.
        """
        ...

    def set_active_followup(
        self, db: Session, user: str, workspace: str, followup: str
    ) -> None: ...

    def confirm(
        self, db: Session, user: str, workspace: str, turn: str, updates: list[dict]
    ) -> list[dict]:
        """Each update: candidateId/type/experienceId/baseExperienceRevision/data/provenance.
        Validate all references, lock sorted, CAS update or allocate UUID, write FOLLOWUP sources.
        Return resulting facts in update order; no commit. [] writes nothing.
        """
        ...

    def create_jd(self, db: Session, user: str, job: dict, title: str) -> dict:
        """Copy source into JD/version plus ANALYZE_JD task/outbox; return AsyncAccepted."""
        ...

    def jd_access(self, db: Session, user: str, version: str) -> None: ...


class BServices(Protocol):
    def resume(self, db: Session, user: str, resume: str, lock: bool) -> dict:
        """Owned, live resume including parent; public Resume fields."""
        ...

    def version(self, db: Session, user: str, version: str, lock: bool) -> dict:
        """Immutable ResumeVersion plus live parent check, document/template/style/jdSnapshot."""
        ...

    def template(self, db: Session, key: str, version: str, section_types: list[str]) -> dict:
        """Validate published assets, section support; return default style."""
        ...

    def create_resume(self, db: Session, user: str, snapshot: dict, request: dict) -> str:
        """Create generation draft only. Return UUID; no commit."""
        ...

    def create_preparation(self, db: Session, user: str, request: dict) -> str:
        """Create new GENERATING row; never overwrite edited previous preparation."""
        ...

    def bind_task(
        self, db: Session, user: str, resource_type: str, resource: str, task: str
    ) -> None: ...

    def check_task(self, db: Session, task: TaskInput, lock: bool) -> None:
        """Parent ownership/deletion, task binding and applicability. Completed task readable.
        Check snapshot/generation identity; manual edits must invalidate in-flight writes.
        """
        ...

    def save_generated(self, db: Session, task: TaskInput, document: dict) -> None:
        """Validate shared document/template/style; save generation draft atomically."""
        ...

    def save_preparation(self, db: Session, task: TaskInput, content: dict) -> None:
        """Shared PreparationContent validation, fixed version and generating row checks."""
        ...

    def task_state(self, db: Session, task: TaskInput, state: str) -> None:
        """Failure/cancel/retry transition with original snapshot and live parent guards."""
        ...

    def invalidate_task(self, db: Session, task: TaskInput) -> None:
        """Owned/live parent only. If still bound to this task, fail generation status.
        Never overwrite edited content, completed results or a newer task's binding.
        """
        ...

    def validate_document(self, document: dict, snapshot: dict) -> None:
        """Pure authoritative B document/template validation, also used before saving."""
        ...

    def validate_target(self, target: dict, value: dict) -> None:
        """Pure shared RichText/education/skills validator; rejects attrs, HTML and limits."""
        ...

    def apply_target(
        self,
        db: Session,
        user: str,
        resume: str,
        revision: int,
        target: dict,
        original: dict,
        proposed: dict,
    ) -> dict:
        """Locked CAS full-revision update of only target; return public Resume, revision+1."""
        ...
