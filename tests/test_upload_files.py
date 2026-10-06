"""本地文件保存的真实磁盘验证：分段写入、校验和、限制与失败清理（不需要数据库）。"""

import hashlib
import threading
from io import BytesIO
from types import SimpleNamespace

import pytest

from uploads import files


# 每个用例使用独立临时根目录，避免污染 data/uploads 和相互影响。
@pytest.fixture
def upload_root(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_ROOT", str(tmp_path))
    return tmp_path


# 生成 PDF 字节：文件头合法、长度可控，用于跨分段和超限场景。
def _pdf_bytes(total_size: int) -> bytes:
    return b"%PDF-1.4\n" + b"a" * (total_size - len(b"%PDF-1.4\n"))


def test_save_pdf_writes_exact_bytes(upload_root):
    payload = _pdf_bytes(files.CHUNK_SIZE + 100)
    saved = files.save_pdf("doc_a", BytesIO(payload))

    # 保存内容与输入逐字节一致，大小和 SHA-256 按原始字节计算。
    target = upload_root / "doc_a" / "source.pdf"
    assert target.read_bytes() == payload
    assert saved.size_bytes == len(payload)
    assert saved.sha256 == hashlib.sha256(payload).hexdigest()
    assert saved.storage_type == "local"
    assert files.storage_key("doc_a") == "doc_a/source.pdf"

    # 发布完成后临时目录不再留文件。
    assert list((upload_root / ".tmp").glob("*")) == []


def test_two_uploads_do_not_overwrite(upload_root):
    first, second = _pdf_bytes(64), _pdf_bytes(128)
    files.save_pdf("doc_a", BytesIO(first))
    files.save_pdf("doc_b", BytesIO(second))

    assert (upload_root / "doc_a" / "source.pdf").read_bytes() == first
    assert (upload_root / "doc_b" / "source.pdf").read_bytes() == second


def test_same_document_id_is_rejected_without_overwrite(upload_root):
    first = _pdf_bytes(64)
    files.save_pdf("doc_a", BytesIO(first))

    # 同一编号第二次保存必须失败，旧文件字节保持第一次的内容，不静默覆盖。
    with pytest.raises(files.TargetExists):
        files.save_pdf("doc_a", BytesIO(_pdf_bytes(128)))

    assert (upload_root / "doc_a" / "source.pdf").read_bytes() == first
    assert list((upload_root / ".tmp").glob("*")) == []


def test_concurrent_same_document_id_keeps_published_bytes(upload_root, monkeypatch):
    created_temp = []
    real_mkstemp = files.tempfile.mkstemp

    # 只替换被测模块看到的 mkstemp，记录每次调用实际使用的临时文件。
    def recording_mkstemp(*args, **kwargs):
        fd, name = real_mkstemp(*args, **kwargs)
        created_temp.append(name)
        return fd, name

    monkeypatch.setattr(files, "tempfile", SimpleNamespace(mkstemp=recording_mkstemp))

    first, second = _pdf_bytes(64), _pdf_bytes(128)
    results, errors = {}, []

    def save(name, payload):
        try:
            results[name] = files.save_pdf("doc_race", BytesIO(payload))
        except Exception as error:  # 并发结果带回主线程断言，避免静默丢失
            errors.append(error)

    threads = [
        threading.Thread(target=save, args=("a", first)),
        threading.Thread(target=save, args=("b", second)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # 恰好一份成功、一份报“目标已存在”；正式文件就是成功那份的原始字节。
    assert len(results) == 1 and len(errors) == 1
    assert isinstance(errors[0], files.TargetExists)
    winner = next(iter(results))
    payload = first if winner == "a" else second
    assert (upload_root / "doc_race" / "source.pdf").read_bytes() == payload
    assert results[winner].sha256 == hashlib.sha256(payload).hexdigest()

    # 每次调用都用独立临时文件；失败方只清理自己的，目录无残留。
    assert len(created_temp) == 2 and created_temp[0] != created_temp[1]
    assert list((upload_root / ".tmp").glob("*")) == []


def test_empty_file_is_rejected_without_leftovers(upload_root):
    with pytest.raises(files.EmptyFile):
        files.save_pdf("doc_empty", BytesIO(b""))

    assert not (upload_root / "doc_empty").exists()
    assert list((upload_root / ".tmp").glob("*")) == []


def test_non_pdf_content_is_rejected(upload_root):
    with pytest.raises(files.NotPdf):
        files.save_pdf("doc_bad", BytesIO(b"not a pdf at all"))

    assert not (upload_root / "doc_bad").exists()
    assert list((upload_root / ".tmp").glob("*")) == []


def test_too_large_file_is_rejected_and_cleaned(upload_root, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "1024")
    with pytest.raises(files.FileTooLarge):
        files.save_pdf("doc_big", BytesIO(_pdf_bytes(2048)))

    assert not (upload_root / "doc_big").exists()
    assert list((upload_root / ".tmp").glob("*")) == []


def test_invalid_limit_config_is_explicit(upload_root, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "twenty")
    with pytest.raises(files.UploadFileError):
        files.save_pdf("doc_x", BytesIO(_pdf_bytes(16)))
