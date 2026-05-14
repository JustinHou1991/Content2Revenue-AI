"""
模拟 Streamlit 页面生命周期的端到端测试。
测试场景：
1. 用户上传数据，开始批量分析
2. 模拟 st.rerun()（页面刷新）
3. 模拟页面切换后返回
4. 验证任务进度持续可见
"""
import pytest
import time
import os
import sys
import tempfile
import json
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.task_manager import (
    BackgroundTaskManager, TaskType, TaskStatus, get_task_manager
)
from services.database import Database


class TestStreamlitFlow:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_flow.db")
        self.db = Database(db_path=self.db_path)
        self.task_manager = get_task_manager(
            self.db, model="deepseek-chat", api_key="test-key"
        )

        yield

        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        BackgroundTaskManager._instance = None
        BackgroundTaskManager._initialized = False

    def _simulate_session_state(self, task_id=None, df=None, mapping=None):
        """模拟 st.session_state"""
        state = {}
        if task_id:
            state["content_analysis_task_id"] = task_id
        if df is not None:
            state["content_df"] = df
        if mapping is not None:
            state["content_field_mapping"] = mapping
        return state

    def _simulate_render_batch_input(self, session_state, uploaded_file_exists=True):
        """
        模拟 _render_batch_input() 的逻辑
        返回: 是否应该调用 _handle_batch_analysis
        """
        if uploaded_file_exists:
            return True

        task_id = session_state.get("content_analysis_task_id")
        content_df = session_state.get("content_df")
        if task_id and content_df is not None:
            return True
        elif not task_id:
            session_state["content_df"] = None
            session_state["content_field_mapping"] = None
        return False

    def _simulate_handle_batch_analysis(self, session_state):
        """
        模拟 _handle_batch_analysis() 的核心逻辑
        返回: (should_show_progress, status, task_dict)
        """
        task_id = session_state.get("content_analysis_task_id")
        if not task_id:
            return False, "no_task", None

        task = self.task_manager.get_task_status(task_id)
        if not task:
            return False, "not_found", None

        status = task.get("status")
        if status in ("completed", "failed", "cancelled"):
            return True, status, task
        elif status in ("running", "pending"):
            return True, status, task

        return False, "unknown", task

    def test_scenario_1_submit_and_rerun(self):
        """场景1: 用户提交任务后 st.rerun()，进度应持续可见"""
        df = pd.DataFrame({"脚本内容": ["测试脚本A", "测试脚本B"]})
        mapping = {"脚本内容": "脚本内容"}

        # 第一次渲染：上传文件，点击按钮
        session = self._simulate_session_state(df=df, mapping=mapping)
        should_handle = self._simulate_render_batch_input(session, uploaded_file_exists=True)
        assert should_handle, "上传文件后应触发批量分析"

        # 提交任务
        task_data = {
            "scripts": [
                {"script_text": "测试脚本A", "script_id": "0"},
                {"script_text": "测试脚本B", "script_id": "1"},
            ],
            "total": 2,
        }
        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )
        session["content_analysis_task_id"] = task_id

        # 等待任务进入 running
        time.sleep(1)

        # 模拟 st.rerun()：uploaded_file 变为 None
        should_handle = self._simulate_render_batch_input(session, uploaded_file_exists=False)
        assert should_handle, (
            f"st.rerun() 后应继续触发批量分析: "
            f"task_id={session.get('content_analysis_task_id')}, "
            f"has_df={session.get('content_df') is not None}"
        )

        # 检查任务状态
        should_show, status, task = self._simulate_handle_batch_analysis(session)
        assert should_show, f"应显示进度, status={status}"
        assert status in ("running", "pending", "completed", "failed"), (
            f"任务状态异常: {status}"
        )

        print(f"✅ 场景1通过: st.rerun()后任务状态={status}, progress={task.get('progress')}%")

    def test_scenario_2_page_switch_and_return(self):
        """场景2: 用户切换到其他页面后返回，进度应持续可见"""
        df = pd.DataFrame({"脚本内容": ["测试脚本C"]})
        mapping = {"脚本内容": "脚本内容"}

        # 提交任务
        session = self._simulate_session_state(df=df, mapping=mapping)
        task_data = {
            "scripts": [{"script_text": "测试脚本C", "script_id": "0"}],
            "total": 1,
        }
        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )
        session["content_analysis_task_id"] = task_id

        time.sleep(1)

        # 模拟切换到其他页面（数据仍在 session_state 中）
        should_handle = self._simulate_render_batch_input(session, uploaded_file_exists=False)
        assert should_handle, (
            f"切换页面后返回应触发批量分析: "
            f"task_id={session.get('content_analysis_task_id')}, "
            f"has_df={session.get('content_df') is not None}"
        )

        should_show, status, task = self._simulate_handle_batch_analysis(session)
        assert should_show, f"应显示进度, status={status}"

        print(f"✅ 场景2通过: 页面切换后任务状态={status}")

    def test_scenario_3_data_cleared_but_task_running(self):
        """场景3: content_df 被意外清空但 task_id 仍在的情况"""
        session = self._simulate_session_state(
            task_id="some-task-id",
            df=None,
            mapping={"脚本内容": "col"}
        )

        # content_df 是 None，但 task_id 存在
        should_handle = self._simulate_render_batch_input(session, uploaded_file_exists=False)
        assert not should_handle, (
            "content_df为None且task_id存在时不应触发分析，"
            "但也不应清空数据（因为task_id存在）"
        )

        # 验证 data 没有被清空
        assert session.get("content_analysis_task_id") == "some-task-id"

        print("✅ 场景3通过: content_df=None 但 task_id 存在时，不触发也不清空")

    def test_scenario_4_running_tasks_includes_pending(self):
        """场景4: get_running_tasks 应同时返回 pending 和 running 任务"""
        task_data = {
            "scripts": [{"script_text": "test", "script_id": "0"}],
            "total": 1,
        }
        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )

        # 立即检查 - 任务应该还在 pending
        running = self.task_manager.get_running_tasks()
        running_ids = [t["task_id"] for t in running]
        assert task_id in running_ids, (
            f"pending 任务应在 get_running_tasks 中: {running_ids}"
        )

        print(f"✅ 场景4通过: pending任务在running_tasks中, 共{len(running)}个")

    def test_scenario_5_task_status_save_succeeds(self):
        """场景5: 任务状态更新能成功写入数据库"""
        task_data = {
            "scripts": [{"script_text": "test", "script_id": "0"}],
            "total": 1,
        }
        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )

        time.sleep(3)

        task = self.task_manager.get_task_status(task_id)
        assert task is not None
        status = task.get("status")
        assert status != "pending", (
            f"任务应离开pending状态, 当前={status}, "
            f"error={task.get('error')}, progress={task.get('progress')}"
        )

        print(f"✅ 场景5通过: 任务状态已更新为 {status}")

    def test_scenario_6_file_uploader_retains_state_on_rerun(self):
        """
        场景6: 关键场景 - file_uploader在rerun后保留状态
        此时uploaded_file不为None，但batch_btn为False，
        必须通过task_id检测来触发进度显示
        """
        df = pd.DataFrame({"脚本内容": ["测试内容X"]})
        mapping = {"脚本内容": "脚本内容"}

        session = self._simulate_session_state(df=df, mapping=mapping)

        task_data = {
            "scripts": [{"script_text": "测试内容X", "script_id": "0"}],
            "total": 1,
        }
        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )
        session["content_analysis_task_id"] = task_id

        time.sleep(1)

        # 模拟rerun后: uploaded_file保留(True), batch_btn为False
        should_handle = self._simulate_render_batch_input(
            session, uploaded_file_exists=True
        )
        assert should_handle, (
            "即使uploaded_file保留, 只要有task_id就应该触发分析"
        )

        should_show, status, task = self._simulate_handle_batch_analysis(session)
        assert should_show, (
            f"应显示进度(即使batch_btn=False但task_id存在), status={status}"
        )

        print(f"✅ 场景6通过: file_uploader保留状态下任务进度正常显示, status={status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])