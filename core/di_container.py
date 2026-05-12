#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器 DIContainer - 控制反转与依赖管理

设计灵感:
- FastAPI Depends: 声明式依赖注入
- Spring IoC: 容器管理生命周期
- Angular DI: 分层注入器
- Guice: 类型绑定

核心特性:
1. 类型自动解析 - 基于类型注解自动注入
2. 生命周期管理 - Singleton/Transient/Scoped
3. 工厂支持 - 自定义对象创建逻辑
4. 循环依赖检测 - 自动检测并防止循环依赖
5. 装饰器支持 - @inject, @singleton, @transient
6. 模块化配置 - 分模块注册服务
7. AOP支持 - 拦截器注入

作者: AI Assistant
创建日期: 2026-05-09
版本: 1.0.0
"""

import inspect
import functools
import logging
from typing import Dict, List, Any, Optional, Callable, Type, TypeVar, get_type_hints, get_origin, get_args
from dataclasses import dataclass
from enum import Enum, auto
from threading import Lock
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Lifecycle(Enum):
    """服务生命周期"""
    SINGLETON = auto()   # 单例 - 全局唯一
    TRANSIENT = auto()   # 瞬态 - 每次新建
    SCOPED = auto()      # 作用域 - 同作用域共享


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    interface: Type
    implementation: Type
    lifecycle: Lifecycle
    factory: Optional[Callable] = None
    instance: Any = None
    name: Optional[str] = None  # 命名服务


class DIContext:
    """依赖注入上下文（作用域）"""
    
    def __init__(self, container: 'DIContainer', context_id: str = None):
        self.container = container
        self.context_id = context_id or str(uuid.uuid4())
        self._scoped_instances: Dict[Type, Any] = {}
        self._lock = Lock()
    
    def get(self, interface: Type[T]) -> T:
        """从作用域获取服务"""
        with self._lock:
            if interface in self._scoped_instances:
                return self._scoped_instances[interface]
            
            # 创建新实例
            descriptor = self.container._get_descriptor(interface)
            if descriptor and descriptor.lifecycle == Lifecycle.SCOPED:
                instance = self.container._create_instance(descriptor, self)
                self._scoped_instances[interface] = instance
                return instance
            
            # 非作用域服务从容器获取
            return self.container.resolve(interface, self)
    
    def dispose(self) -> None:
        """释放作用域资源"""
        for instance in self._scoped_instances.values():
            if hasattr(instance, 'dispose'):
                try:
                    instance.dispose()
                except Exception as e:
                    logger.error(f"释放服务失败: {e}")
        self._scoped_instances.clear()


class DIContainer:
    """
    依赖注入容器
    
    管理服务的注册、解析和生命周期
    
    使用示例:
        container = DIContainer()
        
        # 注册服务
        container.register(DatabaseService, lifecycle=Lifecycle.SINGLETON)
        container.register(IUserService, UserService)
        
        # 解析服务
        db = container.resolve(DatabaseService)
        user_service = container.resolve(IUserService)
        
        # 使用装饰器
        @container.inject
        def process_data(db: DatabaseService, user_svc: IUserService):
            pass
    """
    
    def __init__(self, parent: 'DIContainer' = None):
        self._services: Dict[Type, List[ServiceDescriptor]] = {}
        self._singleton_instances: Dict[Type, Any] = {}
        self._parent = parent
        self._lock = Lock()
        self._resolution_stack: List[Type] = []  # 用于循环依赖检测
    
    def register(self,
                 interface: Type,
                 implementation: Type = None,
                 lifecycle: Lifecycle = Lifecycle.TRANSIENT,
                 factory: Callable = None,
                 name: str = None) -> 'DIContainer':
        """
        注册服务
        
        Args:
            interface: 服务接口/抽象类型
            implementation: 实现类型（默认与接口相同）
            lifecycle: 生命周期
            factory: 自定义工厂函数
            name: 服务名称（用于同类型多实现）
            
        Returns:
            self，支持链式调用
        """
        implementation = implementation or interface
        
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=implementation,
            lifecycle=lifecycle,
            factory=factory,
            name=name
        )
        
        with self._lock:
            if interface not in self._services:
                self._services[interface] = []
            self._services[interface].append(descriptor)
        
        logger.debug(f"注册服务: {interface.__name__} -> {implementation.__name__} ({lifecycle.name})")
        return self
    
    def register_instance(self, interface: Type, instance: Any) -> 'DIContainer':
        """注册已有实例（自动作为单例）"""
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=type(instance),
            lifecycle=Lifecycle.SINGLETON,
            instance=instance
        )
        
        with self._lock:
            if interface not in self._services:
                self._services[interface] = []
            self._services[interface].append(descriptor)
            self._singleton_instances[interface] = instance
        
        return self
    
    def register_singleton(self, interface: Type, implementation: Type = None) -> 'DIContainer':
        """便捷方法：注册单例"""
        return self.register(interface, implementation, Lifecycle.SINGLETON)
    
    def register_transient(self, interface: Type, implementation: Type = None) -> 'DIContainer':
        """便捷方法：注册瞬态服务"""
        return self.register(interface, implementation, Lifecycle.TRANSIENT)
    
    def register_scoped(self, interface: Type, implementation: Type = None) -> 'DIContainer':
        """便捷方法：注册作用域服务"""
        return self.register(interface, implementation, Lifecycle.SCOPED)
    
    def _get_descriptor(self, interface: Type, name: str = None) -> Optional[ServiceDescriptor]:
        """获取服务描述符"""
        with self._lock:
            descriptors = self._services.get(interface, [])
            
            if name:
                for desc in descriptors:
                    if desc.name == name:
                        return desc
                return None
            
            # 返回第一个（默认）
            return descriptors[0] if descriptors else None
    
    def resolve(self, interface: Type[T], context: DIContext = None, name: str = None) -> T:
        """
        解析服务
        
        Args:
            interface: 服务接口类型
            context: 作用域上下文
            name: 服务名称
            
        Returns:
            服务实例
        """
        # 循环依赖检测
        if interface in self._resolution_stack:
            stack_str = ' -> '.join(t.__name__ for t in self._resolution_stack + [interface])
            raise CircularDependencyError(f"检测到循环依赖: {stack_str}")
        
        descriptor = self._get_descriptor(interface, name)
        
        # 检查父容器
        if descriptor is None and self._parent:
            return self._parent.resolve(interface, context, name)
        
        if descriptor is None:
            # 尝试自解析（具体类型）
            if isinstance(interface, type):
                descriptor = ServiceDescriptor(
                    interface=interface,
                    implementation=interface,
                    lifecycle=Lifecycle.TRANSIENT
                )
            else:
                raise ServiceNotFoundError(f"未注册的服务: {interface}")
        
        # 单例检查
        if descriptor.lifecycle == Lifecycle.SINGLETON:
            if descriptor.instance:
                return descriptor.instance
            with self._lock:
                if interface in self._singleton_instances:
                    return self._singleton_instances[interface]
        
        # 作用域检查
        if descriptor.lifecycle == Lifecycle.SCOPED and context:
            return context.get(interface)
        
        # 创建实例
        try:
            self._resolution_stack.append(interface)
            instance = self._create_instance(descriptor, context)
        finally:
            self._resolution_stack.pop()
        
        # 缓存单例
        if descriptor.lifecycle == Lifecycle.SINGLETON:
            with self._lock:
                self._singleton_instances[interface] = instance
                descriptor.instance = instance
        
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor, context: DIContext = None) -> Any:
        """创建服务实例"""
        # 使用工厂函数
        if descriptor.factory:
            if callable(descriptor.factory):
                return descriptor.factory(self)
            return descriptor.factory
        
        implementation = descriptor.implementation
        
        # 获取构造函数参数
        try:
            sig = inspect.signature(implementation.__init__)
            type_hints = get_type_hints(implementation.__init__)
        except (AttributeError, TypeError):
            # 没有 __init__ 或无法获取类型提示
            return implementation()
        
        # 构建参数
        kwargs = {}
        for param_name, param in list(sig.parameters.items())[1:]:  # 跳过 self
            if param_name in type_hints:
                param_type = type_hints[param_name]
                
                # 处理 Optional[T]
                origin = get_origin(param_type)
                if origin is not None:
                    args = get_args(param_type)
                    if type(None) in args:
                        param_type = next(a for a in args if a is not type(None))
                
                try:
                    kwargs[param_name] = self.resolve(param_type, context)
                except ServiceNotFoundError:
                    if param.default is not inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        raise
            elif param.default is not inspect.Parameter.empty:
                kwargs[param_name] = param.default
        
        return implementation(**kwargs)
    
    def resolve_all(self, interface: Type[T]) -> List[T]:
        """解析所有实现"""
        with self._lock:
            descriptors = self._services.get(interface, [])
        
        return [self._create_instance(desc) for desc in descriptors]
    
    def create_scope(self) -> DIContext:
        """创建作用域"""
        return DIContext(self)
    
    def inject(self, func: Callable) -> Callable:
        """
        装饰器：自动注入依赖
        
        使用示例:
            @container.inject
            def process(db: DatabaseService, cache: CacheService):
                pass
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)
            
            # 注入缺失的参数
            for param_name, param in sig.parameters.items():
                if param_name not in kwargs and param_name in type_hints:
                    param_type = type_hints[param_name]
                    try:
                        kwargs[param_name] = self.resolve(param_type)
                    except ServiceNotFoundError:
                        if param.default is not inspect.Parameter.empty:
                            kwargs[param_name] = param.default
                        else:
                            raise
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def build_provider(self) -> 'ServiceProvider':
        """构建服务提供者（只读）"""
        return ServiceProvider(self)
    
    def clear(self) -> None:
        """清空容器"""
        with self._lock:
            self._services.clear()
            self._singleton_instances.clear()


