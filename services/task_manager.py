"""任务管理服务

提供任务提交、状态查询等基础功能
"""
import json
import uuid
import logging
import threading
from datetime import datetime, timedelta
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
    
    def __new__(cls, db: Database = None, model: str = "deepseek-chat", api_key: str = ""):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db: Database = None, model: str = "deepseek-chat", api_key: str = ""):
        if not self._initialized:
            self.db = db
            self.model = model
            self.api_key = api_key
            self._executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="bg_task_")
            self._running_tasks: Dict[str, Future] = {}
            self._task_callbacks: Dict[str, List[Callable]] = {}
            self._lock = threading.Lock()
            
            self._initialized = True
            logger.info("后台任务管理器初始化完成 (model=%s)", model)
        else:
            if db is not None and self.db is None:
                self.db = db
            if model != "deepseek-chat" or self.model == "deepseek-chat":
                self.model = model
                self.api_key = api_key
    
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
        from services.orchestrator import Orchestrator
        
        orchestrator = Orchestrator(model=self.model, api_key=self.api_key)
        scripts = task_data.get("scripts", [])
        total = len(scripts)
        results = []
        
        self._update_task_progress(task_id, 0, total, 5)
        
        for i, script in enumerate(scripts):
            self._update_task_progress(task_id, i, total, max(5, int(i / total * 100)))
            
            try:
                result = orchestrator.content_analyzer.analyze(script)
                orchestrator.db.save_content_analysis(result)
                results.append({"success": True, "data": result})
            except Exception as e:
                logger.error(f"内容分析失败 (item {i+1}/{total}): {e}")
                results.append({"success": False, "error": str(e)})
            
            self._update_task_progress(task_id, i + 1, total, int((i + 1) / total * 100))
        
        return {
            "total": total,
            "completed": len([r for r in results if r.get("success")]),
            "failed": len([r for r in results if not r.get("success")]),
            "results": results,
        }
    
    def _execute_lead_analysis(self, task_id: str, task_data: Dict[str, Any]) -> Dict:
        from services.orchestrator import Orchestrator
        
        orchestrator = Orchestrator(model=self.model, api_key=self.api_key)
        leads = task_data.get("leads", [])
        total = len(leads)
        results = []
        
        self._update_task_progress(task_id, 0, total, 5)
        
        for i, lead in enumerate(leads):
            self._update_task_progress(task_id, i, total, max(5, int(i / total * 100)))
            
            try:
                result = orchestrator.lead_analyzer.analyze(
                    lead_data=lead.get("lead_data", {}),
                    lead_id=lead.get("lead_id"),
                )
                orchestrator.db.save_lead_analysis(result)
                results.append({"success": True, "data": result})
            except Exception as e:
                logger.error(f"线索分析失败 (item {i+1}/{total}): {e}")
                results.append({"success": False, "error": str(e)})
            
            self._update_task_progress(task_id, i + 1, total, int((i + 1) / total * 100))
        
        return {
            "total": total,
            "completed": len([r for r in results if r.get("success")]),
            "failed": len([r for r in results if not r.get("success")]),
            "results": results,
        }
    
    def _execute_batch_match(self, task_id: str, task_data: Dict[str, Any]) -> Dict:
        from services.orchestrator import Orchestrator
        
        orchestrator = Orchestrator(model=self.model, api_key=self.api_key)
        top_k = task_data.get("top_k", 3)
        
        contents = orchestrator.db.get_all_content_analyses(limit=500)
        leads = orchestrator.db.get_all_lead_analyses(limit=500)
        total_leads = len(leads)
        
        if not contents or not leads:
            self._update_task_progress(task_id, 0, 0, 100)
            return {"total_matches": 0, "results": []}
        
        self._update_task_progress(task_id, 0, total_leads, 5)
        
        content_list = [
            {"analysis": c["analysis_json"], "content_id": c["id"]} for c in contents
        ]
        lead_list = [
            {
                "profile": lead["profile_json"],
                "lead_id": lead["id"],
                "raw_data": lead.get("raw_data_json", {}),
            }
            for lead in leads
        ]
        
        results = []
        match_results_to_save = []

        lead_data_map = {}
        all_lead_data = orchestrator.db.get_all_lead_analyses(limit=total_leads + 100)
        for ld in all_lead_data:
            lead_data_map[ld.get("id", "")] = ld

        for item in lead_list:
            lid = item["lead_id"]
            if lid not in lead_data_map:
                lead_data_map[lid] = {
                    "profile_json": item["profile"],
                    "raw_data_json": item.get("raw_data", {}),
                }

        lead_snapshot_map = {}
        for lid, ld in lead_data_map.items():
            profile = ld.get("profile_json", {})
            lead_snapshot_map[lid] = {
                "company_name": profile.get("company_name", "未知"),
                "industry": profile.get("industry", "未知"),
                "lead_grade": profile.get("lead_grade", "C"),
                "intent_level": profile.get("intent_level", 5),
                "lead_id": lid,
            }

        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        tasks = []
        for lead_idx, lead_data_item in enumerate(lead_list):
            lead_id = lead_data_item["lead_id"]
            for content_item in content_list:
                tasks.append((lead_idx, lead_id, lead_data_item, content_item))

        total_tasks = len(tasks)
        matches_by_lead = {i: [] for i in range(total_leads)}
        completed = 0
        lock = threading.Lock()

        def do_match(lead_idx, lead_id, lead_data_item, content_item):
            nonlocal completed
            try:
                match_result = orchestrator.match_engine.match(
                    content_item["analysis"],
                    lead_data_item["profile"],
                    content_id=content_item.get("content_id"),
                    lead_id=lead_id,
                )
                return lead_idx, {
                    "content_id": content_item.get("content_id"),
                    "content_snapshot": match_result.get("content_snapshot", {}),
                    "match_result": match_result.get("match_result", {}),
                }
            except Exception as e:
                logger.error(f"匹配失败 lead={lead_id}: {e}")
                return lead_idx, {"error": str(e)}

        max_workers = min(8, total_tasks)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(do_match, lead_idx, lead_id, lead_data_item, content_item)
                for lead_idx, lead_id, lead_data_item, content_item in tasks
            ]
            for future in as_completed(futures):
                lead_idx, match = future.result()
                with lock:
                    matches_by_lead[lead_idx].append(match)
                    completed += 1
                if completed % 50 == 0 or completed == total_tasks:
                    pct = int(completed / total_tasks * 90)
                    self._update_task_progress(task_id, completed, total_tasks, max(5, pct))

        for lead_idx, lead_data_item in enumerate(lead_list):
            lead_id = lead_data_item["lead_id"]
            matches = matches_by_lead.get(lead_idx, [])

            matches.sort(
                key=lambda m: m.get("match_result", {}).get("overall_score", 0),
                reverse=True,
            )
            top_matches = matches[:top_k]

            lead_snapshot = lead_snapshot_map.get(lead_id, {})

            results.append({
                "lead_id": lead_id,
                "lead_snapshot": lead_snapshot,
                "top_matches": top_matches,
            })

            for match in top_matches:
                if "error" not in match and "match_id" not in match:
                    import uuid
                    match["match_id"] = str(uuid.uuid4())
                if "error" not in match:
                    match.setdefault("content_snapshot", {})["content_id"] = match.get("content_id", "")
                    match.setdefault("lead_snapshot", {})["lead_id"] = lead_id
                    match_results_to_save.append(match)

            self._update_task_progress(task_id, lead_idx + 1, total_leads, int((lead_idx + 1) / total_leads * 90))
        
        if match_results_to_save:
            try:
                orchestrator.db.save_match_results_batch(match_results_to_save)
            except Exception as e:
                logger.error(f"批量保存匹配结果失败: {e}")
        
        self._update_task_progress(task_id, total_leads, total_leads, 100)
        
        return {
            "total_matches": len(results),
            "results": results,
        }
    
    def _execute_single_match(self, task_id: str, task_data: Dict[str, Any]) -> Dict:
        from services.orchestrator import Orchestrator
        
        orchestrator = Orchestrator(model=self.model, api_key=self.api_key)
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
                with self.db._get_conn() as conn:
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
        """获取进行中的任务（包括pending和running）"""
        tasks = self.get_user_tasks(TaskStatus.RUNNING)
        pending_tasks = self.get_user_tasks(TaskStatus.PENDING)
        return tasks + pending_tasks
    
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
            with self.db._get_conn() as conn:
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
                    json.dumps(task_record["task_data"]) if isinstance(task_record.get("task_data"), dict) else task_record.get("task_data", "{}"),
                    json.dumps(task_record["result"]) if task_record.get("result") is not None else None,
                    task_record.get("error"),
                    task_record["created_at"],
                    task_record["updated_at"],
                    task_record.get("completed_at"),
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
            with self.db._get_conn() as conn:
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
            with self.db._get_conn() as conn:
                conn.execute(
                    "DELETE FROM background_tasks WHERE created_at < ?",
                    (cutoff,)
                )
                logger.info(f"清理了 {days} 天前的旧任务")
        except Exception as e:
            logger.error(f"清理旧任务失败: {e}")


# 便捷函数
def get_task_manager(db: Database = None, model: str = "deepseek-chat", api_key: str = "") -> BackgroundTaskManager:
    return BackgroundTaskManager(db, model=model, api_key=api_key)
