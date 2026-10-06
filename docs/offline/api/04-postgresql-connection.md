# 小步骤：本地 PostgreSQL 与 Python 连接

状态：PG 接入已实现并完成实际连接验证，待用户评审代码；尚未建上传记录表或实现上传接口。

## 这一步有哪些文件

- 根目录 `compose.yaml`：启动一个 PostgreSQL 容器，版本固定为 `18.6-bookworm`。
- 根目录 `.env.example`：本地数据库的账号、数据库名称、端口和 Python 连接地址示例。
- 本机 `.env`：实际使用的配置，已被 Git 忽略；本轮已从示例创建。
- `src/db/connection.py`：创建数据库连接；不包含日志配置或命令入口。
- `src/check_database.py`：独立连接检查入口，导入共用 logger 后记录检查结果。
- `src/common/logger.py`：集中初始化日志，各模块直接导入使用。
- `pyproject.toml`、`uv.lock`：新增并锁定 `psycopg[binary]` 驱动，当前版本 3.3.6。

Psycopg 是 Python 与 PostgreSQL 通信的驱动。现阶段用直接连接讲清数据库操作；连接池随接口接入再讨论。

## 启动和检查

在项目根目录运行；先确保 Docker Desktop 已启动。
其他机器第一次使用时，将 `.env.example` 复制成 `.env`；不要覆盖已有配置。

```sh
docker compose up -d --wait postgres
uv run --env-file .env python src/check_database.py
```

连接成功时输出 INFO 日志：`PostgreSQL connection successful: modular_rag`。
统一日志配置及 `logs/` 文件位置见 [日志说明](05-logging.md)。
`--env-file .env` 让 uv 把文件中的配置传给 Python；模块本身不自动读取配置文件。
Compose 会读取根目录的 `.env`，Python 则使用其中的 `DATABASE_URL`。
示例中账号、密码或端口改变时，两处对应配置要一起更新。
数据库初始化后，修改 `.env` 中的密码不会自动修改已有数据库账号，须另行执行账号变更。

## 连接代码怎么执行

1. 调用 `get_connection()`，从环境变量读取 `DATABASE_URL`。
2. 缺少配置时立即报错；有配置时用 Psycopg 连接，连接超时设置为 5 秒。
3. 检查入口导入共用 logger，用 `with` 包住连接，查询当前数据库名称。
4. 离开 `with` 时，正常操作提交事务，异常操作回滚，并关闭连接；成功记录 INFO，失败记录 ERROR 并退出。

仅导入模块不会连接 PG；当前同步连接还未接入 FastAPI，不在异步路由中直接执行阻塞数据库操作。
检查入口不输出完整连接地址或底层错误，避免打印密码；本步不会建表或写入业务记录。

## 数据保存与停止

数据库端口只绑定本机 `127.0.0.1:5432`。
数据保存在项目专属的 Docker 数据卷 `postgres_data`，不是容器的临时文件层。
停止数据库：`docker compose stop postgres`；再次运行启动命令即可恢复。
默认移除容器时仍保留数据卷；删除数据卷会删除数据库内容，本步不执行删除操作。

## 验证记录

- 容器 `modular-rag-service-postgres-1` 为 healthy，实际服务版本为 PostgreSQL 18.6。
- 检查命令成功查询 `modular_rag`，离开 `with` 后连接已关闭。
- 缺少配置、端口不可达时检查入口退出码为 1，未误报成功、未输出测试密码。
- Compose 配置检查、`uv sync --locked`、Ruff 代码与格式检查通过。
- 本步没有新增自动测试文件；以上为真实数据库与独立子进程检查。
- 本机 PG 容器保留运行，方便用户自行验证；上传、任务调度与 10 用户并发尚未实现。

依据：[PostgreSQL 官方镜像说明](https://github.com/docker-library/docs/blob/master/postgres/README.md)、
[Psycopg 连接与事务说明](https://www.psycopg.org/psycopg3/docs/basic/usage.html)。
