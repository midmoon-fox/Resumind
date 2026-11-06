"""c0002：C 的追问/建议/推荐五张业务表，依赖 ai_tasks（c0001）与 A 的 users。"""
from alembic import op

revision = "c0002"
down_revision = "b0001"
branch_labels = None
depends_on = None

_TABLES = (
    "followup_sessions",
    "followup_turns",
    "ai_suggestions",
    "recommendation_runs",
    "recommended_jobs",
)


def _bind():
    import app.modules.c_core.models  # noqa: F401
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
