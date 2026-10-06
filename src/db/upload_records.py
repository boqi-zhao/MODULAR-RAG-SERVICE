"""上传记录读写：短事务写入 uploading 记录，条件更新结束上传。

调用顺序由 docs/offline/api/03-upload-records.md 规定：
创建 uploading → 保存文件 → 标记 uploaded 或 failed。
每个函数自己开、关 Session，上传期间不长时间占用数据库连接。
"""

from sqlalchemy import func, update
from sqlalchemy.orm import Session, sessionmaker

from db.models.document_upload import DocumentUpload
from db.session import SessionFactory


# 写入初始记录；状态、创建时间由数据库列默认值填写，文件信息留空等结束后补齐。
def create_uploading(
    *,
    document_id: str,
    filename: str,
    source_format: str,
    storage_type: str,
    storage_key: str,
    session_factory: sessionmaker[Session] = SessionFactory,
) -> None:
    """用一个短事务写入 uploading 记录；失败时不留下半条记录。"""
    record = DocumentUpload(
        document_id=document_id,
        filename=filename,
        source_format=source_format,
        storage_type=storage_type,
        storage_key=storage_key,
    )
    with session_factory() as session:
        try:
            session.add(record)
            session.commit()
        except Exception:
            session.rollback()
            raise


# 只有仍处于 uploading 的记录会被更新；受影响行数决定本次调用是否为唯一成功者。
def _finish_uploading(
    document_id: str,
    values: dict,
    session_factory: sessionmaker[Session],
) -> bool:
    """把 uploading 记录改成终态；返回是否由本次调用完成。"""
    statement = (
        update(DocumentUpload)
        .where(
            DocumentUpload.document_id == document_id,
            DocumentUpload.status == "uploading",
        )
        .values(**values)
    )
    with session_factory() as session:
        try:
            result = session.execute(statement)
            session.commit()
        except Exception:
            session.rollback()
            raise
        return result.rowcount == 1


# 成功结束：补齐大小和校验和；值不合法时由数据库约束拒绝，状态保持 uploading。
def mark_uploaded(
    document_id: str,
    *,
    size_bytes: int,
    sha256: str,
    session_factory: sessionmaker[Session] = SessionFactory,
) -> bool:
    """记录上传成功；返回 True 表示本次调用完成上传，False 表示已结束或记录不存在。"""
    return _finish_uploading(
        document_id,
        {
            "status": "uploaded",
            "size_bytes": size_bytes,
            "sha256": sha256,
            "completed_at": func.now(),
        },
        session_factory,
    )


# 失败结束：只写可排查的简短原因；不写服务器路径、数据库凭据或完整堆栈。
def mark_failed(
    document_id: str,
    *,
    error_message: str,
    session_factory: sessionmaker[Session] = SessionFactory,
) -> bool:
    """记录上传失败；返回 True 表示本次调用结束了上传。"""
    return _finish_uploading(
        document_id,
        {"status": "failed", "completed_at": func.now(), "error_message": error_message},
        session_factory,
    )


# 读取入口供测试和后续接口使用；Session 关闭后对象已加载字段仍可访问。
def get_upload(
    document_id: str,
    *,
    session_factory: sessionmaker[Session] = SessionFactory,
) -> DocumentUpload | None:
    """按文档编号读取记录；不存在时返回 None。"""
    with session_factory() as session:
        return session.get(DocumentUpload, document_id)
