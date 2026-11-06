"""Business-side retry/cancel rules; C remains the only Task state owner."""
from .documents import uuid4 as validate_uuid
from .service import StateConflict


class ExportLifecycle:
    def _pending(self, session, user, export_id, task_id):
        validate_uuid(task_id, "/taskId")
        record = self._lock_record(session, user, export_id)
        if record.task_id != task_id:
            raise StateConflict("task does not own this export")
        if record.file_id is not None:
            raise StateConflict("export already has a committed file")
        return record

    def check_retry(self, session, user, export_id, task_id):
        """C checks retryable Task status and increments attempt in this same transaction."""
        record = self._pending(session, user, export_id, task_id)
        return {"resourceId": record.id, "taskId": record.task_id}

    def check_cancel(self, session, user, export_id, task_id):
        """No separate export status column: C's cancellation is the visible business state."""
        record = self._pending(session, user, export_id, task_id)
        return {"resourceId": record.id, "taskId": record.task_id}

    def discard(self, artifact, reference_safe_cleanup):
        """Outside transaction: A rechecks effective file references before deleting a temp object."""
        return reference_safe_cleanup(artifact)
