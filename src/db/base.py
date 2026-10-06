"""ORM 模型共用的基类；这里只定义结构，不连接数据库或创建表。"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# 给索引和约束固定命名，方便迁移文件明确指出要修改哪一条规则。
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# 后续上传模型继承 Base，Alembic 从 metadata 读取这些模型的表结构。
class Base(DeclarativeBase):
    """所有业务 ORM 模型的共同入口。"""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
