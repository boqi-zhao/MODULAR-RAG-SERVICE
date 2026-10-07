"""上传结果的数据模型：校验业务输出，并供 HTTP 接口生成文档。"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


# service 汇总同一份逐项结果；数据库错误数只供 router 决定 HTTP 状态码。
class UploadBatchResult(BaseModel):
    """可独立校验、序列化的业务结果；不依赖 FastAPI。"""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    documents: list[UploadResult]
    succeeded: int = Field(ge=0)
    database_errors: int = Field(ge=0)

    @property
    def failed(self) -> int:
        """失败数从清单与成功数计算，避免额外保存一份计数。"""
        return len(self.documents) - self.succeeded

    # 计数影响 HTTP 状态码：只校验整数类型还不足以阻止错误的批次汇总。
    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        actual_succeeded = sum(item.status == "uploaded" for item in self.documents)
        if self.succeeded != actual_succeeded:
            raise ValueError("成功数必须与逐份上传结果一致")
        if self.database_errors > self.failed:
            raise ValueError("数据库错误数不能超过失败份数")
        return self


class UploadResponse(BaseModel):
    """批次响应；业务内部的数据库失败计数不对外暴露。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    documents: list[UploadResult]
