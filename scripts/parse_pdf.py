"""本地 review 调用入口；不连接 HTTP、数据库或 Runner。"""

import argparse
from pathlib import Path

from common.logger import logger
from pdf.schemas import PdfParseInput
from pdf.service import parse_pdf


# 输出目录显式指定且不可覆盖，便于分别查看多次解析的原始结果。
def main():
    parser = argparse.ArgumentParser(description="按旧方案解析 PDF 并保存快照")
    parser.add_argument("source", type=Path, help="本地 PDF 路径")
    parser.add_argument("output", type=Path, help="本次解析的新输出目录")
    parser.add_argument("--no-images", action="store_true", help="只转换文字")
    args = parser.parse_args()
    result = parse_pdf(
        PdfParseInput(
            source_path=args.source, output_dir=args.output, extract_images=not args.no_images
        )
    )
    # 运行信息走共用 logger，不输出正文或任意图片字节。
    logger.info(
        "PDF 快照已保存 output=%s diagnostics=%s", args.output.resolve(), len(result.diagnostics)
    )


if __name__ == "__main__":
    main()
