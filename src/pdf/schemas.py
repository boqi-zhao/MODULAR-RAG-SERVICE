"""MVP 解析输入与结果：沿用旧文档、图片和占位符结构。"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# 所有结果都能直接序列化 JSON；冻结对象避免后续调用改写已有结果。
class PdfModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class PdfParseInput(PdfModel):
    """读取已有本地 PDF；output_dir 必须是本次调用的新目录。"""

    source_path: Path
    output_dir: Path
    extract_images: bool = True


# position 沿用旧字段：像素尺寸、页码、资源下标，不代表页面矩形坐标。
class ImagePosition(PdfModel):
    width: int = Field(ge=0)
    height: int = Field(ge=0)
    page: int = Field(ge=1)
    index: int = Field(ge=0)


class ImageMetadata(PdfModel):
    id: str
    path: str
    page: int = Field(ge=1)
    text_offset: int = Field(ge=0)
    text_length: int = Field(gt=0)
    position: ImagePosition


# 与旧 metadata 对齐；空图片清单和空标题显式保存，避免无约束字典。
class DocumentMetadata(PdfModel):
    source_path: str
    doc_type: Literal["pdf"] = "pdf"
    doc_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    title: str | None = None
    images: tuple[ImageMetadata, ...] = ()


class ParseDiagnostic(PdfModel):
    """图片降级的结构化记录；旧流程继续解析的行为保持不变。"""

    code: str
    page: int | None = None
    image_index: int | None = None
    exception_type: str


# 保存实际依赖与实现版本；只是解析快照，不冒充正式 Stage 版本产物。
class ParserInfo(PdfModel):
    strategy_id: Literal["markitdown-pymupdf-resources"] = "markitdown-pymupdf-resources"
    implementation_version: Literal["0.2.0-mvp"] = "0.2.0-mvp"
    markitdown_version: str
    pymupdf_version: str
    mupdf_version: str
    pillow_version: str


class PdfParseResult(PdfModel):
    """id/text/metadata 沿用旧文档结构；配置、诊断和版本用于追溯。"""

    id: str
    text: str
    metadata: DocumentMetadata
    parser: ParserInfo
    extract_images: bool
    diagnostics: tuple[ParseDiagnostic, ...] = ()
    schema_version: Literal["2.0.0-dev"] = "2.0.0-dev"
