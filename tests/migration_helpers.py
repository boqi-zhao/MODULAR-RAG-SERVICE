"""迁移测试辅助函数：构造 Alembic 配置并在指定数据库执行升级或回退。"""

from pathlib import Path

from alembic import command
from alembic.config import Config

# 从项目根目录定位 alembic.ini，测试在任意工作目录运行都能找到配置。
ROOT = Path(__file__).resolve().parents[1]

# 首次迁移的版本号；旧结构升级测试先停在这里，再升级到最新迁移。
LEGACY_REVISION = "e5690f23be74"


def alembic_config(database_url: str) -> Config:
    """构造指向指定数据库的配置；地址放在 attributes 中，不经过 ConfigParser 插值。

    set_main_option 会把 % 当作插值语法，含特殊字符的密码（如 %40）会直接报错。
    """
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.attributes["database_url"] = database_url
    return config


def run_upgrade(database_url: str, revision: str = "head") -> None:
    """升级到指定版本；重复升级到同一版本不会重复建表。"""
    command.upgrade(alembic_config(database_url), revision)


def run_downgrade(database_url: str, revision: str = "base") -> None:
    """回退到指定版本；默认回退全部迁移。"""
    command.downgrade(alembic_config(database_url), revision)
