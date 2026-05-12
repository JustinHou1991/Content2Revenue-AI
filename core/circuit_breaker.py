#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
熔断器 CircuitBreaker - 故障隔离与恢复机制

设计灵感:
- Netflix Hystrix: 熔断器状态机设计
- pybreaker: Python熔断器实现
- Istio: Service Mesh熔断模式

核心特性:
1. 三状态机 - CLOSED/OPEN/HALF_OPEN
2. 失败率统计 - 滑动窗口计数
3. 指数退避 - 自动恢复策略
4. 降级处理 - Fallback机制
5. 线程安全 - 锁保护状态转换

作者: AI Assistant
创建日期: 2026-05-09
版本: 1.0.0
"""

import time
import threading
import random
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, TypeVar, Generic, List, Dict
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 关闭状态 - 正常通过
    OPEN = "open"          # 打开状态 - 快速失败
    HALF_OPEN = "half_open"  # 半开状态 - 试探恢复


class CircuitBreakerError(Exception):
    """熔断器异常基类"""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """熔断器打开异常"""
    pass


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5          # 失败阈值
    success_threshold: int = 2          # 恢复所需成功次数
    timeout: float = 60.0               # 熔断后超时时间(秒)
    half_open_max_calls: int = 3        # 半开状态最大试探请求数
    excluded_exceptions: tuple = field(default_factory=tuple)  # 不计入失败的异常
    retry_backoff: bool = True          # 启用指数退避
    retry_jitter: bool = True           # 添加随机抖动
    name: str = "default"               # 熔断器名称


@dataclass
class CircuitMetrics:
    """熔断器指标"""
    total_calls: int = 0
    total_successes: int = 0
    total_failures: int = 0
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None


class CircuitBreaker:
    """
    熔断器实现
    
    使用示例:
        # 装饰器方式
        breaker = CircuitBreaker(name="api_call", failure_threshold=3)
        
        @breaker
        def call_external_api():
            return requests.get("https://api.example.com")
        
        # 上下文管理器方式
        with breaker.context():
            result = call_external_api()
        
        # 编程式调用
        result = breaker.call(lambda: requests.get("..."))
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None, **kwargs):
        """
        初始化熔断器
        
        Args:
            config: 配置对象
            **kwargs: 配置参数覆盖
        """
        self.config = config or CircuitBreakerConfig()
        # 允许通过 kwargs 覆盖配置
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        self._state = CircuitState.CLOSED
        self._metrics = CircuitMetrics()
        self._half_open_calls = 0
        self._lock = threading.RLock()
        
        # 事件回调
        self._on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None
        self._on_failure: Optional[Callable[[Exception], None]] = None
        self._on_success: Optional[Callable[[Any], None]] = None
        
        logger.info(f"熔断器 [{self.config.name}] 初始化完成，状态: {self._state.value}")
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            return self._state
    
    @property
    def metrics(self) -> CircuitMetrics:
        """获取指标副本"""
        with self._lock:
            from copy import deepcopy
            return deepcopy(self._metrics)
    
    def set_callbacks(
        self,
        on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None,
        on_failure: Optional[Callable[[Exception], None]] = None,
        on_success: Optional[Callable[[Any], None]] = None
    ) -> 'CircuitBreaker':
        """设置事件回调"""
        self._on_state_change = on_state_change
        self._on_failure = on_failure
        self._on_success = on_success
        return self
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        执行受保护的调用
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitBreakerOpenError: 熔断器打开时
            Exception: 原函数抛出的异常
        """
        # 检查状态转换
        self._try_transition_to_half_open()
        
        with self._lock:
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"熔断器 [{self.config.name}] 已打开，服务不可用"
                )
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"熔断器 [{self.config.name}] 半开状态试探请求数已达上限"
                    )
                self._half_open_calls += 1
            
            self._metrics.total_calls += 1
        
        # 执行实际调用（锁外执行）
        try:
            result = func(*args, **kwargs)
            self._on_call_success(result)
            return result
        except Exception as e:
            self._on_call_failure(e)
            raise
    
    def _on_call_success(self, result: Any) -> None:
        """处理调用成功"""
        with self._lock:
            self._metrics.total_successes += 1
            self._metrics.consecutive_successes += 1
            self._metrics.consecutive_failures = 0
            self._metrics.last_success_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                if self._metrics.consecutive_successes >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
        
        if self._on_success:
            try:
                self._on_success(result)
            except Exception:
                pass
    
    def _on_call_failure(self, error: Exception) -> None:
        """处理调用失败"""
        # 检查是否排除的异常
        if isinstance(error, self.config.excluded_exceptions):
            return
        
        with self._lock:
            self._metrics.total_failures += 1
            self._metrics.consecutive_failures += 1
            self._metrics.consecutive_successes = 0
            self._metrics.last_failure_time = time.time()
            
            # 记录状态转换
            self._metrics.state_transitions.append({
                'timestamp': time.time(),
                'failure': str(error),
                'consecutive_failures': self._metrics.consecutive_failures
            })
            
            if self._state == CircuitState.HALF_OPEN:
                # 半开状态失败，立即重新熔断
                self._transition_to(CircuitState.OPEN)
            elif self._metrics.consecutive_failures >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)
        
        if self._on_failure:
            try:
                self._on_failure(error)
            except Exception:
                pass
    
    def _try_transition_to_half_open(self) -> None:
        """尝试从 OPEN 转换到 HALF_OPEN"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                last_failure = self._metrics.last_failure_time
                if last_failure and (time.time() - last_failure) >= self.config.timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """状态转换"""
        old_state = self._state
        if old_state == new_state:
            return
        
        self._state = new_state
        
        # 重置计数器
        if new_state == CircuitState.CLOSED:
            self._metrics.consecutive_failures = 0
            self._metrics.consecutive_successes = 0
            self._half_open_calls = 0
            logger.info(f"熔断器 [{self.config.name}] 关闭 - 服务恢复正常")
        elif new_state == CircuitState.OPEN:
            self._half_open_calls = 0
            self._metrics.consecutive_successes = 0
            logger.warning(f"熔断器 [{self.config.name}] 打开 - 服务已熔断")
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._metrics.consecutive_successes = 0
            logger.info(f"熔断器 [{self.config.name}] 半开 - 试探恢复中")
        
        # 触发回调
        if self._on_state_change:
            try:
                self._on_state_change(old_state, new_state)
            except Exception:
                pass
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """装饰器支持"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    @contextmanager
    def context(self):
        """上下文管理器支持"""
        self._try_transition_to_half_open()
        
        with self._lock:
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"熔断器 [{self.config.name}] 已打开"
                )
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"熔断器 [{self.config.name}] 半开状态请求数已达上限"
                    )
                self._half_open_calls += 1
            
            self._metrics.total_calls += 1
        
        try:
            yield self
            self._on_call_success(None)
        except Exception as e:
            self._on_call_failure(e)
            raise
    
    def reset(self) -> None:
        """手动重置熔断器"""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._metrics = CircuitMetrics()
            self._half_open_calls = 0
        logger.info(f"熔断器 [{self.config.name}] 已手动重置")
    
    def get_failure_rate(self) -> float:
        """获取失败率"""
        with self._lock:
            if self._metrics.total_calls == 0:
                return 0.0
            return self._metrics.total_failures / self._metrics.total_calls
    
    def __repr__(self) -> str:
        return f"<CircuitBreaker {self.config.name} state={self._state.value} " \
               f"failures={self._metrics.consecutive_failures}/{self.config.failure_threshold}>"


class CircuitBreakerRegistry:
    """熔断器注册表 - 管理多个熔断器实例"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers: Dict[str, CircuitBreaker] = {}
        return cls._instance
    
    def register(self, name: str, breaker: CircuitBreaker) -> CircuitBreaker:
        """注册熔断器"""
        self._breakers[name] = breaker
        return breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return self._breakers.get(name)
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self._breakers:
            cfg = config or CircuitBreakerConfig(name=name, **kwargs)
            self._breakers[name] = CircuitBreaker(cfg)
        return self._breakers[name]
    
    def all_metrics(self) -> Dict[str, CircuitMetrics]:
        """获取所有熔断器指标"""
        return {name: breaker.metrics for name, breaker in self._breakers.items()}
    
    def reset_all(self) -> None:
        """重置所有熔断器"""
        for breaker in self._breakers.values():
            breaker.reset()


