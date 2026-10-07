# MODULAR-RAG-SERVICE

新建的独立 RAG 服务项目，计划采用 FastAPI，并支持阶段产物落盘、子阶段独立重跑和版本化测评。

首个 MVP 已实现 MarkItDown 文字、PyMuPDF 图片和 `[IMAGE: 图片ID]`，用户代码评审已通过；入口、调用与范围见 [PDF 解析](docs/offline/02-pdf-parse.md)。文字、图片和 JSON 快照已落盘；正式版本产物、复用和 Runner 尚未实现。
当前已实现 `GET /health` 与 `POST /documents` 上传接口（本地保存原文件 + PostgreSQL 上传记录）；PDF 解析接口尚未实现。

开发接手请先阅读 [协作约定](AGENTS.md) 和 [任务进度与下一步](TASKS.md)，再查看相关设计与代码。

文档按主题阅读：[离线入口](docs/offline/README.md) / [在线边界](docs/online/README.md) / [评测边界](docs/evaluation/README.md)，术语见 [GLOSSARY.md](GLOSSARY.md)。
每个 Stage 落盘、可追溯、可复用，以及调整策略后从指定阶段重跑，是已确认要求；具体存储与执行仍分批评审。
MVP 优先沿用旧业务策略，精准定位、OCR 和复杂结构后置；每次选型/调优的详细记录见 [decisions](docs/decisions/README.md)。
独立解析与快照已评审通过，下一步等待用户指定；chunk 暂缓，后续并发、索引和格式规划按需查看 [后续范围](docs/offline/05-future-scope.md)。

## 开发环境

- Python 3.12.11
- uv 管理虚拟环境及依赖，提交 `uv.lock` 保证依赖版本可复现。
- 基础依赖：FastAPI、Pydantic（结构化数据校验）、Uvicorn、Psycopg（PostgreSQL 驱动）、concurrent-log-handler（协调日志文件写入）。
- 数据库工程化：SQLAlchemy ORM、Alembic；ORM 基础、上传记录表、两个迁移、记录读写与上传接口已实现。
- 开发依赖：pytest、HTTPX、Ruff；后续按实际需要添加其他依赖。

```sh
cd '/Users/zhaoboqi/project/MODULAR-RAG-SERVICE'
uv sync --locked
source .venv/bin/activate
```

也可以使用 `uv run`，无需先激活虚拟环境：

```sh
uv run python --version
uv run ruff check .
uv run ruff format --check .
```

已有迁移、记录读写、文件保存、上传接口及旧方案 MVP 解析测试，使用真实 PG：`uv run --env-file .env pytest -q`；最新结果统一见 [TASKS.md](TASKS.md)。
未提供数据库配置时测试会跳过；正式 Stage 版本存储与复用尚未完成，扫描规则不纳入首个 MVP。
公开样本与已生成控制 PDF 保留在忽略的 `data/` 下；原生成脚本已删除。

## 启动与调用

在项目根目录启动服务：

```sh
make api            # 自动启动 PostgreSQL、升级结构并启动 Uvicorn（默认 8080）
make api PORT=8000  # 换端口；Postman 环境的 url 须同步修改
```

等价的手工命令见 Makefile；另开一个终端调用：

```sh
curl http://127.0.0.1:8080/health
curl -F "files=@data/samples/pdf-controls/01-multilingual.pdf" \
     -F "files=@data/samples/pdf-controls/02-repeated-images.pdf" \
     http://127.0.0.1:8080/documents
```

返回 HTTP 200 和 `{"status":"ok"}`，说明服务能够响应请求。
上传命令返回 HTTP 201 和逐份结果 `succeeded`/`failed`/`documents`；一次最多 10 份、单份 20 MiB、单次总大小 100 MiB，见 [上传接口说明](docs/offline/01-upload.md)。
浏览器打开 `http://127.0.0.1:8080/docs`，可以查看并试用接口；按 Ctrl+C 停止服务。

Postman 请求保存在 `postman/`，项目关联配置保存在 `.postman/`。
在 Postman 的项目本地视图中选择 `local` 环境，再发送 `00-健康检查` 下的 `health` 请求。
上传用 `01-上传文档` 下的 `upload` 请求：Body 选 form-data，字段名 `files`；需要多份时添加多行同名 `files`，每行选一个文件。
环境变量 `url` 默认指向 `http://127.0.0.1:8080`；改端口时须与服务启动命令保持一致。

## 本地 PostgreSQL

当前已实现驱动连接、ORM、上传表/读写和独立 PDF 解析；解析 HTTP 接口尚未实现。
本机 `.env` 已创建且不提交 Git；其他机器首次使用时从 `.env.example` 复制配置。
先启动 Docker Desktop，再在项目根目录运行：

```sh
docker compose up -d --wait postgres
uv run --env-file .env python src/check_database.py
uv run --env-file .env python src/check_orm_database.py
uv run --env-file .env alembic upgrade head  # 建表或升级结构，重复执行安全
uv run --env-file .env alembic current       # 查看数据库当前迁移版本
```

成功时输出 INFO 日志：`PostgreSQL connection successful: modular_rag`。
ORM 检查输出 `ORM connection successful: modular_rag`，代码与事务用法见 [ORM 基础](docs/offline/06-local-runtime.md)。
数据库端口为 `127.0.0.1:5432`，数据保存在 Docker 数据卷中。
停止命令：`docker compose stop postgres`；详细配置与代码逻辑见 [PG 接入说明](docs/offline/06-local-runtime.md)。

## 日志

日志统一配置在 `config/logging.ini`，同时输出到控制台与 `logs/service.log`，包含线程名称和线程 ID。
各模块使用 `from common.logger import logger`；首次导入自动初始化，启动服务无需 `--log-config`。
单个文件上限 10 MiB，保留 10 个编号备份；实际日志不提交 Git，详见 [日志说明](docs/offline/06-local-runtime.md)。

## 目录

- `src/pdf/`：parse_pdf 独立解析；MarkItDown 文字、PyMuPDF 原编码图片、占位符与工作目录快照。
- `src/api/`：FastAPI 应用入口与上传路由。
- `src/db/`：PostgreSQL 连接、ORM 基类、Session、上传记录模型与读写模块。
- `src/uploads/`：`service.py` 编排上传业务；`files.py` 保存文件；`schemas.py` 定义 Pydantic 结果模型。
- `migrations/`：Alembic 迁移脚本；创建 `document_uploads` 表及升级空白约束。
- `alembic.ini`：迁移工具配置；连接地址从环境变量读取，不写密码。
- `Makefile`：常用命令快捷方式（`make api/db/migrate/test/lint`）。
- `src/common/`：共用日志模块。
- `src/check_database.py`：独立数据库连接检查入口。
- `src/check_orm_database.py`：独立 ORM 连接检查入口。
- `tests/`：原有 PG/磁盘/上传验证；test_pdf_parse.py 检查旧方案 MVP 文字、图片、快照与故障降级。
- `docs/offline/`：当前主题文档；历史方案另见 `docs/history/offline/`。
- `docs/online/`：在线检索阶段边界，待详细设计。
- `docs/evaluation/`：评测阶段边界，待详细设计。
- `AGENTS.md`：协作约定。

## 参考项目

旧项目位于 `/Users/zhaoboqi/project/MODULAR-RAG-MCP-SERVER`。
参考其组件实现；新项目采用独立 Git、配置、依赖和运行数据。
