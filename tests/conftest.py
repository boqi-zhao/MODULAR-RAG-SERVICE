"""测试共用夹具：为上传表测试创建独立临时数据库并执行迁移。"""

import os
from uuid import uuid4

import psycopg
import pytest
from migration_helpers import LEGACY_REVISION, run_upgrade
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


# 连接维护库；autocommit 才能执行 CREATE/DROP DATABASE 这类管理语句。
def _connect_for_admin(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn, autocommit=True)


@pytest.fixture
def empty_database():
    """创建独立临时数据库，结束后强制删除；夹具本身不执行迁移。

    使用临时库而不是开发库，避免验证数据混入正式上传记录。
    """
    if not os.environ.get("DATABASE_URL", "").strip():
        pytest.skip("使用 uv run --env-file .env pytest 加载真实 PG 配置")

    base_url = make_url(os.environ["DATABASE_URL"])
    temp_database = f"test_upload_{uuid4().hex[:12]}"
    # render_as_string 会包含真实密码；str(URL) 会把密码显示成 *** 而无法连接。
    admin_dsn = base_url.render_as_string(hide_password=False)
    temp_dsn = base_url.set(database=temp_database).render_as_string(hide_password=False)

    with _connect_for_admin(admin_dsn) as connection:
        connection.execute(f'CREATE DATABASE "{temp_database}"')
    try:
        yield temp_dsn
    finally:
        with _connect_for_admin(admin_dsn) as connection:
            connection.execute(f'DROP DATABASE IF EXISTS "{temp_database}" WITH (FORCE)')


@pytest.fixture
def migrated_database(empty_database):
    """在临时库执行全部迁移，用于验证最新结构。"""
    run_upgrade(empty_database)
    yield empty_database


@pytest.fixture
def legacy_database(empty_database):
    """在临时库只执行首次迁移，用于验证旧结构升级路径。"""
    run_upgrade(empty_database, LEGACY_REVISION)
    yield empty_database


@pytest.fixture
def upload_engine(migrated_database):
    """指向最新结构临时库的引擎；先释放连接池，夹具随后才能删除数据库。"""
    engine = create_engine(migrated_database)
    try:
        yield engine
    finally:
        engine.dispose()
