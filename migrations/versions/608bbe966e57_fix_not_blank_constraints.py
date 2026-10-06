"""fix not blank constraints：非空白约束改用 Unicode 空白字符集合。

旧约束只把空格、制表符、换行和回车当作空白，竖向制表符、换页符、全角空格等
可以绕过校验。本迁移只替换 5 条约束，不改写历史数据。
历史库可能存在旧规则放行的纯空白文本，因此用 NOT VALID 添加新约束：
已有记录原样保留，新写入和修改立即受新规则限制，不因历史数据导致升级失败。
不修改已执行的首次迁移，符合“结构变化新增迁移”的约定。

Revision ID: 608bbe966e57
Revises: e5690f23be74
Create Date: 2026-10-06 18:34:20.763111

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "608bbe966e57"
down_revision: str | None = "e5690f23be74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 新集合与 ORM 模型一致；旧集合用于降级回退。
_UNICODE_WHITESPACE = (
    "E' \\t\\n\\r\\v\\f' || "
    "U&'\\0085\\00A0\\1680\\2000\\2001\\2002\\2003\\2004\\2005\\2006"
    "\\2007\\2008\\2009\\200A\\2028\\2029\\202F\\205F\\3000'"
)
_LEGACY_WHITESPACE = "E' \\t\\n\\r'"


def _replace(name: str, condition: str, *, not_valid: bool) -> None:
    """删除并重建一条检查约束；not_valid 为真时不校验已有行。"""
    constraint = f"ck_document_uploads_{name}"
    op.drop_constraint(op.f(constraint), "document_uploads", type_="check")
    suffix = " NOT VALID" if not_valid else ""
    op.execute(
        f"ALTER TABLE document_uploads ADD CONSTRAINT {constraint} CHECK ({condition}){suffix}"
    )


def _replace_not_blank_constraints(whitespace: str, *, not_valid: bool) -> None:
    """替换 5 条非空白约束；只改规则，不触碰表中已有记录。"""
    _replace("filename_not_blank", f"btrim(filename, {whitespace}) <> ''", not_valid=not_valid)
    _replace(
        "source_format_not_blank", f"btrim(source_format, {whitespace}) <> ''", not_valid=not_valid
    )
    _replace(
        "storage_type_not_blank", f"btrim(storage_type, {whitespace}) <> ''", not_valid=not_valid
    )
    _replace(
        "storage_key_not_blank", f"btrim(storage_key, {whitespace}) <> ''", not_valid=not_valid
    )
    _replace(
        "error_message_not_blank",
        f"error_message IS NULL OR btrim(error_message, {whitespace}) <> ''",
        not_valid=not_valid,
    )


def upgrade() -> None:
    """用 Unicode 空白集合替换旧约束；历史记录保留，新写入立即受限。"""
    _replace_not_blank_constraints(_UNICODE_WHITESPACE, not_valid=True)


def downgrade() -> None:
    """恢复旧集合；旧规则更宽松，已有记录一定满足。"""
    _replace_not_blank_constraints(_LEGACY_WHITESPACE, not_valid=False)
