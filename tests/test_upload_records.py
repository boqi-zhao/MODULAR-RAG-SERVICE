"""上传记录读写的真实 PG 验证：短事务、失败回滚与并发结束只成功一次。"""

import os
import threading
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# 未配置数据库时整模块跳过；db.upload_records 导入即初始化引擎，不能先导入再跳过。
if not os.environ.get("DATABASE_URL", "").strip():
    pytest.skip("使用 uv run --env-file .env pytest 加载真实 PG 配置", allow_module_level=True)

from db.upload_records import (  # noqa: E402
    create_uploading,
    get_upload,
    mark_failed,
    mark_uploaded,
)


# 记录读写跑在独立临时库；把绑定临时库的工厂传给被测函数，不使用开发库。
@pytest.fixture
def session_factory(upload_engine):
    return sessionmaker(bind=upload_engine)


# 构造一次上传的登记信息；文件内容由 T-09 负责，本步只关心记录字段。
def _fields(**overrides) -> dict:
    document_id = overrides.pop("document_id", f"doc_{uuid4().hex}")
    fields = {
        "document_id": document_id,
        "filename": "sample.pdf",
        "source_format": "pdf",
        "storage_type": "local",
        "storage_key": f"{document_id}/source.pdf",
    }
    fields.update(overrides)
    return fields


def test_create_uploading_writes_initial_record(session_factory):
    fields = _fields()
    create_uploading(**fields, session_factory=session_factory)

    # 初始记录只有已知道信息；大小、校验和、完成时间等文件保存结束后补齐。
    record = get_upload(fields["document_id"], session_factory=session_factory)
    assert record is not None
    assert record.status == "uploading"
    assert record.filename == "sample.pdf"
    assert record.created_at is not None
    assert record.size_bytes is None and record.sha256 is None
    assert record.completed_at is None and record.error_message is None


def test_create_uploading_rolls_back_duplicate_storage_key(session_factory):
    first = _fields()
    create_uploading(**first, session_factory=session_factory)

    # 同一存储位置不允许两条记录；第二笔插入失败后不能留下半条记录。
    second = _fields(storage_type=first["storage_type"], storage_key=first["storage_key"])
    with pytest.raises(IntegrityError):
        create_uploading(**second, session_factory=session_factory)

    assert get_upload(second["document_id"], session_factory=session_factory) is None
    kept = get_upload(first["document_id"], session_factory=session_factory)
    assert kept is not None and kept.status == "uploading"


def test_mark_uploaded_completes_once(session_factory):
    fields = _fields()
    create_uploading(**fields, session_factory=session_factory)
    document_id = fields["document_id"]

    assert (
        mark_uploaded(
            document_id, size_bytes=1024, sha256="a" * 64, session_factory=session_factory
        )
        is True
    )
    record = get_upload(document_id, session_factory=session_factory)
    assert record is not None and record.status == "uploaded"
    assert record.size_bytes == 1024 and record.sha256 == "a" * 64
    assert record.completed_at is not None

    # 已结束的记录不能被第二次结束覆盖：再次标记成功或失败都应返回 False。
    assert (
        mark_uploaded(
            document_id, size_bytes=2048, sha256="b" * 64, session_factory=session_factory
        )
        is False
    )
    assert (
        mark_failed(document_id, error_message="迟到失败", session_factory=session_factory) is False
    )
    kept = get_upload(document_id, session_factory=session_factory)
    assert kept is not None and kept.size_bytes == 1024


def test_mark_failed_keeps_reason(session_factory):
    fields = _fields()
    create_uploading(**fields, session_factory=session_factory)
    document_id = fields["document_id"]

    assert (
        mark_failed(document_id, error_message="文件写入失败", session_factory=session_factory)
        is True
    )
    record = get_upload(document_id, session_factory=session_factory)
    assert record is not None and record.status == "failed"
    assert record.error_message == "文件写入失败" and record.completed_at is not None

    # 失败后不允许再改成 uploaded，避免“上传失败”被成功状态覆盖。
    assert (
        mark_uploaded(
            document_id, size_bytes=1024, sha256="a" * 64, session_factory=session_factory
        )
        is False
    )
    kept = get_upload(document_id, session_factory=session_factory)
    assert kept is not None and kept.error_message == "文件写入失败"


def test_finish_unknown_document_returns_false(session_factory):
    missing = f"doc_{uuid4().hex}"
    assert (
        mark_uploaded(missing, size_bytes=1024, sha256="a" * 64, session_factory=session_factory)
        is False
    )
    assert (
        mark_failed(missing, error_message="不存在的记录", session_factory=session_factory) is False
    )


def test_invalid_values_are_rejected_and_state_kept(session_factory):
    fields = _fields()
    create_uploading(**fields, session_factory=session_factory)
    document_id = fields["document_id"]

    # 大小为零、校验和格式不对、失败原因为纯空白，都由数据库约束拒绝。
    with pytest.raises(IntegrityError):
        mark_uploaded(document_id, size_bytes=0, sha256="a" * 64, session_factory=session_factory)
    with pytest.raises(IntegrityError):
        mark_uploaded(
            document_id, size_bytes=1024, sha256="not-a-hash", session_factory=session_factory
        )
    with pytest.raises(IntegrityError):
        mark_failed(document_id, error_message="\u3000", session_factory=session_factory)

    # 每次失败都已回滚，记录仍停在 uploading，可以用合法值继续完成。
    kept = get_upload(document_id, session_factory=session_factory)
    assert kept is not None and kept.status == "uploading"
    assert (
        mark_uploaded(
            document_id, size_bytes=1024, sha256="a" * 64, session_factory=session_factory
        )
        is True
    )


def test_concurrent_finish_only_one_succeeds(session_factory):
    fields = _fields()
    create_uploading(**fields, session_factory=session_factory)
    document_id = fields["document_id"]

    # 两条真实连接同时结束同一条记录；条件更新保证只有一个调用拿到 True。
    barrier = threading.Barrier(2)
    results, errors = {}, []

    def finish(kind: str) -> None:
        try:
            barrier.wait()
            if kind == "uploaded":
                results["uploaded"] = mark_uploaded(
                    document_id, size_bytes=1024, sha256="a" * 64, session_factory=session_factory
                )
            else:
                results["failed"] = mark_failed(
                    document_id, error_message="上传中断", session_factory=session_factory
                )
        except Exception as error:  # 线程里的异常带回主线程断言，避免静默丢失
            errors.append(error)

    threads = [threading.Thread(target=finish, args=(kind,)) for kind in ("uploaded", "failed")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sorted(results.values()) == [False, True]

    # 最终状态与唯一成功的调用一致；另一路的信息不会混进来。
    record = get_upload(document_id, session_factory=session_factory)
    assert record is not None
    if results["uploaded"]:
        assert record.status == "uploaded" and record.error_message is None
    else:
        assert record.status == "failed" and record.size_bytes is None
