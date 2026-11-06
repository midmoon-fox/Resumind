"""Durable tombstone sweeper; run periodically from deployment scheduler/C worker."""
from sqlalchemy import select

from .models import File, JdVersion, JobDescription, Material, Segment, now


def cleanup_once(sessions, storage, relations, tasks):
    counts = dict(materials=0, jdVersions=0, files=0)
    with sessions.begin() as db:
        for material in db.scalars(select(Material).where(Material.deleted_at.is_not(None)).with_for_update()):
            tasks.purge_resource_input(db, material.user_id, 'MATERIAL', material.id)
            material.input_text = None
            material.error_json = None
            for segment in db.scalars(select(Segment).where(Segment.material_id == material.id, Segment.user_id == material.user_id)):
                segment.text = ''
            counts['materials'] += 1
        for version in db.scalars(select(JdVersion).join(JobDescription, JobDescription.id == JdVersion.jd_id).where(JobDescription.deleted_at.is_not(None), JdVersion.purged_at.is_(None)).with_for_update()):
            tasks.purge_resource_input(db, version.user_id, 'JD_VERSION', version.id)
            version.original_text, version.requirements_json = '', []
            version.job_title, version.company_name, version.purged_at = None, None, now()
            version.source_url = None
            counts['jdVersions'] += 1
    # Deletion and DB state are intentionally separate: a crash after unlink is safe to retry.
    with sessions.begin() as db:
        for file in db.scalars(select(File).where(File.status == 'DELETING').with_for_update()):
            if relations.file_referenced(db, file):
                file.status, file.deleted_at = 'READY', None
                continue
            storage.delete(file.object_key)
            file.status = 'DELETED'
            counts['files'] += 1
    return counts


if __name__ == '__main__':
    from .main import create_app
    app = create_app()
    print(cleanup_once(app.state.sessions, app.state.storage, app.state.relations, app.state.tasks))
