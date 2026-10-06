"""迁移配置回归测试：特殊字符密码不经过 ConfigParser 插值。"""

from migration_helpers import alembic_config


def test_percent_encoded_password_is_not_interpolated():
    """含 %40 的地址原样保留，不会再触发 ConfigParser 的插值错误。"""
    database_url = "postgresql+psycopg://rag:a%40b@127.0.0.1:5432/modular_rag"
    config = alembic_config(database_url)

    assert config.attributes["database_url"] == database_url
    # 地址不再写入 ini 配置；读取该项才会触发插值解析。
    assert config.get_main_option("sqlalchemy.url", "") == ""
