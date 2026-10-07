# 设计文档

设计按三个大阶段组织；各阶段的设计与实现进度分别记录。
开发完成项、待办与当前停点统一见根目录 [TASKS.md](../TASKS.md)。
每次技术选型与调优实验独立记录在 [技术选型与调优目录](decisions/README.md)，保留决策、证据与面试讲述。
原 PDF 解析实现已删除，准备根据文档分步重写；已实现健康检查、PDF 上传、原文件保存与 PG 上传记录。
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
当前从接口层逐步开始；[第一步：服务入口与健康检查](offline/api/01-service-entry.md) 已实现，用户已通过 Postman 验证。
已实现 [PDF 上传接口](offline/api/02-document-upload.md)：原文件先保存本地，[上传记录写入 PG](offline/api/03-upload-records.md)，后续再异步解析。
上传接口与记录方案已评审通过；[本地 PG 接入](offline/api/04-postgresql-connection.md) 已完成连接验证，存储桶记为 TODO。
[上传记录表设计](offline/api/06-upload-table.md) 和 [SQLAlchemy 与 Alembic](offline/api/07-orm-migrations.md) 接入方案已通过评审。
已实现并验证 [ORM 基础](offline/api/08-orm-foundation.md)、上传模型、两个迁移及 [记录读写](offline/api/03-upload-records.md)。
T-08～T-10 已实现、验证并通过用户评审；下一步为 T-11，见 [解析计划](offline/05-pdf-parse-plan.md)。
已补充 [日志基础](offline/api/05-logging.md)，统一控制台和本地 `logs/` 文件输出。
[PDF parse 首批需求与用例](offline/reviews/01-pdf-parse-cases.md) 已评审通过，保留为重写依据；后续安排见 [解析计划](offline/05-pdf-parse-plan.md)。
业务样本由用户后续补充，本轮不补；当前代码与样本情况见 [实现状态](offline/reviews/pdf-parse/09-implementation-status.md)。
parse 版本产物存储仍待设计与评审；[chunk 既有草案](offline/reviews/03-chunk.md) 暂缓，不作为当前开发依据。

跨阶段术语见根目录 [GLOSSARY.md](../GLOSSARY.md)。
设计草案不代表已批准全部业务实现；实现范围逐步确定。
