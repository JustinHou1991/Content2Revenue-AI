"""
Database 集成测试 - 验证上下文管理器、事务、连接管理和数据一致性
"""

import os
import sys
import sqlite3
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.database import Database


class TestContextManagerCommit:
    """测试 _get_conn() 上下文管理器的正常提交行为"""

    def test_context_manager_commits_on_success(self, db):
        """正常退出时应自动提交"""
        with db._get_conn() as conn:
            conn.execute(
                "INSERT INTO content_analysis (id, raw_text, analysis_json, model, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("ctx-test-001", "test text", '{"key": "value"}', "test-model", "2025-01-01T00:00:00"),
            )

        # 退出上下文后，数据应已提交，用新连接验证
        result = db.get_content_analysis("ctx-test-001")
        assert result is not None
        assert result["raw_text"] == "test text"

    def test_context_manager_yields_connection(self, db):
        """上下文管理器应 yield 一个可用的连接对象"""
        with db._get_conn() as conn:
            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)
            # 验证连接可用
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1


class TestContextManagerRollback:
    """测试异常时自动回滚"""

    def test_rollback_on_exception(self, db):
        """上下文管理器内抛出异常时应自动回滚"""
        content_id = "rollback-test-001"

        # 先插入一条正常数据
        db.save_content_analysis({
            "content_id": content_id,
            "raw_text": "original text",
            "analysis": {"key": "original"},
            "model": "test-model",
            "created_at": "2025-01-01T00:00:00",
        })

        # 在上下文管理器中修改数据后抛出异常
        try:
            with db._get_conn() as conn:
                conn.execute(
                    "UPDATE content_analysis SET raw_text = ? WHERE id = ?",
                    ("modified text", content_id),
                )
                raise RuntimeError("模拟异常")
        except RuntimeError:
            pass

        # 数据应未被修改（已回滚）
        result = db.get_content_analysis(content_id)
        assert result is not None
        assert result["raw_text"] == "original text"

    def test_rollback_does_not_affect_other_data(self, db):
        """回滚不应影响之前已提交的数据"""
        # 插入第一条数据（正常提交）
        db.save_content_analysis({
            "content_id": "committed-001",
            "raw_text": "committed data",
            "analysis": {"key": "value"},
            "model": "test",
            "created_at": "2025-01-01T00:00:00",
        })

        # 尝试插入第二条数据但回滚
        try:
            with db._get_conn() as conn:
                conn.execute(
                    "INSERT INTO content_analysis (id, raw_text, analysis_json, model, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("rolled-back-001", "rolled back", '{"k": "v"}', "test", "2025-01-01T00:00:00"),
                )
                raise ValueError("force rollback")
        except ValueError:
            pass

        # 第一条数据应仍在
        assert db.get_content_analysis("committed-001") is not None
        # 第二条数据应不存在
        assert db.get_content_analysis("rolled-back-001") is None


class TestConnectionLeak:
    """测试连接正确关闭，验证没有连接泄漏"""

    def test_connection_closed_after_context_exit(self, db):
        """退出上下文后连接应被关闭"""
        conn_obj = None
        with db._get_conn() as conn:
            conn_obj = conn
            # 连接应该是打开的
            assert conn_obj is not None

        # 退出后连接应已关闭
        # 尝试在已关闭的连接上执行查询应抛出异常
        import pytest
        with pytest.raises(Exception):
            conn_obj.execute("SELECT 1")

    def test_multiple_sequential_connections(self, db):
        """多次连续使用上下文管理器不应泄漏连接"""
        # 连续创建和关闭多个连接
        for i in range(20):
            with db._get_conn() as conn:
                conn.execute(
                    "INSERT INTO content_analysis (id, raw_text, analysis_json, model, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (f"conn-test-{i:03d}", f"text-{i}", '{"k": "v"}', "test", "2025-01-01T00:00:00"),
                )

        # 验证所有数据都正确写入了
        stats = db.get_stats()
        assert stats["content_count"] == 20

    def test_nested_operations_use_separate_connections(self, db):
        """嵌套操作应使用不同的连接"""
        with db._get_conn() as conn1:
            conn1.execute(
                "INSERT INTO content_analysis (id, raw_text, analysis_json, model, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("nested-001", "from conn1", '{"k": "v"}', "test", "2025-01-01T00:00:00"),
            )
            # conn1 的数据在 conn1 内部可见
            row = conn1.execute(
                "SELECT raw_text FROM content_analysis WHERE id = ?", ("nested-001",)
            ).fetchone()
            assert row is not None

        # conn1 退出后，通过 db 方法（新连接）应能看到数据
        result = db.get_content_analysis("nested-001")
        assert result is not None


