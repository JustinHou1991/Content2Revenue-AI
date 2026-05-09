"""
数据库模块单元测试
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.database import Database


class TestDatabaseInit:

    def test_init_tables(self, db):
        """验证所有表都被正确创建"""
        with db._get_conn() as conn:
            cursor = conn.cursor()

            # 获取所有表名
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "content_analysis",
            "lead_analysis",
            "match_results",
            "strategy_advice",
            "app_settings",
        }
        assert expected_tables.issubset(tables), f"缺少表: {expected_tables - tables}"

    def test_db_path_auto_create(self):
        """测试数据库目录自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            # 在临时目录下创建一个不存在的子目录
            nested_dir = os.path.join(tmp_dir, "a", "b", "c")
            db_path = os.path.join(nested_dir, "test.db")
            # 确保目录不存在
            assert not os.path.exists(nested_dir)

            db = Database(db_path=db_path)
            # 目录应该被自动创建
            assert os.path.exists(nested_dir)
            # 数据库文件应该存在
            assert os.path.exists(db_path)
            db.close()

            # 清理
            os.remove(db_path)
            os.rmdir(nested_dir)
            os.rmdir(os.path.dirname(nested_dir))
            os.rmdir(os.path.dirname(os.path.dirname(nested_dir)))
        finally:
            # 确保临时目录被清理
            import shutil

            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)


class TestContentAnalysisCRUD:

    def test_save_and_get_content_analysis(self, db, sample_content_result):
        """保存和查询内容分析"""
        content_id = db.save_content_analysis(sample_content_result)
        assert content_id == "content-001"

        result = db.get_content_analysis("content-001")
        assert result is not None
        assert result["id"] == "content-001"
        assert result["raw_text"] == sample_content_result["raw_text"]
        # JSON 字段应被自动解析为 dict
        assert isinstance(result["analysis_json"], dict)
        assert result["analysis_json"]["hook_type"] == "痛点反问型"
        assert result["model"] == "deepseek-chat"

    def test_get_content_analysis_not_found(self, db):
        """查询不存在的内容分析"""
        result = db.get_content_analysis("non-existent")
        assert result is None


class TestLeadAnalysisCRUD:

    def test_save_and_get_lead_analysis(self, db, sample_lead_result):
        """保存和查询线索分析"""
        lead_id = db.save_lead_analysis(sample_lead_result)
        assert lead_id == "lead-001"

        result = db.get_lead_analysis("lead-001")
        assert result is not None
        assert result["id"] == "lead-001"
        # JSON 字段应被自动解析
        assert isinstance(result["raw_data_json"], dict)
        assert isinstance(result["profile_json"], dict)
        assert result["profile_json"]["industry"] == "教育/培训"
        assert result["profile_json"]["lead_score"] == 75


class TestMatchResultCRUD:

    def test_save_and_get_match_result(self, db, sample_match_result):
        """保存和查询匹配结果（注意新的content_id/lead_id参数）"""
        match_id = db.save_match_result(
            sample_match_result,
            content_id="content-001",
            lead_id="lead-001",
        )
        assert match_id == "match-001"

        result = db.get_match_result("match-001")
        assert result is not None
        assert result["id"] == "match-001"
        assert result["content_id"] == "content-001"
        assert result["lead_id"] == "lead-001"
        # JSON 字段应被自动解析
        assert isinstance(result["match_result_json"], dict)
        assert result["match_result_json"]["overall_score"] == 8.5

    def test_save_match_result_without_explicit_ids(self, db, sample_match_result):
        """保存匹配结果时不传显式content_id/lead_id，从snapshot中提取"""
        match_id = db.save_match_result(sample_match_result)
        assert match_id == "match-001"

        result = db.get_match_result("match-001")
        assert result is not None
        # 应从 snapshot 中提取 content_id 和 lead_id
        assert result["content_id"] == "content-001"
        assert result["lead_id"] == "lead-001"

    def test_get_match_result_not_found(self, db):
        """查询不存在的匹配结果"""
        result = db.get_match_result("non-existent")
        assert result is None


