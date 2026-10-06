# 设计文档

设计按三个大阶段组织；各阶段的设计与实现进度分别记录。
原 PDF 解析实现已删除，准备根据文档分步重写；当前没有业务代码或 HTTP 接口。
已确认 PostgreSQL、至少 10 用户并发、PDF 方案 B、PyMuPDF 与页/块区域定位；其余建议待评审。

| 阶段 | 文档 | 当前范围 |
| --- | --- | --- |
| 离线文档处理 | [设计草案](offline/02-design.md) | 文档身份、阶段契约、版本产物、执行与索引快照 |
| 在线检索 | [阶段边界](online/README.md) | 仅列出后续设计范围与离线交接要求 |
| 评测 | [阶段边界](evaluation/README.md) | 仅列出后续设计范围与版本绑定要求 |

离线阶段另有 [技术选型说明](offline/03-technology-options.md)：比较状态库、任务分发、缓存、事件流和产物存储。
结合可靠性与面试展示目标提出建议；PostgreSQL 已选定，Redis/Kafka 尚未选定。
另见 [多用户并发与批次进度](offline/04-concurrency.md)，区分用户并发、内部额度和完整流程验收。
开发遵循 [分步开发与讲解流程](offline/01-development-flow.md)：不采用 TDD，先解释逻辑，用户指示开始后每次实现一个小步骤。
前期讨论见 [PDF parse 行为评审](offline/reviews/02-pdf-parse.md)。
[PDF parse 首批需求与用例](offline/reviews/01-pdf-parse-cases.md) 已评审通过，保留为重写依据；后续安排见 [解析计划](offline/05-pdf-parse-plan.md)。
业务样本由用户后续补充，本轮不补；当前代码与样本情况见 [实现状态](offline/reviews/pdf-parse/09-implementation-status.md)。
parse 版本产物存储仍待设计与评审；[chunk 既有草案](offline/reviews/03-chunk.md) 暂缓，不作为当前开发依据。

跨阶段术语见根目录 [GLOSSARY.md](../GLOSSARY.md)。
设计草案不代表已批准全部业务实现；实现范围逐步确定。
