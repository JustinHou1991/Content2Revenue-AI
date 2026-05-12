#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中间件管理器 MiddlewareManager - 请求/响应拦截处理系统

设计灵感:
- Django Middleware: 请求/响应处理链
- Express.js Middleware: 洋葱模型中间件
- Koa.js: 异步中间件组合

核心特性:
1. 洋葱模型 - 支持前置处理和后置处理
2. 异步支持 - 完全支持 async/await
3. 条件执行 - 基于条件的中间件触发
4. 错误处理 - 统一的错误处理中间件
5. 优先级排序 - 中间件执行顺序控制
6. 短路机制 - 支持提前返回响应
7. 上下文共享 - 请求级数据共享

作者: AI Assistant
创建日期: 2026-05-09
版本: 1.0.0
"""

import asyncio
import functools
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from contextvars import ContextVar
import time
import traceback

logger = logging.getLogger(__name__)

# 上下文变量，用于在中间件链中共享数据
_request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class MiddlewarePhase(Enum):
    """中间件执行阶段"""
    BEFORE = "before"      # 前置处理
    AFTER = "after"        # 后置处理
    AROUND = "around"      # 环绕处理（洋葱模型）
    ERROR = "error"        # 错误处理


@dataclass
class MiddlewareConfig:
    """中间件配置"""
    name: str
    priority: int = 100           # 优先级，数字越小越先执行
    condition: Optional[Callable] = None  # 执行条件
    exclude_paths: List[str] = field(default_factory=list)  # 排除路径
    include_paths: List[str] = field(default_factory=list)  # 包含路径（空表示全部）
    enabled: bool = True          # 是否启用
    timeout: Optional[float] = None  # 超时时间（秒）


class MiddlewareContext:
    """
    中间件上下文
    
    在中间件链中传递的上下文对象，包含请求信息、响应数据、共享状态等
    """
    
    def __init__(self, request: Any = None, metadata: Dict = None):
        self.request = request
        self.response: Any = None
        self.metadata = metadata or {}
        self.data: Dict[str, Any] = {}  # 共享数据存储
        self.errors: List[Exception] = []
        self.start_time: float = time.time()
        self.finished: bool = False
        self.short_circuit: bool = False  # 是否短路
        self._state: Dict[str, Any] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取共享数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置共享数据"""
        self.data[key] = value
    
    def add_error(self, error: Exception) -> None:
        """添加错误"""
        self.errors.append(error)
        logger.error(f"中间件错误: {error}")
    
    def elapsed_time(self) -> float:
        """获取已执行时间"""
        return time.time() - self.start_time
    
    def finish(self, response: Any = None) -> None:
        """标记完成"""
        self.finished = True
        if response is not None:
            self.response = response
    
    def copy(self) -> 'MiddlewareContext':
        """创建上下文副本"""
        new_ctx = MiddlewareContext(self.request, self.metadata.copy())
        new_ctx.data = self.data.copy()
        return new_ctx


class Middleware:
    """
    中间件基类
    
    所有中间件应继承此类，实现 process 方法
    """
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        self.config = config or MiddlewareConfig(name=self.__class__.__name__)
        self._next_middleware: Optional['Middleware'] = None
    
    async def process(self, context: MiddlewareContext) -> Any:
        """
        处理请求
        
        Args:
            context: 中间件上下文
            
        Returns:
            处理结果
        """
        raise NotImplementedError("子类必须实现 process 方法")
    
    def should_execute(self, context: MiddlewareContext) -> bool:
        """检查是否应该执行此中间件"""
        if not self.config.enabled:
            return False
        
        if self.config.condition and not self.config.condition(context):
            return False
        
        # 路径检查
        path = getattr(context.request, 'path', '') or context.metadata.get('path', '')
        if path:
            if self.config.exclude_paths:
                if any(path.startswith(exclude) for exclude in self.config.exclude_paths):
                    return False
            if self.config.include_paths:
                if not any(path.startswith(include) for include in self.config.include_paths):
                    return False
        
        return True
    
    async def __call__(self, context: MiddlewareContext) -> Any:
        """调用中间件"""
        if not self.should_execute(context):
            if self._next_middleware:
                return await self._next_middleware(context)
            return context.response
        
        try:
            # 设置超时
            if self.config.timeout:
                result = await asyncio.wait_for(
                    self.process(context),
                    timeout=self.config.timeout
                )
            else:
                result = await self.process(context)
            
            # 如果短路，直接返回
            if context.short_circuit:
                return result
            
            # 调用下一个中间件
            if self._next_middleware:
                return await self._next_middleware(context)
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"中间件 {self.config.name} 执行超时")
            context.add_error(asyncio.TimeoutError(f"中间件 {self.config.name} 超时"))
            raise
        except Exception as e:
            logger.error(f"中间件 {self.config.name} 执行错误: {e}")
            context.add_error(e)
            raise
    
    def set_next(self, middleware: 'Middleware') -> 'Middleware':
        """设置下一个中间件"""
        self._next_middleware = middleware
        return middleware


