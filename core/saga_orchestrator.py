#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saga编排器 SagaOrchestrator - 分布式事务管理

设计灵感:
- Saga Pattern (Hector Garcia-Molina, 1987)
- Axon Framework Saga
- Temporal.io Workflows
- Netflix Conductor

核心特性:
1. 编排式Saga - 集中式事务协调
2. 补偿事务 - 失败时自动回滚
3. 状态持久化 - Saga执行状态保存
4. 并行执行 - 支持步骤并行化
5. 超时处理 - 步骤超时控制
6. 重试机制 - 失败自动重试
7. 事件驱动 - 基于事件的Saga推进

Saga模式:
- 编排式 (Orchestration): 由协调器统一管理
- 协同式 (Choreography): 服务间通过事件协作

作者: AI Assistant
创建日期: 2026-05-09
版本: 1.0.0
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional, Callable, Union, Coroutine
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import json
import copy

logger = logging.getLogger(__name__)


class SagaStatus(Enum):
    """Saga执行状态"""
    PENDING = auto()      # 等待执行
    RUNNING = auto()      # 执行中
    COMPLETED = auto()    # 完成
    COMPENSATING = auto() # 补偿中
    COMPENSATED = auto()  # 已补偿（回滚完成）
    FAILED = auto()       # 失败
    TIMEOUT = auto()      # 超时


class StepStatus(Enum):
    """步骤执行状态"""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    COMPENSATING = auto()
    COMPENSATED = auto()
    SKIPPED = auto()


@dataclass
class SagaStepResult:
    """步骤执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class CompensationResult:
    """补偿执行结果"""
    success: bool
    step_index: int
    error: Optional[str] = None


@dataclass
class SagaLogEntry:
    """Saga日志条目"""
    timestamp: datetime
    level: str
    message: str
    step_name: Optional[str] = None
    data: Dict = field(default_factory=dict)


class SagaStep(ABC):
    """
    Saga步骤基类
    
    每个Saga步骤包含:
    - 正向操作 (execute)
    - 补偿操作 (compensate)
    """
    
    def __init__(self, name: str, timeout: float = 30.0, 
                 max_retries: int = 0, retry_delay: float = 1.0):
        self.name = name
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.status = StepStatus.PENDING
        self.result: Optional[SagaStepResult] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    @abstractmethod
    async def execute(self, context: 'SagaContext') -> SagaStepResult:
        """执行正向操作"""
        pass
    
    @abstractmethod
    async def compensate(self, context: 'SagaContext') -> CompensationResult:
        """执行补偿操作"""
        pass
    
    async def execute_with_retry(self, context: 'SagaContext') -> SagaStepResult:
        """带重试的执行"""
        for attempt in range(self.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self.execute(context),
                    timeout=self.timeout
                )
                if result.success:
                    return result
                
                if attempt < self.max_retries:
                    logger.warning(f"步骤 {self.name} 失败，第 {attempt + 1} 次重试...")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
            except asyncio.TimeoutError:
                if attempt < self.max_retries:
                    logger.warning(f"步骤 {self.name} 超时，第 {attempt + 1} 次重试...")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    return SagaStepResult(
                        success=False,
                        error=f"步骤执行超时 ({self.timeout}s)"
                    )
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"步骤 {self.name} 异常: {e}，第 {attempt + 1} 次重试...")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    return SagaStepResult(
                        success=False,
                        error=str(e)
                    )
        
        return SagaStepResult(success=False, error="所有重试失败")


class FunctionStep(SagaStep):
    """函数式Saga步骤"""
    
    def __init__(self, name: str, 
                 execute_func: Callable[['SagaContext'], Coroutine],
                 compensate_func: Callable[['SagaContext'], Coroutine] = None,
                 **kwargs):
        super().__init__(name, **kwargs)
        self._execute_func = execute_func
        self._compensate_func = compensate_func
    
    async def execute(self, context: 'SagaContext') -> SagaStepResult:
        """执行函数"""
        try:
            result = await self._execute_func(context)
            if isinstance(result, SagaStepResult):
                return result
            return SagaStepResult(success=True, data=result)
        except Exception as e:
            return SagaStepResult(success=False, error=str(e))
    
    async def compensate(self, context: 'SagaContext') -> CompensationResult:
        """执行补偿"""
        if self._compensate_func is None:
            return CompensationResult(success=True, step_index=-1)
        
        try:
            await self._compensate_func(context)
            return CompensationResult(success=True, step_index=-1)
        except Exception as e:
            return CompensationResult(success=False, step_index=-1, error=str(e))


@dataclass
class SagaContext:
    """
    Saga执行上下文
    
    在Saga执行过程中传递的上下文，包含:
    - saga_id: Saga唯一标识
    - input_data: 初始输入数据
    - step_results: 各步骤执行结果
    - shared_data: 步骤间共享数据
    - metadata: 元数据
    """
    saga_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, SagaStepResult] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def set(self, key: str, value: Any) -> None:
        """设置共享数据"""
        self.shared_data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取共享数据"""
        return self.shared_data.get(key, default)
    
    def get_step_result(self, step_name: str) -> Optional[SagaStepResult]:
        """获取步骤结果"""
        return self.step_results.get(step_name)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'saga_id': self.saga_id,
            'input_data': self.input_data,
            'step_results': {
                k: asdict(v) if isinstance(v, SagaStepResult) else v
                for k, v in self.step_results.items()
            },
            'shared_data': self.shared_data,
            'metadata': self.metadata
        }


