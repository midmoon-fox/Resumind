"""Add a deletion timestamp for interview preparation records."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "i0002"
down_revision = "i0001"
branch_labels = None
depends_on = None


def upgrade():
    # The initial B migration imports current metadata on a fresh install.
    columns = sa.inspect(op.get_bind()).get_columns("preparations")
    if not any(column["name"] == "deleted_at" for column in columns):
        op.add_column("preparations", sa.Column("deleted_at", DATETIME(fsp=6), nullable=True))


def downgrade():
    op.drop_column("preparations", "deleted_at")
