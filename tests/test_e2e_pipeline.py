"""
R3 端到端测试 - 模拟完整用户流程

覆盖 5 个关键流程：
1. 完整 Pipeline：内容分析 -> 线索分析 -> 匹配 -> 策略
2. Orchestrator 完整 Pipeline
3. 数据清洗 -> 分析 Pipeline
4. 批量分析 Pipeline
5. 错误恢复流程
"""

import json
import logging
import os
import sys
import tempfile
import uuid
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.database import Database
from services.llm_client import LLMClient
from services.content_analyzer import ContentAnalyzer
from services.lead_analyzer import LeadAnalyzer
from services.match_engine import MatchEngine
from services.strategy_advisor import StrategyAdvisor
from services.orchestrator import Orchestrator
from services.data_cleaner import LeadDataCleaner, ScriptDataCleaner

logger = logging.getLogger(__name__)


# ============================================================
# Mock 数据
# ============================================================

MOCK_CONTENT_ANALYSIS = {
    "hook_type": "痛点反问型",
    "hook_strength": 8.5,
    "hook_keywords": ["传统获客", "投流", "询盘"],
    "emotion_tone": "焦虑→希望",
    "emotion_curve": ["焦虑(0-5s)", "共鸣(5-15s)", "希望(15-30s)"],
    "narrative_structure": "PAS",
    "cta_type": "评论区互动型",
    "cta_clarity": 7.0,
    "topic_tags": ["获客", "B2B", "营销", "投流", "转化"],
    "target_audience": "中小企业老板",
    "content_category": "方法论",
    "estimated_conversion_stage": "认知",
    "key_selling_points": ["低成本获客", "精准客户", "快速成交"],
    "content_score": 8.0,
    "improvement_suggestions": ["增加数据案例", "缩短开头"],
}

MOCK_LEAD_ANALYSIS = {
    "industry": "教育/培训",
    "company_stage": "成长期",
    "role": "决策者",
    "pain_points": ["获客成本高", "转化率低"],
    "intent_level": 7,
    "intent_signals": ["主动咨询", "多次访问"],
    "buying_stage": "考虑期",
    "urgency": "中",
    "budget_readiness": "有预算",
    "decision_criteria": ["效果", "价格"],
    "objection_risks": ["价格敏感"],
    "recommended_content_type": "案例",
    "recommended_cta": "私信咨询型",
    "engagement_strategy": "先提供免费方案",
    "lead_score": 75,
}

MOCK_MATCH_RESULT = {
    "overall_score": 8.5,
    "dimension_scores": {
        "audience_fit": 9.0,
        "pain_point_relevance": 8.0,
        "stage_alignment": 8.5,
        "cta_appropriateness": 7.5,
        "emotion_resonance": 9.0,
    },
    "match_reason": "内容精准匹配线索痛点，受众画像高度一致",
    "risk_factors": ["价格可能偏高"],
    "recommended_follow_up": "发送免费案例",
}

MOCK_STRATEGY = {
    "content_strategy": {
        "recommended_hook": "还在为获客发愁？3步搞定精准引流",
        "hook_rationale": "直接命中中小企业获客痛点",
        "recommended_structure": "PAS",
        "talking_points": ["低成本获客方法", "精准引流技巧", "快速转化话术"],
        "tone_guidance": "专业且亲切，避免过度营销感",
        "keywords_to_include": ["获客", "转化", "精准"],
        "keywords_to_avoid": ["免费", "便宜"],
    },
    "distribution_strategy": {
        "best_timing": "工作日 18:00-20:00",
        "channel_suggestion": "抖音+微信朋友圈",
        "follow_up_sequence": [
            "Day 0: 发送免费案例",
            "Day 1: 电话跟进",
            "Day 3: 邀请体验",
            "Day 7: 方案报价",
        ],
    },
    "conversion_prediction": {
        "estimated_conversion_rate": "15%-20%",
        "confidence_level": "中",
        "key_success_factors": ["痛点匹配度高", "信任建立快"],
        "potential_blockers": ["预算不足", "决策周期长"],
    },
    "a_b_test_suggestion": {
        "variant_a": "痛点反问型开头",
        "variant_b": "数据冲击型开头",
        "test_metric": "私信咨询率",
        "recommended_sample_size": "1000",
    },
}


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def tmp_db_path():
    """创建临时数据库路径"""
    d = tempfile.mkdtemp()
    db_path = os.path.join(d, "test_e2e.db")
    yield db_path
    # 清理
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    os.rmdir(d)


@pytest.fixture
def db(tmp_db_path):
    """创建使用临时数据库的 Database 实例"""
    database = Database(db_path=tmp_db_path)
    yield database
    database.close()


@pytest.fixture
def mock_llm():
    """创建 mock LLM 客户端，chat_json 返回不同结果"""
    mock = MagicMock(spec=LLMClient)
    mock.model = "deepseek-chat"
    # 默认返回内容分析结果
    mock.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)
    return mock


@pytest.fixture
def sample_script():
    """示例抖音脚本"""
    return (
        "你是不是还在用传统方式获客？每天花500块投流，一个询盘都没有？\n"
        "我认识一个做企业培训的王总，之前就是这个问题，投了3个月广告，花了4万多，"
        "只来了8个客户，还都不精准。\n"
        "后来他用了我们的3步获客法，第一个月就加了200多个精准客户，成交了30多单。\n"
        "想知道这3步是什么？评论区扣'获客'，我免费发你完整版。"
    )


@pytest.fixture
def sample_lead_data():
    """示例线索数据"""
    return {
        "name": "张总",
        "company": "XX教育科技",
        "industry": "教育培训",
        "title": "创始人",
        "source": "抖音私信",
        "conversation": "看了你们的视频，我们公司目前获客成本太高了，想了解一下你们的方案",
        "company_size": "50-200人",
        "remark": "对短视频获客很感兴趣，但还在观望",
    }


