"""请求批处理器 - 合并相似的 LLM 请求"""
import asyncio
from typing import List, Dict, Any, Callable, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RequestBatcher:
    """请求批处理器"""

    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._pending: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._processing: Dict[str, bool] = defaultdict(bool)

    async def submit(self, key: str, request: Dict, processor: Callable[[List[Dict]], List[Any]]) -> Any:
        """提交请求到批处理队列

        Args:
            key: 批处理键，相同key的请求会被合并
            request: 请求数据
            processor: 批处理函数，接收请求列表，返回结果列表

        Returns:
            单个请求的结果
        """
        future = asyncio.Future()

        batch_to_process = None
        async with self._lock:
            self._pending[key].append({
                "request": request,
                "future": future,
            })

            # 如果达到批处理大小，立即处理
            if len(self._pending[key]) >= self.batch_size:
                batch_to_process = self._pending[key][:self.batch_size]
                self._pending[key] = self._pending[key][self.batch_size:]
                self._processing[key] = True

        if batch_to_process:
            await self._process_batch(key, processor, batch_to_process)

        # 如果没有立即处理，启动超时处理
        if not future.done():
            asyncio.create_task(self._timeout_process(key, processor))

        # 等待结果
        return await future

    async def _timeout_process(self, key: str, processor: Callable[[List[Dict]], List[Any]]) -> None:
        """超时处理"""
        await asyncio.sleep(self.batch_timeout)
        async with self._lock:
            if self._pending[key] and not self._processing[key]:
                batch = self._pending[key][:self.batch_size]
                self._pending[key] = self._pending[key][self.batch_size:]
                self._processing[key] = True
        if self._processing.get(key):
            await self._process_batch(key, processor, batch)

    async def _process_batch(self, key: str, processor: Callable[[List[Dict]], List[Any]],
                          batch: list = None) -> None:
        """处理一批请求"""
        if batch is None:
            if self._processing.get(key):
                return
            self._processing[key] = True
            async with self._lock:
                batch = self._pending[key][:self.batch_size]
                self._pending[key] = self._pending[key][self.batch_size:]

        if not batch:
            self._processing[key] = False
            return

        logger.debug(f"处理批处理请求: key={key}, count={len(batch)}")

        # 提取请求数据
        requests = [item["request"] for item in batch]

        # 调用处理器
        try:
            results = await asyncio.to_thread(processor, requests)

            # 分发结果
            for item, result in zip(batch, results):
                if not item["future"].done():
                    item["future"].set_result(result)
        except Exception as e:
            logger.error(f"批处理失败: {e}")
            # 向所有等待的future传播错误
            for item in batch:
                if not item["future"].done():
                    item["future"].set_exception(e)
        finally:
            self._processing[key] = False


class LLMBatcher:
    """LLM 请求批处理器 - 专门用于合并 LLM 调用"""

    def __init__(self, batch_size: int = 5, batch_timeout: float = 0.05):
        self.batcher = RequestBatcher(batch_size, batch_timeout)
        self._stats = {
            "total_requests": 0,
            "batched_requests": 0,
            "saved_calls": 0,
        }

    async def submit_chat_json(
        self,
        llm_client,
        system_prompt: str,
        user_content: str,
        **kwargs
    ) -> Dict[str, Any]:
        """提交 chat_json 请求到批处理

        Args:
            llm_client: LLMClient 实例
            system_prompt: 系统提示词
            user_content: 用户内容
            **kwargs: 其他参数

        Returns:
            LLM 响应
        """
        key = f"{llm_client.model}:{hash(system_prompt) % 10000}"
        request = {
            "system_prompt": system_prompt,
            "user_content": user_content,
            "kwargs": kwargs,
        }

        def processor(requests: List[Dict]) -> List[Dict[str, Any]]:
            """处理一批请求"""
            results = []
            for req in requests:
                try:
                    result = llm_client.chat_json(
                        system_prompt=req["system_prompt"],
                        user_content=req["user_content"],
                        **req["kwargs"]
                    )
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
            return results

        self._stats["total_requests"] += 1
        return await self.batcher.submit(key, request, processor)

    def get_stats(self) -> Dict[str, int]:
        """获取批处理统计"""
        return self._stats.copy()


# 全局批处理器实例
_default_batcher: Optional[LLMBatcher] = None


def get_llm_batcher() -> LLMBatcher:
    """获取默认的 LLM 批处理器"""
    global _default_batcher
    if _default_batcher is None:
        _default_batcher = LLMBatcher()
    return _default_batcher
