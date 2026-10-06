"""读取配置并创建 PostgreSQL 连接；检查入口见 src/check_database.py。"""

import os

import psycopg


# 驱动检查与 ORM 使用同一配置入口，缺少配置时给出明确提示。
def get_database_url() -> str:
    """读取连接配置，不打印可能含账号密码的地址。"""
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("请配置 DATABASE_URL，可通过 uv run --env-file .env 加载。")
    return database_url


# 只在调用时连接数据库，原独立检查命令继续使用这个入口。
def get_connection() -> psycopg.Connection:
    """创建连接；调用者使用 with 管理事务并关闭连接。"""
    return psycopg.connect(
        get_database_url(), connect_timeout=5, application_name="modular-rag-service"
    )