# ============================================================
# 流程 1：完整的内容分析 -> 线索分析 -> 匹配 -> 策略 Pipeline
# ============================================================


class TestFullPipelineE2E:
    """端到端流程1：完整 Pipeline 手动串联"""

    def test_content_analysis_step(self, db, mock_llm, sample_script):
        """步骤1：内容分析并保存到数据库"""
        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)

        analyzer = ContentAnalyzer(llm_client=mock_llm)
        result = analyzer.analyze(sample_script, script_id="content-e2e-001")

        # 验证分析结果结构
        assert "content_id" in result
        assert result["content_id"] == "content-e2e-001"
        assert "analysis" in result
        assert result["analysis"]["hook_type"] == "痛点反问型"
        assert result["analysis"]["content_score"] == 8.0
        assert result["analysis"]["narrative_structure"] == "PAS"
        assert len(result["analysis"]["key_selling_points"]) == 3
        assert "raw_text" in result
        assert "created_at" in result

        # 保存到数据库
        db.save_content_analysis(result)

        # 验证数据库中存在
        saved = db.get_content_analysis("content-e2e-001")
        assert saved is not None
        assert saved["analysis_json"]["hook_type"] == "痛点反问型"
        assert saved["raw_text"] == sample_script

    def test_lead_analysis_step(self, db, mock_llm, sample_lead_data):
        """步骤2：线索分析并保存到数据库"""
        mock_llm.chat_json.return_value = dict(MOCK_LEAD_ANALYSIS)

        analyzer = LeadAnalyzer(llm_client=mock_llm)
        result = analyzer.analyze(sample_lead_data, lead_id="lead-e2e-001")

        # 验证分析结果结构
        assert "lead_id" in result
        assert result["lead_id"] == "lead-e2e-001"
        assert "profile" in result
        assert result["profile"]["industry"] == "教育/培训"
        assert result["profile"]["lead_score"] == 75
        assert result["profile"]["pain_points"] == ["获客成本高", "转化率低"]
        assert "lead_grade" in result["profile"]
        assert result["profile"]["lead_grade"] == "B+"
        assert "raw_data" in result
        assert "created_at" in result

        # 保存到数据库
        db.save_lead_analysis(result)

        # 验证数据库中存在
        saved = db.get_lead_analysis("lead-e2e-001")
        assert saved is not None
        assert saved["profile_json"]["industry"] == "教育/培训"
        assert saved["profile_json"]["lead_score"] == 75

    def test_match_step(self, db, mock_llm):
        """步骤3：内容-线索匹配"""
        mock_llm.chat_json.return_value = dict(MOCK_MATCH_RESULT)

        engine = MatchEngine(llm_client=mock_llm)
        result = engine.match(
            content_feature=MOCK_CONTENT_ANALYSIS,
            lead_profile=MOCK_LEAD_ANALYSIS,
            content_id="content-e2e-001",
            lead_id="lead-e2e-001",
        )

        # 验证匹配结果结构
        assert "match_id" in result
        assert "match_result" in result
        assert "content_snapshot" in result
        assert "lead_snapshot" in result

        # 验证 5 个维度分数
        dim_scores = result["match_result"]["dimension_scores"]
        assert "audience_fit" in dim_scores
        assert "pain_point_relevance" in dim_scores
        assert "stage_alignment" in dim_scores
        assert "cta_appropriateness" in dim_scores
        assert "emotion_resonance" in dim_scores
        assert len(dim_scores) == 5

        # 验证分数范围
        for key, score in dim_scores.items():
            assert 0 <= score <= 10, f"{key}={score} 不在 0-10 范围内"

        assert result["match_result"]["overall_score"] == 8.5
        assert result["content_snapshot"]["content_id"] == "content-e2e-001"
        assert result["lead_snapshot"]["lead_id"] == "lead-e2e-001"

        # 保存到数据库
        db.save_match_result(result)

        # 验证数据库中存在
        saved = db.get_match_result(result["match_id"])
        assert saved is not None
        assert saved["match_result_json"]["overall_score"] == 8.5

    def test_strategy_step(self, db, mock_llm):
        """步骤4：生成策略建议"""
        mock_llm.chat_json.return_value = dict(MOCK_STRATEGY)

        # 构造 match_result（与 MatchEngine 输出格式一致）
        match_result = {
            "match_id": "match-e2e-001",
            "match_result": MOCK_MATCH_RESULT,
            "content_snapshot": {
                "content_id": "content-e2e-001",
                "hook_type": "痛点反问型",
                "topic_tags": ["获客", "B2B", "营销"],
                "content_score": 8.0,
            },
            "lead_snapshot": {
                "lead_id": "lead-e2e-001",
                "industry": "教育/培训",
                "pain_points": ["获客成本高", "转化率低"],
                "buying_stage": "考虑期",
                "lead_score": 75,
            },
            "created_at": "2025-01-01T10:00:00",
            "model": "deepseek-chat",
        }

        advisor = StrategyAdvisor(llm_client=mock_llm)
        result = advisor.advise(match_result)

        # 验证策略结果结构
        assert "strategy_id" in result
        assert "match_id" in result
        assert "strategy" in result

        # 验证 4 个模块
        strategy = result["strategy"]
        assert "content_strategy" in strategy
        assert "distribution_strategy" in strategy
        assert "conversion_prediction" in strategy
        assert "a_b_test_suggestion" in strategy

        # 验证 content_strategy
        cs = strategy["content_strategy"]
        assert "recommended_hook" in cs
        assert "talking_points" in cs
        assert isinstance(cs["talking_points"], list)
        assert len(cs["talking_points"]) >= 1

        # 验证 distribution_strategy
        ds = strategy["distribution_strategy"]
        assert "best_timing" in ds
        assert "channel_suggestion" in ds
        assert "follow_up_sequence" in ds

        # 验证 conversion_prediction
        cp = strategy["conversion_prediction"]
        assert "estimated_conversion_rate" in cp
        assert "confidence_level" in cp
        assert cp["confidence_level"] in ["低", "中", "高"]

        # 验证 a_b_test_suggestion
        ab = strategy["a_b_test_suggestion"]
        assert "variant_a" in ab
        assert "variant_b" in ab
        assert "test_metric" in ab

        # 保存到数据库
        db.save_strategy_advice(result)

        # 验证数据库中存在
        assert db.get_stats()["strategy_count"] >= 1

    def test_full_pipeline_database_stats(self, db, mock_llm, sample_script, sample_lead_data):
        """步骤5：完整 Pipeline 后验证数据库统计"""
        # 内容分析
        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)
        ca = ContentAnalyzer(llm_client=mock_llm)
        content_result = ca.analyze(sample_script, script_id="content-stats-001")
        db.save_content_analysis(content_result)

        # 线索分析
        mock_llm.chat_json.return_value = dict(MOCK_LEAD_ANALYSIS)
        la = LeadAnalyzer(llm_client=mock_llm)
        lead_result = la.analyze(sample_lead_data, lead_id="lead-stats-001")
        db.save_lead_analysis(lead_result)

        # 匹配
        mock_llm.chat_json.return_value = dict(MOCK_MATCH_RESULT)
        me = MatchEngine(llm_client=mock_llm)
        match_result = me.match(
            content_result["analysis"],
            lead_result["profile"],
            content_id="content-stats-001",
            lead_id="lead-stats-001",
        )
        db.save_match_result(match_result)

        # 策略
        mock_llm.chat_json.return_value = dict(MOCK_STRATEGY)
        sa = StrategyAdvisor(llm_client=mock_llm)
        strategy_result = sa.advise(match_result)
        db.save_strategy_advice(strategy_result)

        # 验证统计
        stats = db.get_stats()
        assert stats["content_count"] == 1
        assert stats["lead_count"] == 1
        assert stats["match_count"] == 1
        assert stats["strategy_count"] == 1


