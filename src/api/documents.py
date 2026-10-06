"""POST /documents：接收 HTTP 上传，调用业务服务并返回响应。"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session, sessionmaker

from uploads.schemas import UploadResponse
from uploads.service import BatchLimitExceeded, UploadInput
from uploads.service import upload_documents as upload_documents_service

router = APIRouter()


# 依赖注入让测试替换成临时库工厂；延迟导入使启动服务不必先连库。
def get_session_factory() -> sessionmaker[Session]:
    """返回数据库 Session 工厂；测试通过依赖覆盖指向临时库。"""
    from db.session import SessionFactory

    return SessionFactory


# 成功与全失败使用同一批次模型，让接口文档展示每种响应的字段。
@router.post(
    "/documents",
    status_code=201,
    summary="上传一份或多份 PDF",
    response_model=UploadResponse,
    responses={
        400: {"model": UploadResponse, "description": "全部上传失败"},
        503: {"model": UploadResponse, "description": "全部失败且存在数据库错误"},
    },
)
def upload_documents(
    files: Annotated[
        list[UploadFile], File(description="form-data 文件字段，字段名 files，可多行")
    ],
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    response: Response,
) -> UploadResponse:
    """把 HTTP 文件转换为业务输入，再将业务结果映射为 HTTP 响应。"""
    # service 只接收普通数据和文件流，不接收 FastAPI 请求或响应对象。
    inputs = [UploadInput(file.filename or "", file.file, file.size) for file in files]
    try:
        result = upload_documents_service(inputs, session_factory)
    except BatchLimitExceeded as error:
        raise HTTPException(status_code=413, detail=str(error)) from error

    # 保持现有契约：有成功项返回 201；全失败且有数据库错误返回 503，其余 400。
    if result.succeeded == 0:
        response.status_code = 503 if result.database_errors else 400
    return UploadResponse(
        succeeded=result.succeeded,
        failed=result.failed,
        documents=result.documents,
    )