class FunctionMiddleware(Middleware):
    """函数式中间件包装器"""
    
    def __init__(self, func: Callable, config: Optional[MiddlewareConfig] = None):
        name = config.name if config else func.__name__
        super().__init__(config or MiddlewareConfig(name=name))
        self.func = func
    
    async def process(self, context: MiddlewareContext) -> Any:
        """执行函数"""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(context)
        else:
            return self.func(context)


class ErrorHandlerMiddleware(Middleware):
    """错误处理中间件"""
    
    def __init__(self, error_handlers: Dict[type, Callable] = None):
        super().__init__(MiddlewareConfig(name="ErrorHandler", priority=0))
        self.error_handlers = error_handlers or {}
    
    async def process(self, context: MiddlewareContext) -> Any:
        """错误处理逻辑在异常捕获中执行"""
        return context.response
    
    async def __call__(self, context: MiddlewareContext) -> Any:
        """包装调用，捕获异常"""
        try:
            if self._next_middleware:
                return await self._next_middleware(context)
            return context.response
        except Exception as e:
            handler = self._find_handler(e)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(e, context)
                else:
                    return handler(e, context)
            raise
    
    def _find_handler(self, error: Exception) -> Optional[Callable]:
        """查找错误处理器"""
        for error_type, handler in self.error_handlers.items():
            if isinstance(error, error_type):
                return handler
        return None


class LoggingMiddleware(Middleware):
    """日志记录中间件"""
    
    def __init__(self, log_level: int = logging.INFO):
        super().__init__(MiddlewareConfig(name="Logger", priority=10))
        self.log_level = log_level
    
    async def process(self, context: MiddlewareContext) -> Any:
        """记录请求信息"""
        logger.log(self.log_level, f"请求开始: {context.metadata}")
        context.set('start_time', time.time())
        
        # 让后续中间件执行
        if self._next_middleware:
            result = await self._next_middleware(context)
        else:
            result = context.response
        
        # 记录完成信息
        elapsed = time.time() - context.get('start_time', time.time())
        logger.log(self.log_level, f"请求完成: 耗时 {elapsed:.3f}s")
        
        return result


class AuthenticationMiddleware(Middleware):
    """认证中间件示例"""
    
    def __init__(self, auth_func: Callable, excluded_paths: List[str] = None):
        super().__init__(MiddlewareConfig(
            name="Auth",
            priority=20,
            exclude_paths=excluded_paths or ['/login', '/register']
        ))
        self.auth_func = auth_func
    
    async def process(self, context: MiddlewareContext) -> Any:
        """执行认证"""
        request = context.request
        
        # 获取 token
        token = getattr(request, 'headers', {}).get('Authorization') or \
                context.metadata.get('token')
        
        if not token:
            context.short_circuit = True
            context.response = {'error': '未提供认证令牌', 'code': 401}
            return context.response
        
        # 验证 token
        try:
            user = await self.auth_func(token) if asyncio.iscoroutinefunction(self.auth_func) \
                   else self.auth_func(token)
            context.set('user', user)
        except Exception as e:
            context.short_circuit = True
            context.response = {'error': f'认证失败: {str(e)}', 'code': 401}
            return context.response
        
        # 继续执行
        if self._next_middleware:
            return await self._next_middleware(context)
        return context.response


class RateLimitMiddleware(Middleware):
    """限流中间件"""
    
    def __init__(self, max_requests: int = 100, window: int = 60):
        super().__init__(MiddlewareConfig(name="RateLimit", priority=15))
        self.max_requests = max_requests
        self.window = window
        self._requests: Dict[str, List[float]] = {}
    
    async def process(self, context: MiddlewareContext) -> Any:
        """检查限流"""
        client_id = self._get_client_id(context)
        now = time.time()
        
        # 清理过期记录
        if client_id in self._requests:
            self._requests[client_id] = [
                t for t in self._requests[client_id]
                if now - t < self.window
            ]
        else:
            self._requests[client_id] = []
        
        # 检查是否超限
        if len(self._requests[client_id]) >= self.max_requests:
            context.short_circuit = True
            context.response = {
                'error': '请求过于频繁',
                'code': 429,
                'retry_after': self.window
            }
            return context.response
        
        # 记录请求
        self._requests[client_id].append(now)
        
        # 继续执行
        if self._next_middleware:
            return await self._next_middleware(context)
        return context.response
    
    def _get_client_id(self, context: MiddlewareContext) -> str:
        """获取客户端标识"""
        request = context.request
        return getattr(request, 'client_ip', None) or \
               context.metadata.get('client_id', 'unknown')


