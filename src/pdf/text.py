"""直接使用旧项目的 MarkItDown 文字转换和标题提取规则。"""

from pathlib import Path

from markitdown import MarkItDown

from common.logger import logger


class PdfParseError(RuntimeError):
    """文字转换失败，调用方不能将它当作正常空文档。"""


# MarkItDown 负责文字转换；不再提取文字块、坐标或自己补 Markdown。
def extract_pdf_text(source_path: Path) -> str:
    try:
        converted = MarkItDown().convert(str(source_path))
        return converted.text_content
    except Exception as exc:
        logger.warning("MarkItDown PDF 文字转换失败", exc_info=True)
        raise PdfParseError("PDF 文字转换失败") from exc


# 保留旧规则：先找前 20 行的一级标题，再找前 10 行的首个非空行。
def extract_title(text: str) -> str | None:
    lines = text.split("\n")
    for line in lines[:20]:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    # 标题只写入元数据，全文不会因此被裁剪或重排。
    for line in lines[:10]:
        stripped = line.strip()
        if stripped:
            return stripped
    return None