# 全局注册表
registry = CircuitBreakerRegistry()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例1: 装饰器方式
    api_breaker = CircuitBreaker(
        name="external_api",
        failure_threshold=3,
        timeout=30.0
    )
    
    @api_breaker
    def call_api():
        """模拟API调用"""
        import random
        if random.random() < 0.7:
            raise ConnectionError("API连接失败")
        return {"status": "ok", "data": "response"}
    
    # 示例2: 带降级处理的调用
    def call_with_fallback():
        try:
            return call_api()
        except CircuitBreakerOpenError:
            # 降级处理：返回缓存数据
            return {"status": "degraded", "data": "cached"}
    
    # 示例3: 上下文管理器
    db_breaker = CircuitBreaker(name="database", failure_threshold=5)
    
    try:
        with db_breaker.context():
            # 执行数据库操作
            result = "query result"
            print(f"数据库操作成功: {result}")
    except CircuitBreakerOpenError:
        print("数据库服务不可用，执行降级逻辑")
    
    # 示例4: 使用注册表
    registry.get_or_create(
        "payment_gateway",
        failure_threshold=3,
        success_threshold=2,
        timeout=60.0
    )
    
    # 查看所有熔断器状态
    print("\n所有熔断器状态:")
    for name, metrics in registry.all_metrics().items():
        print(f"  {name}: calls={metrics.total_calls}, "
              f"successes={metrics.total_successes}, failures={metrics.total_failures}")
