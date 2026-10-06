# 开发任务与交接

最后更新：2026-10-06。本文件跟踪开发进度；约束见 [AGENTS.md](AGENTS.md)，运行方法见 [README.md](README.md)。
接手顺序：先读上述两个文件，再读本文件，最后查看当前任务对应的设计和代码。
“已完成”表示已有代码和实际验证；需求评审、代码评审、Git 提交分别记录，不能相互替代。

## 当前停在哪里

- 当前推进离线 PDF 接入：上传文件 → 保存上传记录 → 提交后台解析；后续再做 chunk。
- T-07 提交为 `aa20f42`，T-08 提交为 `6971d95`；T-09/T-10 已实现、验证及用户评审通过，代码、测试和相关文档包含在本文件所在的提交中。
- 上传接口、上传记录表、ORM 与迁移方案已评审通过；T-09/T-10 完成后，下一步待评审的是 PDF 解析模块重写（T-11）。
- 用户要求一次只实现一个能讲清楚的小步骤，完成后展示代码和验证结果，再由用户决定下一步。
- 当前不采用 TDD；此前整套 PDF 解析实现与测试已按用户要求删除，不能从历史描述认定仍可用。

## 已实现并验证

| 编号 | 功能 | 代码或说明 |
| --- | --- | --- |
| T-01 | Python 3.12、uv、FastAPI 与检查工具初始化 | [依赖配置](pyproject.toml)、[锁定文件](uv.lock) |
| T-02 | FastAPI 入口、`GET /health`、Postman 健康检查请求 | [应用入口](src/api/main.py)、[接口说明](docs/offline/api/01-service-entry.md) |
| T-03 | 共用 logger、控制台及本地日志、10 个滚动备份、线程信息 | [日志模块](src/common/logger.py)、[日志说明](docs/offline/api/05-logging.md) |
| T-04 | 本地 Docker PostgreSQL、Psycopg 连接与独立检查命令 | [Compose](compose.yaml)、[连接模块](src/db/connection.py)、[说明](docs/offline/api/04-postgresql-connection.md) |
| T-05 | ORM 基类、连接引擎、Session、安装 SQLAlchemy 与 Alembic | [基类](src/db/base.py)、[Session](src/db/session.py)、[本步说明](docs/offline/api/08-orm-foundation.md) |
| T-06 | 2 个真实 PG 测试：提交/回滚、Session 独立及连接归还 | [测试文件](tests/test_orm_database.py) |
| T-07 | 上传记录表 ORM 模型、Alembic 配置与首次迁移 | [模型](src/db/models/document_upload.py)、[首次迁移](migrations/versions/e5690f23be74_create_document_uploads.py)、[空白约束修正](migrations/versions/608bbe966e57_fix_not_blank_constraints.py) |
| T-08 | 上传记录读写：短事务创建 uploading，条件更新为 uploaded/failed | [代码](src/db/upload_records.py)、[测试](tests/test_upload_records.py)、[记录方案](docs/offline/api/03-upload-records.md) |
| T-09 | 本地文件保存：分段写入、大小限制、SHA-256、独立临时文件发布（拒绝覆盖）与失败清理 | [代码](src/uploads/files.py)、[测试](tests/test_upload_files.py) |
| T-10 | `POST /documents` 多份上传：`files` 字段、逐份结果、份数与总大小限额 | [路由](src/api/documents.py)、[接口测试](tests/test_document_upload_api.py)、[Postman 请求](postman/collections/01-上传文档/upload.request.yaml) |

T-05～T-10 已提交；T-09/T-10 的实现、验证与用户评审均已通过。
2026-10-06 修复后复查通过：65 个测试无跳过，Ruff、格式及 diff 检查通过。独立临时文件与硬链接发布已解决顺序/并发覆盖问题；按上次出错的交错顺序补验，第一份成功、第二份拒绝覆盖，原始字节保持不变且临时文件清理完成。本轮未发现新的阻塞问题，agent review 通过，用户已同意提交。此前一次上传 3 份同名不同内容文件，编号、真实 PG 记录和磁盘字节均已验证独立。
Alembic 已配置，重复升级不重复建表。
最近实际验证：65 个测试通过（含多份混合成功/失败、全失败 400、限额 413、数据库不可用 503、同编号重复保存拒绝覆盖与并发交错保护）；Ruff 检查与格式检查通过；另启动服务混合上传 4 份（2 份真实样本成功、错名与假头各 1 份失败），逐份结果与磁盘 SHA-256 一致，份数超限整单 413。
T-08/T-09/T-10 复查：加载 `.env` 时 65 个测试通过，无跳过；未配置 `DATABASE_URL` 时 9 个通过、50 个跳过，无收集错误。
上传读写测试在未配置数据库时按整个模块跳过，因此跳过计数不等于其中的用例数；跳过不代表 PG 验证通过。
错误配置、连接不可达、密码不输出及导入不连接的检查已完成，详见 ORM 基础说明。
这些结果不代表 PDF 解析或 10 用户端到端并发已经验证。

