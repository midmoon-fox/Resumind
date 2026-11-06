"""单一 DeclarativeBase，承载 A/B/C 全部业务表的同一 metadata。

合并方案 F02：A 的 Base、B 的 Base、C 的 TaskBase 原本各自独立，导致
alembic 只迁移本模块的表、跨模块外键无法解析。此处提供唯一 Base，
三个模型文件分别 import 它（保留各自模块内的旧别名以最小化改动）。
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """26 张业务表共享的唯一 metadata。"""
