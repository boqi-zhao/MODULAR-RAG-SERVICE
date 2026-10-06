"""统一日志入口：导入 logger 即可使用，配置在本进程首次导入时加载。"""

import logging
import logging.config
from pathlib import Path


# 根据本文件定位项目目录，自动创建日志目录，不依赖启动时的工作目录。
def _configure_logging() -> None:
    project_root = Path(__file__).resolve().parents[2]
    log_file = project_root / "logs" / "service.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.config.fileConfig(
        project_root / "config" / "logging.ini",
        defaults={"log_file": repr(str(log_file))},
        disable_existing_loggers=False,
    )


# Python 会缓存已导入的模块，其他模块重复导入时不会再次执行初始化。
_configure_logging()
logger = logging.getLogger("rag")
