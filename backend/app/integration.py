"""Call from the final combined Alembic migration, after C has created its tables."""
from sqlalchemy import ForeignKeyConstraint, inspect


EXTERNAL_FOREIGN_KEYS = (
    ('workspaces', 'active_followup_session_id', 'followup_sessions', 'fk_workspace_followup'),
    ('experiences', 'generation_task_id', 'ai_tasks', 'fk_experience_generation_task'),
    ('experience_sources', 'turn_id', 'followup_turns', 'fk_experience_source_turn'),
)


def install_external_foreign_keys(connection):
    """Never creates C tables; all names are a fixed server-side allowlist."""
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    required = {target for _, _, target, _ in EXTERNAL_FOREIGN_KEYS}
    if not required <= tables:
        raise RuntimeError('C 表未齐全，不能安装跨模块外键：' + ','.join(sorted(required - tables)))
    for table, column, target, name in EXTERNAL_FOREIGN_KEYS:
        if name not in {fk['name'] for fk in inspector.get_foreign_keys(table)}:
            connection.exec_driver_sql(f'ALTER TABLE `{table}` ADD CONSTRAINT `{name}` FOREIGN KEY (`{column}`) REFERENCES `{target}` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT')


def attach_external_metadata(metadata):
    """Call after C ORM is registered in the shared Base, before final autogenerate."""
    for table, column, target, name in EXTERNAL_FOREIGN_KEYS:
        if target not in metadata.tables:
            raise RuntimeError('请先在共享Base注册C的ORM表：' + target)
        if name not in {fk.name for fk in metadata.tables[table].foreign_key_constraints}:
            metadata.tables[table].append_constraint(ForeignKeyConstraint([column], [target + '.id'], name=name, ondelete='RESTRICT', onupdate='RESTRICT'))
