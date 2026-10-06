"""直接调用上传 service，验证业务流程不需要 HTTP 请求。"""

from io import BytesIO

import pytest


# 复用真实 PG 临时库，并用临时目录接收上传，避免污染本机数据。
def test_service_uploads_without_fastapi(upload_engine, tmp_path, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from db.upload_records import get_upload
    from uploads.service import UploadInput, upload_documents

    factory = sessionmaker(bind=upload_engine)
    monkeypatch.setenv("UPLOAD_ROOT", str(tmp_path))
    payload = b"%PDF-1.4\nservice upload"
    files = [
        UploadInput("good.pdf", BytesIO(payload), len(payload)),
        UploadInput("wrong.txt", BytesIO(payload), len(payload)),
    ]
    result = upload_documents(files, factory)

    # 成功文件和 PG 记录都能核对；另一份失败不影响成功项。
    assert result.succeeded == 1 and result.failed == 1
    assert result.database_errors == 0
    document_id = result.documents[0]["document_id"]
    assert (tmp_path / document_id / "source.pdf").read_bytes() == payload
    assert get_upload(document_id, session_factory=factory).status == "uploaded"
    assert result.documents[1]["status"] == "failed"


# 批次超限在写入前拒绝；无需数据库或 FastAPI 即可判断。
def test_service_rejects_batch_before_database_access(monkeypatch):
    from uploads.service import BatchLimitExceeded, UploadInput, upload_documents

    monkeypatch.setenv("UPLOAD_MAX_FILES", "1")
    files = [UploadInput("a.pdf", BytesIO()), UploadInput("b.pdf", BytesIO())]

    def unexpected_session():
        pytest.fail("超限时不应打开数据库 Session")

    with pytest.raises(BatchLimitExceeded, match="一次最多上传 1 份文件"):
        upload_documents(files, unexpected_session)
