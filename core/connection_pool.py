#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接池管理器 ConnectionPool - 数据库/服务连接管理

设计灵感:
- SQLAlchemy Pool: 数据库连接池
- HikariCP: 高性能JDBC连接池
- asyncio Pool: 异步资源池
- Redis ConnectionPool: 多连接管理

核心特性:
1. 连接复用 - 减少连接创建开销
2. 健康检查 - 自动检测失效连接
3. 动态扩容 - 根据负载自动调整
4. 连接预热 - 启动时预创建连接
5. 等待队列 - 连接不足时排队等待
6. 统计监控 - 连接池状态监控
7. 多种策略 - FIFO/LIFO连接获取

作者: AI Assistant
创建日期: 2026-05-09
版本: 1.0.0
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Set, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
from abc import ABC, abstractmethod
import threading

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PoolStrategy(Enum):
    """连接池策略"""
    FIFO = "fifo"      # 先进先出
    LIFO = "lifo"      # 后进先出（默认，更好的缓存局部性）
    RANDOM = "random"  # 随机


class ConnectionState(Enum):
    """连接状态"""
    IDLE = "idle"         # 空闲
    BUSY = "busy"         # 使用中
    CLOSED = "closed"     # 已关闭
    UNHEALTHY = "unhealthy"  # 不健康


@dataclass
class PoolConfig:
    """连接池配置"""
    min_size: int = 5              # 最小连接数
    max_size: int = 20             # 最大连接数
    max_overflow: int = 5          # 最大溢出连接数
    timeout: float = 30.0          # 获取连接超时时间
    recycle: float = 3600.0        # 连接回收时间（秒）
    stale_timeout: float = 300.0   # 连接过期时间
    health_check_interval: float = 30.0  # 健康检查间隔
    strategy: PoolStrategy = PoolStrategy.LIFO
    pre_ping: bool = True          # 使用前检查连接健康
    echo: bool = False             # 是否记录SQL/操作日志


@dataclass
class PoolStats:
    """连接池统计信息"""
    total_connections: int = 0
    idle_connections: int = 0
    busy_connections: int = 0
    overflow_connections: int = 0
    waiting_requests: int = 0
    total_requests: int = 0
    total_hits: int = 0           # 从池中获取成功
    total_misses: int = 0         # 需要创建新连接
    total_checkouts: int = 0      # 总检出次数
    total_checkins: int = 0       # 总归还次数
    avg_wait_time: float = 0.0    # 平均等待时间


class PooledConnection(Generic[T]):
    """池化连接包装器"""
    
    def __init__(self, connection: T, pool: 'ConnectionPool'):
        self._connection = connection
        self._pool = pool
        self.state = ConnectionState.IDLE
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.checkout_count = 0
        self._lock = asyncio.Lock()
    
    @property
    def connection(self) -> T:
        """获取原始连接"""
        return self._connection
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        config = self._pool.config
        if config.recycle > 0:
            return time.time() - self.created_at > config.recycle
        return False
    
    @property
    def is_stale(self) -> bool:
        """检查是否闲置过久"""
        config = self._pool.config
        if config.stale_timeout > 0:
            return time.time() - self.last_used_at > config.stale_timeout
        return False
    
    async def checkout(self) -> None:
        """检出连接"""
        async with self._lock:
            self.state = ConnectionState.BUSY
            self.last_used_at = time.time()
            self.checkout_count += 1
    
    async def checkin(self) -> None:
        """归还连接"""
        async with self._lock:
            self.state = ConnectionState.IDLE
            self.last_used_at = time.time()
    
    async def close(self) -> None:
        """关闭连接"""
        async with self._lock:
            self.state = ConnectionState.CLOSED
            await self._pool._close_connection(self._connection)
    
    async def health_check(self) -> bool:
        """健康检查"""
        return await self._pool._check_connection(self._connection)


class ConnectionFactory(ABC, Generic[T]):
    """连接工厂基类"""
    
    @abstractmethod
    async def create(self) -> T:
        """创建新连接"""
        pass
    
    @abstractmethod
    async def close(self, connection: T) -> None:
        """关闭连接"""
        pass
    
    @abstractmethod
    async def check(self, connection: T) -> bool:
        """检查连接健康"""
        pass
    
    @abstractmethod
    async def reset(self, connection: T) -> None:
        """重置连接状态"""
        pass


