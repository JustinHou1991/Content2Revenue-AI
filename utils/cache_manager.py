"""缓存管理器 - 统一的内存和磁盘缓存"""
import hashlib
import json
import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
import threading


class CacheManager:
    """缓存管理器 - 支持内存缓存和TTL"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
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
        """设置缓存值"""
        with self._lock:
            # LRU清理
            if len(self._cache) >= self._max_size:
                self._evict_oldest()

            expires = time.time() + (ttl or self._default_ttl)
            self._cache[key] = {
                "value": value,
                "expires": expires,
                "created": time.time(),
            }

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def _evict_oldest(self) -> None:
        """淘汰最旧的缓存项"""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(),
                        key=lambda k: self._cache[k]["created"])
        del self._cache[oldest_key]

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate * 100, 2),
            }


def cached(ttl: int = 3600, key_func: Optional[Callable] = None):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        cache = CacheManager()

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(a) for a in args[1:])  # 跳过self
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
