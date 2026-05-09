"""
分析器模块单元测试（使用 mock 避免 LLM 调用）
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.content_analyzer import ContentAnalyzer
from services.lead_analyzer import LeadAnalyzer
from services.match_engine import MatchEngine
from services.strategy_advisor import StrategyAdvisor

# ============================================================
# ContentAnalyzer 测试
# ============================================================


class TestContentAnalyzerValidateOutput:

    def test_content_analyzer_validate_output(
        self, mock_llm_client, sample_content_analysis_output
    ):
        """测试输出校验逻辑 - 完整数据"""
        analyzer = ContentAnalyzer(llm_client=mock_llm_client)
        validated = analyzer._validate_output(sample_content_analysis_output)

        # 所有字段应保留
        assert validated["hook_type"] == "痛点反问型"
        assert validated["hook_strength"] == 8.5
        assert validated["content_score"] == 8.0
        assert isinstance(validated["hook_keywords"], list)

    def test_content_analyzer_validate_output_missing_fields(self, mock_llm_client):
        """测试输出校验逻辑 - 缺失字段补全"""
        analyzer = ContentAnalyzer(llm_client=mock_llm_client)
        validated = analyzer._validate_output({})

        # 缺失字段应被补全为默认值
        assert validated["hook_type"] == "未知"
        assert validated["hook_strength"] == 5.0
        assert validated["content_score"] == 5.0
        assert validated["cta_clarity"] == 5.0
        assert validated["hook_keywords"] == []
        assert validated["topic_tags"] == []

    def test_content_analyzer_validate_output_score_clamping(self, mock_llm_client):
        """测试输出校验逻辑 - 分数范围限制"""
        analyzer = ContentAnalyzer(llm_client=mock_llm_client)

        # 超出范围的分数应被限制在 0-10
        validated = analyzer._validate_output(
            {
                "hook_strength": 15.0,
                "cta_clarity": -5.0,
                "content_score": 100.0,
            }
        )
        assert validated["hook_strength"] == 10.0
        assert validated["cta_clarity"] == 0.0
        assert validated["content_score"] == 10.0

    def test_content_analyzer_validate_output_list_coercion(self, mock_llm_client):
        """测试输出校验逻辑 - 列表字段强制转换"""
        analyzer = ContentAnalyzer(llm_client=mock_llm_client)

        validated = analyzer._validate_output(
            {
                "hook_keywords": "单个关键词",
                "emotion_curve": "单个阶段",
                "topic_tags": None,
            }
        )
        assert validated["hook_keywords"] == ["单个关键词"]
        assert validated["emotion_curve"] == ["单个阶段"]
        assert validated["topic_tags"] == []

    def test_content_analyzer_validate_output_invalid_score(self, mock_llm_client):
        """测试输出校验逻辑 - 无效分数值"""
        analyzer = ContentAnalyzer(llm_client=mock_llm_client)

        validated = analyzer._validate_output(
            {
                "hook_strength": "invalid",
                "cta_clarity": None,
                "content_score": "abc",
            }
        )
        assert validated["hook_strength"] == 5.0
        assert validated["cta_clarity"] == 5.0
        assert validated["content_score"] == 5.0


# ============================================================
# LeadAnalyzer 测试
# ============================================================


class TestLeadAnalyzerValidateOutput:

    def test_lead_analyzer_validate_output(
        self, mock_llm_client, sample_lead_analysis_output
    ):
        """测试输出校验逻辑 - 完整数据"""
        analyzer = LeadAnalyzer(llm_client=mock_llm_client)
        validated = analyzer._validate_output(sample_lead_analysis_output)

        assert validated["industry"] == "教育/培训"
        assert validated["intent_level"] == 7
        assert validated["lead_score"] == 75
        assert isinstance(validated["pain_points"], list)

    def test_lead_analyzer_validate_output_missing_fields(self, mock_llm_client):
        """测试输出校验逻辑 - 缺失字段补全"""
        analyzer = LeadAnalyzer(llm_client=mock_llm_client)
        validated = analyzer._validate_output({})

        assert validated["industry"] == "未知"
        assert validated["company_stage"] == "未知"
        assert validated["role"] == "未知"
        assert validated["intent_level"] == 5
        assert validated["lead_score"] == 50
        assert validated["pain_points"] == []
        assert validated["intent_signals"] == []

    def test_lead_analyzer_validate_output_grade_calculation(self, mock_llm_client):
        """测试输出校验逻辑 - 等级计算"""
        analyzer = LeadAnalyzer(llm_client=mock_llm_client)

        # A 级: score >= 85
        validated_a = analyzer._validate_output({"lead_score": 90})
        assert validated_a["lead_grade"] == "A"

        # B+ 级: 70 <= score < 85
        validated_bplus = analyzer._validate_output({"lead_score": 78})
        assert validated_bplus["lead_grade"] == "B+"

        # B 级: 55 <= score < 70
        validated_b = analyzer._validate_output({"lead_score": 60})
        assert validated_b["lead_grade"] == "B"

        # C 级: 40 <= score < 55
        validated_c = analyzer._validate_output({"lead_score": 45})
        assert validated_c["lead_grade"] == "C"

        # D 级: score < 40
        validated_d = analyzer._validate_output({"lead_score": 20})
        assert validated_d["lead_grade"] == "D"

    def test_lead_analyzer_validate_output_score_clamping(self, mock_llm_client):
        """测试输出校验逻辑 - 分数范围限制"""
        analyzer = LeadAnalyzer(llm_client=mock_llm_client)

        validated = analyzer._validate_output(
            {
                "intent_level": 15,
                "lead_score": 200,
            }
        )
        assert validated["intent_level"] == 10  # 0-10 范围
        assert validated["lead_score"] == 100  # 0-100 范围

    def test_lead_analyzer_validate_output_list_coercion(self, mock_llm_client):
        """测试输出校验逻辑 - 列表字段强制转换"""
        analyzer = LeadAnalyzer(llm_client=mock_llm_client)

        validated = analyzer._validate_output(
            {
                "pain_points": "单个痛点",
                "objection_risks": None,
            }
        )
        assert validated["pain_points"] == ["单个痛点"]
        assert validated["objection_risks"] == []


# ============================================================
# MatchEngine 测试
# ============================================================


class TestMatchEngineValidateOutput:

    def test_match_engine_validate_output(self, mock_llm_client, sample_match_output):
        """测试匹配结果校验 - 完整数据"""
        engine = MatchEngine(llm_client=mock_llm_client)
        validated = engine._validate_output(sample_match_output)

        assert validated["overall_score"] == 8.5
        assert validated["dimension_scores"]["audience_fit"] == 9.0
        assert validated["match_reason"] == "内容精准匹配线索痛点"
        assert isinstance(validated["risk_factors"], list)

    def test_match_engine_validate_output_missing_fields(self, mock_llm_client):
        """测试匹配结果校验 - 缺失字段补全"""
        engine = MatchEngine(llm_client=mock_llm_client)
        validated = engine._validate_output({})

        assert validated["overall_score"] == 5.0
        assert validated["match_reason"] == ""
        assert validated["risk_factors"] == []
        assert validated["recommended_follow_up"] == ""
        # 维度分数应全部补全为 5.0
        for key in [
            "audience_fit",
            "pain_point_relevance",
            "stage_alignment",
            "cta_appropriateness",
            "emotion_resonance",
        ]:
            assert validated["dimension_scores"][key] == 5.0

    def test_match_engine_validate_output_score_clamping(self, mock_llm_client):
        """测试匹配结果校验 - 分数范围限制"""
        engine = MatchEngine(llm_client=mock_llm_client)
        validated = engine._validate_output(
            {
                "overall_score": 15.0,
                "dimension_scores": {
                    "audience_fit": -3.0,
                    "pain_point_relevance": 12.0,
                },
            }
        )
        assert validated["overall_score"] == 10.0
        assert validated["dimension_scores"]["audience_fit"] == 0.0
        assert validated["dimension_scores"]["pain_point_relevance"] == 10.0
        # 缺失的维度分数应补全为 5.0
        assert validated["dimension_scores"]["stage_alignment"] == 5.0

    def test_match_engine_validate_output_list_coercion(self, mock_llm_client):
        """测试匹配结果校验 - 列表字段强制转换"""
        engine = MatchEngine(llm_client=mock_llm_client)
        validated = engine._validate_output(
            {
                "risk_factors": "单个风险",
            }
        )
        assert validated["risk_factors"] == ["单个风险"]


# ============================================================
# StrategyAdvisor 测试
# ============================================================


class TestStrategyAdvisorValidateOutput:

    def test_strategy_advisor_validate_output(
        self, mock_llm_client, sample_strategy_output
    ):
        """测试策略建议校验 - 完整数据"""
        advisor = StrategyAdvisor(llm_client=mock_llm_client)
        validated = advisor._validate_output(sample_strategy_output)

        assert "content_strategy" in validated
        assert "distribution_strategy" in validated
        assert "conversion_prediction" in validated
        assert "a_b_test_suggestion" in validated
        assert isinstance(validated["content_strategy"]["talking_points"], list)
        assert isinstance(
            validated["distribution_strategy"]["follow_up_sequence"], list
        )

    def test_strategy_advisor_validate_output_missing_sections(self, mock_llm_client):
        """测试策略建议校验 - 缺失模块补全"""
        advisor = StrategyAdvisor(llm_client=mock_llm_client)
        validated = advisor._validate_output({})

        # 四大模块都应存在
        assert "content_strategy" in validated
        assert "distribution_strategy" in validated
        assert "conversion_prediction" in validated
        assert "a_b_test_suggestion" in validated
        # content_strategy 的子字段会被补全默认值
        cs = validated["content_strategy"]
        assert cs["recommended_hook"] == "待定"
        assert cs["talking_points"] == []
        assert cs["keywords_to_include"] == []
        assert cs["keywords_to_avoid"] == []

    def test_strategy_advisor_validate_output_list_coercion(self, mock_llm_client):
        """测试策略建议校验 - 列表字段强制转换"""
        advisor = StrategyAdvisor(llm_client=mock_llm_client)
        validated = advisor._validate_output(
            {
                "content_strategy": {
                    "talking_points": "单个要点",
                    "keywords_to_include": None,
                },
                "distribution_strategy": {
                    "follow_up_sequence": "单个步骤",
                },
                "conversion_prediction": {
                    "key_success_factors": "单个因素",
                    "potential_blockers": None,
                },
            }
        )
        assert validated["content_strategy"]["talking_points"] == ["单个要点"]
        assert validated["content_strategy"]["keywords_to_include"] == []
        # follow_up_sequence 不是列表时会被替换为空列表
        assert validated["distribution_strategy"]["follow_up_sequence"] == []
        assert validated["conversion_prediction"]["key_success_factors"] == ["单个因素"]
        assert validated["conversion_prediction"]["potential_blockers"] == []


# ============================================================
# 摘要统计测试
# ============================================================


class TestContentAnalyzerSummary:

    def test_content_analyzer_get_summary(self, mock_llm_client):
        """测试摘要统计"""
        analyzer = ContentAnalyzer(llm_client=mock_llm_client)

        # 空列表
        summary = analyzer.get_content_summary([])
        assert summary == {}

        # 有成功和失败的结果
        results = [
            {
                "success": True,
                "data": {
                    "analysis": {
                        "hook_type": "痛点反问型",
                        "hook_strength": 8.0,
                        "cta_clarity": 7.0,
                        "content_score": 8.5,
                    }
                },
            },
            {
                "success": True,
                "data": {
                    "analysis": {
                        "hook_type": "数据冲击型",
                        "hook_strength": 6.0,
                        "cta_clarity": 5.0,
                        "content_score": 6.5,
                    }
                },
            },
            {
                "success": False,
                "error": "LLM调用失败",
            },
        ]

        summary = analyzer.get_content_summary(results)
        assert summary["total"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["avg_hook_strength"] == 7.0
        assert summary["avg_cta_clarity"] == 6.0
        assert summary["avg_content_score"] == 7.5
        assert summary["hook_type_distribution"] == {
            "痛点反问型": 1,
            "数据冲击型": 1,
        }

    def test_content_analyzer_get_summary_all_failed(self, mock_llm_client):
        """测试摘要统计 - 全部失败"""
        analyzer = ContentAnalyzer(llm_client=mock_llm_client)

        results = [
            {"success": False, "error": "error1"},
            {"success": False, "error": "error2"},
        ]
        summary = analyzer.get_content_summary(results)
        assert summary["total"] == 2
        assert summary["successful"] == 0
        assert summary["failed"] == 2


class TestLeadAnalyzerSummary:

    def test_lead_analyzer_get_summary(self, mock_llm_client):
        """测试线索摘要统计"""
        analyzer = LeadAnalyzer(llm_client=mock_llm_client)

        # 空列表
        summary = analyzer.get_lead_summary([])
        assert summary == {}

        results = [
            {
                "success": True,
                "data": {
                    "profile": {
                        "industry": "教育/培训",
                        "intent_level": 7,
                        "lead_score": 85,
                        "buying_stage": "考虑期",
                        "lead_grade": "A",
                    }
                },
            },
            {
                "success": True,
                "data": {
                    "profile": {
                        "industry": "制造业",
                        "intent_level": 5,
                        "lead_score": 60,
                        "buying_stage": "认知期",
                        "lead_grade": "B",
                    }
                },
            },
            {
                "success": False,
                "error": "分析失败",
            },
        ]

        summary = analyzer.get_lead_summary(results)
        assert summary["total"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["avg_intent_level"] == 6.0
        assert summary["avg_lead_score"] == 72.5
        assert summary["industry_distribution"] == {
            "教育/培训": 1,
            "制造业": 1,
        }
        assert summary["buying_stage_distribution"] == {
            "考虑期": 1,
            "认知期": 1,
        }
        assert summary["grade_distribution"]["A"] == 1
        assert summary["grade_distribution"]["B"] == 1

    def test_lead_analyzer_get_summary_all_failed(self, mock_llm_client):
        """测试线索摘要统计 - 全部失败"""
        analyzer = LeadAnalyzer(llm_client=mock_llm_client)

        results = [
            {"success": False, "error": "error1"},
        ]
        summary = analyzer.get_lead_summary(results)
        assert summary["total"] == 1
        assert summary["successful"] == 0
        assert summary["failed"] == 1