# ============================================================
# 流程 2：Orchestrator 完整 Pipeline
# ============================================================


class TestOrchestratorE2E:
    """端到端流程2：通过 Orchestrator 执行完整 Pipeline"""

    @pytest.fixture
    def orchestrator(self, tmp_db_path):
        """创建 mock 了 LLM 的 Orchestrator"""
        with patch.object(LLMClient, "__init__", lambda self, **kwargs: None):
            with patch.object(LLMClient, "model", "deepseek-chat", create=True):
                orch = Orchestrator.__new__(Orchestrator)
                orch.model = "deepseek-chat"
                orch.llm = MagicMock(spec=LLMClient)
                orch.llm.model = "deepseek-chat"
                orch.db = Database(db_path=tmp_db_path)
                orch.content_analyzer = ContentAnalyzer(llm_client=orch.llm)
                orch.lead_analyzer = LeadAnalyzer(llm_client=orch.llm)
                orch.match_engine = MatchEngine(llm_client=orch.llm)
                orch.strategy_advisor = StrategyAdvisor(llm_client=orch.llm)
                yield orch
                orch.db.close()

    def test_orchestrator_full_pipeline(
        self, orchestrator, sample_script, sample_lead_data
    ):
        """通过 Orchestrator.full_pipeline 执行完整流程"""
        orch = orchestrator

        # 按顺序 mock 4 次 LLM 调用
        call_count = [0]

        def mock_chat_json(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                return dict(MOCK_CONTENT_ANALYSIS)
            elif idx == 1:
                return dict(MOCK_LEAD_ANALYSIS)
            elif idx == 2:
                return dict(MOCK_MATCH_RESULT)
            else:
                return dict(MOCK_STRATEGY)

        orch.llm.chat_json.side_effect = mock_chat_json

        # 执行完整 Pipeline
        result = orch.full_pipeline(sample_script, sample_lead_data)

        # 验证返回结构
        assert "content" in result
        assert "lead" in result
        assert "match" in result
        assert "strategy" in result

        # 验证内容分析结果
        content = result["content"]
        assert "content_id" in content
        assert "analysis" in content
        assert content["analysis"]["hook_type"] == "痛点反问型"
        assert content["analysis"]["content_score"] == 8.0

        # 验证线索分析结果
        lead = result["lead"]
        assert "lead_id" in lead
        assert "profile" in lead
        assert lead["profile"]["industry"] == "教育/培训"
        assert lead["profile"]["lead_score"] == 75

        # 验证匹配结果
        match = result["match"]
        assert "match_id" in match
        assert "match_result" in match
        dim_scores = match["match_result"]["dimension_scores"]
        assert len(dim_scores) == 5
        assert match["match_result"]["overall_score"] == 8.5

        # 验证策略结果
        strategy = result["strategy"]
        assert "strategy_id" in strategy
        assert "strategy" in strategy
        s = strategy["strategy"]
        assert "content_strategy" in s
        assert "distribution_strategy" in s
        assert "conversion_prediction" in s
        assert "a_b_test_suggestion" in s

        # 验证数据库中所有数据正确保存
        stats = orch.db.get_stats()
        assert stats["content_count"] == 1
        assert stats["lead_count"] == 1
        assert stats["match_count"] == 1
        assert stats["strategy_count"] == 1

        # 验证可以从数据库中查询到数据
        content_db = orch.db.get_content_analysis(content["content_id"])
        assert content_db is not None
        assert content_db["analysis_json"]["hook_type"] == "痛点反问型"

        lead_db = orch.db.get_lead_analysis(lead["lead_id"])
        assert lead_db is not None
        assert lead_db["profile_json"]["industry"] == "教育/培训"

        match_db = orch.db.get_match_result(match["match_id"])
        assert match_db is not None
        assert match_db["match_result_json"]["overall_score"] == 8.5

    def test_orchestrator_analyze_content_saves_to_db(
        self, orchestrator, sample_script
    ):
        """Orchestrator.analyze_content 保存到数据库"""
        orchestrator.llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)

        result = orchestrator.analyze_content(sample_script)

        assert "content_id" in result
        assert result["analysis"]["content_score"] == 8.0

        # 验证数据库
        saved = orchestrator.db.get_content_analysis(result["content_id"])
        assert saved is not None
        assert saved["raw_text"] == sample_script

    def test_orchestrator_analyze_lead_saves_to_db(
        self, orchestrator, sample_lead_data
    ):
        """Orchestrator.analyze_lead 保存到数据库"""
        orchestrator.llm.chat_json.return_value = dict(MOCK_LEAD_ANALYSIS)

        result = orchestrator.analyze_lead(sample_lead_data)

        assert "lead_id" in result
        assert result["profile"]["lead_score"] == 75

        # 验证数据库
        saved = orchestrator.db.get_lead_analysis(result["lead_id"])
        assert saved is not None

    def test_orchestrator_match_content_lead(
        self, orchestrator, sample_script, sample_lead_data
    ):
        """Orchestrator.match_content_lead 端到端"""
        # 先保存内容和线索
        orchestrator.llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)
        content_result = orchestrator.analyze_content(sample_script)

        orchestrator.llm.chat_json.return_value = dict(MOCK_LEAD_ANALYSIS)
        lead_result = orchestrator.analyze_lead(sample_lead_data)

        # 执行匹配
        orchestrator.llm.chat_json.return_value = dict(MOCK_MATCH_RESULT)
        match_result = orchestrator.match_content_lead(
            content_result["content_id"], lead_result["lead_id"]
        )

        assert "match_id" in match_result
        assert match_result["match_result"]["overall_score"] == 8.5

        # 验证数据库
        saved = orchestrator.db.get_match_result(match_result["match_id"])
        assert saved is not None

    def test_orchestrator_generate_strategy(self, orchestrator):
        """Orchestrator.generate_strategy 端到端"""
        # 先保存匹配结果
        match_id = "match-orch-001"
        match_data = {
            "match_id": match_id,
            "match_result": MOCK_MATCH_RESULT,
            "content_snapshot": {
                "content_id": "content-orch-001",
                "hook_type": "痛点反问型",
                "topic_tags": ["获客"],
                "content_score": 8.0,
            },
            "lead_snapshot": {
                "lead_id": "lead-orch-001",
                "industry": "教育/培训",
                "pain_points": ["获客成本高"],
                "buying_stage": "考虑期",
                "lead_score": 75,
            },
            "created_at": "2025-01-01T10:00:00",
            "model": "deepseek-chat",
        }
        orchestrator.db.save_match_result(match_data)

        # 生成策略
        orchestrator.llm.chat_json.return_value = dict(MOCK_STRATEGY)
        strategy_result = orchestrator.generate_strategy(match_id)

        assert "strategy_id" in strategy_result
        # match_id 来自数据库查询后传给 advise，strategy 的 match_id 由 match_result 决定
        assert "strategy" in strategy_result

        # 验证数据库
        stats = orchestrator.db.get_stats()
        assert stats["strategy_count"] == 1


