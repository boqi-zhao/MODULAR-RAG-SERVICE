# 开发任务与交接

最后更新：2026-10-07。协作规则见 [AGENTS.md](AGENTS.md)，启动见 [README.md](README.md)，主题文档见 [离线入口](docs/offline/README.md)。
需求通过、实现、验证、用户代码评审和提交分别记录，不能互相替代。

## 当前停点

文档已整理/复核；上传 service 的 Pydantic 已补齐、验证，按用户授权单独提交为 `cd09455`，已推送；不推进解析接口、存储或 Runner。
离线文档从 50 份/2258 行收敛为 7 份当前主题文档，旧解析与分块提案压缩到 [历史区](docs/history/offline/README.md)。
整理前真实工作区（含未提交文档）备份于 `data/history/offline-docs-20261007-155755/before.tar.gz`，附摘要清单，不随 Git 克隆。
文档复核和模型补齐的验证见下方；本次按用户授权单独提交文档整理，解析代码、依赖和测试保留在工作区。

T-11 当前是旧基线独立解析和工作目录快照：MarkItDown 文字、PyMuPDF 原编码图片、`[IMAGE: 图片ID]`。
代码已实现、验证，仍待用户代码评审。入口 [parse_pdf](src/pdf/service.py)，完整说明见 [02 PDF 解析](docs/offline/02-pdf-parse.md)。
正式 artifact_id、固定上游、文件摘要清单、执行尝试、成功标记和复用校验尚未实现，不能标记完整 Stage 已交付。

下一步继续 review 解析代码，再按用户指示评审正式保存/读回契约或后续接口；chunk 暂缓。
产物与策略重跑基本要求已通过，具体存储/身份/Runner 方案仍待评审，见 [03](docs/offline/03-stage-artifacts.md)、[04](docs/offline/04-execution.md)。
解析快照的现有新进程读回不等于正式产物完整性/复用验收；接入正常流水线前须先补齐 Stage 交接。

## 已实现功能

| 编号 | 功能 | 状态/代码 |
| --- | --- | --- |
| T-01 | Python 3.12、uv、FastAPI、检查工具 | 已实现，[pyproject.toml](pyproject.toml) / uv.lock |
| T-02 | 应用入口、GET /health、Postman | 已实现及实际 HTTP 验证，[main.py](src/api/main.py) |
| T-03 | 统一 logger、控制台/本地滚动、多进程协调 | 已实现及运行验证，[logger.py](src/common/logger.py) |
| T-04 | Docker PostgreSQL、驱动连接检查 | 已实现及真实连接验证，[connection.py](src/db/connection.py) |
| T-05 / T-06 | ORM、Session 与提交/回滚测试 | 已实现及真实 PG 验证，[session.py](src/db/session.py) |
| T-07 | 上传表和两个 Alembic 迁移 | 已实现、评审、提交，[模型](src/db/models/document_upload.py) / migrations/ |
| T-08 | 创建上传记录与条件结束更新 | 已实现、评审、提交，[upload_records.py](src/db/upload_records.py) |
| T-09 | 分段保存、摘要、限额、原子拒绝覆盖 | 已实现、评审、提交，[files.py](src/uploads/files.py) |
| T-10 | 多文件上传、逐份结果、router/service、Pydantic | 已实现、评审、提交，[documents.py](src/api/documents.py) / [service.py](src/uploads/service.py) |

上传行为、表字段、事务/故障边界只维护在 [01 文档上传](docs/offline/01-upload.md)，运行/迁移/日志见 [06](docs/offline/06-local-runtime.md)。
规范差距已补齐：[UploadBatchResult](src/uploads/schemas.py) 从 service 的 dataclass 改为 Pydantic；校验逐项结构、成功数与结果一致、数据库错误数不超过失败数。文件流输入 UploadInput 保留普通 dataclass，HTTP 字段和状态码不变；本步已单独提交 `cd09455`。

## 最近验证与评审

