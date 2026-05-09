"""
LLMClient 线程安全测试 - 验证 _record_usage() 和 batch_process() 的线程安全性
使用 unittest.mock 来 mock OpenAI API，不需要真实 API key
"""

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.llm_client import LLMClient


def _create_mock_llm_client():
    """创建一个使用 mock OpenAI client 的 LLMClient 实例"""
    with patch("services.llm_client.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # 设置环境变量以避免 API key 检查
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            llm = LLMClient(model="deepseek-chat", api_key="test-key")
        return llm, mock_client


def _create_mock_response(input_tokens=100, output_tokens=50):
    """创建 mock 的 OpenAI 响应对象"""
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = input_tokens
    mock_usage.completion_tokens = output_tokens

    mock_response = MagicMock()
    mock_response.usage = mock_usage
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "test"}'
    return mock_response


class TestRecordUsageThreadSafety:
    """测试 _record_usage() 在多线程下计数准确"""

    def test_record_usage_single_thread(self):
        """单线程下 _record_usage() 计数正确"""
        llm, mock_client = _create_mock_llm_client()

        # 初始状态应为零
        assert llm.total_calls == 0
        assert llm.total_input_tokens == 0
        assert llm.total_output_tokens == 0

        # 记录一次使用
        mock_response = _create_mock_response(input_tokens=100, output_tokens=50)
        llm._record_usage(mock_response)

        assert llm.total_calls == 1
        assert llm.total_input_tokens == 100
        assert llm.total_output_tokens == 50

        # 再记录一次
        mock_response2 = _create_mock_response(input_tokens=200, output_tokens=80)
        llm._record_usage(mock_response2)

        assert llm.total_calls == 2
        assert llm.total_input_tokens == 300
        assert llm.total_output_tokens == 130

    def test_record_usage_concurrent_threads(self):
        """多线程并发调用 _record_usage() 计数应准确"""
        llm, mock_client = _create_mock_llm_client()

        num_threads = 50
        tokens_per_call = 10
        errors = []

        def record_once():
            try:
                mock_response = _create_mock_response(
                    input_tokens=tokens_per_call,
                    output_tokens=tokens_per_call,
                )
                llm._record_usage(mock_response)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_once) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证没有异常
        assert len(errors) == 0, f"线程执行出错: {errors}"

        # 验证计数准确
        assert llm.total_calls == num_threads, \
            f"期望 {num_threads} 次调用，实际 {llm.total_calls}"
        assert llm.total_input_tokens == num_threads * tokens_per_call, \
            f"期望 {num_threads * tokens_per_call} 输入token，实际 {llm.total_input_tokens}"
        assert llm.total_output_tokens == num_threads * tokens_per_call, \
            f"期望 {num_threads * tokens_per_call} 输出token，实际 {llm.total_output_tokens}"

    def test_record_usage_high_concurrency(self):
        """高并发（200线程）下计数应准确"""
        llm, mock_client = _create_mock_llm_client()

        num_threads = 200
        errors = []
        barrier = threading.Barrier(num_threads)

        def record_with_barrier():
            try:
                barrier.wait()  # 所有线程同时开始
                mock_response = _create_mock_response(input_tokens=5, output_tokens=3)
                llm._record_usage(mock_response)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_with_barrier) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"高并发执行出错: {errors}"
        assert llm.total_calls == num_threads
        assert llm.total_input_tokens == num_threads * 5
        assert llm.total_output_tokens == num_threads * 3

    def test_record_usage_with_db_instance(self, db):
        """_record_usage() 传入 db_instance 时应正确保存到数据库"""
        llm, mock_client = _create_mock_llm_client()

        mock_response = _create_mock_response(input_tokens=100, output_tokens=50)
        llm._record_usage(
            mock_response,
            operation_type="content_analysis",
            content_id="test-content-001",
            db_instance=db,
        )

        # 验证内存计数
        assert llm.total_calls == 1
        assert llm.total_input_tokens == 100

        # 验证数据库记录
        usage_stats = db.get_api_usage_stats()
        assert usage_stats["total_calls"] == 1
        assert usage_stats["total_input_tokens"] == 100
        assert usage_stats["total_output_tokens"] == 50

    def test_record_usage_none_usage(self):
        """response.usage 为 None 时不应崩溃"""
        llm, mock_client = _create_mock_llm_client()

        mock_response = MagicMock()
        mock_response.usage = None

        # 不应抛出异常
        llm._record_usage(mock_response)

        assert llm.total_calls == 0
        assert llm.total_input_tokens == 0

    def test_reset_usage_stats(self):
        """重置统计数据"""
        llm, mock_client = _create_mock_llm_client()

        mock_response = _create_mock_response(input_tokens=100, output_tokens=50)
        llm._record_usage(mock_response)
        assert llm.total_calls == 1

        llm.reset_usage_stats()
        assert llm.total_calls == 0
        assert llm.total_input_tokens == 0
        assert llm.total_output_tokens == 0


