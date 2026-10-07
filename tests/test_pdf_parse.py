"""旧方案 MVP：真实文字转换、原编码图片、占位符、快照和降级行为。"""

import os
import subprocess
import sys
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from pdf import images, text
from pdf.schemas import PdfParseInput, PdfParseResult
from pdf.service import parse_pdf
from pdf.text import PdfParseError, extract_title


# 独立创建已知红/蓝 JPEG；原始字节可直接核对，没有以解析结果反推预期。
@pytest.fixture
def source_pdf(tmp_path):
    image_bytes = []
    for color in ("red", "blue"):
        with Image.new("RGB", (8, 6), color) as image:
            encoded = BytesIO()
            image.save(encoded, format="JPEG")
            image_bytes.append(encoded.getvalue())
    source_path = tmp_path / "input.pdf"
    with pymupdf.open() as document:
        for page_index in range(2):
            page = document.new_page()
            page.insert_text((30, 40), f"MVP document page {page_index + 1}")
            page.insert_image(pymupdf.Rect(30, 80, 110, 140), stream=image_bytes[0])
            # 第一页再加入另一资源，第二页复用第一张；资源编号与出现位置无关。
            if page_index == 0:
                page.insert_image(pymupdf.Rect(150, 80, 230, 140), stream=image_bytes[1])
        document.save(source_path)
    return source_path, (image_bytes[0], image_bytes[1], image_bytes[0])


def test_old_flow_preserves_bytes_placeholders_and_disk_snapshot(source_pdf, tmp_path):
    source_path, expected_bytes = source_pdf
    output_dir = tmp_path / "run-one"
    result = parse_pdf(PdfParseInput(source_path=source_path, output_dir=output_dir))
    doc_hash = sha256(source_path.read_bytes()).hexdigest()
    assert result.id == f"doc_{doc_hash[:16]}"
    assert result.metadata.doc_hash == doc_hash
    assert "MVP document page 1" in result.text and "MVP document page 2" in result.text
    assert result.metadata.title == "MVP document page 1"
    assert result.diagnostics == ()
    # 三份资源分别保存，保留旧 ID/序号、原 JPEG 字节及真实像素尺寸。
    image_records = result.metadata.images
    assert [(image.page, image.position.index) for image in image_records] == [
        (1, 0),
        (1, 1),
        (2, 0),
    ]
    for image, expected in zip(image_records, expected_bytes, strict=True):
        assert image.id == f"{doc_hash[:8]}_{image.page}_{image.position.index + 1}"
        assert Path(image.path).suffix == ".jpeg"
        assert Path(image.path).read_bytes() == expected
        assert (image.position.width, image.position.height) == (8, 6)
        placeholder = f"[IMAGE: {image.id}]"
        assert result.text[image.text_offset : image.text_offset + image.text_length] == placeholder
    # 文本和模型均从磁盘独立读回，不依赖调用时的 PDF 或内存对象。
    assert (output_dir / "document.md").read_text() == result.text
    saved = PdfParseResult.model_validate_json((output_dir / "result.json").read_text())
    assert saved == result


# 新进程直接读取快照与图片，证明磁盘文件不依赖上一调用的内存状态。
def test_new_process_reads_snapshot_and_images(source_pdf, tmp_path):
    source_path, _ = source_pdf
    output_dir = tmp_path / "readback"
    parse_pdf(PdfParseInput(source_path=source_path, output_dir=output_dir))
    code = (
        "import sys; from pathlib import Path; from pdf.schemas import PdfParseResult; "
        "r=PdfParseResult.model_validate_json(Path(sys.argv[1]).read_text()); "
        "assert all(Path(i.path).is_file() for i in r.metadata.images); "
        "print(len(r.metadata.images))"
    )
    process = subprocess.run(
        [sys.executable, "-c", code, str(output_dir / "result.json")],
        env={**os.environ, "PYTHONPATH": str(Path("src").resolve())},
        capture_output=True,
        text=True,
        check=True,
    )
    assert process.stdout.strip() == "3"


# 不开启图片提取时仍保存正文；之后开启使用新目录，先前结果保持原样。
def test_images_option_and_runs_are_independent(source_pdf, tmp_path):
    source_path, _ = source_pdf
    first_dir, second_dir = tmp_path / "text-only", tmp_path / "with-images"
    first = parse_pdf(
        PdfParseInput(
            source_path=source_path,
            output_dir=first_dir,
            extract_images=False,
        )
    )
    original_json = (first_dir / "result.json").read_bytes()
    second = parse_pdf(PdfParseInput(source_path=source_path, output_dir=second_dir))
    assert first.metadata.images == () and "[IMAGE:" not in first.text
    assert not (first_dir / "images").exists()
    assert len(second.metadata.images) == 3 and second.id == first.id
    assert second.extract_images and not first.extract_images
    assert (first_dir / "result.json").read_bytes() == original_json


