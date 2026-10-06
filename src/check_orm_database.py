"""独立 ORM 检查入口：通过 Session 查询数据库，并在退出前释放连接池。"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.logger import logger


# 在错误处理范围内加载配置，连接地址无效时也使用统一日志报告失败。
def main() -> None:
    engine = None
    try:
        from db.session import SessionFactory, engine

        with SessionFactory.begin() as session:
            database_name = session.execute(text("SELECT current_database()")).scalar_one()
        logger.info("ORM connection successful: %s", database_name)
    except (RuntimeError, SQLAlchemyError) as error:
        # 不输出底层异常文本或连接地址，避免记录密码与 SQL 参数。
        logger.error(
            "ORM connection failed (%s); check DATABASE_URL and PostgreSQL", type(error).__name__
        )
        raise SystemExit(1) from None
    finally:
        if engine is not None:
            engine.dispose()


# 作为脚本运行时检查连接；被其他模块导入时不执行数据库查询。
if __name__ == "__main__":
    main()