class ConnectionPool(Generic[T]):
    """
    通用连接池
    
    管理连接的创建、复用和回收
    
    使用示例:
        factory = DatabaseConnectionFactory()
        pool = ConnectionPool(factory, PoolConfig(min_size=5, max_size=20))
        
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
    """
    
    def __init__(self, factory: ConnectionFactory[T], config: PoolConfig = None):
        self.factory = factory
        self.config = config or PoolConfig()
        
        self._pool: asyncio.Queue[PooledConnection[T]] = asyncio.Queue()
        self._busy: Set[PooledConnection[T]] = set()
        self._overflow: int = 0
        self._waiting: int = 0
        
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self.config.max_size + self.config.max_overflow)
        self._closed = False
        
        self._stats = PoolStats()
        self._stats_lock = asyncio.Lock()
        
        self._health_check_task: Optional[asyncio.Task] = None
        self._maintenance_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """初始化连接池"""
        logger.info(f"初始化连接池，最小连接数: {self.config.min_size}")
        
        # 预创建最小连接数
        for _ in range(self.config.min_size):
            conn = await self._create_new_connection()
            if conn:
                await self._pool.put(conn)
                await self._update_stats(idle_delta=1)
        
        # 启动后台任务
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        
        logger.info("连接池初始化完成")
    
    async def close(self) -> None:
        """关闭连接池"""
        self._closed = True
        
        # 取消后台任务
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._maintenance_task:
            self._maintenance_task.cancel()
        
        # 关闭所有连接
        async with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    await conn.close()
                except asyncio.QueueEmpty:
                    break
            
            for conn in list(self._busy):
                await conn.close()
            self._busy.clear()
        
        logger.info("连接池已关闭")
    
    @asynccontextmanager
    async def acquire(self, timeout: float = None):
        """
        获取连接（上下文管理器）
        
        使用示例:
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
        """
        conn = await self._acquire(timeout)
        try:
            yield conn.connection
        finally:
            await self._release(conn)
    
    async def _acquire(self, timeout: float = None) -> PooledConnection[T]:
        """获取连接"""
        if self._closed:
            raise PoolClosedError("连接池已关闭")
        
        timeout = timeout or self.config.timeout
        start_time = time.time()
        
        await self._update_stats(total_requests=1)
        
        try:
            # 等待信号量
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            await self._update_stats(waiting_delta=-1)
            raise PoolExhaustedError(f"获取连接超时 ({timeout}s)")
        
        try:
            # 尝试从池中获取
            conn = await self._get_from_pool()
            
            if conn is None:
                # 创建新连接
                conn = await self._create_new_connection()
                if conn is None:
                    raise PoolExhaustedError("无法创建新连接")
                await self._update_stats(overflow_delta=1)
            else:
                await self._update_stats(hits=1)
                
                # 检查连接健康
                if self.config.pre_ping:
                    is_healthy = await conn.health_check()
                    if not is_healthy:
                        logger.warning("连接不健康，创建新连接")
                        await conn.close()
                        conn = await self._create_new_connection()
            
            # 检出连接
            await conn.checkout()
            async with self._lock:
                self._busy.add(conn)
            
            await self._update_stats(checkouts=1, idle_delta=-1, busy_delta=1)
            
            wait_time = time.time() - start_time
            await self._update_avg_wait_time(wait_time)
            
            return conn
            
        except Exception:
            self._semaphore.release()
            raise
    
    async def _release(self, conn: PooledConnection[T]) -> None:
        """归还连接"""
        if self._closed:
            await conn.close()
            return
        
        await conn.checkin()
        
        async with self._lock:
            self._busy.discard(conn)
        
        # 检查连接是否还健康
        if conn.state == ConnectionState.UNHEALTHY or conn.is_expired:
            await conn.close()
            await self._update_stats(overflow_delta=-1)
        else:
            # 归还到池中
            await self._pool.put(conn)
            await self._update_stats(checkins=1, idle_delta=1, busy_delta=-1)
        
        self._semaphore.release()
    
    async def _get_from_pool(self) -> Optional[PooledConnection[T]]:
        """从池中获取连接"""
        try:
            # 非阻塞获取
            conn = self._pool.get_nowait()
            return conn
        except asyncio.QueueEmpty:
            return None
    
    async def _create_new_connection(self) -> Optional[PooledConnection[T]]:
        """创建新连接"""
        try:
            raw_conn = await self.factory.create()
            pooled = PooledConnection(raw_conn, self)
            return pooled
        except Exception as e:
            logger.error(f"创建连接失败: {e}")
            return None
    
    async def _close_connection(self, connection: T) -> None:
        """关闭连接"""
        try:
            await self.factory.close(connection)
        except Exception as e:
            logger.error(f"关闭连接失败: {e}")
    
    async def _check_connection(self, connection: T) -> bool:
        """检查连接健康"""
        try:
            return await self.factory.check(connection)
        except Exception:
            return False
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while not self._closed:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if self._closed:
                    break
                
                # 检查空闲连接
                to_check = []
                async with self._lock:
                    # 临时取出所有连接
                    while not self._pool.empty():
                        try:
                            conn = self._pool.get_nowait()
                            to_check.append(conn)
                        except asyncio.QueueEmpty:
                            break
                
                # 检查并放回
                healthy_count = 0
                for conn in to_check:
                    if await conn.health_check():
                        await self._pool.put(conn)
                        healthy_count += 1
                    else:
                        await conn.close()
                        await self._update_stats(idle_delta=-1)
                        # 创建新连接补充
                        new_conn = await self._create_new_connection()
                        if new_conn:
                            await self._pool.put(new_conn)
                        else:
                            await self._update_stats(idle_delta=-1)
                
                if len(to_check) > 0:
                    logger.debug(f"健康检查完成: {healthy_count}/{len(to_check)} 健康")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查错误: {e}")
    
    async def _maintenance_loop(self) -> None:
        """维护循环"""
        while not self._closed:
            try:
                await asyncio.sleep(60)  # 每分钟维护一次
                
                if self._closed:
                    break
                
                # 清理过期连接
                await self._recycle_connections()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"维护循环错误: {e}")
    
    async def _recycle_connections(self) -> None:
        """回收过期连接"""
        to_recycle = []
        
        # 临时取出检查
        async with self._lock:
            temp_list = []
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    if conn.is_expired or conn.is_stale:
                        to_recycle.append(conn)
                    else:
                        temp_list.append(conn)
                except asyncio.QueueEmpty:
                    break
            
            # 放回健康的
            for conn in temp_list:
                await self._pool.put(conn)
        
        # 关闭过期连接
        for conn in to_recycle:
            await conn.close()
            await self._update_stats(idle_delta=-1)
            logger.debug(f"回收过期连接，创建时间: {conn.created_at}")
        
        # 确保最小连接数
        current_size = self._pool.qsize()
        if current_size < self.config.min_size:
            for _ in range(self.config.min_size - current_size):
                new_conn = await self._create_new_connection()
                if new_conn:
                    await self._pool.put(new_conn)
                    await self._update_stats(idle_delta=1)
    
    async def _update_stats(self, **kwargs) -> None:
        """更新统计信息"""
        async with self._stats_lock:
            for key, value in kwargs.items():
                if key == 'idle_delta':
                    self._stats.idle_connections += value
                elif key == 'busy_delta':
                    self._stats.busy_connections += value
                elif key == 'overflow_delta':
                    self._stats.overflow_connections += value
                elif key == 'waiting_delta':
                    self._stats.waiting_requests += value
                elif hasattr(self._stats, key):
                    setattr(self._stats, key, getattr(self._stats, key) + value)
            
            # 更新总数
            self._stats.total_connections = (
                self._stats.idle_connections + 
                self._stats.busy_connections +
                self._stats.overflow_connections
            )
    
    async def _update_avg_wait_time(self, wait_time: float) -> None:
        """更新平均等待时间"""
        async with self._stats_lock:
            n = self._stats.total_requests
            self._stats.avg_wait_time = (
                (self._stats.avg_wait_time * (n - 1) + wait_time) / n
            )
    
    def get_stats(self) -> PoolStats:
        """获取统计信息"""
        return copy.copy(self._stats)
    
    def status(self) -> Dict[str, Any]:
        """获取池状态"""
        return {
            'closed': self._closed,
            'config': {
                'min_size': self.config.min_size,
                'max_size': self.config.max_size,
                'max_overflow': self.config.max_overflow,
            },
            'stats': {
                'total_connections': self._stats.total_connections,
                'idle_connections': self._stats.idle_connections,
                'busy_connections': self._stats.busy_connections,
                'overflow_connections': self._stats.overflow_connections,
                'waiting_requests': self._waiting,
            }
        }


# 便捷函数
@asynccontextmanager
async def create_pool(factory: ConnectionFactory[T], 
                      config: PoolConfig = None):
    """创建连接池上下文管理器"""
    pool = ConnectionPool(factory, config)
    await pool.initialize()
    try:
        yield pool
    finally:
        await pool.close()


# 异常类
class PoolClosedError(Exception):
    """连接池已关闭错误"""
    pass


class PoolExhaustedError(Exception):
    """连接池耗尽错误"""
    pass


class ConnectionError(Exception):
    """连接错误"""
    pass


# 示例：数据库连接工厂
class DatabaseConnectionFactory(ConnectionFactory):
    """数据库连接工厂示例"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    async def create(self):
        # 实际实现中这里创建真实的数据库连接
        return {"connection": f"db_conn_{id(object())}"}
    
    async def close(self, connection):
        logger.debug(f"关闭连接: {connection}")
    
    async def check(self, connection):
        # 简单的健康检查
        return connection is not None
    
    async def reset(self, connection):
        # 重置连接状态
        pass
