"""结果模型拒绝不完整数据，HTTP 文档展示成功与失败的具体字段。"""

import pytest
from pydantic import ValidationError

from uploads.schemas import UploadResponse


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
