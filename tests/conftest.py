"""
共享测试 fixtures
"""

import sys
import os
import tempfile
import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.database import Database

# ============================================================
# 数据库 fixtures
# ============================================================


@pytest.fixture
def tmp_db_dir():
    """创建临时目录并在测试结束后清理"""
    d = tempfile.mkdtemp()
    yield d
    # 清理临时目录下所有文件
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    os.rmdir(d)


@pytest.fixture
def db(tmp_db_dir):
    """创建使用临时数据库的 Database 实例"""
    db_path = os.path.join(tmp_db_dir, "test.db")
    database = Database(db_path=db_path)
    yield database
    database.close()


@pytest.fixture
def sample_content_result():
    """示例内容分析结果"""
    return {
        "content_id": "content-001",
        "raw_text": "你是不是还在用传统方式获客？每天花500块投流，一个询盘都没有？",
        "analysis": {
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
        },
        "model": "deepseek-chat",
        "created_at": "2025-01-01T10:00:00",
    }


@pytest.fixture
def sample_lead_result():
    """示例线索分析结果"""
    return {
        "lead_id": "lead-001",
        "raw_data": {
            "name": "张总",
            "company": "XX教育科技",
            "industry": "教育培训",
        },
        "profile": {
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
            "lead_grade": "B+",
        },
        "model": "deepseek-chat",
        "created_at": "2025-01-01T10:00:00",
    }


@pytest.fixture
def sample_match_result():
    """示例匹配结果"""
    return {
        "match_id": "match-001",
        "match_result": {
            "overall_score": 8.5,
            "dimension_scores": {
                "audience_fit": 9.0,
                "pain_point_relevance": 8.0,
                "stage_alignment": 8.5,
                "cta_appropriateness": 7.5,
                "emotion_resonance": 9.0,
            },
            "match_reason": "内容精准匹配线索痛点",
            "risk_factors": ["价格可能偏高"],
            "recommended_follow_up": "发送免费案例",
        },
        "content_snapshot": {
            "content_id": "content-001",
            "hook_type": "痛点反问型",
            "topic_tags": ["获客", "B2B", "营销"],
            "content_score": 8.0,
        },
        "lead_snapshot": {
            "lead_id": "lead-001",
            "industry": "教育/培训",
            "pain_points": ["获客成本高", "转化率低"],
            "buying_stage": "考虑期",
            "lead_score": 75,
        },
        "model": "deepseek-chat",
        "created_at": "2025-01-01T10:00:00",
    }


@pytest.fixture
def sample_strategy_result():
    """示例策略建议结果"""
    return {
        "strategy_id": "strategy-001",
        "match_id": "match-001",
        "content_id": "content-001",
        "lead_id": "lead-001",
        "strategy": {
            "content_strategy": {
                "recommended_hook": "还在为获客发愁？",
                "hook_rationale": "直接命中痛点",
                "recommended_structure": "PAS",
                "talking_points": ["低成本获客", "精准引流", "快速转化"],
                "tone_guidance": "专业且亲切",
                "keywords_to_include": ["获客", "转化"],
                "keywords_to_avoid": ["免费"],
            },
            "distribution_strategy": {
                "best_timing": "工作日 18:00-20:00",
                "channel_suggestion": "抖音+微信",
                "follow_up_sequence": [
                    "Day 0: 发送案例",
                    "Day 1: 电话跟进",
                    "Day 3: 邀请体验",
                    "Day 7: 方案报价",
                ],
            },
            "conversion_prediction": {
                "estimated_conversion_rate": "15%-20%",
                "confidence_level": "中",
                "key_success_factors": ["痛点匹配", "信任建立"],
                "potential_blockers": ["预算不足"],
            },
            "a_b_test_suggestion": {
                "variant_a": "痛点反问型开头",
                "variant_b": "数据冲击型开头",
                "test_metric": "私信咨询率",
                "recommended_sample_size": "1000",
            },
        },
        "model": "deepseek-chat",
        "created_at": "2025-01-01T10:00:00",
    }


# ============================================================
# 数据清洗 fixtures
# ============================================================


