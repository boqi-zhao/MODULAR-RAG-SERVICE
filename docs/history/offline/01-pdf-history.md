# 历史：PyMuPDF 解析方案

状态：此前经评审并实施 A/B/C；2026-10-07 用户决定 MVP 沿用旧流程，现已被 [决策 04](../../decisions/04-mvp-original-pdf-strategy.md) 替代。
本文压缩原模块设计/模型/分步记录和旧项目核对；旧接口、测试命令、扫描规则不作为当前 MVP 要求。

## 原目标与契约

固定 PDF 字节 → 逐页文字块/位图与原始位置 → 扫描风险 → 结果一致性；内存计算完成后仍需正式版本落盘。
首批文本层、嵌入位图；OCR、密码解密、结构化表格、多栏修复、矢量图和展示高亮转换后置。
部分结果用于诊断，任何必需项失败、未处理页或疑似扫描使整份 failed，禁止进入正常下游。

| 原模型 | 主要内容 |
| --- | --- |
| PdfParseInput / ParseConfig | source_bytes；扫描面积默认 0.80、字符默认 80，严格数值与未知字段校验 |
| PdfParseResult | status、schema/source 摘要、page_count、pages、image_assets、diagnostics、parser、config、execution |
| PageResult | 页序/status、未旋转宽高、text_blocks、image_occurrences、非空白字数/覆盖率 |
| TextBlock | 引擎 block_number、原 text、bbox |
| ImageAsset | 最终 PNG SHA-256、bytes、媒体类型、尺寸、alpha |
| ImageOccurrence | 页内序号、asset_key、原 bbox；失败可保留可空字段 |
| Diagnostic | severity/code/message、页/对象、明确 observations 模型，不用任意字典 |

页面从 1 开始，全部页都有 succeeded/failed/not_processed 记录，未知尺寸/观察值留空而不是 0。
原 bbox 为有限 `(x0,y0,x1,y1)`，左上原点、point（1/72 英寸）、未旋转坐标，允许跨页边界，不裁写原始位置。
原文字顺序/空白/连字保留，不去连字符、重排或拼全文；get_text(blocks, sort=False)，TEXTFLAGS_BLOCKS 当时为 195。
文字块不是 RAG chunk；模型 frozen/tuple，关闭 PDF 后普通字节、文字与坐标仍可读，内容比较不含时间。
U+FFFD 只告警、不新增乱码失败阈值；页或对象异常尽量继续，其余未处理页明确记录。
诊断分类曾含不可读取/密码、页/文本失败、图片清单/提取/定位/解码/透明度、OCR 风险、结果无效和处理中止。

## 原图片与扫描方案

get_image_info 枚举实际出现，dict + INFINITE_RECT 取完整图片块/遮罩，用尺寸、变换与像素摘要匹配。
与未旋转边界相交只作筛选；每次出现各保留来源，最终 PNG 字节可按 SHA-256 去重。
透明图合成遮罩/alpha，必要时转 RGB；内联图、跨裁剪图不因资源 API 限制漏掉，不用截图替代。
无法对应、解码、还原透明或定位时诊断失败，不猜引用；位置未知的字节只作诊断资产。

原扫描规则：每页矩形与边界相交，求并集面积（重叠只算一次），覆盖率 ≥0.80 且非空白字数 <80 即“疑似需 OCR”。
原建议按横向条带合并纵向区间算并集；缺少文字/位置观察值不得当 0。原阈值必须 >0，面积 ≤1、字符严格整数。
79% 或 80 字不触发，80% 与 79 字触发；普通满页照片可误拒、小面积扫描可能漏判，不能宣称识别了扫描文字。
空页/短标题不因字少独立失败；乱码先告警。没有抛异常、页数完整或引用可读都不能证明全文语义完整。
原政策全 PDF 重跑，不做单页恢复；D 扫描与 E 最终契约验收没有实施。

## 既有项目源码核对

2026-10-07 只读查看 `/Users/zhaoboqi/project/MODULAR-RAG-MCP-SERVER`，HEAD `8600596`；loader 无改动，pipeline 当时有本地改动。
未运行/修改旧项目或复制数据；下表描述查看时源码，不是效果测量。

| 位置 | 行为 |
| --- | --- |
| src/libs/loader/pdf_loader.py:79 | 路径校验、SHA-256、MarkItDown.convert 取 text_content |
| 同文件 :181 | 逐页 get_images(full=True)，xref → extract_image，保存原字节/扩展名 |
| 同文件 :248 | `[IMAGE: ID]` 追加全文末尾；页码/尺寸/文本偏移，没有 bbox |
| 同文件 :280 | 图片异常告警继续，整段失败退回只有文字 |
| src/ingestion/pipeline.py:260 | loader → chunk → refine/enrich/caption → 编码 → 向量/BM25/图片索引 |

曾选 PyMuPDF 单引擎是为了页/块坐标和减少对齐工作，不是已测出质量更好；选择变化详见决策 [02](../../decisions/02-pdf-parser-selection.md) → [03](../../decisions/03-pdf-image-fallback-withdrawal.md) → [04](../../decisions/04-mvp-original-pdf-strategy.md)。

## A/B/C 的历史证据

| 步骤 | 当时验证 | 局限 |
| --- | --- | --- |
| A 打开/关闭、密码/页数 | 21 项；当时全套 93 通过 | 仅打开，不是完整 parse |
| B 逐页文字/矩形 | 12 项；当时全套 105 通过；11 个公开锚点 | 没有图片、扫描或正式产物 |
| C 图文匹配 | 撤回前全套 113 通过、1 资产数量假设失败；改测试后图片 9 通过 | 不是撤回后证据 |
| C 撤掉资源兜底后 | 图文/打开 43 项通过，图片 10 项；未重跑全套/固定语料 | D/E 未完成，开发状态仍阻断 |

A/B 的29份固定PDF报告在 `data/checks/pdf-open-a.json`、`pdf-text-b.json`；C 撤回前报告在 `pdf-images-c.json` 和同名目录。
这些本机报告不是正式 Stage 产物，不作为当前 MarkItDown 策略的通过证据；旧复现脚本/接口已移除。
曾因一个 CMYK 样本追加 xref 资源字节兜底和解码切换；用户要求移除，按统一块字节处理，摘要不一致诊断失败。
资产数量失败源于两条路径产生不同 PNG，测试改为内容/摘要/引用检查，没有修改生产代码凑数量。
后续文字具名解包/图片助手拆分仅改可读性；用户仍认为图片方案复杂，最终授权回归旧基线。
旧代码、测试与脚本本机备份 `data/history/pdf-pymupdf-pre-mvp/`；目前正确入口是 [PDF MVP](../../offline/02-pdf-parse.md)。

流水线版本产物与指定 Stage 重跑要求仍有效，见当前 [03](../../offline/03-stage-artifacts.md)、[04](../../offline/04-execution.md)。
