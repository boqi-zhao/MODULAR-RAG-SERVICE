"""旧结构升级验证：替换非空白约束时保留已有记录，且新规则立即生效。"""

import pytest
from migration_helpers import LEGACY_REVISION, run_upgrade
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# 插入 uploaded 状态记录的 SQL；参数化避免手工拼接字符串。
_INSERT_RECORD = text(
    "INSERT INTO document_uploads ("
    "document_id, filename, source_format, size_bytes, sha256, "
    "storage_type, storage_key, status, completed_at"
    ") VALUES ("
    ":document_id, :filename, :source_format, :size_bytes, :sha256, "
    "'local', :storage_key, 'uploaded', now()"
    ")"
)


# 构造一条合法 uploaded 记录；文档编号同时用作存储路径的一部分。
def _record(document_id: str, filename: str) -> dict:
    return {
        "document_id": document_id,
        "filename": filename,
        "source_format": "pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
        "storage_key": f"{document_id}/source.pdf",
    }


def test_upgrade_from_legacy_structure_keeps_records(legacy_database):
    """旧库升级后：版本前进、已有记录保留、特殊空白从可写入变为被拒绝。"""
    engine = create_engine(legacy_database)
    try:
        # 旧约束放行纯全角空格文件名；这条记录代表升级前的历史数据。
        with engine.begin() as connection:
            connection.execute(_INSERT_RECORD, _record("doc_legacy_1", "legacy.pdf"))
            connection.execute(_INSERT_RECORD, _record("doc_legacy_2", "\u3000"))

        run_upgrade(legacy_database)
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            rows = connection.execute(
                text("SELECT document_id, filename FROM document_uploads ORDER BY document_id")
            ).all()

        # 迁移只替换约束，不清理历史数据：两条记录都还在。
        assert version != LEGACY_REVISION
        assert rows == [("doc_legacy_1", "legacy.pdf"), ("doc_legacy_2", "\u3000")]

        # 升级后同样的纯空白文件名会被新约束拒绝。
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(_INSERT_RECORD, _record("doc_legacy_3", "\u3000"))

        # 合法记录仍可正常写入，说明约束替换没有误伤正常数据。
        with engine.begin() as connection:
            connection.execute(_INSERT_RECORD, _record("doc_legacy_4", "normal.pdf"))
    finally:
        engine.dispose()
