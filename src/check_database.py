"""独立数据库检查入口：使用共享 logger，查询数据库名称。"""

import psycopg

from common.logger import logger
from db.connection import get_connection

# 日志模块负责配置；这里仅执行检查并记录结果，不重复初始化日志。
if __name__ == "__main__":
    try:
        with get_connection() as connection:
            database_name = connection.execute("SELECT current_database()").fetchone()[0]
        logger.info("PostgreSQL connection successful: %s", database_name)
    except (RuntimeError, psycopg.Error) as error:
        # 记录错误类型，不输出可能含密码的底层错误文本或连接地址。
        logger.error(
            "PostgreSQL connection failed (%s); check Docker, DATABASE_URL and port",
            type(error).__name__,
        )
        raise SystemExit(1) from None
