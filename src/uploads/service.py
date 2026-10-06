"""上传业务：检查批次限制，逐份保存文件并登记上传记录。"""

from dataclasses import dataclass
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from common.logger import logger
from db.upload_records import create_uploading, mark_failed, mark_uploaded
from uploads.files import (
    EmptyFile,
    FileTooLarge,
    NotPdf,
    UploadFileError,
    max_files,
    max_total_bytes,
    save_pdf,
    storage_key,
)


# 普通 Python 输入，HTTP 上传或其他调用方都能提供文件流。
@dataclass(frozen=True)
class UploadInput:
    filename: str
    stream: BinaryIO
    size: int | None = None


class BatchLimitExceeded(Exception):
    """整批上传超过限制；由调用方决定如何向用户展示。"""


# 返回业务结果及数据库失败数，HTTP 状态码留给路由决定。
@dataclass(frozen=True)
class UploadBatchResult:
    documents: list[dict]
    succeeded: int
    database_errors: int

    @property
    def failed(self) -> int:
        return len(self.documents) - self.succeeded


# 数据库失败提示不暴露连接信息。
_DATABASE_ERROR = "数据库暂不可用，请稍后重试。"


# 记录更新失败不能掩盖原始文件错误；只记日志，继续返回该份的失败结果。
def _mark_failed_quietly(
    document_id: str,
    message: str,
    session_factory: sessionmaker[Session],
) -> None:
    try:
        mark_failed(document_id, error_message=message, session_factory=session_factory)
    except SQLAlchemyError:
        logger.exception("更新上传失败记录时出错 document_id=%s", document_id)


# 文件检查失败原因到提示语的映射；响应只说原因，不含服务器路径。
def _file_error_message(error: Exception) -> str:
    if isinstance(error, EmptyFile):
        return "文件内容为空。"
    if isinstance(error, NotPdf):
        return "首批只接收 PDF 文件，文件头校验未通过。"
    if isinstance(error, FileTooLarge):
        return "文件超过大小限制。"
    return "本地文件保存失败，请稍后重试。"


# 处理一份文件；返回结果项和“是否数据库失败”，供调用方判断失败原因。
def _process_file(
    file: UploadInput,
    session_factory: sessionmaker[Session],
) -> tuple[dict, bool]:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        detail = "首批只接收 PDF 文件，文件名需以 .pdf 结尾。"
        return {"filename": filename, "status": "failed", "error": detail}, False

    # 每份文件分配独立编号；一份失败不回滚其他已成功的文件或记录。
    document_id = f"doc_{uuid4().hex}"
    try:
        create_uploading(
            document_id=document_id,
            filename=filename,
            source_format="pdf",
            storage_type="local",
            storage_key=storage_key(document_id),
            session_factory=session_factory,
        )
    # 初始记录创建失败时停止该份处理，避免产生无法追踪的文件。
    except SQLAlchemyError:
        logger.exception("创建上传记录失败 document_id=%s", document_id)
        return {"filename": filename, "status": "failed", "error": _DATABASE_ERROR}, True

    try:
        saved = save_pdf(document_id, file.stream)
    except (EmptyFile, NotPdf, FileTooLarge, UploadFileError, OSError) as error:
        detail = _file_error_message(error)
        if not isinstance(error, (EmptyFile, NotPdf, FileTooLarge)):
            logger.exception("保存上传文件失败 document_id=%s", document_id)
        _mark_failed_quietly(document_id, detail, session_factory)
        return {"filename": filename, "status": "failed", "error": detail}, False

    try:
        finished = mark_uploaded(
            document_id,
            size_bytes=saved.size_bytes,
            sha256=saved.sha256,
            session_factory=session_factory,
        )
    except SQLAlchemyError:
        # 文件已保存但记录未更新：保留文件供排查，不报告该份上传成功。
        logger.exception("更新上传成功记录失败 document_id=%s", document_id)
        return {"filename": filename, "status": "failed", "error": _DATABASE_ERROR}, True
    if not finished:
        logger.error("上传记录状态异常 document_id=%s", document_id)
        detail = "上传状态异常，请重试或联系管理员。"
        return {"filename": filename, "status": "failed", "error": detail}, False

    logger.info("上传完成 document_id=%s size=%s", document_id, saved.size_bytes)
    item = {
        "filename": filename,
        "status": "uploaded",
        "document_id": document_id,
        "source_format": "pdf",
        "size_bytes": saved.size_bytes,
        "sha256": saved.sha256,
    }
    return item, False


# 批次限制先检查，整单超限时不创建记录，也不写文件。
def upload_documents(
    files: list[UploadInput],
    session_factory: sessionmaker[Session],
) -> UploadBatchResult:
    """独立执行业务流程；至少一份成功与逐份失败均保留在结果中。"""
    limit = max_files()
    if len(files) > limit:
        logger.warning("上传份数超过限制 count=%s", len(files))
        raise BatchLimitExceeded(f"一次最多上传 {limit} 份文件。")
    # 未知大小按 0 计，单份大小仍在写入时逐段校验。
    total_bytes = sum(file.size or 0 for file in files)
    if total_bytes > max_total_bytes():
        logger.warning("上传总大小超过限制 total=%s", total_bytes)
        raise BatchLimitExceeded("本次上传总大小超过限制。")

    # 每份独立处理；失败不会回滚其他已经完成的文件。
    results: list[dict] = []
    db_errors = 0
    for file in files:
        item, is_db_error = _process_file(file, session_factory)
        results.append(item)
        db_errors += int(is_db_error)

    succeeded = sum(1 for item in results if item["status"] == "uploaded")
    return UploadBatchResult(results, succeeded, db_errors)
