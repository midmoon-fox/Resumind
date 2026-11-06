import os

from alembic import context
from sqlalchemy import create_engine

# 导入全部模型，使 26 张业务表都注册进共享 Base.metadata（合并方案 F02）。
import app.models  # noqa: F401   A：账户/资料
import resume_b.models  # noqa: F401   B：模板/简历/导出
import app.modules.tasks.models  # noqa: F401   C：ai_tasks/outbox
import app.modules.c_core.models  # noqa: F401   C：追问/建议/推荐

from app.shared.base import Base
from app.core import mysql_version_allowed

config = context.config
url = os.environ.get("DATABASE_URL")
if not url:
    raise RuntimeError("请设置 DATABASE_URL；迁移支持 MySQL 8.4/26.7")
if not url.startswith("mysql+pymysql://"):
    raise RuntimeError("部署迁移需要 mysql+pymysql://，SQLite 仅用于隔离测试")

if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as connection:
        version = str(connection.exec_driver_sql("SELECT VERSION()").scalar())
        if not mysql_version_allowed(version, url):
            raise RuntimeError(f"支持 MySQL 8.4 或 26.7，实际 {version}")
        connection.exec_driver_sql("SET time_zone = '+00:00'")
        connection.commit()
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
