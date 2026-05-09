"""
缓存模块 - 基于内容hash的SQLite缓存系统

提供内容分析结果的缓存功能，支持TTL过期机制。
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


class ContentCache:
    """基于SQLite的内容分析结果缓存系统"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化缓存系统

        Args:
            db_path: SQLite数据库路径，默认为项目根目录下的 cache.db
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent
            db_path = project_root / "cache.db"

        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    content_hash TEXT PRIMARY KEY,
                    result TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON analysis_cache(expires_at)
            """)
            conn.commit()

    @staticmethod
    def compute_hash(content: str) -> str:
        """
        计算内容的MD5哈希值

        Args:
            content: 要哈希的内容字符串

        Returns:
            MD5哈希值的十六进制字符串
        """
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get_cached_analysis(self, content_hash: str) -> Optional[Any]:
        """
        获取缓存的分析结果

        Args:
            content_hash: 内容的哈希值

        Returns:
            缓存的结果，如果不存在或已过期则返回None
        """
        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT result, expires_at FROM analysis_cache WHERE content_hash = ?",
                (content_hash,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            result_json, expires_at = row

            # 检查是否过期
            if current_time > expires_at:
                # 删除过期缓存
                conn.execute(
                    "DELETE FROM analysis_cache WHERE content_hash = ?", (content_hash,)
                )
                conn.commit()
                return None

            # 解析JSON结果
            try:
                return json.loads(result_json)
            except json.JSONDecodeError:
                return None

    def set_cached_analysis(
        self, content_hash: str, result: Any, ttl: int = 3600
    ) -> bool:
        """
        设置缓存的分析结果

        Args:
            content_hash: 内容的哈希值
            result: 要缓存的结果（会被序列化为JSON）
            ttl: 生存时间（秒），默认1小时

        Returns:
            是否成功设置缓存
        """
        current_time = time.time()
        expires_at = current_time + ttl

        try:
            result_json = json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO analysis_cache
                (content_hash, result, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (content_hash, result_json, current_time, expires_at),
            )
            conn.commit()

        return True

    def clear_expired_cache(self) -> int:
        """
        清理所有过期的缓存条目

        Returns:
            清理的条目数量
        """
        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM analysis_cache WHERE expires_at < ?", (current_time,)
            )
            conn.commit()
            return cursor.rowcount

    def clear_all_cache(self) -> int:
        """
        清空所有缓存

        Returns:
            清理的条目数量
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM analysis_cache")
            conn.commit()
            return cursor.rowcount

    def get_cache_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            包含缓存统计信息的字典
        """
        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            # 总条目数
            cursor = conn.execute("SELECT COUNT(*) FROM analysis_cache")
            total_count = cursor.fetchone()[0]

            # 过期条目数
            cursor = conn.execute(
                "SELECT COUNT(*) FROM analysis_cache WHERE expires_at < ?",
                (current_time,),
            )
            expired_count = cursor.fetchone()[0]

            # 有效条目数
            valid_count = total_count - expired_count

        return {
            "total_entries": total_count,
            "valid_entries": valid_count,
            "expired_entries": expired_count,
            "db_path": self.db_path,
        }


# 全局缓存实例
default_cache: Optional[ContentCache] = None


def get_cache() -> ContentCache:
    """获取默认缓存实例（单例模式）"""
    global default_cache
    if default_cache is None:
        default_cache = ContentCache()
    return default_cache
