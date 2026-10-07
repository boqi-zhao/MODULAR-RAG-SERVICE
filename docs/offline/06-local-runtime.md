# 本地运行与检查

在项目根目录执行，使用 Python 3.12 和 uv；新机器先启动 Docker Desktop，从 `.env.example` 创建 `.env`，不要覆盖已有配置。
本机凭据、样本、日志和数据库数据不随 Git 克隆；不要复制旧项目运行数据。

## 常用命令

```sh
uv sync --locked
make db       # 启动 PostgreSQL，并执行 Alembic upgrade head
make api      # 准备数据库后启动 API，默认 8080；换端口用 PORT=8000
make test     # 加载 .env，运行包含真实 PG 的测试
make lint     # Ruff 和格式检查
```

`GET /health` 返回 200 与 `{"status":"ok"}`，只说明接口能响应，不证明数据库/解析任务正常。
`http://127.0.0.1:8080/docs` 可试用接口；Postman 选 `local` 环境，上传使用同名 `files` 多行。
完整上传行为见 [01](01-upload.md)，独立解析命令见 [02](02-pdf-parse.md)。

## PostgreSQL、ORM 和迁移

本地容器固定 `18.6-bookworm`，只绑定 `127.0.0.1:5432`，数据保存于 `postgres_data` 卷。
Compose 读取 .env；Python 通过 uv 的 `--env-file .env` 获取 DATABASE_URL，模块不自动读取 .env。
初始化后改 .env 密码不会自动改数据库账号。停止用 `docker compose stop postgres`，不要把删除数据卷当普通停止。

```sh
uv run --env-file .env python src/check_database.py
uv run --env-file .env python src/check_orm_database.py
uv run --env-file .env alembic current
uv run --env-file .env alembic upgrade head
```

[connection.py](../../src/db/connection.py) 读取/校验地址，Psycopg 连接超时 5 秒；[session.py](../../src/db/session.py) 定义引擎和 SessionFactory。
导入配置引擎，不立即连接；实际查询才连接。每次操作用独立 Session，正常提交、异常回滚、退出归还连接。
同步 ORM 放普通 def 路由/线程池；每进程池上限 5、不扩容，等待 30 秒，取出时检查连接，不能当成多用户吞吐量结论。
接收文件期间不持有长事务，创建与结束上传分别短事务；多进程总连接预算后续评审。

ORM 模型是代码期望结构，Alembic 是结构升级记录；不在应用启动时 create_all 或自动迁移，make db 是明确执行入口。
现有迁移：`e5690f23be74` 建上传表、`608bbe966e57` 修正 Unicode 空白约束。
后一迁移用 NOT VALID 保留旧记录、新写入受限；历史已执行迁移不修改，新变化新增迁移并人工核对生成草稿。
连接地址从环境获取，不写入 alembic.ini；首次迁移降级会删表，不能用来恢复数据。
迁移往返检查使用独立测试库，地址通过 config.attributes 传入，避免密码中特殊字符触发 INI 插值。

## 日志与验证边界

[logging.ini](../../config/logging.ini) 统一配置；业务模块导入 `from common.logger import logger`，首次自动初始化，不重复配置或 print。
控制台与项目绝对定位的 `logs/service.log` 同步输出，含线程名称/ID、模块/行号；线程不是用户身份。
concurrent-log-handler 协调本机多进程，10 MiB 滚动、保留 `.1`～`.10`；重启追加，修改配置需重启，真实日志不入 Git。
历史运行检查验证过双进程完整写入/滚动、重复导入和从其他目录导入；多机集中收集尚未设计。

运行 `uv run --env-file .env pytest -q` 才包含 PG 验证；未配置时跳过不能算通过。
最新验证数量、范围和对应轮次只维护在 [TASKS.md](../../TASKS.md)；未测试的文档整理不能当成本轮业务验证。
SWIG/Starlette 依赖警告保留，未屏蔽。PG 锁行为用真实 PG、解析用已知输入，模拟错误与真实样本分别记录。
每次先说明一个小步骤，用户指示实现后再编码、验证、讲解并等待评审；详细协作规则只维护在 [AGENTS.md](../../AGENTS.md)。
