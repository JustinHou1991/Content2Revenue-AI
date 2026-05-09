"""缓存管理器测试"""
import pytest
import time
import threading
from utils.cache_manager import CacheManager, cached


class TestCacheManager:
    def test_basic_get_set(self):
        cache = CacheManager()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss(self):
        cache = CacheManager()
        assert cache.get("nonexistent") is None

    def test_cache_ttl(self):
        cache = CacheManager(default_ttl=1)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        time.sleep(1.1)
        assert cache.get("key") is None

    def test_cache_lru_eviction(self):
        cache = CacheManager(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # 应该淘汰 a
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_cache_stats(self):
        cache = CacheManager()
        cache.set("key", "value")
        cache.get("key")  # hit
        cache.get("missing")  # miss
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_thread_safety(self):
        cache = CacheManager()
        errors = []

        def writer():
            try:
                for i in range(100):
                    cache.set(f"key_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.get_stats()["size"] > 0

    def test_delete(self):
        cache = CacheManager()
        cache.set("key", "value")
        assert cache.delete("key") is True
        assert cache.get("key") is None
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        cache = CacheManager()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get_stats()["size"] == 0

    def test_custom_ttl(self):
        cache = CacheManager(default_ttl=3600)
        cache.set("key", "value", ttl=1)
        assert cache.get("key") == "value"
        time.sleep(1.1)
        assert cache.get("key") is None


class TestCachedDecorator:
    def test_cached_function(self):
        call_count = 0

        @cached(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(5)

        assert result1 == result2 == 10
        assert call_count == 1  # 只调用一次

    def test_cached_with_different_args(self):
        call_count = 0

        # The cached decorator skips args[0] (assumes it's 'self'),
        # so we simulate a method by having a dummy first parameter
        @cached(ttl=60)
        def my_function(self_, x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        result1 = my_function(None, 5, 10)
        result2 = my_function(None, 5, 20)
        result3 = my_function(None, 10, 10)

        assert call_count == 3  # 不同参数应该调用三次
        assert result1 == 15
        assert result2 == 25
        assert result3 == 20

    def test_cached_access_to_cache_stats(self):
        @cached(ttl=60)
        def test_func(x):
            return x * 2

        test_func(5)
        test_func(5)

        stats = test_func._cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