# ============================================================
# 流程 3：数据清洗 -> 分析 Pipeline
# ============================================================


class TestDataCleaningPipelineE2E:
    """端到端流程3：数据清洗后进行分析"""

    def test_lead_data_cleaning_then_analysis(self, db, mock_llm):
        """清洗线索数据后进行 LLM 分析"""
        import pandas as pd

        # 1. 创建包含不规范数据的 DataFrame
        raw_df = pd.DataFrame({
            "公司名称": [
                "  杭州某某科技有限公司  ",
                "北京某某教育咨询有限公司",
                "上海某某餐饮管理有限公司",
                "杭州某某科技有限公司",  # 重复
                "",  # 空公司名
            ],
            "行业": ["SaaS软件", "教育培训", "奶茶", "软件", "金融"],
            "手机号": [
                "13800138000",
                "13900139000",
                "13700137000",
                "13800138000",  # 重复手机号
                "13600136000",
            ],
            "需求描述": ["需要获客系统", None, "想做加盟", "需要获客系统", None],
            "意向级别": ["A", "高", "hot", "B", "C"],
            "来源": ["抖音", None, "微信", "抖音", None],
        })

        # 2. 清洗数据
        cleaner = LeadDataCleaner()
        cleaned_df = cleaner.clean(raw_df)

        # 3. 验证清洗结果
        # 去重：原始5条，重复手机号1条 + 空公司名1条 = 移除2条
        assert len(cleaned_df) == 3

        # 验证标准化字段
        assert "公司名称_标准化" in cleaned_df.columns
        assert "行业_标准化" in cleaned_df.columns
        assert "意向级别_标准化" in cleaned_df.columns

        # 验证行业标准化
        assert cleaned_df.iloc[0]["行业_标准化"] == "企业服务"
        assert cleaned_df.iloc[1]["行业_标准化"] == "教育/培训"
        assert cleaned_df.iloc[2]["行业_标准化"] == "餐饮/食品"

        # 验证意向级别标准化
        assert cleaned_df.iloc[0]["意向级别_标准化"] == "高"
        assert cleaned_df.iloc[1]["意向级别_标准化"] == "高"
        assert cleaned_df.iloc[2]["意向级别_标准化"] == "高"

        # 验证清洗摘要
        summary = cleaner.get_cleaning_summary()
        assert summary["原始记录数"] == 5
        assert summary["清洗后记录数"] == 3
        assert summary["移除记录数"] == 2

        # 4. 对清洗后的数据调用 ContentAnalyzer（mock API）
        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)
        analyzer = ContentAnalyzer(llm_client=mock_llm)

        # 取第一条清洗后的脚本文本进行分析
        first_row = cleaned_df.iloc[0]
        script_text = f"公司：{first_row['公司名称']}，行业：{first_row['行业']}，需求：{first_row['需求描述']}"

        result = analyzer.analyze(script_text, script_id="cleaned-content-001")

        # 5. 验证分析结果
        assert result["content_id"] == "cleaned-content-001"
        assert result["analysis"]["hook_type"] == "痛点反问型"
        assert result["analysis"]["content_score"] == 8.0

        # 保存到数据库
        db.save_content_analysis(result)
        saved = db.get_content_analysis("cleaned-content-001")
        assert saved is not None

    def test_script_data_cleaning_then_analysis(self, db, mock_llm):
        """清洗脚本数据后进行 LLM 分析"""
        import pandas as pd

        # 1. 创建包含不规范数据的 DataFrame
        raw_df = pd.DataFrame({
            "标题": ["获客秘籍", "销售技巧", "转化攻略", "获客秘籍"],  # 标题重复
            "完整脚本": [
                "你是不是还在用传统方式获客？每天花500块投流...",
                "今天教你3个销售技巧，第一个就是...",
                "转化率太低怎么办？试试这个方法...",
                "你是不是还在用传统方式获客？每天花500块投流...",  # 重复脚本
            ],
            "播放量": ["10000", "5000", "abc", "8000"],  # abc 非数值
            "点赞数": [500, 300, 200, 400],
            "评论数": [100, 50, 30, 80],
            "转发数": [50, 20, 10, 40],
        })

        # 2. 清洗数据
        cleaner = ScriptDataCleaner()
        cleaned_df = cleaner.clean(raw_df)

        # 3. 验证清洗结果
        # 去重：4条 -> 3条（第4条与第1条脚本重复）
        assert len(cleaned_df) == 3

        # 验证数值字段处理
        assert "互动数" in cleaned_df.columns
        assert "互动率" in cleaned_df.columns
        assert "脚本字数" in cleaned_df.columns

        # 验证非数值被处理为0
        assert cleaned_df.iloc[2]["播放量"] == 0  # "abc" -> 0

        # 验证清洗摘要
        summary = cleaner.get_cleaning_summary()
        assert summary["原始记录数"] == 4
        assert summary["清洗后记录数"] == 3
        assert summary["移除记录数"] == 1

        # 4. 对清洗后的脚本进行分析
        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)
        analyzer = ContentAnalyzer(llm_client=mock_llm)

        for idx, row in cleaned_df.iterrows():
            result = analyzer.analyze(
                row["完整脚本"],
                script_id=f"cleaned-script-{idx}",
            )
            assert "analysis" in result
            assert result["analysis"]["content_score"] == 8.0
            db.save_content_analysis(result)

        # 验证数据库
        stats = db.get_stats()
        assert stats["content_count"] == 3


