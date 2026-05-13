"""缓存管理器 - 支持内存和SQLite持久化"""
import hashlib
import json
import time
import sqlite3
import os
from typing import Any, Optional, Dict, Callable
from functools import wraps
import threading
import logging

logger = logging.getLogger(__name__)


class CacheBackend:
    """缓存后端基类"""
    def get(self, key: str) -> Optional[Any]: raise NotImplementedError
    def set(self, key: str, value: Any, ttl: int) -> None: raise NotImplementedError
    def delete(self, key: str) -> bool: raise NotImplementedError
    def clear(self) -> None: raise NotImplementedError
    def get_stats(self) -> Dict[str, Any]: raise NotImplementedError


class MemoryBackend(CacheBackend):
    """内存缓存后端"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            item = self._cache[key]
            if time.time() > item["expires"]:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return item["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            
            expires = time.time() + (ttl or self._default_ttl)
            self._cache[key] = {
                "value": value,
                "expires": expires,
                "created": time.time(),
            }
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
    
    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(),
                        key=lambda k: self._cache[k]["created"])
        del self._cache[oldest_key]
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate * 100, 2),
            }


class SQLiteBackend(CacheBackend):
    """SQLite持久化缓存后端"""
    
    def __init__(self, db_path: str = "data/cache.db", default_ttl: int = 86400):
        self._db_path = db_path
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化缓存表"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires REAL NOT NULL,
                    created REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON llm_cache(expires)")
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    row = conn.execute(
                        "SELECT value, expires FROM llm_cache WHERE key = ?",
                        (key,)
                    ).fetchone()
                    
                    if row is None:
                        self._misses += 1
                        return None
                    
                    if time.time() > row[1]:
                        conn.execute("DELETE FROM llm_cache WHERE key = ?", (key,))
                        self._misses += 1
                        return None
                    
                    self._hits += 1
                    return json.loads(row[0])
            except Exception as e:
                logger.warning(f"缓存读取失败: {e}")
                self._misses += 1
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            try:
                expires = time.time() + (ttl or self._default_ttl)
                value_json = json.dumps(value)
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO llm_cache (key, value, expires, created)
                        VALUES (?, ?, ?, ?)
                    """, (key, value_json, expires, time.time()))
            except Exception as e:
                logger.warning(f"缓存写入失败: {e}")
    
    def delete(self, key: str) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute(
                        "DELETE FROM llm_cache WHERE key = ?",
                        (key,)
                    )
                    return cursor.rowcount > 0
            except Exception as e:
                logger.warning(f"缓存删除失败: {e}")
                return False
    
    def clear(self) -> None:
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("DELETE FROM llm_cache")
            except Exception as e:
                logger.warning(f"缓存清空失败: {e}")
    
    def cleanup_expired(self) -> int:
        """清理过期缓存，返回删除数量"""
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute(
                        "DELETE FROM llm_cache WHERE expires < ?",
                        (time.time(),)
                    )
                    return cursor.rowcount
            except Exception as e:
                logger.warning(f"缓存清理失败: {e}")
                return 0
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            try:
                with sqlite3.connect(self._db_path) as conn:
                    size = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
            except:
                size = 0
            return {
                "size": size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate * 100, 2),
            }


class CacheManager:
    """统一缓存管理器 - 自动选择后端"""
    
    def __init__(
        self, 
        backend: str = "sqlite",
        max_size: int = 1000, 
        default_ttl: int = 86400,
        db_path: str = "data/cache.db"
    ):
        """
        Args:
            backend: 后端类型，"memory" 或 "sqlite"
            max_size: 最大缓存数量（仅内存模式生效）
            default_ttl: 默认过期时间（秒）
            db_path: SQLite数据库路径
        """
        if backend == "memory":
            self._backend = MemoryBackend(max_size, default_ttl)
        else:
            self._backend = SQLiteBackend(db_path, default_ttl)
        
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        result = self._backend.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._backend.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        return self._backend.delete(key)
    
    def clear(self) -> None:
        self._backend.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        stats = self._backend.get_stats()
        total = self._hits + self._misses
        stats["total_hits"] = self._hits
        stats["total_misses"] = self._misses
        stats["overall_hit_rate"] = round((self._hits / total * 100), 2) if total > 0 else 0
        return stats
    
    def cleanup_expired(self) -> int:
        """清理过期缓存（仅SQLite后端有效）"""
        if hasattr(self._backend, "cleanup_expired"):
            return self._backend.cleanup_expired()
        return 0


def cached(ttl: int = 86400, key_func: Optional[Callable] = None, backend: str = "memory"):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        cache = CacheManager(backend=backend, default_ttl=ttl)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(a) for a in args[1:])
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()

            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        wrapper._cache = cache
        return wrapper
    return decorator
