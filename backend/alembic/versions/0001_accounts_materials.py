"""A-owned schema, frozen MySQL 8.4 DDL; B/C tables are maintained by their owners."""
from pathlib import Path
from alembic import op

revision = 'a0001'
down_revision = None
branch_labels = ('accounts_materials',)
depends_on = None


def execute_file(name):
    sql = Path(__file__).with_name(name).read_text(encoding='utf-8')
    for statement in sql.split(';'):
        if statement.strip():
            op.execute(statement.strip())


def upgrade():
    execute_file('a0001_up.sql')


def downgrade():
    execute_file('a0001_down.sql')
