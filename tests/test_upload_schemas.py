"""结果模型拒绝不完整数据，HTTP 文档展示成功与失败的具体字段。"""

import pytest
from pydantic import ValidationError

from uploads.schemas import UploadBatchResult, UploadFailed, UploadResponse, UploadSucceeded


# 使用正常的混合批次，不依赖数据库；校验的是 service 的结果交接边界。
@pytest.fixture
def batch_values():
    return {
        "documents": [
            UploadSucceeded(
                filename="a.pdf",
                document_id="doc_" + "0" * 32,
                size_bytes=12,
                sha256="1" * 64,
            ),
            UploadFailed(filename="b.pdf", error="文件保存失败"),
        ],
        "succeeded": 1,
        "database_errors": 0,
    }


# 保存后读回仍能得到派生失败数；转 HTTP 响应时不泄露内部数据库计数。
def test_batch_result_roundtrip_and_response(batch_values):
    result = UploadBatchResult(**batch_values)
    restored = UploadBatchResult.model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.failed == 1
    response = UploadResponse(
        succeeded=restored.succeeded, failed=restored.failed, documents=restored.documents
    )
    assert set(response.model_dump()) == {"succeeded", "failed", "documents"}


# 不合法的类型、嵌套结果或计数不能流向 router，避免错误的 201/400/503。
@pytest.mark.parametrize(
    "changes",
    [
        {"succeeded": "1"},
        {"succeeded": True},
        {"succeeded": 0},
        {"database_errors": -1},
        {"database_errors": 2},
        {"unexpected": "extra"},
        {"documents": [{"filename": "a.pdf", "status": "uploaded"}]},
    ],
)
def test_batch_result_rejects_invalid_summary(batch_values, changes):
    with pytest.raises(ValidationError):
        UploadBatchResult(**(batch_values | changes))


# 伪造错误输出，确认模型能发现缺字段、错误类型和成功/失败字段混用。
@pytest.mark.parametrize(
    "item",
    [
        {"filename": "a.pdf", "status": "uploaded"},
        {"filename": "a.pdf", "status": "failed", "error": 123},
        {"filename": "a.pdf", "status": "failed", "error": "失败", "document_id": "x"},
        {"filename": "a.pdf", "status": "unknown"},
    ],
)
def test_rejects_invalid_upload_result(item):
    with pytest.raises(ValidationError):
        UploadResponse(succeeded=0, failed=1, documents=[item])


# /docs 使用 OpenAPI；批次响应通过 status 映射成功、失败两种明确结构。
def test_openapi_describes_upload_responses():
    from api.main import app

    schema = app.openapi()
    responses = schema["paths"]["/documents"]["post"]["responses"]
    for status in ("201", "400", "503"):
        assert responses[status]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/UploadResponse"
        }
    items = schema["components"]["schemas"]["UploadResponse"]["properties"]
    assert items["documents"]["items"]["discriminator"]["propertyName"] == "status"
    success = schema["components"]["schemas"]["UploadSucceeded"]
    assert {"document_id", "size_bytes", "sha256"} <= set(success["required"])
