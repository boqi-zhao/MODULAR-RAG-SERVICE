"""同步 ORM 的连接引擎与 Session 工厂；导入时配置，首次查询时连接 PG。"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import sessionmaker

from db.connection import get_database_url


# 校验连接地址并选择 Psycopg 同步驱动；Alembic 迁移复用同一规则。
def build_database_url(raw_url: str | None = None) -> URL:
    """返回 SQLAlchemy 可用的 URL 对象；不通过字符串替换改写密码。"""
    try:
        database_url = make_url(raw_url or get_database_url())
    except (ArgumentError, ValueError):
        raise RuntimeError("DATABASE_URL 格式无效，请检查 PostgreSQL 连接配置。") from None
    if database_url.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise RuntimeError("ORM 仅支持 PostgreSQL，使用 Psycopg 同步驱动。")
    return database_url.set(drivername="postgresql+psycopg")


# 引擎在本进程内复用；create_engine 本身不连接，首次查询时才建立连接。
def _create_engine() -> Engine:
    # 本步开发配置：最多 5 个连接，等待最多 30 秒；接口接入时再核对总预算。
    return create_engine(
        build_database_url(),
        pool_size=5,
        max_overflow=0,
        pool_timeout=30,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5, "application_name": "modular-rag-service"},
        echo=False,
        hide_parameters=True,
    )


# 引擎和工厂在本进程内复用；每次调用工厂都会创建独立 Session。
engine = _create_engine()
SessionFactory = sessionmaker(bind=engine)
