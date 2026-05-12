"""LLM 响应缓存 - 缓存 LLM 调用结果"""
import hashlib
import json
from typing import Dict, Any, Optional
from utils.cache_manager import CacheManager


class LLMCache:
    """LLM 响应缓存"""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self._cache = cache_manager or CacheManager(max_size=500, default_ttl=7200)

    def _generate_key(self, messages: list, model: str, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            "messages": messages,
            "model": model,
            "kwargs": kwargs,
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, messages: list, model: str, **kwargs) -> Optional[Dict]:
        """获取缓存的 LLM 响应"""
        key = self._generate_key(messages, model, **kwargs)
        return self._cache.get(key)

    def set(self, messages: list, model: str, response: Dict, **kwargs) -> None:
        """缓存 LLM 响应"""
        key = self._generate_key(messages, model, **kwargs)
        self._cache.set(key, response)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self._cache.get_stats()

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
