"""
Content2Revenue AI - 统一配置管理模块

集中管理所有配置项，支持三级配置源：
  1. 环境变量（最高优先级）
  2. .streamlit/secrets.toml
  3. 数据库 app_settings 表
  4. 代码默认值（最低优先级）

使用方式：
    from config import get_config
    cfg = get_config()
    print(cfg["model"], cfg["api_key"])
"""

import os
import sys
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 配置数据结构
# ---------------------------------------------------------------------------

@dataclass
class AppConfig:
    """应用配置数据类，集中定义所有配置项及其默认值"""

    # ---- 模型配置 ----
    model: str = "deepseek-chat"
    api_key: str = ""

    # ---- 数据库配置 ----
    db_path: str = "data/c2r.db"

    # ---- 日志配置 ----
    log_level: str = "INFO"
    log_dir: str = "data/logs"
    log_file: str = "c2r.log"
    log_max_bytes: int = 10 * 1024 * 1024   # 10 MB
    log_backup_count: int = 5

    # ---- LLM 调用参数 ----
    temperature: float = 0.3
    max_tokens: int = 4096
    max_retries: int = 2

    # ---- 匹配引擎 ----
    match_top_k: int = 3
    match_concurrency: int = 3

    # ---- 仪表盘 ----
    dashboard_recent_limit: int = 5

    def to_dict(self) -> Dict[str, Any]:
        """转换为普通字典"""
        return {
            "model": self.model,
            "api_key": self.api_key,
            "db_path": self.db_path,
            "log_level": self.log_level,
            "log_dir": self.log_dir,
            "log_file": self.log_file,
            "log_max_bytes": self.log_max_bytes,
            "log_backup_count": self.log_backup_count,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_retries": self.max_retries,
            "match_top_k": self.match_top_k,
            "match_concurrency": self.match_concurrency,
            "dashboard_recent_limit": self.dashboard_recent_limit,
        }


# ---------------------------------------------------------------------------
# 配置源读取器
# ---------------------------------------------------------------------------

def _read_from_env(cfg: AppConfig) -> None:
    """从环境变量读取配置，覆盖默认值"""
    env_map = {
        "C2R_MODEL": ("model", str),
        "C2R_API_KEY": ("api_key", str),
        "C2R_DB_PATH": ("db_path", str),
        "C2R_LOG_LEVEL": ("log_level", str),
        "C2R_LOG_DIR": ("log_dir", str),
        "C2R_TEMPERATURE": ("temperature", float),
        "C2R_MAX_TOKENS": ("max_tokens", int),
        "C2R_MAX_RETRIES": ("max_retries", int),
        "C2R_MATCH_TOP_K": ("match_top_k", int),
        "C2R_MATCH_CONCURRENCY": ("match_concurrency", int),
        # 兼容已有的环境变量命名
        "DEEPSEEK_API_KEY": ("api_key", str),
        "DASHSCOPE_API_KEY": ("api_key", str),
    }

    for env_key, (attr, type_fn) in env_map.items():
        value = os.environ.get(env_key)
        if value is not None:
            try:
                setattr(cfg, attr, type_fn(value))
                logger.debug("从环境变量加载配置: %s -> %s.%s = %s",
                             env_key, type(cfg).__name__, attr, value)
            except (ValueError, TypeError) as e:
                logger.warning("环境变量 %s 值无效 (%s): %s", env_key, e, value)


def _read_from_secrets(cfg: AppConfig) -> None:
    """从 Streamlit secrets.toml 读取配置"""
    try:
        import streamlit as st
        secrets = st.secrets

        secret_map = {
            "MODEL": "model",
            "API_KEY": "api_key",
            "DB_PATH": "db_path",
            "LOG_LEVEL": "log_level",
            "LOG_DIR": "log_dir",
            "TEMPERATURE": "temperature",
            "MAX_TOKENS": "max_tokens",
            "MAX_RETRIES": "max_retries",
            "MATCH_TOP_K": "match_top_k",
            "MATCH_CONCURRENCY": "match_concurrency",
        }

        for secret_key, attr in secret_map.items():
            if secret_key in secrets:
                value = secrets[secret_key]
                try:
                    # 类型转换
                    current_type = type(getattr(cfg, attr))
                    if current_type in (int, float):
                        value = current_type(value)
                    setattr(cfg, attr, value)
                    logger.debug("从 secrets.toml 加载配置: %s -> %s.%s = %s",
                                 secret_key, type(cfg).__name__, attr, value)
                except (ValueError, TypeError) as e:
                    logger.warning("secrets.toml 中 %s 值无效 (%s): %s",
                                   secret_key, e, value)
    except Exception:
        # Streamlit 未运行或 secrets 不可用，静默跳过
        logger.debug("secrets.toml 不可用，跳过")


def _read_from_database(cfg: AppConfig) -> None:
    """从数据库 app_settings 表读取配置"""
    try:
        db_path = cfg.db_path
        if not os.path.isabs(db_path):
            db_path = os.path.join(PROJECT_ROOT, db_path)

        if not os.path.exists(db_path):
            logger.debug("数据库文件不存在，跳过数据库配置: %s", db_path)
            return

        import sqlite3
        conn = sqlite3.connect(db_path, timeout=3)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT key, value FROM app_settings"
            ).fetchall()

            db_map = {
                "model": ("model", str),
                "api_key": ("api_key", str),
                "db_path": ("db_path", str),
                "log_level": ("log_level", str),
                "log_dir": ("log_dir", str),
                "temperature": ("temperature", float),
                "max_tokens": ("max_tokens", int),
                "max_retries": ("max_retries", int),
                "match_top_k": ("match_top_k", int),
                "match_concurrency": ("match_concurrency", int),
            }

            for row in rows:
                key, value = row["key"], row["value"]
                if key in db_map:
                    attr, type_fn = db_map[key]
                    try:
                        setattr(cfg, attr, type_fn(value))
                        logger.debug("从数据库加载配置: %s -> %s.%s = %s",
                                     key, type(cfg).__name__, attr, value)
                    except (ValueError, TypeError) as e:
                        logger.warning("数据库配置 %s 值无效 (%s): %s",
                                       key, e, value)
        finally:
            conn.close()
    except Exception as e:
        logger.debug("从数据库读取配置失败，跳过: %s", e)


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

_config_cache: Optional[AppConfig] = None


def get_config(refresh: bool = False) -> Dict[str, Any]:
    """
    获取应用配置字典。

    配置加载优先级（后者覆盖前者）：
      默认值 -> 数据库 -> secrets.toml -> 环境变量

    Args:
        refresh: 是否强制重新加载（忽略缓存）

    Returns:
        包含所有配置项的字典
    """
    global _config_cache

    if _config_cache is not None and not refresh:
        return _config_cache.to_dict()

    cfg = AppConfig()

    # 按优先级从低到高加载
    _read_from_database(cfg)
    _read_from_secrets(cfg)
    _read_from_env(cfg)

    _config_cache = cfg

    logger.info("配置加载完成 (model=%s, db_path=%s, log_level=%s)",
                cfg.model, cfg.db_path, cfg.log_level)

    return cfg.to_dict()


def get_config_object(refresh: bool = False) -> AppConfig:
    """
    获取 AppConfig 对象（可直接通过属性访问配置项）。

    Args:
        refresh: 是否强制重新加载

    Returns:
        AppConfig 实例
    """
    get_config(refresh=refresh)  # 触发加载（含缓存逻辑）
    return _config_cache  # type: ignore[return-value]
