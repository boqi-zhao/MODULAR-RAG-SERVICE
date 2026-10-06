# ORM 基础实现

状态：ORM 基础已实现、通过真实 PG 验证并提交；上传模型与两个迁移已实现，见 [上传表设计](06-upload-table.md)。

## 三个入口怎么用

| 入口 | 用途 |
| --- | --- |
| `src/db/base.py` 中的 `Base` | 后续 ORM 模型继承它，共用表结构信息和约束命名规则 |
| `src/db/session.py` 中的 `engine` | 管理本进程的连接池，实际查询时才创建数据库连接 |
| `src/db/session.py` 中的 `SessionFactory` | 每次调用创建独立 Session，管理一小段数据库操作 |

原始驱动和 ORM 共用 `src/db/connection.py` 的配置读取入口。
导入 `db.session` 前要加载 `DATABASE_URL`；导入只配置引擎，不查询数据库、不建表。
已锁定 SQLAlchemy 2.1.3、Alembic 1.20.0；Alembic 配置及两个迁移已实现。

## Session 怎样提交和回滚

独立脚本或后续同步业务模块可以这样使用：

```python
from sqlalchemy import text
from db.session import SessionFactory

# 正常结束时提交；发生异常时回滚；退出后关闭 Session，将连接归还池中。
with SessionFactory.begin() as session:
    database_name = session.execute(text("SELECT current_database()")).scalar_one()
```

每次数据库操作使用自己的 Session；不同请求和线程不能共用它。
接收 PDF 前先完成创建记录的事务，文件接收完成后再开另一个事务更新结果。
这两段记录操作已在 `src/db/upload_records.py` 实现；以上代码只展示连接与事务用法，本地文件保存仍待实现。
服务引擎持续复用；独立检查脚本退出前调用 `engine.dispose()`，释放连接池。

## 当前连接池设置

每个进程最多使用 5 个连接，不额外扩容；连接全部占用时最多等待 30 秒。
建立新连接最多等待 5 秒；取出池中的连接时先检查是否仍可用。
这些是本步开发配置，接口接入时再确定配置项和多进程的总连接预算。
5 个数据库连接不等于只能有 5 个用户：用户上传文件时不应一直占数据库连接。
10 用户完整流程并发尚未验证，不能把连接池上限或本步测试当成压测结果。
数据库操作使用同步 ORM，后续放入普通 `def` 路由或线程池，避免阻塞异步路由。

## 检查命令与实际结果

在项目根目录执行，先确保本地 PG 正常运行：

```sh
uv run --env-file .env python src/check_orm_database.py
uv run --env-file .env pytest -q
uv run ruff check .
uv run ruff format --check .
```

- ORM 检查成功查询 `modular_rag`，使用统一日志输出结果。
- 2 个真实 PG 测试通过：正常写入提交、异常写入回滚；两个 Session 独立使用连接。
- 测试只写数据库临时表，释放连接后清除；未创建正式业务表或保留验证数据。
- 缺少配置、地址格式错误、错误数据库类型、连接不可达均明确失败，未输出测试密码。
- URL 转换保留编码密码中的特殊字符；导入引擎时未建立实际连接。
- 未加载 `DATABASE_URL` 时，这 2 个 PG 测试会跳过；跳过不代表真实数据库验证通过。

设计依据见 [ORM 与迁移方案](07-orm-migrations.md)；记录读写已通过 agent 复查，下一小步是本地文件保存（T-09）。
