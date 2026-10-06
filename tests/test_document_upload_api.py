"""POST /documents 多份上传的真实 PG + 磁盘验证：逐份结果、限额与整体状态码。"""

import hashlib
from types import SimpleNamespace

import pytest


# 生成 PDF 字节；只用于上传检查，不做完整 PDF 解析。
def _pdf_bytes(size: int = 64) -> bytes:
    head = b"%PDF-1.4\n"
    return head + b"a" * max(size - len(head), 0)


# 统一用 files 字段提交多份文件；entries 为 (文件名, 字节) 列表。
def _upload(api, entries):
    return api.client.post(
        "/documents",
        files=[("files", (name, payload, "application/pdf")) for name, payload in entries],
    )


# 读取临时库里的全部上传记录，用于核对逐份处理结果。
def _records(api):
    from sqlalchemy import select

    from db.models.document_upload import DocumentUpload

    with api.factory() as session:
        return session.scalars(select(DocumentUpload)).all()


def _record_count(api) -> int:
    from sqlalchemy import func, select

    from db.models.document_upload import DocumentUpload

    with api.factory() as session:
        return session.scalar(select(func.count()).select_from(DocumentUpload))


# 临时上传目录 + 临时库的测试客户端；导入放在夹具内，无数据库配置时先跳过。
@pytest.fixture
def api(tmp_path, monkeypatch, upload_engine):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from api.documents import get_session_factory
    from api.main import app

    factory = sessionmaker(bind=upload_engine)
    app.dependency_overrides[get_session_factory] = lambda: factory
    root = tmp_path / "uploads"
    monkeypatch.setenv("UPLOAD_ROOT", str(root))
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, factory=factory, root=root, app=app)
    app.dependency_overrides.clear()


def test_upload_saves_file_and_record(api):
    payload = _pdf_bytes(4096)
    response = _upload(api, [("example.pdf", payload)])
    assert response.status_code == 201

    body = response.json()
    assert body["succeeded"] == 1 and body["failed"] == 0
    item = body["documents"][0]
    assert item["status"] == "uploaded" and item["filename"] == "example.pdf"
    assert item["size_bytes"] == len(payload)
    assert item["sha256"] == hashlib.sha256(payload).hexdigest()

    # 磁盘字节与请求一致；记录指向该文件并补齐完成时间。
    stored = api.root / item["document_id"] / "source.pdf"
    assert stored.read_bytes() == payload
    records = _records(api)
    assert len(records) == 1 and records[0].status == "uploaded"
    assert records[0].storage_key == f"{item['document_id']}/source.pdf"


def test_multiple_files_processed_independently(api):
    good = _pdf_bytes(128)
    response = _upload(
        api,
        [("good.pdf", good), ("note.txt", _pdf_bytes()), ("bad.pdf", b"not a pdf")],
    )
    assert response.status_code == 201

    # 顺序与请求一致；只有文件名和文件头都合格的 1 份成功。
    body = response.json()
    assert body["succeeded"] == 1 and body["failed"] == 2
    assert [item["filename"] for item in body["documents"]] == ["good.pdf", "note.txt", "bad.pdf"]
    assert body["documents"][0]["status"] == "uploaded"
    assert "文件名需以 .pdf 结尾" in body["documents"][1]["error"]
    assert "文件头" in body["documents"][2]["error"]

    # 成功的文件和记录保留；失败的两份没有正式文件。
    assert (api.root / body["documents"][0]["document_id"] / "source.pdf").read_bytes() == good
    assert [record.status for record in _records(api)].count("uploaded") == 1
    assert len(list(api.root.glob("*/source.pdf"))) == 1


def test_repeat_upload_creates_new_document(api):
    payload = _pdf_bytes(128)
    first = _upload(api, [("same-name.pdf", payload)])
    second = _upload(api, [("same-name.pdf", payload)])

    # 同名、同内容也分配新编号；两份文件和记录都保留，互不覆盖。
    assert first.status_code == 201 and second.status_code == 201
    first_id = first.json()["documents"][0]["document_id"]
    second_id = second.json()["documents"][0]["document_id"]
    assert first_id != second_id
    for document_id in (first_id, second_id):
        assert (api.root / document_id / "source.pdf").read_bytes() == payload
    assert _record_count(api) == 2


def test_missing_files_field_returns_422(api):
    assert api.client.post("/documents").status_code == 422
    assert _record_count(api) == 0


def test_all_failed_files_return_400(api):
    response = _upload(api, [("fake.pdf", b"not a pdf")])
    assert response.status_code == 400

    # 失败项在 body 中说明原因；记录标 failed，磁盘没有正式文件。
    body = response.json()
    assert body["succeeded"] == 0 and body["failed"] == 1
    assert body["documents"][0]["status"] == "failed"
    assert _records(api)[0].status == "failed"
    assert not list(api.root.glob("*/source.pdf"))


def test_too_many_files_rejected_before_writing(api, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_FILES", "2")
    response = _upload(
        api, [("a.pdf", _pdf_bytes()), ("b.pdf", _pdf_bytes()), ("c.pdf", _pdf_bytes())]
    )

    # 份数超限整单拒绝：不建记录、不写文件。
    assert response.status_code == 413
    assert _record_count(api) == 0
    assert not api.root.exists()


def test_total_size_rejected_before_writing(api, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_TOTAL_BYTES", "2048")
    response = _upload(api, [("a.pdf", _pdf_bytes(2048)), ("b.pdf", _pdf_bytes(2048))])

    assert response.status_code == 413
    assert _record_count(api) == 0
    assert not api.root.exists()


def test_oversize_file_fails_but_others_succeed(api, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "1024")
    response = _upload(api, [("big.pdf", _pdf_bytes(4096)), ("small.pdf", _pdf_bytes(512))])

    # 单份超限只影响该份，其他份照常完成，整体返回 201。
    assert response.status_code == 201
    body = response.json()
    assert body["succeeded"] == 1 and body["failed"] == 1
    assert "大小限制" in body["documents"][0]["error"]
    assert body["documents"][1]["status"] == "uploaded"


def test_storage_failure_marks_file_failed(api, monkeypatch, tmp_path):
    # 根目录位置被普通文件占据，建目录失败；响应不能泄露服务器路径。
    blocked = tmp_path / "blocked"
    blocked.write_text("占位文件", encoding="utf-8")
    monkeypatch.setenv("UPLOAD_ROOT", str(blocked))

    response = _upload(api, [("sample.pdf", _pdf_bytes())])
    assert response.status_code == 400
    assert response.json()["documents"][0]["status"] == "failed"
    assert str(blocked) not in response.text
    assert _records(api)[0].status == "failed"


def test_database_unavailable_returns_503(api):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from api.documents import get_session_factory

    # 指向一个连不上的端口，模拟数据库整体不可用；文件不能成为已完成的上传。
    broken = sessionmaker(bind=create_engine("postgresql+psycopg://rag:rag@127.0.0.1:1/rag"))
    api.app.dependency_overrides[get_session_factory] = lambda: broken

    response = _upload(api, [("sample.pdf", _pdf_bytes())])
    assert response.status_code == 503
    assert response.json()["succeeded"] == 0


def test_health_check_still_works(api):
    assert api.client.get("/health").json() == {"status": "ok"}