class TestBatchProcessThreadSafety:
    """测试 batch_process() 的结果完整性"""

    def test_batch_process_basic(self):
        """batch_process() 基本功能测试"""
        llm, mock_client = _create_mock_llm_client()

        # Mock chat.completions.create 返回
        mock_response = _create_mock_response(input_tokens=50, output_tokens=30)
        mock_response.choices[0].message.content = '{"result": "ok"}'
        mock_client.chat.completions.create.return_value = mock_response

        items = [{"id": i} for i in range(5)]

        def prompt_builder(item):
            return ("system prompt", f"user content {item['id']}")

        results = llm.batch_process(items, prompt_builder, concurrency=2)

        # 验证结果完整性
        assert len(results) == 5
        for r in results:
            assert r["success"] is True
            assert "data" in r
            assert "item" in r

        # 验证调用次数
        assert llm.total_calls == 5

    def test_batch_process_with_failures(self):
        """batch_process() 部分失败时应继续处理"""
        llm, mock_client = _create_mock_llm_client()

        call_count = [0]

        # Mock chat_json 方法，因为 batch_process 内部调用 chat_json
        original_chat_json = llm.chat_json

        def mock_chat_json(system_prompt, user_content, **kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 0:
                raise RuntimeError("模拟API失败")
            return {"result": "ok", "call": call_count[0]}

        llm.chat_json = mock_chat_json

        items = [{"id": i} for i in range(6)]

        def prompt_builder(item):
            return ("system", f"content {item['id']}")

        results = llm.batch_process(items, prompt_builder, concurrency=2)

        # 所有 6 个结果都应返回
        assert len(results) == 6

        # 验证成功和失败的数量
        success_count = sum(1 for r in results if r["success"])
        fail_count = sum(1 for r in results if not r["success"])

        assert success_count + fail_count == 6
        assert fail_count >= 1  # 至少有一次失败

        # 失败的结果应有 error 字段
        for r in results:
            if not r["success"]:
                assert "error" in r
                assert "item" in r

    def test_batch_process_empty_list(self):
        """batch_process() 空列表"""
        llm, mock_client = _create_mock_llm_client()

        results = llm.batch_process([], lambda x: ("s", "u"), concurrency=2)
        assert results == []
        assert llm.total_calls == 0

    def test_batch_process_result_ordering(self):
        """batch_process() 结果应包含所有原始 item"""
        llm, mock_client = _create_mock_llm_client()

        mock_response = _create_mock_response(input_tokens=10, output_tokens=5)
        mock_response.choices[0].message.content = '{"data": true}'
        mock_client.chat.completions.create.return_value = mock_response

        items = [{"id": f"item-{i}", "value": i * 10} for i in range(10)]

        def prompt_builder(item):
            return ("system", f"process {item['id']}")

        results = llm.batch_process(items, prompt_builder, concurrency=5)

        # 验证所有 item 都在结果中
        result_items = {r["item"]["id"] for r in results}
        expected_items = {item["id"] for item in items}
        assert result_items == expected_items

        # 验证每个结果的 item 数据完整
        for r in results:
            assert r["item"]["value"] == int(r["item"]["id"].split("-")[1]) * 10


class TestLLMClientCostTracking:
    """测试成本追踪的线程安全性"""

    def test_total_cost_property(self):
        """total_cost 属性计算正确"""
        llm, mock_client = _create_mock_llm_client()

        # deepseek-chat: cost_per_1k_input=0.001, cost_per_1k_output=0.002
        mock_response = _create_mock_response(input_tokens=1000, output_tokens=500)
        llm._record_usage(mock_response)

        expected_cost = (1000 / 1000) * 0.001 + (500 / 1000) * 0.002
        assert abs(llm.total_cost - expected_cost) < 0.0001

    def test_concurrent_cost_tracking(self):
        """并发下成本追踪准确"""
        llm, mock_client = _create_mock_llm_client()

        num_threads = 100
        errors = []
        barrier = threading.Barrier(num_threads)

        def record():
            try:
                barrier.wait()
                mock_response = _create_mock_response(input_tokens=100, output_tokens=50)
                llm._record_usage(mock_response)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # 验证成本
        expected_input = num_threads * 100
        expected_output = num_threads * 50
        expected_cost = (expected_input / 1000) * 0.001 + (expected_output / 1000) * 0.002

        assert llm.total_input_tokens == expected_input
        assert llm.total_output_tokens == expected_output
        assert abs(llm.total_cost - expected_cost) < 0.0001

    def test_get_usage_summary(self):
        """获取使用摘要"""
        llm, mock_client = _create_mock_llm_client()

        mock_response = _create_mock_response(input_tokens=100, output_tokens=50)
        llm._record_usage(mock_response)

        summary = llm.get_usage_summary()
        assert summary["model"] == "deepseek-chat"
        assert summary["total_calls"] == 1
        assert summary["total_input_tokens"] == 100
        assert summary["total_output_tokens"] == 50
        assert summary["total_tokens"] == 150
        assert summary["total_cost"] > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
