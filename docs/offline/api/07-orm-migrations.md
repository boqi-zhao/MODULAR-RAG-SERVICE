# ORM 与数据库表迁移

状态：SQLAlchemy + Alembic 接入设计已评审通过。
已安装依赖并实现 [ORM 基础](08-orm-foundation.md)；上传模型、Alembic 配置和首次迁移尚未实现。

## 三个组件各做什么

| 组件 | 职责 | 在本项目中的例子 |
| --- | --- | --- |
| SQLAlchemy ORM | 把 Python 类与数据库表对应起来，负责记录读写和事务 | `DocumentUpload` 类对应 `document_uploads` 表 |
| Alembic | 按版本管理数据库结构的变化 | 首次创建上传表；以后增加字段时执行新的迁移 |
| Psycopg | 实际连接 PostgreSQL、发送数据库指令 | 继续使用已经安装的驱动，供 SQLAlchemy 调用 |

ORM 可以理解为“用 Python 对象操作数据库记录”。
表迁移可以理解为“数据库结构的升级步骤”：除了第一次建表，还要知道以后改过什么、执行到哪一步。
Alembic 会用 `alembic_version` 表记录当前迁移版本；它是工具自己的表，不是上传记录表。

## 为什么两者都需要

ORM 模型描述代码期望的表结构；修改模型文件本身，不会自动修改已有数据库。
例如，以后增加一个字段，需要修改模型，并新增一份迁移文件，在数据库执行后才真正生效。
迁移文件跟代码一起提交 Git，让本机和服务器按同样的步骤升级。
不在服务启动时调用 `create_all()` 建表，统一由 Alembic 执行结构变更。

## 建议的文件位置

| 文件或目录 | 用途 |
| --- | --- |
| `src/db/base.py` | 定义 ORM 模型共用的基类，并统一数据库约束的命名方式 |
| `src/db/session.py` | 创建数据库连接引擎和 Session；Session 管理一次数据库操作及其事务 |
| `src/db/models/document_upload.py` | 按 [上传表设计](06-upload-table.md) 定义字段和数据库约束 |
| `alembic.ini` | Alembic 配置；不写数据库密码 |
| `migrations/env.py` | 读取环境变量中的连接地址，加载模型，配置迁移执行 |
| `migrations/versions/` | 保存每次结构变更的版本文件 |

继续从 `DATABASE_URL` 读取连接配置；通过 SQLAlchemy 的 URL API 指定 Psycopg 驱动，不手工拼接账号密码。
现有 `src/check_database.py` 暂时保留为独立连通性检查，业务记录改由 ORM 读写。
SQLAlchemy 与 Alembic 通过 uv 添加并锁定实际版本；本步不引入额外 ORM 封装或通用增删改查框架。

## 并发与事务边界

首批建议使用同步 ORM；接入 FastAPI 时把同步数据库操作放在普通 `def` 路由或线程池中。
不在 `async def` 路由中直接调用同步 ORM 阻塞等待。
每个进程复用自己的连接引擎和有界连接池；不同请求不共用同一个 Session。
创建上传记录和结束上传各使用一次短事务，接收文件期间不占着 Session 的事务或数据库连接。
连接池容量在接口接入时结合进程数量确定；最终仍需验证 10 用户同时使用的实际效果。

## 迁移如何执行和检查

先修改 ORM 模型，再用 Alembic 生成迁移草稿，人工检查后执行 `upgrade head`。
自动生成不等于自动正确；字段改名、状态检查规则等都要核对，必要时手工补充迁移。
检查约束使用明确名称，并核对迁移里的规则是否与模型一致。
已执行的迁移文件保持不变，后续修改新增迁移；重复升级到同一版本不重复建表。
迁移由开发者或部署流程单独执行，不让多个 API 进程同时自动升级。
首次迁移的降级会删除上传表，不能当作恢复上传数据的方法；往返验证在独立测试数据库进行。

## 接下来怎样分步实现

1. ORM 基础：安装依赖，配置基类、连接引擎和 Session，验证真实 PG 连接。
2. 上传模型与首次迁移：表设计通过后定义模型，接入 Alembic，检查并验证建表和约束。
3. 上传记录读写：实现创建、成功和失败更新，验证事务及并发结束同一记录的行为。
4. 文件保存与上传接口：后续分别实现，再串联完整上传流程。

每一步单独讲解和验收；当前文档不代表上述步骤已实现。
依据：[SQLAlchemy ORM 入门](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)、
[Session 与并发](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)、
[Alembic 迁移入门](https://alembic.sqlalchemy.org/en/latest/tutorial.html)、
[自动生成的限制](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)。