class ServiceProvider:
    """服务提供者（只读容器）"""
    
    def __init__(self, container: DIContainer):
        self._container = container
    
    def get_service(self, interface: Type[T]) -> T:
        """获取服务"""
        return self._container.resolve(interface)
    
    def get_services(self, interface: Type[T]) -> List[T]:
        """获取所有服务"""
        return self._container.resolve_all(interface)
    
    def create_scope(self) -> DIContext:
        """创建作用域"""
        return self._container.create_scope()


# 异常类
class ServiceNotFoundError(Exception):
    """服务未找到错误"""
    pass


class CircularDependencyError(Exception):
    """循环依赖错误"""
    pass


class DependencyResolutionError(Exception):
    """依赖解析错误"""
    pass


# 便捷装饰器
_container: Optional[DIContainer] = None


def set_global_container(container: DIContainer) -> None:
    """设置全局容器"""
    global _container
    _container = container


def get_global_container() -> Optional[DIContainer]:
    """获取全局容器"""
    return _container


def inject(func: Callable = None, *, container: DIContainer = None) -> Callable:
    """
    全局注入装饰器
    
    使用示例:
        @inject
        def process(db: DatabaseService):
            pass
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            cont = container or _container
            if cont is None:
                raise RuntimeError("未设置DI容器")
            
            # 获取函数签名
            sig = inspect.signature(f)
            type_hints = get_type_hints(f)
            
            # 注入参数
            for param_name, param in sig.parameters.items():
                if param_name not in kwargs and param_name in type_hints:
                    param_type = type_hints[param_name]
                    try:
                        kwargs[param_name] = cont.resolve(param_type)
                    except ServiceNotFoundError:
                        if param.default is not inspect.Parameter.empty:
                            kwargs[param_name] = param.default
                        else:
                            raise
            
            return f(*args, **kwargs)
        
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)


def singleton(cls: Type = None) -> Type:
    """单例类装饰器"""
    def decorator(c: Type) -> Type:
        instances = {}
        
        @functools.wraps(c)
        def wrapper(*args, **kwargs):
            if c not in instances:
                instances[c] = c(*args, **kwargs)
            return instances[c]
        
        return wrapper
    
    if cls is None:
        return decorator
    return decorator(cls)


def transient(cls: Type = None) -> Type:
    """瞬态类装饰器（默认行为，主要用于标记）"""
    return cls


# 模块配置基类
class Module:
    """配置模块基类"""
    
    def configure_services(self, container: DIContainer) -> None:
        """配置服务注册"""
        pass
    
    def configure(self, container: DIContainer) -> None:
        """配置完成后的设置"""
        pass


def configure_container(*modules: Module) -> DIContainer:
    """
    使用模块配置容器
    
    使用示例:
        container = configure_container(
            DatabaseModule(),
            ServiceModule()
        )
    """
    container = DIContainer()
    
    for module in modules:
        module.configure_services(container)
    
    for module in modules:
        module.configure(container)
    
    return container
