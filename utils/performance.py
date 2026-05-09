"""
性能监控模块 - 函数执行时间监控装饰器

提供函数执行时间记录和慢操作警告功能。
"""

import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar

from utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def monitor_performance(threshold_ms: float = 1000):
    """性能监控装饰器

    监控函数执行时间，超过阈值时记录警告日志。

    Args:
        threshold_ms: 慢操作阈值（毫秒），默认1000ms

    Example:
        @monitor_performance(threshold_ms=500)
        def my_slow_function():
            time.sleep(0.6)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                if elapsed > threshold_ms:
                    logger.warning(f"慢操作: {func.__name__} 耗时 {elapsed:.2f}ms")
                else:
                    logger.debug(f"{func.__name__} 耗时 {elapsed:.2f}ms")
        return wrapper
    return decorator


def timing_decorator(func: F) -> F:
    """
    计时装饰器 - 记录函数执行时间

    使用 time.perf_counter() 获取高精度计时，
    在日志中记录函数名称、执行时间和参数信息。

    Example:
        @timing_decorator
        def my_function(x, y):
            return x + y
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            # 简化参数显示
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            if len(signature) > 100:
                signature = signature[:97] + "..."

            logger.info(
                f"[TIMING] {func.__name__}({signature}) "
                f"executed in {execution_time_ms:.2f}ms"
            )

    return wrapper  # type: ignore[return-value]


def log_slow_operations(threshold_ms: float = 1000.0) -> Callable[[F], F]:
    """
    慢操作日志装饰器 - 自动记录执行时间超过阈值的函数

    当函数执行时间超过指定阈值时，记录警告日志。
    可用于识别性能瓶颈。

    Args:
        threshold_ms: 慢操作阈值（毫秒），默认1000ms（1秒）

    Example:
        @log_slow_operations(threshold_ms=500)
        def my_slow_function():
            time.sleep(0.6)

        @log_slow_operations()  # 使用默认阈值1000ms
        def another_function():
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                execution_time_ms = (end_time - start_time) * 1000

                if execution_time_ms > threshold_ms:
                    # 简化参数显示
                    args_repr = [repr(a) for a in args]
                    kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                    signature = ", ".join(args_repr + kwargs_repr)
                    if len(signature) > 100:
                        signature = signature[:97] + "..."

                    logger.warning(
                        f"[SLOW OPERATION] {func.__name__}({signature}) "
                        f"took {execution_time_ms:.2f}ms "
                        f"(threshold: {threshold_ms:.0f}ms)"
                    )

        return wrapper  # type: ignore[return-value]

    return decorator


class PerformanceMonitor:
    """
    性能监控上下文管理器

    用于监控代码块的执行时间，支持手动记录和阈值警告。

    Example:
        with PerformanceMonitor("data_processing", threshold_ms=500):
            process_large_dataset()
    """

    def __init__(
        self,
        operation_name: str,
        threshold_ms: Optional[float] = None,
        log_level: int = logging.INFO,
    ):
        """
        初始化性能监控器

        Args:
            operation_name: 操作名称，用于日志标识
            threshold_ms: 慢操作阈值（毫秒），为None时不检查
            log_level: 日志级别
        """
        self.operation_name = operation_name
        self.threshold_ms = threshold_ms
        self.log_level = log_level
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def __enter__(self) -> "PerformanceMonitor":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.end_time = time.perf_counter()
        execution_time_ms = self.elapsed_ms

        if exc_type is not None:
            logger.error(
                f"[PERFORMANCE] {self.operation_name} failed after "
                f"{execution_time_ms:.2f}ms with {exc_type.__name__}"
            )
        else:
            log_msg = (
                f"[PERFORMANCE] {self.operation_name} completed in "
                f"{execution_time_ms:.2f}ms"
            )

            if self.threshold_ms and execution_time_ms > self.threshold_ms:
                logger.warning(
                    f"{log_msg} [SLOW - threshold: {self.threshold_ms:.0f}ms]"
                )
            else:
                logger.log(self.log_level, log_msg)

    @property
    def elapsed_ms(self) -> float:
        """获取已执行时间（毫秒）"""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time is not None else time.perf_counter()
        return (end - self.start_time) * 1000


def benchmark(iterations: int = 100) -> Callable[[F], Callable[[], dict]]:
    """
    基准测试装饰器 - 多次执行函数并统计性能数据

    Args:
        iterations: 执行次数，默认100次

    Returns:
        返回一个函数，调用后返回性能统计字典

    Example:
        @benchmark(iterations=1000)
        def test_function():
            return sum(range(100))

        stats = test_function()
        print(f"Avg: {stats['avg_ms']:.2f}ms")
    """

    def decorator(func: F) -> Callable[[], dict]:
        @functools.wraps(func)
        def wrapper() -> dict:
            times: list[float] = []

            for _ in range(iterations):
                start = time.perf_counter()
                func()
                end = time.perf_counter()
                times.append((end - start) * 1000)

            times.sort()

            return {
                "iterations": iterations,
                "total_ms": sum(times),
                "avg_ms": sum(times) / len(times),
                "min_ms": times[0],
                "max_ms": times[-1],
                "median_ms": times[len(times) // 2],
                "p95_ms": times[int(len(times) * 0.95)],
                "p99_ms": times[int(len(times) * 0.99)],
            }

        return wrapper

    return decorator
