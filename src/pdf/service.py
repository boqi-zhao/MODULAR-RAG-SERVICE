"""MVP 独立解析入口：文字转换 → 原编码图片 → 文档快照。"""

from hashlib import sha256
from importlib.metadata import version

import pymupdf

from common.logger import logger
from pdf.images import extract_pdf_images
from pdf.schemas import DocumentMetadata, ParserInfo, PdfParseInput, PdfParseResult
from pdf.text import extract_pdf_text, extract_title


# 读取本地文件并生成旧文档 ID；不引入旧的逐页图文/扫描判断。
def parse_pdf(request: PdfParseInput) -> PdfParseResult:
    """按旧基线解析，并将文本、图片和 JSON 保存到本次独立目录。"""
    source_path = request.source_path.resolve()
    output_dir = request.output_dir.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path.suffix.lower() != ".pdf":
        raise ValueError("输入文件扩展名必须是 .pdf")
    if output_dir.exists():
        raise FileExistsError("输出目录已存在，请使用新的目录保留历史结果")

    # 沿用分段计算摘要；不以短图片 ID 代替完整文档摘要。
    source_hash = sha256()
    with source_path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(8192), b""):
            source_hash.update(chunk)
    doc_hash = source_hash.hexdigest()
    text = extract_pdf_text(source_path)
    title = extract_title(text)
    output_dir.mkdir(parents=True, exist_ok=False)

    # 图片按旧规则存入文档摘要目录；每次调用的根目录独立，历史图片不被覆盖。
    images, diagnostics = (), ()
    if request.extract_images:
        image_dir = output_dir / "images" / doc_hash
        text, images, diagnostics = extract_pdf_images(source_path, image_dir, text, doc_hash)
    result = PdfParseResult(
        id=f"doc_{doc_hash[:16]}",
        text=text,
        metadata=DocumentMetadata(
            source_path=str(source_path), doc_hash=doc_hash, title=title, images=images
        ),
        extract_images=request.extract_images,
        # 写实际依赖版本，便于复现；完整 Stage 身份与上游引用仍在后续存储任务。
        parser=ParserInfo(
            markitdown_version=version("markitdown"),
            pymupdf_version=pymupdf.VersionBind,
            mupdf_version=pymupdf.VersionFitz,
            pillow_version=version("pillow"),
        ),
        diagnostics=diagnostics,
    )
    # 快照保存正文、元数据与诊断；任何写入失败都向调用方抛出，不宣称成功。
    (output_dir / "document.md").write_text(result.text, encoding="utf-8")
    (output_dir / "result.json").write_text(
        result.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    logger.info("PDF 解析完成 doc_id=%s images=%s", result.id, len(images))
    return result
