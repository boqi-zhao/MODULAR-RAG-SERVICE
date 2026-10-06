"""create document uploads：首次迁移，创建上传记录表。

由 `alembic revision --autogenerate` 生成后人工核对，字段与约束与模型一致。

Revision ID: e5690f23be74
Revises:
Create Date: 2026-10-06 18:17:24.775095

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5690f23be74"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建上传记录表；状态与字段组合规则由 CheckConstraint 保证。"""
    op.create_table(
        "document_uploads",
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("source_format", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column("storage_type", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="uploading", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(status = 'uploading' AND completed_at IS NULL AND error_message IS NULL) OR "
            "(status = 'uploaded' AND size_bytes IS NOT NULL AND size_bytes > 0 "
            "AND sha256 IS NOT NULL "
            "AND completed_at IS NOT NULL AND error_message IS NULL) OR "
            "(status = 'failed' AND completed_at IS NOT NULL AND error_message IS NOT NULL)",
            name=op.f("ck_document_uploads_state_fields_consistent"),
        ),
        sa.CheckConstraint(
            "btrim(filename, E' \\t\\n\\r') <> ''",
            name=op.f("ck_document_uploads_filename_not_blank"),
        ),
        sa.CheckConstraint(
            "btrim(source_format, E' \\t\\n\\r') <> ''",
            name=op.f("ck_document_uploads_source_format_not_blank"),
        ),
        sa.CheckConstraint(
            "btrim(storage_key, E' \\t\\n\\r') <> ''",
            name=op.f("ck_document_uploads_storage_key_not_blank"),
        ),
        sa.CheckConstraint(
            "btrim(storage_type, E' \\t\\n\\r') <> ''",
            name=op.f("ck_document_uploads_storage_type_not_blank"),
        ),
        sa.CheckConstraint(
            "error_message IS NULL OR btrim(error_message, E' \\t\\n\\r') <> ''",
            name=op.f("ck_document_uploads_error_message_not_blank"),
        ),
        sa.CheckConstraint(
            "sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_document_uploads_sha256_format"),
        ),
        sa.CheckConstraint(
            "status IN ('uploading', 'uploaded', 'failed')",
            name=op.f("ck_document_uploads_status_valid"),
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at",
            name=op.f("ck_document_uploads_completed_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name=op.f("ck_document_uploads_size_bytes_nonnegative"),
        ),
        sa.PrimaryKeyConstraint("document_id", name=op.f("pk_document_uploads")),
        sa.UniqueConstraint(
            "storage_type", "storage_key", name="uq_document_uploads_storage_type_storage_key"
        ),
    )


def downgrade() -> None:
    """回退会删除上传记录表；仅用于独立测试库验证，不能用于恢复正式数据。"""
    op.drop_table("document_uploads")