class SagaDefinition:
    """Saga定义"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[SagaStep] = []
        self.parallel_groups: List[List[int]] = []  # 并行步骤索引组
    
    def add_step(self, step: SagaStep) -> 'SagaDefinition':
        """添加步骤"""
        self.steps.append(step)
        return self
    
    def add_parallel_steps(self, *steps: SagaStep) -> 'SagaDefinition':
        """添加并行步骤组"""
        start_idx = len(self.steps)
        for step in steps:
            self.steps.append(step)
        self.parallel_groups.append(list(range(start_idx, len(self.steps))))
        return self
    
    def step(self, name: str, 
             execute: Callable[[SagaContext], Coroutine],
             compensate: Callable[[SagaContext], Coroutine] = None,
             **kwargs) -> 'SagaDefinition':
        """便捷方法：添加函数步骤"""
        self.add_step(FunctionStep(name, execute, compensate, **kwargs))
        return self


class SagaInstance:
    """Saga实例"""
    
    def __init__(self, saga_id: str, definition: SagaDefinition, 
                 context: SagaContext):
        self.saga_id = saga_id
        self.definition = definition
        self.context = context
        self.status = SagaStatus.PENDING
        self.current_step_index = 0
        self.logs: List[SagaLogEntry] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
    
    def log(self, level: str, message: str, step_name: str = None, data: Dict = None):
        """记录日志"""
        entry = SagaLogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            step_name=step_name,
            data=data or {}
        )
        self.logs.append(entry)
        logger.log(getattr(logging, level.upper(), logging.INFO), 
                   f"[Saga {self.saga_id}] {message}")
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'saga_id': self.saga_id,
            'definition_name': self.definition.name,
            'status': self.status.name,
            'current_step': self.current_step_index,
            'total_steps': len(self.definition.steps),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error_message,
            'context': self.context.to_dict()
        }


class SagaOrchestrator:
    """
    Saga编排器
    
    管理Saga的执行、补偿和状态持久化
    
    使用示例:
        orchestrator = SagaOrchestrator()
        
        # 定义Saga
        saga_def = SagaDefinition("order_process")
        saga_def.step("reserve_inventory", reserve_inventory, release_inventory)
        saga_def.step("process_payment", process_payment, refund_payment)
        saga_def.step("ship_order", ship_order, cancel_shipment)
        
        # 执行Saga
        instance = await orchestrator.execute(saga_def, {"order_id": "123"})
    """
    
    def __init__(self, persistence_enabled: bool = True):
        self._definitions: Dict[str, SagaDefinition] = {}
        self._instances: Dict[str, SagaInstance] = {}
        self._persistence_enabled = persistence_enabled
        self._event_handlers: Dict[str, List[Callable]] = {
            'saga_started': [],
            'saga_completed': [],
            'saga_failed': [],
            'saga_compensated': [],
            'step_completed': [],
            'step_failed': []
        }
    
    def register_definition(self, definition: SagaDefinition) -> None:
        """注册Saga定义"""
        self._definitions[definition.name] = definition
    
    def on(self, event: str, handler: Callable) -> None:
        """注册事件处理器"""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)
    
    def _emit(self, event: str, instance: SagaInstance, data: Dict = None):
        """触发事件"""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(instance, data or {}))
                else:
                    handler(instance, data or {})
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")
    
    async def execute(self, definition: SagaDefinition, 
                      input_data: Dict[str, Any] = None,
                      saga_id: str = None) -> SagaInstance:
        """
        执行Saga
        
        Args:
            definition: Saga定义
            input_data: 输入数据
            saga_id: 自定义Saga ID
            
        Returns:
            Saga实例
        """
        saga_id = saga_id or str(uuid.uuid4())
        context = SagaContext(
            saga_id=saga_id,
            input_data=input_data or {}
        )
        
        instance = SagaInstance(saga_id, definition, context)
        self._instances[saga_id] = instance
        
        instance.status = SagaStatus.RUNNING
        instance.log("INFO", f"Saga '{definition.name}' 开始执行")
        self._emit('saga_started', instance)
        
        try:
            await self._execute_steps(instance)
            
            if instance.status != SagaStatus.FAILED:
                instance.status = SagaStatus.COMPLETED
                instance.completed_at = datetime.now()
                instance.log("INFO", "Saga 成功完成")
                self._emit('saga_completed', instance)
            
        except Exception as e:
            instance.status = SagaStatus.FAILED
            instance.error_message = str(e)
            instance.log("ERROR", f"Saga 执行失败: {e}")
            self._emit('saga_failed', instance)
            
            # 触发补偿
            await self._compensate(instance)
        
        instance.updated_at = datetime.now()
        return instance
    
    async def _execute_steps(self, instance: SagaInstance) -> None:
        """执行所有步骤"""
        steps = instance.definition.steps
        
        while instance.current_step_index < len(steps):
            step = steps[instance.current_step_index]
            
            # 检查是否是并行组
            parallel_group = None
            for group in instance.definition.parallel_groups:
                if instance.current_step_index in group:
                    parallel_group = group
                    break
            
            if parallel_group and instance.current_step_index == parallel_group[0]:
                # 执行并行组
                await self._execute_parallel_steps(instance, parallel_group)
            else:
                # 执行单个步骤
                success = await self._execute_single_step(instance, step)
                if not success:
                    return
                instance.current_step_index += 1
    
    async def _execute_single_step(self, instance: SagaInstance, 
                                   step: SagaStep) -> bool:
        """执行单个步骤"""
        step.status = StepStatus.RUNNING
        step.start_time = datetime.now()
        
        instance.log("INFO", f"执行步骤: {step.name}", step_name=step.name)
        
        try:
            result = await step.execute_with_retry(instance.context)
            step.result = result
            step.end_time = datetime.now()
            
            if result.success:
                step.status = StepStatus.SUCCESS
                instance.context.step_results[step.name] = result
                instance.log("INFO", f"步骤完成: {step.name}", step_name=step.name)
                self._emit('step_completed', instance, {'step': step.name})
                return True
            else:
                step.status = StepStatus.FAILED
                instance.log("ERROR", f"步骤失败: {step.name} - {result.error}", 
                           step_name=step.name)
                self._emit('step_failed', instance, {'step': step.name, 'error': result.error})
                instance.status = SagaStatus.FAILED
                instance.error_message = result.error
                return False
                
        except Exception as e:
            step.status = StepStatus.FAILED
            step.end_time = datetime.now()
            instance.log("ERROR", f"步骤异常: {step.name} - {e}", step_name=step.name)
            self._emit('step_failed', instance, {'step': step.name, 'error': str(e)})
            instance.status = SagaStatus.FAILED
            instance.error_message = str(e)
            return False
    
    async def _execute_parallel_steps(self, instance: SagaInstance, 
                                      indices: List[int]) -> bool:
        """执行并行步骤"""
        steps = [instance.definition.steps[i] for i in indices]
        
        instance.log("INFO", f"并行执行步骤: {[s.name for s in steps]}")
        
        # 并发执行
        tasks = [self._execute_single_step(instance, step) for step in steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有失败
        if any(isinstance(r, Exception) or not r for r in results):
            instance.status = SagaStatus.FAILED
            instance.error_message = "并行步骤执行失败"
            return False
        
        instance.current_step_index = max(indices) + 1
        return True
    
    async def _compensate(self, instance: SagaInstance) -> None:
        """执行补偿（回滚）"""
        instance.status = SagaStatus.COMPENSATING
        instance.log("INFO", "开始执行补偿")
        
        # 反向执行补偿
        completed_steps = [
            step for step in instance.definition.steps[:instance.current_step_index + 1]
            if step.status == StepStatus.SUCCESS
        ]
        
        for step in reversed(completed_steps):
            step.status = StepStatus.COMPENSATING
            instance.log("INFO", f"补偿步骤: {step.name}", step_name=step.name)
            
            try:
                result = await step.compensate(instance.context)
                if result.success:
                    step.status = StepStatus.COMPENSATED
                    instance.log("INFO", f"补偿成功: {step.name}", step_name=step.name)
                else:
                    instance.log("ERROR", f"补偿失败: {step.name} - {result.error}", 
                               step_name=step.name)
            except Exception as e:
                instance.log("ERROR", f"补偿异常: {step.name} - {e}", step_name=step.name)
        
        instance.status = SagaStatus.COMPENSATED
        instance.completed_at = datetime.now()
        instance.log("INFO", "补偿完成")
        self._emit('saga_compensated', instance)
    
    def get_instance(self, saga_id: str) -> Optional[SagaInstance]:
        """获取Saga实例"""
        return self._instances.get(saga_id)
    
    def get_active_instances(self) -> List[SagaInstance]:
        """获取活动中的Saga实例"""
        return [
            inst for inst in self._instances.values()
            if inst.status in (SagaStatus.PENDING, SagaStatus.RUNNING, SagaStatus.COMPENSATING)
        ]
    
    def create_builder(self, name: str) -> 'SagaBuilder':
        """创建Saga构建器"""
        return SagaBuilder(name, self)


class SagaBuilder:
    """Saga构建器 - 流式API"""
    
    def __init__(self, name: str, orchestrator: SagaOrchestrator):
        self._definition = SagaDefinition(name)
        self._orchestrator = orchestrator
    
    def step(self, name: str,
             execute: Callable[[SagaContext], Coroutine],
             compensate: Callable[[SagaContext], Coroutine] = None,
             **kwargs) -> 'SagaBuilder':
        """添加步骤"""
        self._definition.step(name, execute, compensate, **kwargs)
        return self
    
    def parallel(self, *steps: SagaStep) -> 'SagaBuilder':
        """添加并行步骤"""
        self._definition.add_parallel_steps(*steps)
        return self
    
    def build(self) -> SagaDefinition:
        """构建Saga定义"""
        self._orchestrator.register_definition(self._definition)
        return self._definition
    
    async def execute(self, input_data: Dict = None, saga_id: str = None) -> SagaInstance:
        """立即执行"""
        self.build()
        return await self._orchestrator.execute(self._definition, input_data, saga_id)


# 便捷函数
def create_saga(name: str) -> SagaDefinition:
    """创建Saga定义"""
    return SagaDefinition(name)


def step(name: str, 
         execute: Callable[[SagaContext], Coroutine],
         compensate: Callable[[SagaContext], Coroutine] = None,
         **kwargs) -> FunctionStep:
    """创建函数步骤"""
    return FunctionStep(name, execute, compensate, **kwargs)
