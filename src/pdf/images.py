"""沿用旧项目：按资源 xref 提取原编码图片，并追加全文末尾占位符。"""

from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image

from common.logger import logger
from pdf.schemas import ImageMetadata, ImagePosition, ParseDiagnostic


# 尺寸读不到时沿用旧项目的 (0, 0)，不改写图片字节或新增拒绝规则。
def _read_image_size(image_bytes: bytes) -> tuple[int, int]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return image.size
    except Exception:
        return 0, 0


def extract_pdf_images(
    source_path: Path,  # pdf的输入路径
    image_dir: Path,  # 图片的输出路径
    text: str,  # 已经提取好的正文
    doc_hash: str,  # 文档的sha256哈希
) -> tuple[str, tuple[ImageMetadata, ...], tuple[ParseDiagnostic, ...]]:
    """保存资源图片；单图失败继续，整段失败退回原文和空图片清单。"""
    modified_text = text
    images: list[ImageMetadata] = []
    diagnostics: list[ParseDiagnostic] = []
    try:
        image_dir.mkdir(parents=True)
        # with 保证失败时也关闭 PDF；业务提取路径与旧项目一致。
        with pymupdf.open(source_path) as document:
            for page_number, page in enumerate(document, start=1):
                # full 模式下，每项资源的字段依次为：
                # xref, smask, width, height, bpc, colorspace, alt_colorspace, name, filter。
                image_resources = page.get_images(full=True)
                # enumerate 把每项拆成两个值：
                #   image_index 是本页资源下标（0 起），只表示返回顺序，每页重新计数；
                #   image_resource 是该图的资源元组，首字段 xref 才是它在 PDF 里的编号。
                for image_index, image_resource in enumerate(image_resources):
                    try:
                        # 第一个字段是资源 xref；直接取原编码字节与扩展名。
                        xref = image_resource[0]
                        extracted = document.extract_image(xref)
                        # 图片的二进制内容本身
                        image_bytes = extracted["image"]
                        # 图片的扩展名，比如png、jpeg
                        extension = extracted["ext"]
                        image_id = f"{doc_hash[:8]}_{page_number}_{image_index + 1}"
                        image_path = image_dir / f"{image_id}.{extension}"
                        image_path.write_bytes(image_bytes)
                        # 读取图片的大小
                        width, height = _read_image_size(image_bytes)
                        placeholder = f"[IMAGE: {image_id}]"
                        image_metadata = ImageMetadata(
                            id=image_id,
                            path=str(image_path),
                            page=page_number,
                            text_offset=len(modified_text) + 1,
                            text_length=len(placeholder),
                            position=ImagePosition(
                                width=width, height=height, page=page_number, index=image_index
                            ),
                        )
                        # 追加图片占位符到文档末尾
                        modified_text += f"\n{placeholder}\n"
                        images.append(image_metadata)
                    except Exception as exc:
                        logger.warning(
                            "PDF 图片提取失败 page=%s index=%s",
                            page_number,
                            image_index,
                            exc_info=True,
                        )
                        # 图片失败不阻断正文和其他图片，另外保存结构化原因。
                        diagnostics.append(
                            ParseDiagnostic(
                                code="image_extract_failed",
                                page=page_number,
                                image_index=image_index,
                                exception_type=type(exc).__name__,
                            )
                        )
    except Exception as exc:
        logger.warning("PDF 图片提取失败，保留纯文本", exc_info=True)
        diagnostics.append(
            ParseDiagnostic(
                code="images_extract_failed",
                exception_type=type(exc).__name__,
            )
        )
        # 与旧流程一致：整段图片处理失败时返回转换前的正文，不留下悬空占位符。
        return text, (), tuple(diagnostics)
    return modified_text, tuple(images), tuple(diagnostics)
