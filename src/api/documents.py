"""POST /documents：一次接收一份或多份 PDF，逐份保存文件并登记上传记录。"""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
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

router = APIRouter()

# 数据库不可用时的统一提示；失败记录和响应都用这句，不暴露内部细节。
_DATABASE_ERROR = "数据库暂不可用，请稍后重试。"


# 依赖注入让测试替换成临时库工厂；延迟导入使启动服务不必先连库。
def get_session_factory() -> sessionmaker[Session]:
    """返回数据库 Session 工厂；测试通过依赖覆盖指向临时库。"""
    from db.session import SessionFactory

    return SessionFactory


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
def _file_error_response(error: Exception) -> tuple[int, str]:
    if isinstance(error, EmptyFile):
        return 400, "文件内容为空。"
    if isinstance(error, NotPdf):
        return 415, "首批只接收 PDF 文件，文件头校验未通过。"
    if isinstance(error, FileTooLarge):
        return 413, "文件超过大小限制。"
    return 500, "本地文件保存失败，请稍后重试。"


# 处理一份文件；返回结果项和“是否数据库失败”，路由据此决定整体状态码。
def _process_file(
    file: UploadFile,
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
    except SQLAlchemyError:
        logger.exception("创建上传记录失败 document_id=%s", document_id)
        return {"filename": filename, "status": "failed", "error": _DATABASE_ERROR}, True

    try:
        saved = save_pdf(document_id, file.file)
    except (EmptyFile, NotPdf, FileTooLarge, UploadFileError, OSError) as error:
        status, detail = _file_error_response(error)
        if status == 500:
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


@router.post("/documents", status_code=201, summary="上传一份或多份 PDF")
def upload_documents(
    files: Annotated[
        list[UploadFile], File(description="form-data 文件字段，字段名 files，可多行")
    ],
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    response: Response,
) -> dict[str, object]:
    """逐份保存文件和记录；至少一份成功返回 201，全部失败按原因返回 400 或 503。"""
    if len(files) > max_files():
        logger.warning("上传份数超过限制 count=%s", len(files))
        raise HTTPException(status_code=413, detail=f"一次最多上传 {max_files()} 份文件。")
    # Starlette 解析后已持有每份大小；未知大小按 0 计，单份大小仍在写入时逐段校验。
    total_bytes = sum(file.size or 0 for file in files)
    if total_bytes > max_total_bytes():
        logger.warning("上传总大小超过限制 total=%s", total_bytes)
        raise HTTPException(status_code=413, detail="本次上传总大小超过限制。")

    results: list[dict] = []
    db_errors = 0
    for file in files:
        item, is_db_error = _process_file(file, session_factory)
        results.append(item)
        db_errors += int(is_db_error)

    succeeded = sum(1 for item in results if item["status"] == "uploaded")
    if succeeded == 0:
        # 全部失败时区分原因：全部因数据库失败给 503，其余（含存储失败）给 400。
        response.status_code = 503 if db_errors else 400
    return {"succeeded": succeeded, "failed": len(results) - succeeded, "documents": results}
