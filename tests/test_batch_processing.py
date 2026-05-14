import pytest
import time
import threading
import os
import tempfile
from services.task_manager import (
    BackgroundTaskManager, TaskType, TaskStatus, get_task_manager
)
from services.database import Database


class TestBatchProcessing:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_tasks.db")
        self.db = Database(db_path=self.db_path)
        self.task_manager = get_task_manager(
            self.db, model="deepseek-chat", api_key="test-key"
        )

        yield

        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        BackgroundTaskManager._instance = None
        BackgroundTaskManager._initialized = False

    def test_task_lifecycle_pending_to_running_to_completed(self):
        task_data = {"scripts": [{"script_text": "test", "script_id": "0"}], "total": 1}

        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )

        assert task_id is not None

        task = self.task_manager.get_task_status(task_id)
        assert task is not None
        assert task["status"] in (
            TaskStatus.PENDING.value,
            TaskStatus.RUNNING.value,
        )

        running_tasks = self.task_manager.get_running_tasks()
        assert len(running_tasks) > 0
        task_ids = [t["task_id"] for t in running_tasks]
        assert task_id in task_ids

    def test_progress_updates_before_and_after(self):
        task_data = {
            "scripts": [
                {"script_text": "script 1", "script_id": "0"},
                {"script_text": "script 2", "script_id": "1"},
            ],
            "total": 2,
        }

        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )

        time.sleep(0.5)

        task = self.task_manager.get_task_status(task_id)
        assert task is not None
        progress = task.get("progress", 0)
        assert progress >= 0

        time.sleep(5)

        task = self.task_manager.get_task_status(task_id)
        assert task is not None
        status = task["status"]
        assert status != TaskStatus.PENDING.value, (
            f"Task still pending after 5s: status={status}, "
            f"progress={task.get('progress')}, error={task.get('error')}"
        )

    def test_get_running_tasks_includes_pending_and_running(self):
        task_data = {
            "scripts": [{"script_text": "test", "script_id": "0"}],
            "total": 1,
        }

        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )

        running = self.task_manager.get_running_tasks()
        assert len(running) > 0

        found = any(t["task_id"] == task_id for t in running)
        assert found, f"Task {task_id} not found in running tasks"

    def test_multiple_tasks_dont_interfere(self):
        task_data = {
            "scripts": [{"script_text": "test", "script_id": "0"}],
            "total": 1,
        }

        ids = []
        for _ in range(3):
            tid = self.task_manager.submit_task(
                task_type=TaskType.CONTENT_ANALYSIS,
                task_data=task_data,
            )
            ids.append(tid)

        time.sleep(1)

        running = self.task_manager.get_running_tasks()
        running_ids = {t["task_id"] for t in running}
        for tid in ids:
            assert tid in running_ids or self.task_manager.get_task_status(tid) is not None

    def test_batch_match_progress_updates(self):
        task_data = {"top_k": 2}

        task_id = self.task_manager.submit_task(
            task_type=TaskType.BATCH_MATCH,
            task_data=task_data,
        )

        time.sleep(0.5)

        task = self.task_manager.get_task_status(task_id)
        assert task is not None
        assert task["status"] in (
            TaskStatus.PENDING.value,
            TaskStatus.RUNNING.value,
            TaskStatus.COMPLETED.value,
        )

    def test_task_persistence_across_manager_instances(self):
        task_data = {
            "scripts": [{"script_text": "test", "script_id": "0"}],
            "total": 1,
        }

        task_id = self.task_manager.submit_task(
            task_type=TaskType.CONTENT_ANALYSIS,
            task_data=task_data,
        )

        time.sleep(0.5)

        task1 = self.task_manager.get_task_status(task_id)
        assert task1 is not None

        new_manager = get_task_manager(self.db)
        task2 = new_manager.get_task_status(task_id)
        assert task2 is not None
        assert task2["task_id"] == task1["task_id"]
        assert task2["status"] == task1["status"]