class TestDataConsistencyCRUD:
    """测试 save -> get -> update -> delete 的数据一致性"""

    def test_full_crud_lifecycle_content(self, db):
        """内容分析的完整 CRUD 生命周期"""
        # 1. Create
        content_data = {
            "content_id": "crud-content-001",
            "raw_text": "初始内容文本",
            "analysis": {
                "hook_type": "痛点反问型",
                "content_score": 8.0,
                "hook_keywords": ["获客", "转化"],
            },
            "model": "deepseek-chat",
            "created_at": "2025-01-01T10:00:00",
        }
        db.save_content_analysis(content_data)

        # 2. Read
        result = db.get_content_analysis("crud-content-001")
        assert result is not None
        assert result["raw_text"] == "初始内容文本"
        assert result["analysis_json"]["content_score"] == 8.0
        assert result["analysis_json"]["hook_keywords"] == ["获客", "转化"]

        # 3. Update (使用 INSERT OR REPLACE)
        updated_data = dict(content_data)
        updated_data["raw_text"] = "更新后的内容文本"
        updated_data["analysis"]["content_score"] = 9.0
        db.save_content_analysis(updated_data)

        result = db.get_content_analysis("crud-content-001")
        assert result["raw_text"] == "更新后的内容文本"
        assert result["analysis_json"]["content_score"] == 9.0
        # 确认只有一条记录
        assert db.get_content_analyses_count() == 1

        # 4. Delete
        deleted = db.delete_content_analysis("crud-content-001")
        assert deleted is True
        assert db.get_content_analysis("crud-content-001") is None
        assert db.get_content_analyses_count() == 0

    def test_full_crud_lifecycle_lead(self, db):
        """线索分析的完整 CRUD 生命周期"""
        lead_data = {
            "lead_id": "crud-lead-001",
            "raw_data": {"name": "张总", "company": "XX科技"},
            "profile": {"industry": "教育/培训", "lead_score": 80},
            "model": "deepseek-chat",
            "created_at": "2025-01-01T10:00:00",
        }
        db.save_lead_analysis(lead_data)

        result = db.get_lead_analysis("crud-lead-001")
        assert result is not None
        assert result["profile_json"]["lead_score"] == 80

        # Update
        updated = dict(lead_data)
        updated["profile"]["lead_score"] = 90
        db.save_lead_analysis(updated)

        result = db.get_lead_analysis("crud-lead-001")
        assert result["profile_json"]["lead_score"] == 90

    def test_full_crud_lifecycle_match(self, db, sample_match_result):
        """匹配结果的完整 CRUD 生命周期"""
        match_id = db.save_match_result(sample_match_result, content_id="c1", lead_id="l1")
        assert match_id == "match-001"

        result = db.get_match_result("match-001")
        assert result is not None
        assert result["content_id"] == "c1"
        assert result["lead_id"] == "l1"

    def test_full_crud_lifecycle_strategy(self, db, sample_strategy_result):
        """策略建议的完整 CRUD 生命周期"""
        strategy_id = db.save_strategy_advice(sample_strategy_result)
        assert strategy_id == "strategy-001"

        advices = db.get_all_strategy_advices()
        assert len(advices) >= 1
        assert advices[0]["strategy_json"]["content_strategy"]["recommended_hook"] == "还在为获客发愁？"

    def test_cross_table_data_consistency(self, db, sample_content_result, sample_lead_result,
                                           sample_match_result, sample_strategy_result):
        """跨表数据一致性：保存所有类型数据后统计应正确"""
        # 保存各类型数据
        db.save_content_analysis(sample_content_result)
        db.save_lead_analysis(sample_lead_result)
        db.save_match_result(sample_match_result)
        db.save_strategy_advice(sample_strategy_result)

        # 验证统计
        stats = db.get_stats()
        assert stats["content_count"] == 1
        assert stats["lead_count"] == 1
        assert stats["match_count"] == 1
        assert stats["strategy_count"] == 1

        # 删除内容分析后统计应更新
        db.delete_content_analysis("content-001")
        stats = db.get_stats()
        assert stats["content_count"] == 0
        # 其他表不受影响
        assert stats["lead_count"] == 1
        assert stats["match_count"] == 1
        assert stats["strategy_count"] == 1