- 解析实现轮次：新解析 13 个检查；加载 .env 后全套 85 个通过、无跳过（既有 72 + 解析 13）；Ruff/格式/diff 通过。
- 检查原 JPEG 字节、ID/占位符偏移、图片开关、拒绝覆盖、新进程读回和受控故障；没有新旧效果指标对比。
- 初次 12 通过、1 失败：坏输入被 MarkItDown 接受，错误测试假设已改为转换故障注入，未增加生产拒绝分支。
- 中文两页 CLI 样本与快照位于 `data/checks/pdf-mvp-review/`，两张 JPEG/占位符，诊断为空；未重跑 29 份固定语料。
- 历史 A/B/C 和固定报告不作为当前方案证据，见 [历史摘要](docs/history/offline/01-pdf-history.md)；旧代码备份 `data/history/pdf-pymupdf-pre-mvp/`。
- 当前策略详见 [决策 04](docs/decisions/04-mvp-original-pdf-strategy.md)；原始定位/扫描方案已被最新决定替代，产物/重跑约束继续有效。
- 文档整理轮次：已核对当前代码、合并重复/纠正过时状态；行数、本地链接/锚点、引用和 Ruff/格式/diff 检查通过。未重跑业务测试，85 是此前实现轮次结果。
- 前一轮两文件复核：去除重复进度/测试数和失效引用，保留 Stage、通用解析、旧策略和独立决策要求；文档及静态检查通过，该轮未改业务代码。
- 本次 Pydantic 补齐：新增 8 个模型边界检查，真实 PG 的 service 测试核对返回类型；加载 .env 后全套 93 个通过、无跳过（85 + 8），Ruff/格式/diff 和文档链接/行数检查通过。验证 JSON 读回、类型/额外字段/嵌套结果/计数拒绝及 HTTP 行为；6 项依赖警告保留，未屏蔽。
- 单独提交验证：暂存快照在临时目录中运行真实 PG 测试，80 个通过、无跳过（原上传等 72 + 本步 8），Ruff/格式通过。工作区 93 包含 13 个未提交 PDF 用例，本次提交不包含它们；93 不能当作仅本次提交的验证数量。
- 本次文档提交：22 份 Markdown 均不超过 200 行，139 个本地链接/锚点检查通过，历史样本 JSON 与原文件字节一致，diff 检查通过；未重跑业务测试。解析源码链接对应本机未提交代码，单独克隆本次提交不包含解析实现。

## 后续任务

- [ ] T-11 独立 PDF 解析及正式交接：核心/快照已实现验证，代码待 review，Stage 交接未完成。
- [ ] T-12 异步解析、独立 worker、任务状态查询。
- [ ] T-13 正式版本产物、完整输入输出、manifest、摘要/读回与固定上游。
- [ ] T-14 Runner：单阶段/下游重跑、失败恢复、强制执行。
- [ ] T-15 chunk：解析 review/验收后再讨论，优先参考旧策略。
- [ ] T-16 refine、enrich、caption、image_register：粒度/依赖草案。
- [ ] T-17 dense/sparse、向量/BM25、语料和索引隔离。
- [ ] T-18 批次进度、多用户、完整流程 10 用户验收，内部并发独立设置。
- [ ] T-19 上传自动恢复、认证归属、保留与清理。
- [ ] T-20 对象存储、Markdown/QA CSV 接入。
- [ ] T-21 在线检索；[阶段边界](docs/online/README.md)。
- [ ] T-22 评测；[阶段边界](docs/evaluation/README.md)，不以解析回归代替业务评测。

后续细节集中 [05 后续范围](docs/offline/05-future-scope.md)；PostgreSQL 已确定，Redis/Kafka/索引后端未选。

## 提交与本机环境

2026-10-07 上次“对齐”已将本地和远端同步至 `cd09455`；本次文档整理单独提交，不推送，实际提交号与领先/落后以 Git 为准。
T-07 `aa20f42`、T-08 `6971d95`、上传 `46b4c9a`、分层 `936c2e6`、Pydantic `d0f6bd0` 已在远端 master。
协作/决策 `9fd1be1`、通用文档 `92b4616`、批次模型补齐 `cd09455` 已正常推送到远端 master；本次新增文档提交，不改写历史。
本次文档提交包含 AGENTS.md、README.md、TASKS.md、离线主题/历史归档、关联决策及入口链接。解析代码、依赖、测试和两个数据库模块的文档字符串改动均未提交；用户面试专用目录不纳入提交。
`.env`、logs、data/samples、数据库卷和本机备份不随克隆；保留现有配置，不复制旧项目凭据/数据。
接手先读 AGENTS → README → TASKS，再核对 Git/代码；启动与命令只维护在 [06](docs/offline/06-local-runtime.md)。
