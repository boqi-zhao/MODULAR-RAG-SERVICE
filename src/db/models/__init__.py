"""ORM 模型集中导入；Alembic 通过这里发现需要建表的模型。"""

from db.models.document_upload import DocumentUpload

__all__ = ["DocumentUpload"]
