"""c0001：C 的 ai_tasks / outbox_events，沿用 a0001（A 已冻结表）之后。"""
from alembic import op

revision = "c0001"
down_revision = "a0001"
branch_labels = None
depends_on = None


def _bind():
    import app.modules.tasks.models  # noqa: F401
    from app.shared.base import Base

    return Base.metadata


def upgrade():
    metadata = _bind()
    for name in ("ai_tasks", "outbox_events"):
        metadata.tables[name].create(op.get_bind(), checkfirst=True)


def downgrade():
    metadata = _bind()
    for name in ("outbox_events", "ai_tasks"):
        metadata.tables[name].drop(op.get_bind(), checkfirst=True)
