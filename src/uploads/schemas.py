"""上传结果的数据模型：校验业务输出，并供 HTTP 接口生成文档。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


# 结构化结果拒绝多余字段和隐式类型转换，及时发现业务代码拼错字段。
class UploadSucceeded(BaseModel):
    """单份成功结果；保存信息必须齐全。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    filename: str
    status: Literal["uploaded"] = "uploaded"
    document_id: str = Field(pattern=r"^doc_[0-9a-f]{32}$")
    source_format: Literal["pdf"] = "pdf"
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


# 失败结果只有文件名、状态和原因，避免附带内部信息或成功字段。
class UploadFailed(BaseModel):
    """单份失败结果；不返回文档编号或保存信息。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    filename: str
    status: Literal["failed"] = "failed"
    error: str = Field(min_length=1)


# 按 status 区分两种结果；例如 uploaded 必须带大小和 SHA-256。
UploadResult = Annotated[UploadSucceeded | UploadFailed, Field(discriminator="status")]


class UploadResponse(BaseModel):
    """批次响应；业务内部的数据库失败计数不对外暴露。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    documents: list[UploadResult]