class TestGetStatsVariousStates:
    """测试 get_stats() 在各种数据状态下的正确性"""

    def test_stats_empty_database(self, db):
        """空数据库的统计应为全零"""
        stats = db.get_stats()
        assert stats == {
            "content_count": 0,
            "lead_count": 0,
            "match_count": 0,
            "strategy_count": 0,
        }

    def test_stats_after_single_insert(self, db, sample_content_result):
        """插入单条数据后统计"""
        db.save_content_analysis(sample_content_result)
        stats = db.get_stats()
        assert stats["content_count"] == 1
        assert stats["lead_count"] == 0
        assert stats["match_count"] == 0
        assert stats["strategy_count"] == 0

    def test_stats_after_bulk_insert(self, db):
        """批量插入后统计"""
        for i in range(5):
            db.save_content_analysis({
                "content_id": f"bulk-content-{i}",
                "raw_text": f"text-{i}",
                "analysis": {"score": i},
                "model": "test",
                "created_at": "2025-01-01T00:00:00",
            })
        for i in range(3):
            db.save_lead_analysis({
                "lead_id": f"bulk-lead-{i}",
                "raw_data": {"name": f"lead-{i}"},
                "profile": {"score": i},
                "model": "test",
                "created_at": "2025-01-01T00:00:00",
            })

        stats = db.get_stats()
        assert stats["content_count"] == 5
        assert stats["lead_count"] == 3
        assert stats["match_count"] == 0
        assert stats["strategy_count"] == 0

    def test_stats_after_clear(self, db, sample_content_result, sample_lead_result):
        """清空数据后统计"""
        db.save_content_analysis(sample_content_result)
        db.save_lead_analysis(sample_lead_result)
        db.clear_all_data()

        stats = db.get_stats()
        assert stats["content_count"] == 0
        assert stats["lead_count"] == 0
        assert stats["match_count"] == 0
        assert stats["strategy_count"] == 0

    def test_stats_after_delete_and_reinsert(self, db, sample_content_result):
        """删除后重新插入的统计"""
        db.save_content_analysis(sample_content_result)
        assert db.get_stats()["content_count"] == 1

        db.delete_content_analysis("content-001")
        assert db.get_stats()["content_count"] == 0

        # 重新插入
        db.save_content_analysis(sample_content_result)
        assert db.get_stats()["content_count"] == 1


class TestClearAllData:
    """测试 clear_all_data() 的完整性"""

    def test_clear_all_tables(self, db, sample_content_result, sample_lead_result,
                               sample_match_result, sample_strategy_result):
        """clear_all_data 应清空所有业务数据表"""
        # 保存各类型数据
        db.save_content_analysis(sample_content_result)
        db.save_lead_analysis(sample_lead_result)
        db.save_match_result(sample_match_result)
        db.save_strategy_advice(sample_strategy_result)

        # 保存 API 使用记录
        db.save_api_usage({
            "model": "deepseek-chat",
            "input_tokens": 100,
            "output_tokens": 50,
            "cost": 0.001,
            "operation_type": "test",
            "created_at": "2025-01-01T00:00:00",
        })

        # 确认数据存在
        assert db.get_stats()["content_count"] == 1
        assert db.get_stats()["lead_count"] == 1
        assert db.get_stats()["match_count"] == 1
        assert db.get_stats()["strategy_count"] == 1

        # 清空
        db.clear_all_data()

        # 验证所有业务表已清空
        assert db.get_content_analyses_count() == 0
        assert db.get_lead_analyses_count() == 0
        assert len(db.get_all_match_results()) == 0
        assert len(db.get_all_strategy_advices()) == 0

        # API 使用记录也应被清空
        usage_stats = db.get_api_usage_stats()
        assert usage_stats["total_calls"] == 0

    def test_clear_preserves_settings(self, db):
        """clear_all_data 不应清空设置表"""
        db.set_setting("test_key", "test_value")
        db.clear_all_data()

        # 设置应保留
        assert db.get_setting("test_key") == "test_value"

    def test_clear_preserves_table_structure(self, db):
        """clear_all_data 应保留表结构"""
        db.save_content_analysis({
            "content_id": "structure-test",
            "raw_text": "test",
            "analysis": {"k": "v"},
            "model": "test",
            "created_at": "2025-01-01T00:00:00",
        })
        db.clear_all_data()

        # 表结构应仍在，可以正常插入新数据
        db.save_content_analysis({
            "content_id": "after-clear-test",
            "raw_text": "new data after clear",
            "analysis": {"k": "v"},
            "model": "test",
            "created_at": "2025-01-01T00:00:00",
        })
        result = db.get_content_analysis("after-clear-test")
        assert result is not None
        assert result["raw_text"] == "new data after clear"

    def test_clear_idempotent(self, db):
        """多次调用 clear_all_data 不应报错"""
        db.clear_all_data()
        db.clear_all_data()
        db.clear_all_data()

        stats = db.get_stats()
        assert stats["content_count"] == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
