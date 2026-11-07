"""Deletion impact and coordinated revocation in the caller's transaction."""
from sqlalchemy import select

from .documents import require
from .models import Export, Preparation, PreparationExport, ResumeVersion


class DeletionService:
    def __init__(self, resumes, *, count_sources, count_tasks, on_deleted):
        self.resumes, self.session = resumes, resumes.session
        self.count_sources, self.count_tasks, self.on_deleted = count_sources, count_tasks, on_deleted

    def related(self, user, resume_id, *, lock=False):
        resume = self.resumes.get(user, resume_id, lock=lock)
        versions = list(self.session.scalars(select(ResumeVersion).where(ResumeVersion.user_id == user, ResumeVersion.resume_id == resume_id)))
        version_ids = [version.id for version in versions]
        exports = list(self.session.scalars(select(Export).where(Export.user_id == user, Export.resume_version_id.in_(version_ids))))
        preparations = list(self.session.scalars(select(Preparation).where(Preparation.user_id == user, Preparation.resume_version_id.in_(version_ids), Preparation.deleted_at.is_(None))))
        preparation_exports = list(self.session.scalars(select(PreparationExport).where(PreparationExport.user_id == user, PreparationExport.preparation_id.in_([p.id for p in preparations]))))
        return resume, versions, exports, preparations, preparation_exports

    def impact(self, user, resume_id, *, lock=False):
        resume, versions, exports, preparations, preparation_exports = self.related(user, resume_id, lock=lock)
        references = {"resumeId": resume_id, "versionIds": [v.id for v in versions], "exportIds": [e.id for e in exports],
                      "preparationIds": [p.id for p in preparations], "preparationExportIds": [e.id for e in preparation_exports]}
        experiences = {item["experienceId"] for document in [resume.document_json, *(v.document_json for v in versions)] for section in document["sections"] for item in section["items"] if item["experienceId"] is not None}
        source_counts = self.count_sources(self.session, user, resume.workspace_id, experiences)
        task_count = self.count_tasks(self.session, user, references)
        counts = {"versions": len(versions), "exports": len(exports), "preparations": len(preparations), "preparationExports": len(preparation_exports),
                  "workspaces": source_counts["workspaces"], "experiences": source_counts["experiences"], "tasks": task_count}
        require(all(type(count) is int and count >= 0 for count in counts.values()), "", "invalid deletion count provider result")
        return {"resourceType": "RESUME", "resourceId": resume_id, "revision": resume.revision, "affectedCounts": counts,
                "messages": ["删除后该简历历史版本、导出和面试资料不可访问；工作区及经历保留。", "文件清理会检查其他有效引用，不会因删除本简历而误删共用文件。"]}

    def delete(self, user, resume_id):
        # Confirmation output is advisory; deletion recomputes under the parent lock.
        impact = self.impact(user, resume_id, lock=True)
        _, _, exports, _, preparation_exports = self.related(user, resume_id)
        file_ids = {record.file_id for record in [*exports, *preparation_exports] if record.file_id is not None}
        self.resumes.delete(user, resume_id)
        self.on_deleted(self.session, user, resume_id, file_ids, impact)
