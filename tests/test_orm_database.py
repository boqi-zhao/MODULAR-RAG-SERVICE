"""ORM 基础的真实 PG 验证；使用临时表，不写正式业务数据。"""

import os

import pytest
from sqlalchemy import text


# 未提供数据库配置时明确跳过；配置已提供但数据库不可用时，测试应失败。
@pytest.fixture
def orm_database():
    if not os.environ.get("DATABASE_URL", "").strip():
        pytest.skip("使用 uv run --env-file .env pytest 加载真实 PG 配置")
    from db.session import SessionFactory, engine

    try:
        yield SessionFactory, engine
    finally:
        engine.dispose()


# 同一连接内的临时表用于观察提交和回滚，连接关闭后不会留下正式表。
def test_session_commits_and_rolls_back(orm_database):
    session_factory, engine = orm_database
    with engine.connect() as connection:
        connection.execute(text("CREATE TEMP TABLE orm_transaction_probe (value integer)"))
        connection.commit()
        with session_factory(bind=connection) as session, session.begin():
            session.execute(text("INSERT INTO orm_transaction_probe VALUES (1)"))
        with pytest.raises(RuntimeError, match="模拟业务失败"):
            with session_factory(bind=connection) as session, session.begin():
                session.execute(text("INSERT INTO orm_transaction_probe VALUES (2)"))
                raise RuntimeError("模拟业务失败")

        # 成功事务的值保留，失败事务的值消失；同一连接还能继续正常查询。
        with session_factory(bind=connection) as session, session.begin():
            values = (
                session.execute(text("SELECT value FROM orm_transaction_probe")).scalars().all()
            )
        assert values == [1]
    assert engine.pool.checkedout() == 0


# 两个会话都实际查询 PG，离开事务后各自释放连接，不共用会话状态。
def test_factory_creates_independent_sessions(orm_database):
    session_factory, engine = orm_database
    with session_factory.begin() as first, session_factory.begin() as second:
        assert first is not second
        first_pid = first.execute(text("SELECT pg_backend_pid()")).scalar_one()
        second_pid = second.execute(text("SELECT pg_backend_pid()")).scalar_one()
        assert first_pid != second_pid
    assert engine.pool.checkedout() == 0
