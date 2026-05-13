"""后台任务管理服务

支持分析/匹配任务在后台执行，页面切换不中断
"""
import json
import uuid
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future

from services.database import Database

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    PAUSED = "paused"        # 暂停（页面切换时）
    COMPLETED = "completed"  # 完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 取消


class TaskType(Enum):
    """任务类型"""
    CONTENT_ANALYSIS = "content_analysis"    # 内容分析
    LEAD_ANALYSIS = "lead_analysis"          # 线索分析
    BATCH_MATCH = "batch_match"              # 批量匹配
    SINGLE_MATCH = "single_match"            # 单对匹配


class BackgroundTaskManager:
    """后台任务管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db: Database = None):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db: Database = None):
        if self._initialized:
            return
        
        self.db = db
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="bg_task_")
        self._running_tasks: Dict[str, Future] = {}
        self._task_callbacks: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        
        self._initialized = True
        logger.info("后台任务管理器初始化完成")
    
    def submit_task(
        self,
        task_type: TaskType,
        task_data: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None
    ) -> str:
        """提交后台任务
        
        Args:
            task_type: 任务类型
            task_data: 任务数据
            progress_callback: 进度回调函数
            completion_callback: 完成回调函数
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 保存任务到数据库
        task_record = {
            "task_id": task_id,
            "task_type": task_type.value,
            "status": TaskStatus.PENDING.value,
            "progress": 0,
            "total": task_data.get("total", 0),
            "current": 0,
            "task_data": json.dumps(task_data),
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
        }
        
        self._save_task(task_record)
        
        # 注册回调
        if completion_callback:
            with self._lock:
                if task_id not in self._task_callbacks:
                    self._task_callbacks[task_id] = []
                self._task_callbacks[task_id].append(completion_callback)
        
        # 提交到线程池
        future = self._executor.submit(self._execute_task, task_id, task_type, task_data)
        
        with self._lock:
            self._running_tasks[task_id] = future
        
        logger.info(f"任务已提交: {task_id}, 类型: {task_type.value}")
        return task_id
    
    def _execute_task(self, task_id: str, task_type: TaskType, task_data: Dict[str, Any]):
        """执行任务"""
        try:
            # 更新状态为运行中
            self._update_task_status(task_id, TaskStatus.RUNNING)
            
            # 根据任务类型执行
            if task_type == TaskType.CONTENT_ANALYSIS:
                result = self._execute_content_analysis(task_id, task_data)
            elif task_type == TaskType.LEAD_ANALYSIS:
                result = self._execute_lead_analysis(task_id, task_data)
            elif task_type == TaskType.BATCH_MATCH:
                result = self._execute_batch_match(task_id, task_data)
            elif task_type == TaskType.SINGLE_MATCH:
                result = self._execute_single_match(task_id, task_data)
            else:
                raise ValueError(f"未知任务类型: {task_type}")
            
            # 更新完成状态
            self._update_task_status(task_id, TaskStatus.COMPLETED, result=result)
            
            # 触发完成回调
            self._trigger_callbacks(task_id, result, None)
            
        except Exception as e:
            logger.error(f"任务执行失败: {task_id}, 错误: {e}", exc_info=True)
            self._update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            self._trigger_callbacks(task_id, None, e)
        
        finally:
            # 清理运行中的任务记录
            with self._lock:
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]
    
    def _execute_content_analysis(self, task_id: str, task_data: Dict[str, Any]) -> Dict:
        """执行内容分析任务"""
        from services.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        scripts = task_data.get("scripts", [])
        total = len(scripts)
        results = []
        
        for i, script in enumerate(scripts):
            try:
                result = orchestrator.content_analyzer.analyze(script)
                orchestrator.db.save_content_analysis(result)
                results.append({"success": True, "data": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
            
            # 更新进度
            progress = int((i + 1) / total * 100)
            self._update_task_progress(task_id, i + 1, total, progress)
        
        return {
            "total": total,
            "completed": len([r for r in results if r.get("success")]),
            "failed": len([r for r in results if not r.get("success")]),
            "results": results,
        }
    
    def _execute_lead_analysis(self, task_id: str, task_data: Dict[str, Any]) -> Dict:
        """执行线索分析任务"""
        from services.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        leads = task_data.get("leads", [])
        total = len(leads)
        results = []
        
        for i, lead in enumerate(leads):
            try:
                result = orchestrator.lead_analyzer.analyze(
                    lead_data=lead.get("lead_data", {}),
                    lead_id=lead.get("lead_id"),
                )
                orchestrator.db.save_lead_analysis(result)
                results.append({"success": True, "data": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
            
            # 更新进度
            progress = int((i + 1) / total * 100)
            self._update_task_progress(task_id, i + 1, total, progress)
        
        return {
            "total": total,
            "completed": len([r for r in results if r.get("success")]),
            "failed": len([r for r in results if not r.get("success")]),
            "results": results,
        }
    
    def _execute_batch_match(self, task_id: str, task_data: Dict[str, Any]) -> Dict:
        """执行批量匹配任务"""
        from services.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        content_ids = task_data.get("content_ids", [])
        lead_ids = task_data.get("lead_ids", [])
        
        results = orchestrator.batch_match(content_ids, lead_ids)
        
        self._update_task_progress(task_id, len(results), len(results), 100)
        
        return {
            "total_matches": len(results),
            "results": results,
        }
    
    def _execute_single_match(self, task_id: str, task_data: Dict[str, Any]) -> Dict:
        """执行单对匹配任务"""
        from services.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        content_id = task_data.get("content_id")
        lead_id = task_data.get("lead_id")
        
        result = orchestrator.match_content_lead(content_id, lead_id)
        
        self._update_task_progress(task_id, 1, 1, 100)
        
        return result
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id in self._running_tasks:
                future = self._running_tasks[task_id]
                future.cancel()
                del self._running_tasks[task_id]
        
        self._update_task_status(task_id, TaskStatus.CANCELLED)
        logger.info(f"任务已取消: {task_id}")
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self._load_task(task_id)
    
    def get_user_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """获取用户的所有任务"""
        # 从数据库加载任务列表
        if self.db:
            try:
                with self.db._get_connection() as conn:
                    if status:
                        rows = conn.execute(
                            "SELECT * FROM background_tasks WHERE status = ? ORDER BY created_at DESC",
                            (status.value,)
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            "SELECT * FROM background_tasks ORDER BY created_at DESC"
                        ).fetchall()
                    
                    return [self._row_to_dict(row) for row in rows]
            except Exception as e:
                logger.error(f"加载任务列表失败: {e}")
        
        return []
    
    def get_running_tasks(self) -> List[Dict[str, Any]]:
        """获取进行中的任务"""
        return self.get_user_tasks(TaskStatus.RUNNING)
    
    def pause_task(self, task_id: str):
        """暂停任务（页面切换时调用）"""
        self._update_task_status(task_id, TaskStatus.PAUSED)
    
    def resume_task(self, task_id: str):
        """恢复任务（页面返回时调用）"""
        task = self._load_task(task_id)
        if task and task.get("status") == TaskStatus.PAUSED.value:
            self._update_task_status(task_id, TaskStatus.RUNNING)
    
    def _save_task(self, task_record: Dict[str, Any]):
        """保存任务到数据库"""
        if not self.db:
            return
        
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO background_tasks (
                        task_id, task_type, status, progress, total, current,
                        task_data, result, error, created_at, updated_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_record["task_id"],
                    task_record["task_type"],
                    task_record["status"],
                    task_record["progress"],
                    task_record["total"],
                    task_record["current"],
                    task_record["task_data"],
                    json.dumps(task_record["result"]) if task_record["result"] else None,
                    task_record["error"],
                    task_record["created_at"],
                    task_record["updated_at"],
                    task_record["completed_at"],
                ))
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
    
    def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Any = None,
        error: str = None
    ):
        """更新任务状态"""
        task = self._load_task(task_id)
        if not task:
            return
        
        task["status"] = status.value
        task["updated_at"] = datetime.now().isoformat()
        
        if result is not None:
            task["result"] = result
        
        if error is not None:
            task["error"] = error
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task["completed_at"] = datetime.now().isoformat()
        
        self._save_task(task)
    
    def _update_task_progress(self, task_id: str, current: int, total: int, progress: int):
        """更新任务进度"""
        task = self._load_task(task_id)
        if not task:
            return
        
        task["current"] = current
        task["total"] = total
        task["progress"] = progress
        task["updated_at"] = datetime.now().isoformat()
        
        self._save_task(task)
    
    def _load_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从数据库加载任务"""
        if not self.db:
            return None
        
        try:
            with self.db._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM background_tasks WHERE task_id = ?",
                    (task_id,)
                ).fetchone()
                
                if row:
                    return self._row_to_dict(row)
        except Exception as e:
            logger.error(f"加载任务失败: {e}")
        
        return None
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return {
            "task_id": row[0],
            "task_type": row[1],
            "status": row[2],
            "progress": row[3],
            "total": row[4],
            "current": row[5],
            "task_data": json.loads(row[6]) if row[6] else {},
            "result": json.loads(row[7]) if row[7] else None,
            "error": row[8],
            "created_at": row[9],
            "updated_at": row[10],
            "completed_at": row[11],
        }
    
    def _trigger_callbacks(self, task_id: str, result: Any, error: Exception):
        """触发任务完成回调"""
        with self._lock:
            callbacks = self._task_callbacks.get(task_id, [])
        
        for callback in callbacks:
            try:
                callback(result, error)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
        
        # 清理回调
        with self._lock:
            if task_id in self._task_callbacks:
                del self._task_callbacks[task_id]
    
    def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务"""
        if not self.db:
            return
        
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            with self.db._get_connection() as conn:
                conn.execute(
                    "DELETE FROM background_tasks WHERE created_at < ?",
                    (cutoff,)
                )
                logger.info(f"清理了 {days} 天前的旧任务")
        except Exception as e:
            logger.error(f"清理旧任务失败: {e}")


# 便捷函数
def get_task_manager(db: Database = None) -> BackgroundTaskManager:
    """获取任务管理器实例"""
    return BackgroundTaskManager(db)
