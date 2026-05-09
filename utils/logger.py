"""
Content2Revenue AI - 统一日志配置模块

提供统一的日志格式和输出管理：
  - 同时输出到控制台和文件
  - 日志文件保存在 data/logs/ 目录
  - 支持按模块设置不同日志级别
  - 使用 RotatingFileHandler 自动轮转日志文件

使用方式：
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Hello")
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# 默认配置
# ---------------------------------------------------------------------------

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 不同模块的日志级别映射
# key 是 logger name 的前缀，value 是日志级别字符串
MODULE_LOG_LEVELS: Dict[str, str] = {
    "services.llm_client": "INFO",
    "services.orchestrator": "INFO",
    "services.database": "INFO",
    "services.content_analyzer": "INFO",
    "services.lead_analyzer": "INFO",
    "services.match_engine": "INFO",
    "services.strategy_advisor": "INFO",
    "services.data_cleaner": "INFO",
    "ui": "WARNING",
    "prompts": "WARNING",
    "config": "INFO",
    "utils": "INFO",
}

# ---------------------------------------------------------------------------
# 日志管理器
# ---------------------------------------------------------------------------

_initialized = False
_root_handler_console: Optional[logging.Handler] = None
_root_handler_file: Optional[logging.Handler] = None


def _resolve_log_dir(log_dir: str) -> str:
    """解析日志目录为绝对路径，并确保目录存在"""
    if not os.path.isabs(log_dir):
        log_dir = os.path.join(PROJECT_ROOT, log_dir)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def setup_logging(
    level: str = "INFO",
    log_dir: str = "data/logs",
    log_file: str = "c2r.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    log_format: Optional[str] = None,
    date_format: Optional[str] = None,
) -> None:
    """
    初始化全局日志配置。

    应在应用启动时调用一次。重复调用不会重复添加 handler。

    Args:
        level: 全局默认日志级别
        log_dir: 日志文件目录
        log_file: 日志文件名
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份日志文件数量
        log_format: 自定义日志格式（None 使用默认格式）
        date_format: 自定义日期格式（None 使用默认格式）
    """
    global _initialized, _root_handler_console, _root_handler_file

    if _initialized:
        return

    fmt = log_format or DEFAULT_LOG_FORMAT
    dfmt = date_format or DEFAULT_DATE_FORMAT
    formatter = logging.Formatter(fmt=fmt, datefmt=dfmt)

    # 获取 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # ---- 控制台 Handler ----
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    _root_handler_console = console_handler

    # ---- 文件 Handler ----
    abs_log_dir = _resolve_log_dir(log_dir)
    log_path = os.path.join(abs_log_dir, log_file)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    _root_handler_file = file_handler

    # ---- 按模块设置不同日志级别 ----
    for module_prefix, module_level in MODULE_LOG_LEVELS.items():
        mod_logger = logging.getLogger(module_prefix)
        mod_logger.setLevel(getattr(logging, module_level.upper(), logging.INFO))

    _initialized = True

    # 使用 root logger 记录初始化完成
    root_logger.info(
        "日志系统初始化完成: level=%s, log_file=%s",
        level,
        log_path,
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger 实例。

    如果日志系统尚未初始化，会自动以默认参数调用 setup_logging()。

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        logging.Logger 实例
    """
    if not _initialized:
        setup_logging()

    return logging.getLogger(name)
