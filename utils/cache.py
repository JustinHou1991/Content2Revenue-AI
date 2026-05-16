"""
缓存模块 - 基于内容hash的SQLite缓存系统

提供内容分析结果的缓存功能，支持TTL过期机制。
同时提供统一缓存接口 UnifiedCache，整合内存LRU缓存与SQLite持久化缓存。
"""

import json
import hashlib
import sqlite3
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional


class ContentCache:
    """基于SQLite的内容分析结果缓存系统（线程安全）"""

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
        self._lock = threading.Lock()
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

        with self._lock:
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

        with self._lock:
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


class UnifiedCache:
    """
    统一缓存接口

    整合内存LRU缓存与SQLite持久化缓存，提供统一的 get/set/delete/exists/clear 操作。
    - 默认使用内存缓存（LRU淘汰策略），读写性能高
    - 可选启用SQLite持久化层，进程重启后缓存仍然有效
    - 支持TTL过期机制
    - 内置命中率统计

    使用示例::

        # 纯内存缓存（默认）
        cache = UnifiedCache()
        cache.set("key", "value", ttl=60)
        result = cache.get("key")

        # 内存 + SQLite 持久化
        cache = UnifiedCache(persist=True, db_path="/tmp/my_cache.db")
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        persist: bool = False,
        db_path: Optional[str] = None,
    ) -> None:
        """
        初始化统一缓存

        Args:
            max_size: 内存缓存最大条目数（LRU淘汰阈值）
            default_ttl: 默认TTL（秒），默认1小时
            persist: 是否启用SQLite持久化层
            db_path: SQLite数据库路径，persist=True时有效；
                     默认为项目根目录下的 unified_cache.db
        """
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._persist = persist

        # 内存缓存：OrderedDict 实现LRU
        self._memory_cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = threading.Lock()

        # 命中率统计
        self._hits: int = 0
        self._misses: int = 0

        # SQLite持久化层（可选）
        self._db_path: Optional[str] = None
        if persist:
            if db_path is None:
                project_root = Path(__file__).parent.parent
                db_path = project_root / "unified_cache.db"
            self._db_path = str(db_path)
            self._init_persist_db()

    # ==================== 公共接口 ====================

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        查找顺序：内存缓存 -> SQLite持久化层（如果启用）

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期返回None
        """
        with self._lock:
            # 优先从内存缓存获取
            if key in self._memory_cache:
                item = self._memory_cache[key]
                if time.time() <= item["expires"]:
                    # LRU：移动到末尾表示最近访问
                    self._memory_cache.move_to_end(key)
                    self._hits += 1
                    return item["value"]
                else:
                    # 内存中已过期，删除
                    del self._memory_cache[key]

            # 内存未命中，尝试持久化层
            if self._persist and self._db_path:
                value = self._get_from_persist(key)
                if value is not None:
                    # 回填到内存缓存
                    self._set_to_memory(key, value, self._default_ttl)
                    self._hits += 1
                    return value

            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值

        同时写入内存缓存和SQLite持久化层（如果启用）。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None则使用默认TTL
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            self._set_to_memory(key, value, effective_ttl)

            if self._persist and self._db_path:
                self._set_to_persist(key, value, effective_ttl)

    def delete(self, key: str) -> bool:
        """
        删除缓存值

        同时从内存缓存和SQLite持久化层中删除。

        Args:
            key: 缓存键

        Returns:
            是否成功删除（键存在时返回True）
        """
        with self._lock:
            deleted = False

            if key in self._memory_cache:
                del self._memory_cache[key]
                deleted = True

            if self._persist and self._db_path:
                if self._delete_from_persist(key):
                    deleted = True

            return deleted

    def exists(self, key: str) -> bool:
        """
        检查缓存键是否存在且未过期

        Args:
            key: 缓存键

        Returns:
            键是否存在且有效
        """
        with self._lock:
            if key in self._memory_cache:
                if time.time() <= self._memory_cache[key]["expires"]:
                    return True
                else:
                    del self._memory_cache[key]

            if self._persist and self._db_path:
                return self._exists_in_persist(key)

            return False

    def clear(self) -> None:
        """
        清空所有缓存

        同时清空内存缓存和SQLite持久化层。
        """
        with self._lock:
            self._memory_cache.clear()

            if self._persist and self._db_path:
                self._clear_persist()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            包含命中率、条目数等统计信息的字典
        """
        with self._lock:
            # 清理内存中过期条目以获取准确计数
            self._evict_expired_memory()

            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0

            stats: Dict[str, Any] = {
                "memory_size": len(self._memory_cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "persist_enabled": self._persist,
            }

            if self._persist and self._db_path:
                persist_stats = self._get_persist_stats()
                stats.update(persist_stats)

            return stats

    def reset_stats(self) -> None:
        """重置命中率统计"""
        with self._lock:
            self._hits = 0
            self._misses = 0

    # ==================== 内存缓存内部方法 ====================

    def _set_to_memory(self, key: str, value: Any, ttl: int) -> None:
        """
        写入内存缓存

        如果达到最大容量，先淘汰最久未访问的条目（LRU）。
        """
        # LRU淘汰
        while len(self._memory_cache) >= self._max_size:
            self._memory_cache.popitem(last=False)

        self._memory_cache[key] = {
            "value": value,
            "expires": time.time() + ttl,
            "created": time.time(),
        }
        self._memory_cache.move_to_end(key)

    def _evict_expired_memory(self) -> int:
        """清理内存中所有过期的缓存条目"""
        now = time.time()
        expired_keys = [
            k for k, v in self._memory_cache.items() if now > v["expires"]
        ]
        for k in expired_keys:
            del self._memory_cache[k]
        return len(expired_keys)

    # ==================== SQLite持久化内部方法 ====================

    def _init_persist_db(self) -> None:
        """初始化SQLite持久化数据库表结构"""
        with sqlite3.connect(self._db_path) as conn:  # type: ignore[arg-type]
            conn.execute("""
                CREATE TABLE IF NOT EXISTS unified_cache (
                    cache_key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_unified_cache_expires
                ON unified_cache(expires_at)
            """)
            conn.commit()

    def _get_from_persist(self, key: str) -> Optional[Any]:
        """从SQLite持久化层获取缓存值"""
        now = time.time()
        with sqlite3.connect(self._db_path) as conn:  # type: ignore[arg-type]
            cursor = conn.execute(
                "SELECT value, expires_at FROM unified_cache WHERE cache_key = ?",
                (key,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            value_json, expires_at = row
            if now > expires_at:
                # 过期，删除
                conn.execute(
                    "DELETE FROM unified_cache WHERE cache_key = ?", (key,)
                )
                conn.commit()
                return None

            try:
                return json.loads(value_json)
            except (json.JSONDecodeError, TypeError):
                return None

    def _set_to_persist(self, key: str, value: Any, ttl: int) -> None:
        """写入SQLite持久化层"""
        now = time.time()
        try:
            value_json = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return

        with sqlite3.connect(self._db_path) as conn:  # type: ignore[arg-type]
            conn.execute(
                """
                INSERT OR REPLACE INTO unified_cache
                (cache_key, value, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, value_json, now, now + ttl),
            )
            conn.commit()

    def _delete_from_persist(self, key: str) -> bool:
        """从SQLite持久化层删除缓存值"""
        with sqlite3.connect(self._db_path) as conn:  # type: ignore[arg-type]
            cursor = conn.execute(
                "DELETE FROM unified_cache WHERE cache_key = ?", (key,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def _exists_in_persist(self, key: str) -> bool:
        """检查SQLite持久化层中键是否存在且未过期"""
        now = time.time()
        with sqlite3.connect(self._db_path) as conn:  # type: ignore[arg-type]
            cursor = conn.execute(
                "SELECT expires_at FROM unified_cache WHERE cache_key = ?",
                (key,),
            )
            row = cursor.fetchone()

            if row is None:
                return False

            if now > row[0]:
                conn.execute(
                    "DELETE FROM unified_cache WHERE cache_key = ?", (key,)
                )
                conn.commit()
                return False

            return True

    def _clear_persist(self) -> None:
        """清空SQLite持久化层"""
        with sqlite3.connect(self._db_path) as conn:  # type: ignore[arg-type]
            conn.execute("DELETE FROM unified_cache")
            conn.commit()

    def _get_persist_stats(self) -> Dict[str, Any]:
        """获取SQLite持久化层统计信息"""
        now = time.time()
        with sqlite3.connect(self._db_path) as conn:  # type: ignore[arg-type]
            cursor = conn.execute("SELECT COUNT(*) FROM unified_cache")
            total_count = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(*) FROM unified_cache WHERE expires_at < ?", (now,)
            )
            expired_count = cursor.fetchone()[0]

        return {
            "persist_total_entries": total_count,
            "persist_valid_entries": total_count - expired_count,
            "persist_expired_entries": expired_count,
            "persist_db_path": self._db_path,
        }


# 全局缓存实例
default_cache: Optional[ContentCache] = None
_cache_lock = threading.Lock()


def get_cache() -> ContentCache:
    """获取默认缓存实例（线程安全单例模式）"""
    global default_cache
    if default_cache is None:
        with _cache_lock:
            if default_cache is None:
                default_cache = ContentCache()
    return default_cache
