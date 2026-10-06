# 设计文档

设计按三个大阶段组织；各阶段的设计与实现进度分别记录。
当前已实现离线阶段的独立 PDF 解析模块，其余范围仍为设计草案。
已确认 PostgreSQL、至少 10 用户并发、PDF 方案 B、PyMuPDF 与页/块区域定位；其余建议待评审。

| 阶段 | 文档 | 当前范围 |
| --- | --- | --- |
| 离线文档处理 | [设计草案](offline/02-design.md) | 文档身份、阶段契约、版本产物、执行与索引快照 |
| 在线检索 | [阶段边界](online/README.md) | 仅列出后续设计范围与离线交接要求 |
| 评测 | [阶段边界](evaluation/README.md) | 仅列出后续设计范围与版本绑定要求 |

离线阶段另有 [技术选型说明](offline/03-technology-options.md)：比较状态库、任务分发、缓存、事件流和产物存储。
结合可靠性与面试展示目标提出建议；PostgreSQL 已选定，Redis/Kafka 尚未选定。
另见 [多用户并发与批次进度](offline/04-concurrency.md)，区分用户并发、内部额度和完整流程验收。
开发遵循 [测试先行与评审流程](offline/01-tdd-plan.md)：用例按实际范围分批设计，评审通过后才能开发。
前期讨论见 [PDF parse 行为评审](offline/reviews/02-pdf-parse.md)。
[PDF parse 首批实施用例](offline/reviews/01-pdf-parse-cases.md) 已全部通过，56 个测试通过；[使用说明](offline/05-pdf-parse-usage.md) 包含调用和样本准备命令。
业务样本由用户后续补充，本轮不补；完整验证记录见 [测试结果](offline/reviews/pdf-parse/09-test-results.md)。
parse 版本产物存储仍待设计与评审；[chunk 既有草案](offline/reviews/03-chunk.md) 暂缓，不作为当前开发依据。

跨阶段术语见根目录 [GLOSSARY.md](../GLOSSARY.md)。
设计草案不代表已批准全部业务实现；实现范围逐步确定。
