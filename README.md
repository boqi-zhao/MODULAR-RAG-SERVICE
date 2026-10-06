# MODULAR-RAG-SERVICE

新建的独立 RAG 服务项目，计划采用 FastAPI，并支持阶段产物落盘、子阶段独立重跑和版本化测评。

原 PDF 解析代码与测试已按用户要求删除，准备根据文档分步重写。
当前已实现 FastAPI 应用入口和 `GET /health`；PDF 上传与解析接口尚未实现。

设计按离线文档处理、在线检索、评测三个阶段组织；首批解析用例已通过，其余范围分批评审。
入口见 [设计文档](docs/README.md)，术语见 [GLOSSARY.md](GLOSSARY.md)。
另有 [离线技术选型说明](docs/offline/03-technology-options.md)，记录候选方案、取舍与验证场景。
已确定 PostgreSQL 为状态库，要求至少 10 用户同时使用，内部文档处理并发由服务配置。
口径见 [并发与批次进度设计](docs/offline/04-concurrency.md)；尚未安装数据库或实现并发能力。
当前实现规划仅覆盖 PDF；Markdown 和 QA 对 CSV 为后续需求，扩展边界见 [离线设计](docs/offline/design/04-formats.md)。
首批 PDF 已选方案 B：文本定位与嵌入图片提取；OCR、结构化表格和复杂版面留待后续。
解析库已选 PyMuPDF，定位到页码和文本块/图片矩形区域；重写时再添加依赖并锁定版本。
采用 [分步开发与讲解流程](docs/offline/01-development-flow.md)：先解释逻辑，用户指示开始后每次实现一个小步骤；不采用 TDD。
已准备 20 页 DocLayNet PDF/JSON 和 9 份控制 PDF；[首批 parse 需求与用例](docs/offline/reviews/01-pdf-parse-cases.md) 已评审通过，保留为重写依据。
后续安排见 [解析重写计划](docs/offline/05-pdf-parse-plan.md)，当前状态见 [实现状态](docs/offline/reviews/pdf-parse/09-implementation-status.md)。
当前先推进 parse，chunk 暂缓；业务 PDF 由用户后续补充，解析回归不等于网管告警业务效果评测。

## 开发环境

- Python 3.12.11
- uv 管理虚拟环境及依赖，提交 `uv.lock` 保证依赖版本可复现。
- 基础依赖：FastAPI、Uvicorn、concurrent-log-handler（协调日志文件写入）。
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

当前没有自动测试；运行 `uv run pytest` 会提示未收集到测试，不能视为验证通过。
公开样本与已生成控制 PDF 保留在忽略的 `data/` 下；原生成脚本已删除。

## 启动与调用

在项目根目录启动服务：

```sh
uv run uvicorn api.main:app --app-dir src --host 127.0.0.1 --port 8080
```

另开一个终端调用：

```sh
curl http://127.0.0.1:8080/health
```

返回 HTTP 200 和 `{"status":"ok"}`，说明服务能够响应请求。
浏览器打开 `http://127.0.0.1:8080/docs`，可以查看并试用接口；按 Ctrl+C 停止服务。
这个检查尚不涉及数据库或 PDF 处理，范围见 [第一步接口说明](docs/offline/api/01-service-entry.md)。

Postman 请求保存在 `postman/`，项目关联配置保存在 `.postman/`。
在 Postman 的项目本地视图中选择 `local` 环境，再发送 `00-健康检查` 下的 `health` 请求。
环境变量 `url` 默认指向 `http://127.0.0.1:8080`；改端口时须与服务启动命令保持一致。

## 日志

日志统一配置在 `config/logging.ini`，同时输出到控制台与 `logs/service.log`，包含线程名称和线程 ID。
各模块使用 `from common.logger import logger`；首次导入自动初始化，启动服务无需 `--log-config`。
单个文件上限 10 MiB，保留 10 个编号备份；实际日志不提交 Git，详见 [日志说明](docs/offline/api/05-logging.md)。

## 目录

- `src/api/`：FastAPI 应用入口与 HTTP 路由；源码直接按功能组织。
- `src/common/`：共用日志模块。
- `tests/`：占位，后续按需要补充验证。
- `docs/offline/`：离线文档处理设计草案。
- `docs/online/`：在线检索阶段边界，待详细设计。
- `docs/evaluation/`：评测阶段边界，待详细设计。
- `AGENTS.md`：协作约定。

## 参考项目

旧项目位于 `/Users/zhaoboqi/project/MODULAR-RAG-MCP-SERVER`。
参考其组件实现；新项目采用独立 Git、配置、依赖和运行数据。