# 同一输出目录拒绝覆盖，既有图片和 JSON 快照均须保留。
def test_existing_output_is_rejected(source_pdf, tmp_path):
    source_path, _ = source_pdf
    request = PdfParseInput(source_path=source_path, output_dir=tmp_path / "existing")
    parse_pdf(request)
    original = (request.output_dir / "result.json").read_bytes()
    with pytest.raises(FileExistsError):
        parse_pdf(request)
    assert (request.output_dir / "result.json").read_bytes() == original


# 明确注入第二张资源失败，检查旧流程的继续行为及其占位符引用。
def test_second_image_failure_keeps_text_and_other_images(source_pdf, tmp_path, monkeypatch):
    source_path, _ = source_pdf
    original = pymupdf.Document.extract_image
    calls = 0

    def broken_extract(document, xref):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("controlled image failure")
        return original(document, xref)

    monkeypatch.setattr(pymupdf.Document, "extract_image", broken_extract)
    result = parse_pdf(PdfParseInput(source_path=source_path, output_dir=tmp_path / "partial"))
    # 单图失败不拒绝整份文档；该图没有占位符，其他图和诊断写入快照。
    assert "MVP document page 2" in result.text
    assert [(image.page, image.position.index) for image in result.metadata.images] == [
        (1, 0),
        (2, 0),
    ]
    assert result.diagnostics[0].code == "image_extract_failed"
    assert (result.diagnostics[0].page, result.diagnostics[0].image_index) == (1, 1)
    assert f"[IMAGE: {result.metadata.doc_hash[:8]}_1_2]" not in result.text


# 整段图片读取失败沿用旧纯文本降级；失败原因随结果保存。
def test_image_open_failure_returns_text_only(source_pdf, tmp_path, monkeypatch):
    source_path, _ = source_pdf

    def broken_open(*args, **kwargs):
        raise RuntimeError("controlled images open failure")

    monkeypatch.setattr(images.pymupdf, "open", broken_open)
    result = parse_pdf(PdfParseInput(source_path=source_path, output_dir=tmp_path / "fallback"))
    assert result.metadata.images == () and "[IMAGE:" not in result.text
    assert "MVP document page 1" in result.text
    assert result.diagnostics[0].code == "images_extract_failed"


# 明确注入转换异常：损坏 PDF 不一定被 MarkItDown 拒绝，不能用它假定异常发生。
def test_text_failure_does_not_return_empty_document(source_pdf, tmp_path, monkeypatch):
    source_path, _ = source_pdf

    def broken_convert(*args, **kwargs):
        raise RuntimeError("controlled text conversion failure")

    monkeypatch.setattr(text.MarkItDown, "convert", broken_convert)
    request = PdfParseInput(source_path=source_path, output_dir=tmp_path / "failed")
    with pytest.raises(PdfParseError):
        parse_pdf(request)
    assert not request.output_dir.exists()


# 输入校验保持旧文件路径约定；缺失文件与错误扩展名各自报错。
@pytest.mark.parametrize("kind", ["missing", "extension"])
def test_source_validation(tmp_path, kind):
    source_path = tmp_path / ("missing.pdf" if kind == "missing" else "wrong.txt")
    if kind == "extension":
        source_path.write_text("not a PDF")
    exception = FileNotFoundError if kind == "missing" else ValueError
    with pytest.raises(exception):
        parse_pdf(PdfParseInput(source_path=source_path, output_dir=tmp_path / "output"))


# 保存快照失败必须向调用方报错，不能只给一份看似成功的内存结果。
def test_snapshot_write_failure_is_raised(source_pdf, tmp_path, monkeypatch):
    source_path, _ = source_pdf
    original = Path.write_text

    def broken_write(path, *args, **kwargs):
        if path.name == "document.md":
            raise OSError("controlled disk failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", broken_write)
    with pytest.raises(OSError):
        parse_pdf(PdfParseInput(source_path=source_path, output_dir=tmp_path / "disk-failure"))


# 标题处理参考旧实现，不借此修改全文或增加新的标题推断策略。
@pytest.mark.parametrize(
    "text, expected", [("first\n# Heading", "Heading"), ("\nbody", "body"), ("", None)]
)
def test_title_rules(text, expected):
    assert extract_title(text) == expected