## 接下来按顺序实现

T-09/T-10 已完成并通过用户评审；下一步为 T-11，具体实现仍需用户明确指示。

上述方案已通过需求评审；接手 agent 应先说明准备实现哪一个小步骤，再按用户指示推进。
`document_uploads` 表、上传模型、`alembic.ini` 与 `migrations/` 已存在；记录读写见 `src/db/upload_records.py`，文件保存见 `src/uploads/files.py`，接口见 `src/api/documents.py`；迁移命令见 README，不在 API 启动时自动迁移。

## 后续功能：尚未实现

- [ ] T-11 重写独立 PDF 解析模块：文本、图片、页码/区域、扫描风险、部分结果与诊断。
  首批 01～06 需求与用例已评审通过；见 [解析计划](docs/offline/05-pdf-parse-plan.md)。
- [ ] T-12 异步解析任务、独立 worker、任务状态查询；具体实现范围仍需分步确定。
- [ ] T-13 版本产物、完整输入输出、manifest、摘要核对与固定上游快照；细节待评审。
- [ ] T-14 Runner：依赖执行、单阶段重跑、下游重跑、失败恢复、强制执行；细节待评审。
- [ ] T-15 chunk 分块；必须等解析样本验收通过后再讨论方案，不提前固定策略。
- [ ] T-16 refine、enrich、caption、image_register；阶段粒度和依赖仍为草案。
- [ ] T-17 dense/sparse 编码、向量写入、BM25 构建与实验索引隔离；选型和契约待评审。
- [ ] T-18 批次任务、进度推送、多用户使用和完整流程 10 用户并发验收。
  用户并发和内部文档处理并发分别控制；见 [并发设计](docs/offline/04-concurrency.md)。
- [ ] T-19 上传中断后的自动恢复、用户认证与归属、文件/产物保留和清理策略；待评审。
- [ ] T-20 对象存储、Markdown 与 QA CSV 接入；仅保留扩展方向，本轮不实现。
- [ ] T-21 在线检索；目前只有 [阶段边界](docs/online/README.md)。
- [ ] T-22 评测；目前只有 [阶段边界](docs/evaluation/README.md)，不把解析回归当作业务效果评测。

Redis/Kafka 未选定；不要因为工业化目标直接引入。详细远期建议见 [路线图](docs/offline/design/08-roadmap.md)。

## 接手时先检查环境

项目路径：`/Users/zhaoboqi/project/MODULAR-RAG-SERVICE`；源码按功能直接放在 `src/`。
先启动 Docker Desktop；新机器从 `.env.example` 创建 `.env`，已有配置不要覆盖，凭据不提交 Git。
在项目根目录执行：

```sh
git status --short --branch
uv sync --locked
make db    # 启动 PostgreSQL 并升级结构
uv run --env-file .env python src/check_orm_database.py
make test
make lint
```

未加载数据库配置时测试会跳过，不能认定 PG 验证通过。启动 API 和 Postman 操作见 README；常用命令见 Makefile（`make api` 自动准备数据库并启动服务）。
本机保留 20 页 DocLayNet PDF/JSON 和 9 份控制 PDF，位于 `data/samples/`，不随 Git 克隆。
`.env`、日志、PDF 样本及数据库数据卷均为本机资源；切换机器时需单独准备，不能复制旧项目凭据或运行数据。

## 提交与维护

本次交接基线：`master`；T-07 为 `aa20f42`，T-08 为 `6971d95`，已推送远端。
T-09/T-10 代码、测试、Postman 请求、Makefile、依赖与相关文档包含在本文件所在的提交中，编号用 `git log -1 --oneline` 查看；本次仅本地提交，尚未推送。
切换账号并沿用当前目录可保留工作区；仅从远端克隆无法获得未推送提交，需先妥善保存。
每步开发完成、需求变化、用户评审或提交后，同步更新本文件的状态、下一步、验证证据和提交基线。
新任务使用新编号，保留既有编号；已验证结果不写成待办，尚未验证或只安装依赖的功能不标完成。
本文件保持简短且不超过 200 行；功能细节放对应 docs 文档，历史过程交给 Git 记录。
