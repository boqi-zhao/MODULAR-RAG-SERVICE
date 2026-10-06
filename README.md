# MODULAR-RAG-SERVICE

新建的独立 RAG 服务项目，计划采用 FastAPI，并支持阶段产物落盘、子阶段独立重跑和版本化测评。

当前仅完成项目初始化；尚未实现应用入口、HTTP 路由或业务逻辑。

已补充离线文档处理的设计草案，尚待评审；设计按离线文档处理、在线检索、评测三个阶段组织。
入口见 [设计文档](docs/README.md)，术语见 [GLOSSARY.md](GLOSSARY.md)。
另有 [离线技术选型说明](docs/offline/technology-options.md)，记录候选方案、取舍与验证场景。
已确定 PostgreSQL 为状态库，要求至少 10 用户同时使用，内部文档处理并发由服务配置。
口径见 [并发与批次进度设计](docs/offline/concurrency.md)；尚未安装数据库或实现并发能力。
当前实现规划仅覆盖 PDF；Markdown 和 QA 对 CSV 为后续需求，扩展边界见 [离线设计](docs/offline/design.md#32-格式扩展边界)。
采用 [TDD 与评审流程](docs/offline/tdd-plan.md)：先分批评审用例和输入输出，通过后先写测试再实现。

## 开发环境

- Python 3.12.11
- uv 管理虚拟环境及依赖，提交 `uv.lock` 保证依赖版本可复现。
- 基础依赖：FastAPI、Uvicorn。
- 开发依赖：pytest、HTTPX、Ruff。

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

添加测试后使用 `uv run pytest`；当前空测试目录执行 pytest 会提示没有测试。
尚无 ASGI 应用，因此当前没有服务启动命令。

## 目录

- `src/modular_rag_service/`：预留源码目录。
- `tests/`：预留测试目录。
- `docs/offline/`：离线文档处理设计草案。
- `docs/online/`：在线检索阶段边界，待详细设计。
- `docs/evaluation/`：评测阶段边界，待详细设计。
- `AGENTS.md`：协作约定。

## 参考项目

旧项目位于 `/Users/zhaoboqi/project/MODULAR-RAG-MCP-SERVER`。
参考其组件实现；新项目采用独立 Git、配置、依赖和运行数据。