@pytest.fixture
def sample_lead_df():
    """示例线索 DataFrame"""
    import pandas as pd

    return pd.DataFrame(
        {
            "公司名称": [
                "  杭州某某科技有限公司  ",
                "北京某某教育咨询有限公司",
                "上海某某餐饮管理有限公司",
                "杭州某某科技有限公司",  # 重复手机号
            ],
            "行业": ["SaaS软件", "教育培训", "奶茶", "软件"],
            "手机号": ["13800138000", "13900139000", "13700137000", "13800138000"],
            "需求描述": ["需要获客系统", None, "想做加盟", "需要获客系统"],
            "意向级别": ["A", "高", "hot", "B"],
            "来源": ["抖音", None, "微信", "抖音"],
        }
    )


@pytest.fixture
def sample_script_df():
    """示例脚本 DataFrame"""
    import pandas as pd

    return pd.DataFrame(
        {
            "标题": ["获客秘籍", "销售技巧", "转化攻略"],
            "完整脚本": [
                "你是不是还在用传统方式获客？每天花500块投流...",
                "你是不是还在用传统方式获客？每天花500块投流...",  # 重复
                "今天教你3个销售技巧，第一个就是...",
            ],
            "播放量": ["10000", "5000", "abc"],  # 包含非数值
            "点赞数": [500, 300, 200],
            "评论数": [100, 50, 30],
            "转发数": [50, 20, 10],
        }
    )


# ============================================================
# 分析器 fixtures
# ============================================================


@pytest.fixture
def mock_llm_client():
    """创建 mock LLM 客户端"""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.model = "deepseek-chat"
    return mock


@pytest.fixture
def sample_content_analysis_output():
    """ContentAnalyzer._validate_output 的输入示例"""
    return {
        "hook_type": "痛点反问型",
        "hook_strength": 8.5,
        "hook_keywords": ["传统获客", "投流"],
        "emotion_tone": "焦虑→希望",
        "emotion_curve": ["焦虑(0-5s)", "希望(15-30s)"],
        "narrative_structure": "PAS",
        "cta_type": "评论区互动型",
        "cta_clarity": 7.0,
        "topic_tags": ["获客", "B2B"],
        "target_audience": "中小企业老板",
        "content_category": "方法论",
        "estimated_conversion_stage": "认知",
        "key_selling_points": ["低成本获客"],
        "content_score": 8.0,
        "improvement_suggestions": ["增加数据案例"],
    }


@pytest.fixture
def sample_lead_analysis_output():
    """LeadAnalyzer._validate_output 的输入示例"""
    return {
        "industry": "教育/培训",
        "company_stage": "成长期",
        "role": "决策者",
        "pain_points": ["获客成本高"],
        "intent_level": 7,
        "intent_signals": ["主动咨询"],
        "buying_stage": "考虑期",
        "urgency": "中",
        "budget_readiness": "有预算",
        "decision_criteria": ["效果"],
        "objection_risks": ["价格敏感"],
        "recommended_content_type": "案例",
        "recommended_cta": "私信咨询型",
        "engagement_strategy": "先提供免费方案",
        "lead_score": 75,
    }


@pytest.fixture
def sample_match_output():
    """MatchEngine._validate_output 的输入示例"""
    return {
        "overall_score": 8.5,
        "dimension_scores": {
            "audience_fit": 9.0,
            "pain_point_relevance": 8.0,
            "stage_alignment": 8.5,
            "cta_appropriateness": 7.5,
            "emotion_resonance": 9.0,
        },
        "match_reason": "内容精准匹配线索痛点",
        "risk_factors": ["价格可能偏高"],
        "recommended_follow_up": "发送免费案例",
    }


@pytest.fixture
def sample_strategy_output():
    """StrategyAdvisor._validate_output 的输入示例"""
    return {
        "content_strategy": {
            "recommended_hook": "还在为获客发愁？",
            "hook_rationale": "直接命中痛点",
            "recommended_structure": "PAS",
            "talking_points": ["低成本获客", "精准引流"],
            "tone_guidance": "专业且亲切",
            "keywords_to_include": ["获客"],
            "keywords_to_avoid": ["免费"],
        },
        "distribution_strategy": {
            "best_timing": "工作日 18:00-20:00",
            "channel_suggestion": "抖音+微信",
            "follow_up_sequence": ["Day 0: 发送案例"],
        },
        "conversion_prediction": {
            "estimated_conversion_rate": "15%-20%",
            "confidence_level": "中",
            "key_success_factors": ["痛点匹配"],
            "potential_blockers": ["预算不足"],
        },
        "a_b_test_suggestion": {
            "variant_a": "痛点反问型开头",
            "variant_b": "数据冲击型开头",
            "test_metric": "私信咨询率",
            "recommended_sample_size": "1000",
        },
    }
