# 调用 PDF 解析模块

状态：首批独立解析模块已实现；输入输出、规则和用例见 [评审入口](reviews/01-pdf-parse-cases.md)。

## 直接调用

在项目根目录执行；`PYTHONPATH=src` 让 Python 找到源码包：

```sh
PYTHONPATH=src uv run python - <<'PY'
from pathlib import Path
from pdf import PdfParser

# 用户只提供 PDF，默认扫描参数由模块提供并记录。
path = Path('data/samples/doclaynet/sample-20/PDF/01-OTC_PMMAF_2004-p10.pdf')
result = PdfParser().parse(path.read_bytes())
print('结果：', result.status, '页数：', result.page_count)
for page in result.pages:
    print('第', page.number, '页：', len(page.text_blocks), '个文字块，', len(page.images), '处图片')
for diagnostic in result.diagnostics:
    print(diagnostic.code, diagnostic.page, diagnostic.message)
PY
```

## 返回什么

统一返回 `ParseResult` 对象，后续分块读取它的内容；不用读取 PyMuPDF 的内部文件对象。

| 内容 | 如何查看 |
| --- | --- |
| 成功或失败、原始文件校验和 | `result.status`、`result.source_sha256` |
| 每页文字、图片、原始位置 | `result.pages`，文字在 `text_blocks`，图片出现记录在 `images` |
| 图片文件内容 | 每次出现的 `resource.data` 是可读取字节；失败时资源或位置可能为空 |
| 失败原因和出问题的位置 | `result.diagnostics`；同页提取失败时会保留已经取得的部分内容 |
| 实际参数与解析库版本 | `result.config`、`result.parser_version` |

成功用 `succeeded`，失败用 `failed`；某页失败不代表其他页内容消失。
无效 PDF 或密码文件返回失败诊断；非法服务配置在解析前抛出 `ValueError`。
对象及内部内容不可原地修改，重复调用不会追加到上次结果中。

## 测试与样本

```sh
uv run pytest -q
uv run pytest -q -m public_pdf
uv run pytest -q -m fault_injection
uv run python scripts/prepare_pdf_controls.py
```

准备脚本生成 9 份人工查看用 PDF，默认目录 `data/samples/pdf-controls/`；目录非空时拒绝覆盖，可指定新的 `--output-dir`。
自动测试会自行重建控制输入，不依赖这些生成文件；公开回归须有固定的 20 份 DocLayNet PDF，缺失或校验和不符会明确失败。
测试覆盖与本轮结果见 [测试记录](reviews/pdf-parse/09-test-results.md)。
