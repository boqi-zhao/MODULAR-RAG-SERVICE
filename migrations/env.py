"""Alembic 运行环境：读取 DATABASE_URL、加载 ORM 模型并执行迁移。"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import db.models  # noqa: F401  导入模型，让 Base.metadata 包含所有表
from db.base import Base
from db.session import build_database_url

# Alembic 的配置对象来自 alembic.ini；连接地址和模型在这里补充。
config = context.config

# 按 alembic.ini 的日志段落初始化日志；直接调用 env.py 时可能没有该文件。
# disable_existing_loggers=False 避免在测试进程内关闭业务 logger。
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# 迁移比对的“目标结构”来自 ORM 模型；新增模型后必须在这里可导入。
target_metadata = Base.metadata


def _database_url() -> str:
    """优先使用调用方通过 config.attributes 传入的地址（测试库），否则读取环境变量。"""
    override = config.attributes.get("database_url")
    # render_as_string 会包含真实密码；str(URL) 只用于展示，会把密码显示成 ***。
    return build_database_url(str(override) if override else None).render_as_string(
        hide_password=False
    )


def run_migrations_offline() -> None:
    """离线模式只把迁移渲染成 SQL，不连接数据库。"""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式用一次性连接执行迁移，执行完由 with 语句释放连接。"""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# 由 alembic 命令行选择模式：默认在线执行，加 --sql 时只输出 SQL。
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
