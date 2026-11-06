"""b0001：B 的六张文档/导出表，依赖 a0001（users/files/workspaces）与 c0001（ai_tasks）。"""
from alembic import op

revision = "b0001"
down_revision = "c0001"
branch_labels = None
depends_on = None

_TABLES = ("templates", "resumes", "resume_versions", "exports", "preparations", "preparation_exports")


def _bind():
    import resume_b.models  # noqa: F401
    from app.shared.base import Base

    return Base.metadata


def upgrade():
    metadata = _bind()
    for name in _TABLES:
        metadata.tables[name].create(op.get_bind(), checkfirst=True)


def downgrade():
    metadata = _bind()
    for name in reversed(_TABLES):
        metadata.tables[name].drop(op.get_bind(), checkfirst=True)
