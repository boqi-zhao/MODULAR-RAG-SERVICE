# PDF 解析：当前 MVP

用户决定沿用旧项目基线：MarkItDown 提取文字，PyMuPDF 保存资源图片，使用 `[IMAGE: 图片ID]`。
独立解析与磁盘快照已实现、验证；代码待用户评审，未提交。选型过程见 [决策 04](../decisions/04-mvp-original-pdf-strategy.md)。

## 先看入口

1. [service.py](../../src/pdf/service.py)：parse_pdf 校验路径、算摘要、调用图文提取、保存结果。
2. [text.py](../../src/pdf/text.py)：MarkItDown.convert → text_content；前 20 行找一级标题，否则取前 10 行首个非空行。
3. [images.py](../../src/pdf/images.py)：逐页 get_images(full=True) → extract_image(xref) → 保存原编码字节 → 追加占位符。
4. [schemas.py](../../src/pdf/schemas.py)：Pydantic 明确输入、文档、图片、配置和诊断。

MarkItDown 的结果原样保留，不另加正文清洗、阅读顺序猜测或针对样本的修复分支。
图片按 PDF 资源记录提取，保留返回扩展名；没有 bbox、实际出现清单匹配、强制 PNG 或遮罩合成。

## 输入与输出

| 模型 | 主要内容 |
| --- | --- |
| PdfParseInput | source_path：已有本地 PDF；output_dir：必须不存在的新目录；extract_images：默认 True |
| PdfParseResult | id、text、metadata；另含 parser、图片选项、diagnostics、schema_version |
| DocumentMetadata | source_path、doc_type、完整 doc_hash、title、images |
| ImageMetadata | id、path、page、text_offset、text_length、position |
| ImagePosition | 像素 width/height、从 1 开始的 page、从 0 开始的资源 index；不是页面坐标 |

文档 ID 为 `doc_{SHA256前16位}`；图片 ID 为 `{SHA256前8位}_{页码}_{资源序号}`，资源序号从 1 开始。
占位符带前后换行，追加在**全文末尾**；text_offset 指向 `[` 的字符下标，text_length 只计占位符长度。
每页资源记录各自保存，不增加实际出现计数或跨页去重。图片 path 和来源路径为本机绝对路径。
冻结模型、tuple 清单、空标题 None 便于独立调用和 JSON 保存；正式身份编码仍待设计。

## 保存和失败行为

```text
output_dir/
  document.md
  result.json
  images/{完整文档摘要}/{图片ID}.{原扩展名}
```

result.json 含完整正文、元数据、配置、诊断和实际依赖版本；新目录拒绝覆盖旧结果。
MarkItDown 转换异常抛 PdfParseError；单张图片失败记录诊断后继续，整段图片失败返回原文字和空图片清单。
图片尺寸无法读取沿用 0×0。快照写入失败向调用方抛错，工作目录中可能留有部分文件。

这是**工作目录快照**：没有正式 artifact_id、固定上游、执行尝试/成功标记、文件摘要清单或复用校验。
目录存在不证明 Stage 成功；正式产物交接还需 [03 阶段产物](03-stage-artifacts.md) 和 [04 执行与调优](04-execution.md)。
HTTP 解析接口、worker、Runner 尚未接入。

## 调用

```python
from pathlib import Path
from pdf.schemas import PdfParseInput
from pdf.service import parse_pdf

result = parse_pdf(
    PdfParseInput(source_path=Path("data/source.pdf"), output_dir=Path("data/parse/run-1"))
)
```

项目根目录运行：`PYTHONPATH=src uv run python scripts/parse_pdf.py data/source.pdf data/parse/run-1`。
加 `--no-images` 仅提取文字；每次换一个输出目录。

## 验证与限制

PDF 重写轮次：新解析 13 个检查、当时加载 .env 后全套 85 个通过，无跳过；后续全套结果见 [TASKS.md](../../TASKS.md)。
覆盖原 JPEG 字节、ID/元数据、占位符偏移、图片开关、拒绝覆盖、独立调用及新进程读取 JSON/图片。
文字转换、单图/整段图片和写盘失败用故障注入验证，不等于所有真实坏 PDF 都会产生同类异常。
首次测试错误假设坏字节必令 MarkItDown 抛错，实际被接受；修正测试为转换故障注入，没有增加生产拒绝规则。

当前不保证任意损坏 PDF 被拒绝，也不保证正确 Markdown 标题/表格、精准图文关联或扫描检测。
未重跑历史 29 份固定语料，没有新旧质量/速度/RAG 指标对比。旧 A/B/C 结果见 [历史](../history/offline/01-pdf-history.md)，不能算当前证据。
独立中文两页 review 输入/输出在本机 `data/checks/pdf-mvp-review/`，两份 JPEG 和占位符，诊断为空。
锁定依赖：MarkItDown 0.1.8、PyMuPDF/MuPDF 1.28.2、Pillow 12.3.0；运行数据不随 Git 克隆。
