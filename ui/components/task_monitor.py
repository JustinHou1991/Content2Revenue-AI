"""任务监控组件 - 显示进行中的后台任务

用于在侧边栏或页面顶部显示任务状态
"""
import streamlit as st
from typing import Optional, Dict, Any, List

from services.task_manager import get_task_manager, TaskStatus


def render_task_monitor():
    
    task_manager = get_task_manager()
    
    running_tasks = task_manager.get_running_tasks()
    
    if not running_tasks:
        return
    
    with st.sidebar:
        st.divider()
        st.markdown("### 🔄 后台任务")
        
        for task in running_tasks[:3]:
            task_id = task.get("task_id", "")[:8]
            task_type = task.get("task_type", "未知")
            progress = task.get("progress", 0)
            current = task.get("current", 0)
            total = task.get("total", 0)
            
            type_names = {
                "content_analysis": "内容分析",
                "lead_analysis": "线索分析",
                "batch_match": "批量匹配",
                "single_match": "单对匹配",
            }
            type_name = type_names.get(task_type, task_type)
            
            st.progress(progress / 100, text=f"{type_name}: {current}/{total}")
        
        if len(running_tasks) > 3:
            st.caption(f"还有 {len(running_tasks) - 3} 个任务进行中...")


def check_and_resume_task(task_id: str) -> Optional[Dict[str, Any]]:
    """检查并恢复任务
    
    页面加载时调用，检查是否有进行中的任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态，如果没有则返回None
    """
    if not task_id:
        return None
    
    task_manager = get_task_manager()
    task = task_manager.get_task_status(task_id)
    
    if not task:
        return None
    
    status = task.get("status")
    
    # 如果任务已完成或失败，显示结果
    if status == TaskStatus.COMPLETED.value:
        st.success(f"✅ 任务已完成！")
        return task
    elif status == TaskStatus.FAILED.value:
        error = task.get("error", "未知错误")
        st.error(f"❌ 任务失败: {error}")
        return task
    elif status == TaskStatus.CANCELLED.value:
        st.warning("⚠️ 任务已取消")
        return task
    elif status in (TaskStatus.RUNNING.value, TaskStatus.PENDING.value):
        progress = task.get("progress", 0)
        current = task.get("current", 0)
        total = task.get("total", 0)
        status_label = "准备中" if status == TaskStatus.PENDING.value else "进行中"
        st.info(f"⏳ 任务{status_label}... {current}/{total} ({progress}%)")
        st.progress(progress / 100 if progress > 0 else 0.01)
        return task
    
    return task


def submit_background_analysis(
    task_type: str,
    items: List[Dict[str, Any]],
    on_complete: Optional[callable] = None
) -> str:
    """提交后台分析任务
    
    Args:
        task_type: 任务类型 (content_analysis/lead_analysis)
        items: 要分析的项目列表
        on_complete: 完成回调函数
        
    Returns:
        任务ID
    """
    from services.task_manager import TaskType
    
    task_manager = get_task_manager()
    
    # 准备任务数据
    task_data = {
        "items": items,
        "total": len(items),
    }
    
    # 映射任务类型
    if task_type == "content_analysis":
        task_type_enum = TaskType.CONTENT_ANALYSIS
        task_data["scripts"] = [item.get("script", "") for item in items]
    elif task_type == "lead_analysis":
        task_type_enum = TaskType.LEAD_ANALYSIS
        task_data["leads"] = items
    else:
        raise ValueError(f"未知任务类型: {task_type}")
    
    # 提交任务
    task_id = task_manager.submit_task(
        task_type=task_type_enum,
        task_data=task_data,
        completion_callback=on_complete,
    )
    
    # 保存到session_state
    st.session_state.current_task_id = task_id
    
    st.info(f"📋 任务已提交，任务ID: {task_id[:8]}...")
    st.info("⏳ 任务正在执行中，请耐心等待...")
    
    return task_id


def render_task_result(task: Dict[str, Any]):
    """渲染任务结果"""
    result = task.get("result", {})
    
    if not result:
        return
    
    total = result.get("total", 0)
    completed = result.get("completed", 0)
    failed = result.get("failed", 0)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总计", total)
    with col2:
        st.metric("成功", completed, delta=f"+{completed}")
    with col3:
        st.metric("失败", failed, delta=f"-{failed}" if failed > 0 else None)
    
    # 显示失败详情
    if failed > 0:
        with st.expander("查看失败详情"):
            results = result.get("results", [])
            for i, r in enumerate(results):
                if not r.get("success"):
                    st.write(f"项目 {i+1}: {r.get('error', '未知错误')}")