class MiddlewareManager:
    """
    中间件管理器
    
    管理中间件的注册、排序和执行
    
    使用示例:
        manager = MiddlewareManager()
        
        # 注册中间件
        manager.use(LoggingMiddleware())
        manager.use(AuthenticationMiddleware(auth_func))
        
        # 执行
        @manager.wrap
        async def handle_request(request):
            return {'data': 'response'}
    """
    
    def __init__(self):
        self._middlewares: List[Middleware] = []
        self._error_handlers: Dict[type, Callable] = {}
        self._global_config: Dict[str, Any] = {}
    
    def use(self, middleware: Union[Middleware, Callable], 
            config: Optional[MiddlewareConfig] = None) -> 'MiddlewareManager':
        """
        注册中间件
        
        Args:
            middleware: 中间件实例或函数
            config: 中间件配置
            
        Returns:
            self，支持链式调用
        """
        if callable(middleware) and not isinstance(middleware, Middleware):
            middleware = FunctionMiddleware(middleware, config)
        elif config and isinstance(middleware, Middleware):
            middleware.config = config
        
        self._middlewares.append(middleware)
        self._sort_middlewares()
        return self
    
    def use_many(self, *middlewares: Middleware) -> 'MiddlewareManager':
        """批量注册中间件"""
        for mw in middlewares:
            self.use(mw)
        return self
    
    def remove(self, name: str) -> bool:
        """移除指定名称的中间件"""
        for i, mw in enumerate(self._middlewares):
            if mw.config.name == name:
                self._middlewares.pop(i)
                return True
        return False
    
    def enable(self, name: str) -> bool:
        """启用中间件"""
        for mw in self._middlewares:
            if mw.config.name == name:
                mw.config.enabled = True
                return True
        return False
    
    def disable(self, name: str) -> bool:
        """禁用中间件"""
        for mw in self._middlewares:
            if mw.config.name == name:
                mw.config.enabled = False
                return True
        return False
    
    def _sort_middlewares(self) -> None:
        """按优先级排序中间件"""
        self._middlewares.sort(key=lambda m: m.config.priority)
    
    def _build_chain(self) -> Optional[Middleware]:
        """构建中间件链"""
        if not self._middlewares:
            return None
        
        # 创建错误处理中间件（最外层）
        error_handler = ErrorHandlerMiddleware(self._error_handlers)
        
        # 构建链
        enabled_middlewares = [m for m in self._middlewares if m.config.enabled]
        if not enabled_middlewares:
            return error_handler
        
        # 连接中间件
        for i in range(len(enabled_middlewares) - 1):
            enabled_middlewares[i].set_next(enabled_middlewares[i + 1])
        
        # 错误处理器在最外层
        error_handler.set_next(enabled_middlewares[0])
        
        return error_handler
    
    async def execute(self, request: Any = None, 
                      metadata: Dict = None) -> Any:
        """
        执行中间件链
        
        Args:
            request: 请求对象
            metadata: 元数据
            
        Returns:
            处理结果
        """
        context = MiddlewareContext(request, metadata)
        chain = self._build_chain()
        
        if chain:
            return await chain(context)
        return None
    
    def wrap(self, handler: Callable) -> Callable:
        """
        包装处理器
        
        Args:
            handler: 最终处理器函数
            
        Returns:
            包装后的函数
        """
        async def wrapper(request: Any = None, **kwargs):
            context = MiddlewareContext(request, kwargs)
            chain = self._build_chain()
            
            if chain:
                try:
                    result = await chain(context)
                    if context.short_circuit:
                        return result
                except Exception as e:
                    logger.error(f"中间件链执行错误: {e}")
                    raise
            
            # 执行最终处理器
            if asyncio.iscoroutinefunction(handler):
                return await handler(request, **kwargs)
            else:
                return handler(request, **kwargs)
        
        return wrapper
    
    def error_handler(self, error_type: type):
        """
        装饰器：注册错误处理器
        
        使用示例:
            @manager.error_handler(ValueError)
            def handle_value_error(error, context):
                return {'error': str(error)}
        """
        def decorator(func: Callable):
            self._error_handlers[error_type] = func
            return func
        return decorator
    
    def get_middlewares(self) -> List[Middleware]:
        """获取所有中间件"""
        return self._middlewares.copy()
    
    def clear(self) -> None:
        """清空所有中间件"""
        self._middlewares.clear()
        self._error_handlers.clear()


# 便捷函数
def create_middleware_chain(*middlewares: Middleware) -> MiddlewareManager:
    """创建中间件链"""
    manager = MiddlewareManager()
    manager.use_many(*middlewares)
    return manager
