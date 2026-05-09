"""
工作流引擎 - DAG 编排和执行

参考 Apache Airflow 和 Prefect 设计
支持复杂业务流程编排、依赖管理、失败重试
"""
import asyncio
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """任务执行结果"""
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retry_count: int = 0
    
    @property
    def duration(self) -> Optional[float]:
        """执行时长"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class Task(ABC):
    """
    任务基类
    
    所有工作流任务必须继承此类
    """
    
    def __init__(self, task_id: str, name: str = "",
                 retries: int = 0, retry_delay: float = 1.0,
                 timeout: Optional[float] = None):
        """
        初始化任务
        
        Args:
            task_id: 任务唯一ID
            name: 任务名称
            retries: 失败重试次数
            retry_delay: 重试间隔（秒）
            timeout: 超时时间（秒）
        """
        self.task_id = task_id
        self.name = name or task_id
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        self.upstream: Set["Task"] = set()
        self.downstream: Set["Task"] = set()
        self.result: Optional[TaskResult] = None
    
    def __rshift__(self, other: "Task") -> "Task":
        """定义依赖关系: task1 >> task2"""
        self.downstream.add(other)
        other.upstream.add(self)
        return other
    
    def __lshift__(self, other: "Task") -> "Task":
        """定义依赖关系: task1 << task2"""
        other >> self
        return other
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        """
        执行任务
        
        Args:
            context: 执行上下文，包含输入数据和上游任务输出
            
        Returns:
            任务输出
        """
        pass
    
    def on_success(self, result: Any) -> None:
        """成功回调"""
        pass
    
    def on_failure(self, error: Exception) -> None:
        """失败回调"""
        pass


class Workflow:
    """
    工作流
    
    管理一组任务的依赖关系和执行
    """
    
    def __init__(self, workflow_id: str, name: str = ""):
        """
        初始化工作流
        
        Args:
            workflow_id: 工作流ID
            name: 工作流名称
        """
        self.workflow_id = workflow_id
        self.name = name or workflow_id
        self.tasks: Dict[str, Task] = {}
        self.context: Dict[str, Any] = {}
        
    def add_task(self, task: Task) -> "Workflow":
        """添加任务"""
        self.tasks[task.task_id] = task
        return self
    
    def get_root_tasks(self) -> List[Task]:
        """获取根任务（没有上游依赖）"""
        return [t for t in self.tasks.values() if not t.upstream]
    
    def get_execution_order(self) -> List[List[Task]]:
        """
        获取任务执行顺序（分层）
        
        Returns:
            每层可以并行执行的任务列表
        """
        # 拓扑排序
        in_degree = {t.task_id: len(t.upstream) for t in self.tasks.values()}
        queue = [t for t in self.tasks.values() if in_degree[t.task_id] == 0]
        layers = []
        sorted_count = 0

        while queue:
            layer = queue[:]
            layers.append(layer)
            sorted_count += len(layer)
            queue = []

            for task in layer:
                for downstream in task.downstream:
                    in_degree[downstream.task_id] -= 1
                    if in_degree[downstream.task_id] == 0:
                        queue.append(downstream)

        # 环检测：如果排序后的任务总数不等于原始任务总数，说明存在环
        if sorted_count != len(self.tasks):
            raise ValueError("工作流中存在循环依赖，无法确定执行顺序")

        return layers


class WorkflowEngine:
    """
    工作流引擎
    
    执行工作流，管理任务调度和状态
    """
    
    def __init__(self, max_workers: int = 4):
        """
        初始化引擎
        
        Args:
            max_workers: 最大并行工作数
        """
        self.max_workers = max_workers
        self._running_workflows: Dict[str, Workflow] = {}
        self._lock = threading.Lock()
    
    async def execute_workflow(self, workflow: Workflow, 
                               context: Optional[Dict] = None) -> Dict[str, TaskResult]:
        """
        执行工作流
        
        Args:
            workflow: 工作流实例
            context: 执行上下文
            
        Returns:
            所有任务的执行结果
        """
        with self._lock:
            self._running_workflows[workflow.workflow_id] = workflow
        
        workflow.context = context or {}
        results = {}
        
        try:
            # 获取执行顺序
            layers = workflow.get_execution_order()
            
            for layer in layers:
                # 并行执行当前层的所有任务
                tasks = [self._execute_task_with_retry(t, workflow) 
                        for t in layer]
                layer_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 收集结果
                for task, result in zip(layer, layer_results):
                    if isinstance(result, Exception):
                        task.result = TaskResult(
                            status=TaskStatus.FAILED,
                            error=str(result)
                        )
                        results[task.task_id] = task.result
                        
                        # 失败处理：跳过下游任务
                        self._skip_downstream(task)
                    else:
                        results[task.task_id] = result
            
            return results
            
        finally:
            with self._lock:
                del self._running_workflows[workflow.workflow_id]
    
    async def _execute_task_with_retry(self, task: Task, 
                                       workflow: Workflow) -> TaskResult:
        """执行任务（带重试）"""
        retry_count = 0
        
        while retry_count <= task.retries:
            start_time = time.time()
            
            try:
                # 准备上下文
                context = {
                    **workflow.context,
                    "upstream_results": {
                        t.task_id: t.result.output 
                        for t in task.upstream if t.result
                    }
                }
                
                # 执行任务
                if task.timeout is not None:
                    output = await asyncio.wait_for(task.execute(context), timeout=task.timeout)
                else:
                    output = await task.execute(context)
                
                result = TaskResult(
                    status=TaskStatus.SUCCESS,
                    output=output,
                    start_time=start_time,
                    end_time=time.time(),
                    retry_count=retry_count
                )
                
                task.result = result
                task.on_success(output)
                return result
                
            except Exception as e:
                retry_count += 1
                
                if retry_count > task.retries:
                    result = TaskResult(
                        status=TaskStatus.FAILED,
                        error=str(e),
                        start_time=start_time,
                        end_time=time.time(),
                        retry_count=retry_count - 1
                    )
                    task.result = result
                    task.on_failure(e)
                    return result
                
                # 等待后重试
                await asyncio.sleep(task.retry_delay)
    
    def _skip_downstream(self, task: Task, visited=None) -> None:
        """跳过下游任务"""
        if visited is None:
            visited = set()
        if task.task_id in visited:
            return
        visited.add(task.task_id)
        for downstream in task.downstream:
            downstream.result = TaskResult(status=TaskStatus.SKIPPED)
            self._skip_downstream(downstream, visited)


# 预定义任务类型

class AnalysisTask(Task):
    """分析任务"""
    
    def __init__(self, task_id: str, analyzer: Any, **kwargs):
        super().__init__(task_id, **kwargs)
        self.analyzer = analyzer
    
    async def execute(self, context: Dict) -> Any:
        data = context.get("data")
        return self.analyzer.analyze(data)


class MatchTask(Task):
    """匹配任务"""
    
    def __init__(self, task_id: str, match_engine: Any, **kwargs):
        super().__init__(task_id, **kwargs)
        self.match_engine = match_engine
    
    async def execute(self, context: Dict) -> Any:
        content = context["upstream_results"].get("analyze_content")
        lead = context["upstream_results"].get("analyze_lead")
        return self.match_engine.match(content, lead)


class StrategyTask(Task):
    """策略任务"""
    
    def __init__(self, task_id: str, strategy_advisor: Any, **kwargs):
        super().__init__(task_id, **kwargs)
        self.strategy_advisor = strategy_advisor
    
    async def execute(self, context: Dict) -> Any:
        match_result = context["upstream_results"].get("match")
        return self.strategy_advisor.advise(match_result)