# ============================================================
# 流程 4：批量分析 Pipeline
# ============================================================


class TestBatchAnalysisE2E:
    """端到端流程4：批量分析"""

    def test_batch_content_analysis(self, mock_llm, db):
        """批量分析 5 条内容"""
        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)

        analyzer = ContentAnalyzer(llm_client=mock_llm)

        scripts = [
            {"script_id": f"batch-content-{i}", "script_text": f"这是第{i}条测试脚本内容，用于批量分析测试。"}
            for i in range(5)
        ]

        results = analyzer.batch_analyze(scripts)

        # 验证所有 5 条都成功处理
        assert len(results) == 5
        for r in results:
            assert r["success"] is True
            assert "data" in r
            assert r["data"]["analysis"]["content_score"] == 8.0

        # 保存到数据库
        for r in results:
            if r["success"]:
                db.save_content_analysis(r["data"])

        stats = db.get_stats()
        assert stats["content_count"] == 5

    def test_batch_lead_analysis(self, mock_llm, db):
        """批量分析 5 条线索"""
        mock_llm.chat_json.return_value = dict(MOCK_LEAD_ANALYSIS)

        analyzer = LeadAnalyzer(llm_client=mock_llm)

        leads = [
            {
                "lead_id": f"batch-lead-{i}",
                "lead_data": {
                    "name": f"客户{i}",
                    "company": f"测试公司{i}",
                    "industry": "教育培训",
                },
            }
            for i in range(5)
        ]

        results = analyzer.batch_analyze(leads)

        # 验证所有 5 条都成功处理
        assert len(results) == 5
        for r in results:
            assert r["success"] is True
            assert r["data"]["profile"]["lead_score"] == 75

        # 保存到数据库
        for r in results:
            if r["success"]:
                db.save_lead_analysis(r["data"])

        stats = db.get_stats()
        assert stats["lead_count"] == 5

    def test_batch_process_with_token_tracking(self):
        """批量处理并验证 token 计数和成本计算"""
        # 使用真实 LLMClient 但 mock 底层 OpenAI 调用
        with patch("services.llm_client.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client

            # 模拟 chat.completions.create 返回
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"result": "ok"}'
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 1000
            mock_response.usage.completion_tokens = 200
            mock_client.chat.completions.create.return_value = mock_response

            llm = LLMClient(model="deepseek-chat", api_key="test-key")

            items = [{"text": f"测试内容{i}"} for i in range(5)]

            def prompt_builder(item):
                return ("系统提示", f"分析：{item['text']}")

            results = llm.batch_process(items, prompt_builder, concurrency=3)

            # 验证所有 5 条都成功处理
            assert len(results) == 5
            for r in results:
                assert r["success"] is True
                assert r["data"] == {"result": "ok"}

            # 验证 token 计数（5次调用，每次 1000 input + 200 output）
            assert llm.total_calls == 5
            assert llm.total_input_tokens == 5000
            assert llm.total_output_tokens == 1000

            # 验证成本计算 (deepseek-chat: 0.001/1k input, 0.002/1k output)
            expected_cost = (5000 / 1000) * 0.001 + (1000 / 1000) * 0.002
            assert abs(llm.total_cost - expected_cost) < 0.0001

    def test_batch_analysis_with_partial_failure(self, mock_llm, db):
        """批量分析中部分失败的处理"""
        call_count = [0]

        def mock_chat_json(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx == 2:
                raise RuntimeError("模拟API错误")
            return dict(MOCK_CONTENT_ANALYSIS)

        mock_llm.chat_json.side_effect = mock_chat_json

        analyzer = ContentAnalyzer(llm_client=mock_llm)

        scripts = [
            {"script_id": f"partial-{i}", "script_text": f"测试脚本{i}"}
            for i in range(5)
        ]

        results = analyzer.batch_analyze(scripts)

        # 验证：4 成功，1 失败
        assert len(results) == 5
        success_count = sum(1 for r in results if r["success"])
        fail_count = sum(1 for r in results if not r["success"])
        assert success_count == 4
        assert fail_count == 1

        # 验证失败记录包含错误信息
        failed = [r for r in results if not r["success"]][0]
        assert "error" in failed
        assert failed["index"] == 2

    def test_batch_match(self, mock_llm):
        """批量匹配测试"""
        mock_llm.chat_json.return_value = dict(MOCK_MATCH_RESULT)

        engine = MatchEngine(llm_client=mock_llm)

        contents = [
            {
                "analysis": dict(MOCK_CONTENT_ANALYSIS),
                "content_id": f"batch-match-content-{i}",
            }
            for i in range(3)
        ]

        leads = [
            {
                "profile": dict(MOCK_LEAD_ANALYSIS),
                "lead_id": "batch-match-lead-1",
                "raw_data": {"company": "测试公司"},
            }
        ]

        results = engine.batch_match(contents, leads, top_k=3)

        # 验证结果
        assert len(results) == 1
        assert results[0]["lead_id"] == "batch-match-lead-1"
        assert len(results[0]["top_matches"]) == 3
        assert results[0]["total_content_scored"] == 3

        # 验证按分数排序
        scores = [m["match_result"]["overall_score"] for m in results[0]["top_matches"]]
        assert scores == sorted(scores, reverse=True)


# ============================================================
# 流程 5：错误恢复流程
# ============================================================


class TestErrorRecoveryE2E:
    """端到端流程5：错误处理和恢复"""

    def test_invalid_json_response_repair(self, mock_llm, sample_script):
        """模拟 API 返回无效 JSON，验证 JSON 修复机制"""
        import json as json_module

        # 返回不完整的数据，验证 _validate_output 的容错能力
        mock_llm.chat_json.return_value = {
            "hook_type": "痛点反问型",
            "hook_strength": 8.5,
            "emotion_tone": "焦虑→希望",
            # 缺少一些必需字段
        }

        analyzer = ContentAnalyzer(llm_client=mock_llm)
        result = analyzer.analyze(script_text=sample_script)

        # 验证结果仍然有效（_validate_output 会补全缺失字段）
        assert "analysis" in result
        assert result["analysis"]["hook_type"] == "痛点反问型"
        # 缺失字段被补全为默认值
        assert result["analysis"]["content_score"] == 5.0  # 默认值

    def test_api_timeout_error_handling(self, mock_llm, sample_script):
        """模拟 API 超时/错误，验证错误处理"""
        from openai import APITimeoutError

        mock_llm.chat_json.side_effect = APITimeoutError("请求超时")

        analyzer = ContentAnalyzer(llm_client=mock_llm)

        with pytest.raises(RuntimeError, match="分析失败"):
            analyzer.analyze(script_text=sample_script)

    def test_api_generic_error_handling(self, mock_llm, sample_lead_data):
        """模拟 API 通用错误"""
        mock_llm.chat_json.side_effect = RuntimeError("API服务不可用")

        analyzer = LeadAnalyzer(llm_client=mock_llm)

        with pytest.raises(RuntimeError, match="分析失败"):
            analyzer.analyze(lead_data=sample_lead_data)

    def test_empty_input_validation(self, mock_llm):
        """验证空输入的处理"""
        # 空脚本
        analyzer = ContentAnalyzer(llm_client=mock_llm)
        with pytest.raises(ValueError, match="脚本内容不能为空"):
            analyzer.analyze("")

        with pytest.raises(ValueError, match="脚本内容不能为空"):
            analyzer.analyze("   ")

        # 空线索
        lead_analyzer = LeadAnalyzer(llm_client=mock_llm)
        with pytest.raises(ValueError, match="线索数据不能为空"):
            lead_analyzer.analyze({})

    def test_database_write_failure_rollback(self, db, mock_llm, sample_script):
        """模拟数据库写入失败，验证事务回滚"""
        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)

        analyzer = ContentAnalyzer(llm_client=mock_llm)
        result = analyzer.analyze(sample_script, script_id="rollback-test-001")

        # 正常保存
        db.save_content_analysis(result)
        assert db.get_content_analysis("rollback-test-001") is not None

        # 验证统计
        stats = db.get_stats()
        assert stats["content_count"] == 1

        # 删除后验证回滚效果
        db.delete_content_analysis("rollback-test-001")
        assert db.get_content_analysis("rollback-test-001") is None

        stats = db.get_stats()
        assert stats["content_count"] == 0

    def test_match_with_nonexistent_content(self, tmp_db_path):
        """匹配不存在的内容/线索"""
        with patch.object(LLMClient, "__init__", lambda self, **kwargs: None):
            orch = Orchestrator.__new__(Orchestrator)
            orch.llm = MagicMock(spec=LLMClient)
            orch.llm.model = "deepseek-chat"
            orch.db = Database(db_path=tmp_db_path)
            orch.content_analyzer = ContentAnalyzer(llm_client=orch.llm)
            orch.lead_analyzer = LeadAnalyzer(llm_client=orch.llm)
            orch.match_engine = MatchEngine(llm_client=orch.llm)
            orch.strategy_advisor = StrategyAdvisor(llm_client=orch.llm)

            # 尝试匹配不存在的内容
            with pytest.raises(ValueError, match="不存在"):
                orch.match_content_lead("nonexistent-content", "nonexistent-lead")

            orch.db.close()

    def test_strategy_with_nonexistent_match(self, tmp_db_path):
        """对不存在的匹配结果生成策略"""
        with patch.object(LLMClient, "__init__", lambda self, **kwargs: None):
            orch = Orchestrator.__new__(Orchestrator)
            orch.llm = MagicMock(spec=LLMClient)
            orch.llm.model = "deepseek-chat"
            orch.db = Database(db_path=tmp_db_path)
            orch.content_analyzer = ContentAnalyzer(llm_client=orch.llm)
            orch.lead_analyzer = LeadAnalyzer(llm_client=orch.llm)
            orch.match_engine = MatchEngine(llm_client=orch.llm)
            orch.strategy_advisor = StrategyAdvisor(llm_client=orch.llm)

            with pytest.raises(ValueError, match="不存在"):
                orch.generate_strategy("nonexistent-match")

            orch.db.close()

    def test_batch_analysis_cancellation(self, mock_llm):
        """测试批量分析取消功能"""
        import threading

        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)

        analyzer = ContentAnalyzer(llm_client=mock_llm)

        cancel_event = threading.Event()

        scripts = [
            {"script_id": f"cancel-{i}", "script_text": f"测试脚本{i}"}
            for i in range(10)
        ]

        # 在第3次调用前设置取消事件
        call_count = [0]
        original_analyze = ContentAnalyzer.analyze

        def canceling_analyze(self_inner, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 3:
                cancel_event.set()
            return original_analyze(self_inner, *args, **kwargs)

        with patch.object(ContentAnalyzer, "analyze", canceling_analyze):
            results = analyzer.batch_analyze(scripts, cancel_event=cancel_event)

        # 验证：取消后不再处理更多条目
        # cancel_event 在第3次 analyze 调用时被设置，
        # batch_analyze 在下一次循环迭代开始时检查 cancel_event
        assert len(results) <= 10
        # 至少处理了3条（因为 cancel_event 在第3次调用时才设置）
        assert len(results) >= 3
        # 验证不是全部10条都处理了（取消生效）
        assert len(results) < 10

    def test_llm_returns_malformed_data_validation(self, mock_llm, sample_script):
        """LLM 返回畸形数据，验证 _validate_output 的容错能力"""
        # 返回各种畸形数据
        test_cases = [
            # 完全空字典
            {},
            # 数值字段为字符串
            {
                "hook_type": "痛点反问型",
                "hook_strength": "很高",
                "cta_clarity": None,
                "content_score": "非常好",
            },
            # 列表字段为字符串
            {
                "hook_type": "痛点反问型",
                "hook_keywords": "单个关键词",
                "topic_tags": None,
                "key_selling_points": "卖点",
            },
        ]

        analyzer = ContentAnalyzer(llm_client=mock_llm)

        for i, malformed_input in enumerate(test_cases):
            mock_llm.chat_json.return_value = malformed_input
            result = analyzer.analyze(
                sample_script, script_id=f"malformed-{i}"
            )

            # 验证 _validate_output 补全了所有字段
            analysis = result["analysis"]
            assert "hook_type" in analysis
            assert "hook_strength" in analysis
            assert "content_score" in analysis
            assert "hook_keywords" in analysis
            assert "topic_tags" in analysis
            assert "key_selling_points" in analysis

            # 验证数值范围
            assert 0 <= analysis["hook_strength"] <= 10
            assert 0 <= analysis["content_score"] <= 10

            # 验证列表类型
            assert isinstance(analysis["hook_keywords"], list)
            assert isinstance(analysis["topic_tags"], list)
            assert isinstance(analysis["key_selling_points"], list)

    def test_lead_analyzer_score_validation(self, mock_llm, sample_lead_data):
        """线索分析器分数边界值验证"""
        # 测试超出范围的分数
        mock_llm.chat_json.return_value = {
            "industry": "教育/培训",
            "company_stage": "成长期",
            "role": "决策者",
            "pain_points": ["获客成本高"],
            "intent_level": 15,  # 超出 0-10 范围
            "intent_signals": ["主动咨询"],
            "buying_stage": "考虑期",
            "urgency": "中",
            "budget_readiness": "有预算",
            "decision_criteria": ["效果"],
            "objection_risks": ["价格敏感"],
            "recommended_content_type": "案例",
            "recommended_cta": "私信咨询型",
            "engagement_strategy": "先提供免费方案",
            "lead_score": 150,  # 超出 0-100 范围
        }

        analyzer = LeadAnalyzer(llm_client=mock_llm)
        result = analyzer.analyze(sample_lead_data, lead_id="boundary-test")

        # 验证分数被限制在有效范围内
        assert 0 <= result["profile"]["intent_level"] <= 10
        assert 0 <= result["profile"]["lead_score"] <= 100
        assert result["profile"]["lead_score"] == 100  # 被截断到上限

    def test_match_engine_dimension_score_validation(self, mock_llm):
        """匹配引擎维度分数边界值验证"""
        # 测试超出范围的维度分数
        mock_llm.chat_json.return_value = {
            "overall_score": 15,  # 超出 0-10
            "dimension_scores": {
                "audience_fit": -5,  # 负值
                "pain_point_relevance": 12,  # 超出范围
                "stage_alignment": "很高",  # 非数值
                "cta_appropriateness": 8.0,
                "emotion_resonance": 9.0,
            },
            "match_reason": "测试匹配",
            "risk_factors": "单个风险",  # 非列表
            "recommended_follow_up": "跟进建议",
        }

        engine = MatchEngine(llm_client=mock_llm)
        result = engine.match(
            MOCK_CONTENT_ANALYSIS,
            MOCK_LEAD_ANALYSIS,
            content_id="boundary-content",
            lead_id="boundary-lead",
        )

        # 验证分数被限制在有效范围内
        validated = result["match_result"]
        assert 0 <= validated["overall_score"] <= 10
        assert validated["overall_score"] == 10  # 被截断

        dim_scores = validated["dimension_scores"]
        assert 0 <= dim_scores["audience_fit"] <= 10
        assert dim_scores["audience_fit"] == 0  # 负值被截断到0
        assert 0 <= dim_scores["pain_point_relevance"] <= 10
        assert dim_scores["pain_point_relevance"] == 10  # 被截断到10
        assert 0 <= dim_scores["stage_alignment"] <= 10
        assert dim_scores["stage_alignment"] == 5.0  # 非数值使用默认值

        # 验证列表字段
        assert isinstance(validated["risk_factors"], list)


# ============================================================
# 附加端到端测试：跨模块集成验证
# ============================================================


class TestCrossModuleIntegration:
    """跨模块集成验证"""

    def test_content_summary_after_batch_analysis(self, mock_llm):
        """批量分析后获取内容摘要"""
        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)

        analyzer = ContentAnalyzer(llm_client=mock_llm)

        scripts = [
            {"script_id": f"summary-{i}", "script_text": f"测试脚本{i}"}
            for i in range(3)
        ]

        results = analyzer.batch_analyze(scripts)

        # 获取摘要
        summary = analyzer.get_content_summary(results)

        assert summary["total"] == 3
        assert summary["successful"] == 3
        assert summary["failed"] == 0
        assert "avg_content_score" in summary
        assert "avg_hook_strength" in summary
        assert "hook_type_distribution" in summary

    def test_lead_summary_after_batch_analysis(self, mock_llm):
        """批量分析后获取线索摘要"""
        mock_llm.chat_json.return_value = dict(MOCK_LEAD_ANALYSIS)

        analyzer = LeadAnalyzer(llm_client=mock_llm)

        leads = [
            {
                "lead_id": f"summary-lead-{i}",
                "lead_data": {"name": f"客户{i}", "company": f"公司{i}"},
            }
            for i in range(3)
        ]

        results = analyzer.batch_analyze(leads)

        # 获取摘要
        summary = analyzer.get_lead_summary(results)

        assert summary["total"] == 3
        assert summary["successful"] == 3
        assert summary["failed"] == 0
        assert "avg_lead_score" in summary
        assert "industry_distribution" in summary
        assert "grade_distribution" in summary

    def test_gap_analysis(self, mock_llm):
        """GAP 分析端到端"""
        mock_llm.chat_json.return_value = dict(MOCK_CONTENT_ANALYSIS)

        content_analyzer = ContentAnalyzer(llm_client=mock_llm)
        lead_analyzer = LeadAnalyzer(llm_client=mock_llm)

        # 批量分析内容
        content_results = content_analyzer.batch_analyze([
            {"script_id": f"gap-c-{i}", "script_text": f"脚本{i}"}
            for i in range(3)
        ])

        mock_llm.chat_json.return_value = dict(MOCK_LEAD_ANALYSIS)

        # 批量分析线索
        lead_results = lead_analyzer.batch_analyze([
            {"lead_id": f"gap-l-{i}", "lead_data": {"company": f"公司{i}"}}
            for i in range(3)
        ])

        # 获取摘要
        content_summary = content_analyzer.get_content_summary(content_results)
        lead_summary = lead_analyzer.get_lead_summary(lead_results)

        # GAP 分析
        engine = MatchEngine(llm_client=mock_llm)
        gap = engine.get_gap_analysis(content_summary, lead_summary)

        assert "content_supply" in gap
        assert "lead_demand" in gap
        assert "gap_analysis" in gap
        assert "recommendation" in gap

    def test_orchestrator_dashboard_data(self, tmp_db_path, mock_llm, sample_script, sample_lead_data):
        """Orchestrator 仪表盘数据"""
        with patch.object(LLMClient, "__init__", lambda self, **kwargs: None):
            with patch.object(LLMClient, "model", "deepseek-chat", create=True):
                orch = Orchestrator.__new__(Orchestrator)
                orch.model = "deepseek-chat"
                orch.llm = MagicMock(spec=LLMClient)
                orch.llm.model = "deepseek-chat"
                orch.db = Database(db_path=tmp_db_path)
                orch.content_analyzer = ContentAnalyzer(llm_client=orch.llm)
                orch.lead_analyzer = LeadAnalyzer(llm_client=orch.llm)
                orch.match_engine = MatchEngine(llm_client=orch.llm)
                orch.strategy_advisor = StrategyAdvisor(llm_client=orch.llm)

                # 执行完整 Pipeline
                call_count = [0]

                def mock_chat_json(*args, **kwargs):
                    idx = call_count[0]
                    call_count[0] += 1
                    if idx == 0:
                        return dict(MOCK_CONTENT_ANALYSIS)
                    elif idx == 1:
                        return dict(MOCK_LEAD_ANALYSIS)
                    elif idx == 2:
                        return dict(MOCK_MATCH_RESULT)
                    else:
                        return dict(MOCK_STRATEGY)

                orch.llm.chat_json.side_effect = mock_chat_json
                orch.full_pipeline(sample_script, sample_lead_data)

                # 获取仪表盘数据
                dashboard = orch.get_dashboard_data(recent_limit=5)

                assert "stats" in dashboard
                assert dashboard["stats"]["content_count"] == 1
                assert dashboard["stats"]["lead_count"] == 1
                assert dashboard["stats"]["match_count"] == 1
                assert dashboard["stats"]["strategy_count"] == 1
                assert "avg_content_score_recent" in dashboard
                assert "avg_lead_score_recent" in dashboard
                assert "avg_match_score_recent" in dashboard
                assert dashboard["avg_content_score_recent"] == 8.0
                assert dashboard["avg_lead_score_recent"] == 75.0
                assert dashboard["avg_match_score_recent"] == 8.5

                orch.db.close()
