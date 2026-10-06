"""上传记录表 ORM 模型；字段与约束依据 docs/offline/api/06-upload-table.md。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base

# Unicode 定义的全部空白字符；\v、\f、全角空格等也必须被识别为空白。
_WHITESPACE_CHARS = (
    "E' \\t\\n\\r\\v\\f' || "
    "U&'\\0085\\00A0\\1680\\2000\\2001\\2002\\2003\\2004\\2005\\2006"
    "\\2007\\2008\\2009\\200A\\2028\\2029\\202F\\205F\\3000'"
)


def _not_blank(column: str) -> str:
    """生成“至少含一个非空白字符”的检查 SQL。"""
    return f"btrim({column}, {_WHITESPACE_CHARS}) <> ''"


class DocumentUpload(Base):
    """一次上传对应一条记录；PDF 字节保存在本地文件，数据库只存描述信息。"""

    __tablename__ = "document_uploads"

    # 文档编号由服务生成（doc_ 加小写 UUID v4）；数据库只保证主键不重复。
    document_id: Mapped[str] = mapped_column(Text, primary_key=True)

    # 原文件名仅用于展示；真实保存位置由 storage_key 决定，不能用文件名拼路径。
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    source_format: Mapped[str] = mapped_column(Text, nullable=False)

    # 接收过程中大小和校验和未知，因此允许为空；已知时分别满足非负与格式约束。
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(Text)

    # 存储类型加相对路径指向正式文件；组合唯一，避免两条记录指向同一位置。
    storage_type: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)

    # 状态标识本次上传所处阶段；初始值由数据库填入 uploading。
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="uploading")

    # 开始时间由数据库时钟填写；完成时间为空表示仍在接收。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 失败说明面向用户；不保存密码、绝对路径或完整底层异常文本。
    error_message: Mapped[str | None] = mapped_column(Text)

    # 数据库必须拦住的错误：状态合法、状态与字段组合一致、各字段格式正确。
    __table_args__ = (
        CheckConstraint("status IN ('uploading', 'uploaded', 'failed')", name="status_valid"),
        CheckConstraint(
            "(status = 'uploading' AND completed_at IS NULL AND error_message IS NULL) OR "
            "(status = 'uploaded' AND size_bytes IS NOT NULL AND size_bytes > 0 "
            "AND sha256 IS NOT NULL "
            "AND completed_at IS NOT NULL AND error_message IS NULL) OR "
            "(status = 'failed' AND completed_at IS NOT NULL AND error_message IS NOT NULL)",
            name="state_fields_consistent",
        ),
        CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="size_bytes_nonnegative"),
        CheckConstraint("sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at",
            name="completed_at_not_before_created_at",
        ),
        CheckConstraint(_not_blank("filename"), name="filename_not_blank"),
        CheckConstraint(_not_blank("source_format"), name="source_format_not_blank"),
        CheckConstraint(_not_blank("storage_type"), name="storage_type_not_blank"),
        CheckConstraint(_not_blank("storage_key"), name="storage_key_not_blank"),
        CheckConstraint(
            "error_message IS NULL OR " + _not_blank("error_message"),
            name="error_message_not_blank",
        ),
        UniqueConstraint(
            "storage_type",
            "storage_key",
            name="uq_document_uploads_storage_type_storage_key",
        ),
    )
