"""上传记录表首次迁移的真实验证：结构、重复升级与往返回退。"""

from contextlib import contextmanager

from migration_helpers import run_downgrade, run_upgrade
from sqlalchemy import create_engine, inspect, text

# 首次迁移中的 10 条检查约束；逐个核对名称，防止漏建或多建。
EXPECTED_CHECK_CONSTRAINTS = {
    "ck_document_uploads_completed_at_not_before_created_at",
    "ck_document_uploads_error_message_not_blank",
    "ck_document_uploads_filename_not_blank",
    "ck_document_uploads_sha256_format",
    "ck_document_uploads_size_bytes_nonnegative",
    "ck_document_uploads_source_format_not_blank",
    "ck_document_uploads_state_fields_consistent",
    "ck_document_uploads_status_valid",
    "ck_document_uploads_storage_key_not_blank",
    "ck_document_uploads_storage_type_not_blank",
}


@contextmanager
def _inspector(database_url: str):
    """临时创建引擎用于读取结构；退出时释放连接，便于随后删除测试库。"""
    engine = create_engine(database_url)
    try:
        yield inspect(engine)
    finally:
        engine.dispose()


def test_upgrade_creates_columns_and_constraints(migrated_database):
    """建表后字段可空性、检查约束和唯一约束与设计一致。"""
    with _inspector(migrated_database) as inspector:
        assert "document_uploads" in inspector.get_table_names()
        columns = {column["name"]: column for column in inspector.get_columns("document_uploads")}
        assert columns["document_id"]["nullable"] is False
        assert columns["status"]["nullable"] is False
        assert columns["size_bytes"]["nullable"] is True
        checks = {item["name"] for item in inspector.get_check_constraints("document_uploads")}
        assert checks == EXPECTED_CHECK_CONSTRAINTS
        unique_names = {
            item["name"] for item in inspector.get_unique_constraints("document_uploads")
        }
        assert unique_names == {"uq_document_uploads_storage_type_storage_key"}
        primary_key = inspector.get_pk_constraint("document_uploads")
        assert primary_key["constrained_columns"] == ["document_id"]


def test_repeated_upgrade_keeps_single_version(migrated_database):
    """重复执行 upgrade head 不再次建表，版本表只保留一行记录。"""
    run_upgrade(migrated_database)
    engine = create_engine(migrated_database)
    try:
        with engine.connect() as connection:
            versions = (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            )
        assert len(versions) == 1
    finally:
        engine.dispose()
    # 表仍然存在且可用，说明重复升级只是跳过，没有重建。
    with _inspector(migrated_database) as inspector:
        assert "document_uploads" in inspector.get_table_names()


def test_downgrade_and_upgrade_round_trip(migrated_database):
    """回退到 base 删除上传表，再升级恢复；只在临时测试库执行。"""
    run_downgrade(migrated_database)
    with _inspector(migrated_database) as inspector:
        assert "document_uploads" not in inspector.get_table_names()
    run_upgrade(migrated_database)
    with _inspector(migrated_database) as inspector:
        assert "document_uploads" in inspector.get_table_names()
