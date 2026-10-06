# 日志基础：控制台与本地文件

状态：已实现并验证，用户已确认单独提交日志基础设施。

## 配置与日志位置

统一配置在根目录 `config/logging.ini`；`src/common/logger.py` 集中加载配置并导出 logger。
文件输出使用 `concurrent-log-handler`，通过文件锁协调本机多个进程写入和滚动备份。
日志同时输出到控制台和项目根目录 `logs/`；以下命令在项目根目录运行。

当前文件为 `logs/service.log`，达到 10 MiB 时滚动保存，最多保留 10 个备份。
备份使用标准库默认名称：`service.log.1` 到 `service.log.10`；`.1` 最近，`.10` 最旧。
再次滚动时删除最旧备份，当前日志继续写入 `service.log`；服务重启后仍追加写入。
API 和其他 Python 模块可以共同写入这个文件；各进程首次导入共用日志模块时自动加载配置。
目录中可能出现隐藏的锁文件，它用于协调写入，不是另一份业务日志。
当前覆盖本机共享目录；多机部署后的集中日志收集留待后续。
修改配置后须重启相应服务，新配置才会生效；之前生成的日志不自动删除。
`logs/.gitkeep` 只用于保留空目录，实际日志已被 Git 忽略。

## 业务代码怎么记录

各模块直接导入共用 logger，不重复读取配置或设置输出位置：

```python
from common.logger import logger

logger.info("Application started")
```

INFO 表示正常运行信息，WARNING 表示需要留意的问题，ERROR 表示操作失败；默认级别为 INFO。
Python 会缓存已导入的模块，同一进程重复导入时不会重新执行初始化。
共用模块自动创建项目根目录的 `logs/`，不依赖启动时的工作目录。
统一格式包含时间、级别、线程名称和 ID、调用处的文件模块名和行号，例如：

```text
2026-10-06 17:04:12 INFO [MainThread:12345] [main:9] FastAPI application initialized
```

日志内容不应包含密码或凭据；业务模块应选择必要信息，不直接记录含敏感内容的输入或异常文本。
业务模块不自行添加输出位置，避免同一条消息重复输出。
线程信息用于定位执行位置，不是用户编号；多个异步请求可能运行在同一线程。

## 启动方式

API 通过导入共用 logger 自动加载配置，无需 `--log-config`：

```sh
uv run uvicorn api.main:app --app-dir src --host 127.0.0.1 --port 8080
```

## 实际验证

- Uvicorn 启动、退出和真实 `/health` 请求均写入日志文件，单次请求只记录一次。
- 真实日志文件未纳入 Git。
- 隔离目录中缩小滚动阈值，验证最多保留 `.1` 到 `.10`，没有第 11 个备份。
- 两个真实进程并发写入并滚动，60 条测试日志完整且不重复，包含实际工作线程名称和 ID。
- 重复导入共用日志模块，logger 和输出处理器保持同一实例，没有重复初始化。
- 从临时工作目录导入共用 logger，日志定位到项目 `logs/`。
- API 不传日志配置参数即可将启动和访问日志写入文件。
- 本轮为真实运行检查，没有新增自动测试文件。

依据：[concurrent-log-handler 官方说明](https://github.com/Preston-Landers/concurrent-log-handler)。