class TestStrategyAdviceCRUD:

    def test_save_and_get_strategy_advice(self, db, sample_strategy_result):
        """保存和查询策略建议"""
        strategy_id = db.save_strategy_advice(sample_strategy_result)
        assert strategy_id == "strategy-001"

        # 通过 get_all_strategy_advices 查询
        advices = db.get_all_strategy_advices()
        assert len(advices) >= 1
        advice = advices[0]
        assert advice["id"] == "strategy-001"
        assert advice["match_id"] == "match-001"
        assert advice["content_id"] == "content-001"
        assert advice["lead_id"] == "lead-001"
        # JSON 字段应被自动解析
        assert isinstance(advice["strategy_json"], dict)
        assert "content_strategy" in advice["strategy_json"]

    def test_get_all_strategy_advices(self, db, sample_strategy_result):
        """测试新增的方法 - 获取所有策略建议"""
        # 保存多条策略建议
        for i in range(3):
            result = dict(sample_strategy_result)
            result["strategy_id"] = f"strategy-{i:03d}"
            result["match_id"] = f"match-{i:03d}"
            db.save_strategy_advice(result)

        advices = db.get_all_strategy_advices(limit=10)
        assert len(advices) == 3

        # 测试 limit 参数
        advices_limited = db.get_all_strategy_advices(limit=2)
        assert len(advices_limited) == 2

    def test_get_strategy_advices_by_lead(self, db, sample_strategy_result):
        """按线索ID查询策略建议"""
        db.save_strategy_advice(sample_strategy_result)

        # 保存另一条不同线索的策略
        another = dict(sample_strategy_result)
        another["strategy_id"] = "strategy-002"
        another["lead_id"] = "lead-002"
        db.save_strategy_advice(another)

        advices = db.get_strategy_advices_by_lead("lead-001")
        assert len(advices) == 1
        assert advices[0]["id"] == "strategy-001"


class TestStats:

    def test_get_stats(
        self,
        db,
        sample_content_result,
        sample_lead_result,
        sample_match_result,
        sample_strategy_result,
    ):
        """测试统计信息"""
        # 初始状态
        stats = db.get_stats()
        assert stats == {
            "content_count": 0,
            "lead_count": 0,
            "match_count": 0,
            "strategy_count": 0,
        }

        # 保存各类型数据
        db.save_content_analysis(sample_content_result)
        db.save_lead_analysis(sample_lead_result)
        db.save_match_result(sample_match_result)
        db.save_strategy_advice(sample_strategy_result)

        stats = db.get_stats()
        assert stats["content_count"] == 1
        assert stats["lead_count"] == 1
        assert stats["match_count"] == 1
        assert stats["strategy_count"] == 1


class TestSettingsCRUD:

    def test_settings_crud(self, db):
        """测试设置的增删改查"""
        # 默认值
        val = db.get_setting("nonexistent", "default_val")
        assert val == "default_val"

        # 设置值
        db.set_setting("api_key", "sk-12345")
        val = db.get_setting("api_key")
        assert val == "sk-12345"

        # 更新值
        db.set_setting("api_key", "sk-67890")
        val = db.get_setting("api_key")
        assert val == "sk-67890"

        # 多个设置
        db.set_setting("model", "deepseek-chat")
        db.set_setting("temperature", "0.3")
        assert db.get_setting("model") == "deepseek-chat"
        assert db.get_setting("temperature") == "0.3"


class TestClearAllData:

    def test_clear_all_data(
        self,
        db,
        sample_content_result,
        sample_lead_result,
        sample_match_result,
        sample_strategy_result,
    ):
        """测试清空数据"""
        # 保存数据
        db.save_content_analysis(sample_content_result)
        db.save_lead_analysis(sample_lead_result)
        db.save_match_result(sample_match_result)
        db.save_strategy_advice(sample_strategy_result)

        # 确认数据存在
        stats = db.get_stats()
        assert stats["content_count"] == 1
        assert stats["lead_count"] == 1
        assert stats["match_count"] == 1
        assert stats["strategy_count"] == 1

        # 清空数据
        db.clear_all_data()

        # 确认数据已清空
        stats = db.get_stats()
        assert stats["content_count"] == 0
        assert stats["lead_count"] == 0
        assert stats["match_count"] == 0
        assert stats["strategy_count"] == 0

        # 设置表不应被清空
        db.set_setting("key", "value")
        assert db.get_setting("key") == "value"


class TestRowToDictJsonParsing:

    def test_row_to_dict_json_parsing(self, db, sample_content_result):
        """测试JSON字段的自动解析"""
        db.save_content_analysis(sample_content_result)
        result = db.get_content_analysis("content-001")

        # analysis_json 应被自动解析为 dict
        assert isinstance(result["analysis_json"], dict)
        assert result["analysis_json"]["hook_type"] == "痛点反问型"
        assert result["analysis_json"]["hook_strength"] == 8.5
        assert isinstance(result["analysis_json"]["hook_keywords"], list)

    def test_row_to_dict_invalid_json(self, db):
        """测试无效JSON字段的容错处理"""
        with db._get_conn() as conn:
            # 手动插入一个无效的 JSON 字段
            conn.execute(
                "INSERT INTO content_analysis (id, raw_text, analysis_json, model, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("bad-json-001", "test", "{invalid json}", "test", "2025-01-01T00:00:00"),
            )

        result = db.get_content_analysis("bad-json-001")
        assert result is not None
        # 无效 JSON 应保留原始字符串（解析失败时不崩溃）
        assert result["analysis_json"] == "{invalid json}"
