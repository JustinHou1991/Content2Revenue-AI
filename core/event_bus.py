"""
事件总线 - 轻量级事件驱动架构

参考 Django Signal 和 Node.js EventEmitter 设计
支持同步和异步事件处理，可选持久化
"""
import asyncio
import threading
import time
import json
from typing import Dict, List, Callable, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
from queue import Queue, Empty
import logging

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 0    # 关键事件，立即处理
    HIGH = 1        # 高优先级
    NORMAL = 2      # 普通优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台任务


@dataclass
class Event:
    """
    事件对象
    
    Attributes:
        name: 事件名称
        data: 事件数据
        timestamp: 事件发生时间
        priority: 事件优先级
        source: 事件来源
        id: 事件唯一ID
    """
    name: str
    data: Dict[str, Any]
    timestamp: float = None
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.id is None:
            self.id = f"{self.name}_{self.timestamp}_{id(self)}"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Event":
        """从字典创建"""
        return cls(
            name=data["name"],
            data=data["data"],
            timestamp=data["timestamp"],
            priority=EventPriority(data["priority"]),
            source=data.get("source", ""),
            id=data.get("id")
        )


class EventHandler:
    """事件处理器包装类"""
    
    def __init__(self, callback: Callable, priority: int = 0, 
                 once: bool = False, filter_func: Optional[Callable] = None):
        """
        初始化处理器
        
        Args:
            callback: 回调函数
            priority: 处理优先级（数字越小优先级越高）
            once: 是否只执行一次
            filter_func: 事件过滤函数
        """
        self.callback = callback
        self.priority = priority
        self.once = once
        self.filter_func = filter_func
        self.call_count = 0
    
    def should_handle(self, event: Event) -> bool:
        """检查是否应该处理此事件"""
        if self.filter_func:
            return self.filter_func(event)
        return True
    
    def handle(self, event: Event) -> Any:
        """处理事件"""
        try:
            result = self.callback(event)
            self.call_count += 1
            return result
        except Exception as e:
            logger.error(f"事件处理失败 {event.name}: {e}")
            raise


class EventBus:
    """
    事件总线
    
    轻量级事件系统，支持：
    - 同步/异步事件处理
    - 事件优先级
    - 持久化（可选）
    - 事件过滤
    
    使用示例：
        bus = EventBus()
        
        # 订阅事件
        @bus.on("analysis.complete")
        def on_analysis(event):
            print(f"分析完成: {event.data}")
        
        # 发布事件
        bus.emit("analysis.complete", {"result": "success"})
    """
    
    def __init__(self, persistent: bool = False, max_queue_size: int = 10000):
        """
        初始化事件总线
        
        Args:
            persistent: 是否持久化事件
            max_queue_size: 事件队列最大大小
        """
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._persistent = persistent
        self._event_queue: Queue = Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            "published": 0,
            "handled": 0,
            "dropped": 0,
            "errors": 0
        }
    
    def on(self, event_name: str, priority: int = 0, once: bool = False,
           filter_func: Optional[Callable] = None) -> Callable:
        """
        装饰器：订阅事件
        
        Args:
            event_name: 事件名称
            priority: 处理优先级
            once: 是否只执行一次
            filter_func: 过滤函数
            
        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            self.subscribe(event_name, func, priority, once, filter_func)
            return func
        return decorator
    
    def subscribe(self, event_name: str, callback: Callable, 
                  priority: int = 0, once: bool = False,
                  filter_func: Optional[Callable] = None) -> None:
        """
        订阅事件
        
        Args:
            event_name: 事件名称
            callback: 回调函数
            priority: 处理优先级
            once: 是否只执行一次
            filter_func: 过滤函数
        """
        with self._lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            
            handler = EventHandler(callback, priority, once, filter_func)
            self._handlers[event_name].append(handler)
            
            # 按优先级排序
            self._handlers[event_name].sort(key=lambda h: h.priority)
            
        logger.debug(f"订阅事件: {event_name}")
    
    def unsubscribe(self, event_name: str, callback: Callable) -> bool:
        """
        取消订阅
        
        Args:
            event_name: 事件名称
            callback: 回调函数
            
        Returns:
            是否成功取消
        """
        with self._lock:
            if event_name not in self._handlers:
                return False
            
            original_count = len(self._handlers[event_name])
            self._handlers[event_name] = [
                h for h in self._handlers[event_name] 
                if h.callback != callback
            ]
            
            return len(self._handlers[event_name]) < original_count
    
    def emit(self, event_name: str, data: Dict[str, Any] = None,
             priority: EventPriority = EventPriority.NORMAL,
             source: str = "", async_mode: bool = False) -> None:
        """
        发布事件
        
        Args:
            event_name: 事件名称
            data: 事件数据
            priority: 事件优先级
            source: 事件来源
            async_mode: 是否异步处理
        """
        event = Event(
            name=event_name,
            data=data or {},
            priority=priority,
            source=source
        )
        
        if async_mode:
            # 异步处理：放入队列
            try:
                self._event_queue.put_nowait(event)
                self._stats["published"] += 1
            except Exception:
                self._stats["dropped"] += 1
                logger.warning(f"事件队列已满，丢弃事件: {event_name}")
        else:
            # 同步处理：立即执行
            self._process_event(event)
    
    def _process_event(self, event: Event) -> None:
        """处理单个事件"""
        with self._lock:
            handlers = list(self._handlers.get(event.name, []))

        for handler in handlers:
            if not handler.should_handle(event):
                continue
            
            try:
                handler.handle(event)
                self._stats["handled"] += 1
                
                # 如果只执行一次，移除处理器
                if handler.once:
                    with self._lock:
                        if handler in self._handlers.get(event.name, []):
                            self._handlers[event.name].remove(handler)
                            
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"事件处理错误 {event.name}: {e}")
    
    def start_async_processor(self) -> None:
        """启动异步事件处理器"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._async_worker)
        self._worker_thread.daemon = True
        self._worker_thread.start()
        logger.info("异步事件处理器已启动")
    
    def stop_async_processor(self) -> None:
        """停止异步事件处理器"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("异步事件处理器已停止")
    
    def _async_worker(self) -> None:
        """异步处理工作线程"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=1)
                self._process_event(event)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"异步事件处理错误: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self._stats.copy()
    
    def clear(self) -> None:
        """清除所有订阅"""
        with self._lock:
            self._handlers.clear()
        logger.info("所有事件订阅已清除")


# 全局事件总线实例
event_bus = EventBus()
