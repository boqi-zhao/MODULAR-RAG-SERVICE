"""上传记录表约束的真实验证：合法记录可保存，非法数据被数据库拒绝。"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models.document_upload import DocumentUpload


# 构造一条字段齐全的合法记录；每个用例只覆盖需要出错的字段。
def _record_values(**overrides) -> dict:
    values = {
        "document_id": f"doc_{uuid4()}",
        "filename": "sample.pdf",
        "source_format": "pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
        "storage_type": "local",
        "storage_key": f"doc_{uuid4()}/source.pdf",
        "status": "uploading",
    }
    values.update(overrides)
    return values


# 插入并提交一条记录；数据库拒绝时抛出 IntegrityError 供用例捕获。
def _insert(engine, **overrides) -> None:
    with Session(engine) as session, session.begin():
        session.add(DocumentUpload(**_record_values(**overrides)))


def test_valid_records_are_saved(upload_engine):
    """三种状态各保存一条；完成时间用数据库时钟，避免主机时钟误差。"""
    _insert(upload_engine, status="uploading")
    _insert(upload_engine, status="uploaded", completed_at=func.now())
    _insert(
        upload_engine,
        status="failed",
        size_bytes=None,
        sha256=None,
        completed_at=func.now(),
        error_message="文件超过大小限制",
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "done"},  # 状态取值不在允许列表
        {"status": "uploaded", "completed_at": func.now(), "size_bytes": None},
        {"status": "uploaded", "completed_at": func.now(), "size_bytes": 0},
        {"status": "uploaded", "completed_at": func.now(), "sha256": None},
        {"status": "uploaded", "size_bytes": 1024},  # 缺少完成时间
        {"status": "failed", "completed_at": func.now()},  # 缺少失败说明
        {"status": "failed", "error_message": "失败原因"},  # 缺少完成时间
        {"status": "uploading", "completed_at": func.now()},
        {"status": "uploading", "error_message": "意外失败"},
        {"status": "uploading", "size_bytes": -1},  # 大小不能为负
        {"status": "uploading", "sha256": "A" * 64},  # 校验和必须为小写十六进制
        {"status": "uploading", "sha256": "abc"},
        {
            "status": "failed",
            "completed_at": func.now(),
            "error_message": "   ",  # 仅空白不算失败说明
        },
        {
            "status": "uploaded",
            "completed_at": datetime(2000, 1, 1, tzinfo=UTC),  # 早于开始时间
        },
        {"filename": "  "},  # 文件名不能为空白
        {"source_format": "\t"},
        {"storage_type": "\n"},
        {"storage_key": "  "},
    ],
)
def test_invalid_records_are_rejected(upload_engine, overrides):
    """每种非法组合都应由数据库约束拒绝，而不是只靠 Python 检查。"""
    with pytest.raises(IntegrityError):
        _insert(upload_engine, **overrides)


# 空白字符不止空格和常见换行：竖向制表符、换页符和全角空格都必须被拒绝。
@pytest.mark.parametrize(
    ("field", "blank_only"),
    [
        ("filename", "\v"),
        ("filename", "\f"),
        ("filename", "\u3000"),  # 全角空格
        ("filename", "\u00a0"),  # 不换行空格
        ("filename", "\u2028"),  # 行分隔符
        ("source_format", "\f"),
        ("storage_type", "\v\u3000"),
        ("storage_key", "\u3000"),
        ("error_message", "\v"),
        ("error_message", "\u3000"),
    ],
)
def test_whitespace_only_text_is_rejected(upload_engine, field, blank_only):
    """纯空白文本即使不是普通空格，也必须被数据库拒绝。"""
    overrides = {field: blank_only}
    if field == "error_message":
        # 失败状态还要求完成时间；其余字段沿用合法默认值。
        overrides.update(status="failed", completed_at=func.now())
    with pytest.raises(IntegrityError):
        _insert(upload_engine, **overrides)


def test_duplicate_document_id_is_rejected(upload_engine):
    """主键保证同一文档编号不能出现两条记录。"""
    record = _record_values()
    _insert(upload_engine, **record)
    with pytest.raises(IntegrityError):
        _insert(upload_engine, document_id=record["document_id"])


def test_duplicate_storage_location_is_rejected(upload_engine):
    """同一存储位置只允许一条记录，避免两次上传互相覆盖。"""
    record = _record_values()
    _insert(upload_engine, **record)
    with pytest.raises(IntegrityError):
        _insert(upload_engine, storage_key=record["storage_key"])


def test_same_content_can_be_uploaded_twice(upload_engine):
    """相同文件名和校验和各有编号、文件与记录；SHA-256 不设唯一约束。"""
    same_content = {"filename": "same.pdf", "sha256": "b" * 64}
    _insert(upload_engine, **same_content)
    _insert(upload_engine, **same_content)
