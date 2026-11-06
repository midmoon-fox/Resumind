"""i0001：跨模块外键（A 的表引用 C 的 ai_tasks / followup 会话与轮次）。"""
import sqlalchemy as sa
from alembic import op

from app.integration import EXTERNAL_FOREIGN_KEYS

revision = "i0001"
down_revision = "c0002"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = {fk["name"] for table in inspector.get_table_names() for fk in inspector.get_foreign_keys(table)}
    for table, column, target, name in EXTERNAL_FOREIGN_KEYS:
        if name not in existing:
            op.create_foreign_key(name, table, target, [column], ["id"])


def downgrade():
    for table, column, target, name in EXTERNAL_FOREIGN_KEYS:
        op.drop_constraint(name, table, type_="foreignkey")
