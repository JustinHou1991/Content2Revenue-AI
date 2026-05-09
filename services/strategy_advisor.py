"""
策略建议模块 - 基于匹配结果生成内容策略
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from .llm_client import LLMClient

logger = logging.getLogger(__name__)

# a_b_test_suggestion 必需字段及其默认值
_AB_TEST_REQUIRED_FIELDS: Dict[str, Any] = {
    "variant_a": "待定",
    "variant_b": "待定",
    "test_metric": "转化率",
    "recommended_sample_size": "建议至少100条",
}


class StrategyAdvisor:
    """AI策略顾问"""

    def __init__(self, llm_client: LLMClient) -> None:
        """
        初始化策略顾问

        Args:
            llm_client: LLM客户端实例
        """
        self.llm: LLMClient = llm_client
        self.system_prompt: str = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        """获取系统Prompt"""
        return """你是一位顶级的B2B内容营销策略顾问，拥有丰富的抖音运营和销售转化经验。

基于内容-线索匹配结果，从以下四个维度生成具体可执行的内容策略建议：
1. 内容策略（推荐Hook、叙事结构、话术要点、语气指导）
2. 分发策略（最佳时间、渠道建议、跟进节奏）
3. 转化预测（预估转化率、成功因素、潜在障碍）
4. A/B测试建议（对比方案、测试指标、样本量）

请严格按照要求的JSON格式输出。"""

    def advise(
        self,
        match_result: Dict[str, Any],
        content_feature: Optional[Dict[str, Any]] = None,
        lead_profile: Optional[Dict[str, Any]] = None,
        historical_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成策略建议

        Args:
            match_result: MatchEngine的输出
            content_feature: ContentAnalyzer的输出（可选，补充上下文）
            lead_profile: LeadAnalyzer的输出（可选，补充上下文）
            historical_data: 历史数据（可选）

        Returns:
            策略建议结果

        Raises:
            RuntimeError: LLM调用失败时
        """
        match_id: str = match_result.get("match_id", "")
        logger.info("开始生成策略建议，match_id=%s", match_id)

        user_prompt: str = self._build_advice_prompt(
            match_result, content_feature, lead_profile, historical_data
        )

        try:
            result: Dict[str, Any] = self.llm.chat_json(
                system_prompt=self.system_prompt,
                user_content=user_prompt,
                temperature=0.5,  # 策略建议需要一定创造性
                max_tokens=3000,
            )
        except Exception as e:
            logger.error("策略生成LLM调用失败，match_id=%s，错误=%s", match_id, e)
            raise RuntimeError(f"策略生成失败: {str(e)}") from e

        validated: Dict[str, Any] = self._validate_output(result)

        logger.info("策略建议生成完成，match_id=%s", match_id)

        return {
            "strategy_id": str(uuid.uuid4()),
            "match_id": match_id,
            "content_id": match_result.get("content_snapshot", {}).get(
                "content_id", ""
            ),
            "lead_id": match_result.get("lead_snapshot", {}).get("lead_id", ""),
            "strategy": validated,
            "created_at": datetime.now().isoformat(),
            "model": self.llm.model,
        }

    def _build_advice_prompt(
        self,
        match_result: Dict[str, Any],
        content: Optional[Dict[str, Any]] = None,
        lead: Optional[Dict[str, Any]] = None,
        history: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建策略建议Prompt"""
        match_data: Dict[str, Any] = match_result.get("match_result", {})
        content_snap: Dict[str, Any] = match_result.get("content_snapshot", {})
        lead_snap: Dict[str, Any] = match_result.get("lead_snapshot", {})

        # 补充详细信息
        content_detail: str = ""
        if content:
            content_detail = f"""
【内容详细信息】
- Hook类型: {content.get('hook_type', '未知')}
- 话题标签: {', '.join(content.get('topic_tags', []))}
- 核心卖点: {', '.join(content.get('key_selling_points', []))}
- 改进建议: {', '.join(content.get('improvement_suggestions', []))}"""

        lead_detail: str = ""
        if lead:
            lead_detail = f"""
【线索详细信息】
- 公司阶段: {lead.get('company_stage', '未知')}
- 决策角色: {lead.get('role', '未知')}
- 核心痛点: {', '.join(lead.get('pain_points', []))}
- 紧迫程度: {lead.get('urgency', '未知')}
- 预算准备: {lead.get('budget_readiness', '未知')}
- 决策标准: {', '.join(lead.get('decision_criteria', []))}
- 异议风险: {', '.join(lead.get('objection_risks', []))}
- 互动策略: {lead.get('engagement_strategy', '')}"""

        history_section: str = ""
        if history:
            history_section = f"""
【历史数据参考】
{json.dumps(history, ensure_ascii=False, indent=2)}"""

        return f"""基于以下匹配分析结果，生成具体可执行的内容策略建议：

【匹配分析】
- 综合匹配度: {match_data.get('overall_score', '未知')}/10
- 维度评分:
  · 受众匹配: {match_data.get('dimension_scores', {}).get('audience_fit', '未知')}/10
  · 痛点相关: {match_data.get('dimension_scores', {}).get('pain_point_relevance', '未知')}/10
  · 阶段对齐: {match_data.get('dimension_scores', {}).get('stage_alignment', '未知')}/10
  · CTA适当: {match_data.get('dimension_scores', {}).get('cta_appropriateness', '未知')}/10
  · 情感共鸣: {match_data.get('dimension_scores', {}).get('emotion_resonance', '未知')}/10
- 匹配理由: {match_data.get('match_reason', '')}
- 风险因素: {', '.join(match_data.get('risk_factors', []))}
- 跟进建议: {match_data.get('recommended_follow_up', '')}

【内容快照】
- 行业: {content_snap.get('industry', lead_snap.get('industry', '未知'))}
- 痛点: {', '.join(content_snap.get('pain_points', lead_snap.get('pain_points', [])))}
{content_detail}
{lead_detail}
{history_section}

【输出格式要求】
请严格按照以下JSON格式输出：
{{
  "content_strategy": {{
    "recommended_hook": "具体的Hook文案建议（15字以内）",
    "hook_rationale": "为什么建议这个Hook（1句话）",
    "recommended_structure": "推荐的叙事结构",
    "talking_points": ["核心话术要点1", "核心话术要点2", "核心话术要点3"],
    "tone_guidance": "语气和风格指导",
    "keywords_to_include": ["建议包含的关键词"],
    "keywords_to_avoid": ["建议避免的关键词"]
  }},
  "distribution_strategy": {{
    "best_timing": "最佳发布时间",
    "channel_suggestion": "渠道建议",
    "follow_up_sequence": ["Day 0: 具体动作", "Day 1: 具体动作", "Day 3: 具体动作", "Day 7: 具体动作"]
  }},
  "conversion_prediction": {{
    "estimated_conversion_rate": "预估转化率区间",
    "confidence_level": "置信度（低/中/高）",
    "key_success_factors": ["关键成功因素"],
    "potential_blockers": ["潜在障碍"]
  }},
  "a_b_test_suggestion": {{
    "variant_a": "方案A描述",
    "variant_b": "方案B描述",
    "test_metric": "测试指标",
    "recommended_sample_size": "建议样本量"
  }}
}}"""

    def _validate_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        校验策略建议输出

        Args:
            data: LLM返回的原始数据

        Returns:
            校验后的数据
        """
        # 确保四大模块存在
        sections: List[str] = [
            "content_strategy",
            "distribution_strategy",
            "conversion_prediction",
            "a_b_test_suggestion",
        ]
        for section in sections:
            if section not in data or not isinstance(data[section], dict):
                logger.warning("策略输出缺少模块 '%s'，使用空字典填充", section)
                data[section] = {}

        # 校验 content_strategy
        cs: Dict[str, Any] = data["content_strategy"]
        cs_str_defaults: Dict[str, str] = {
            "recommended_hook": "待定",
            "hook_rationale": "",
            "recommended_structure": "未知",
            "tone_guidance": "",
        }
        for field_name, default_value in cs_str_defaults.items():
            if field_name not in cs or not isinstance(cs[field_name], str):
                cs[field_name] = default_value

        for field_name in [
            "talking_points",
            "keywords_to_include",
            "keywords_to_avoid",
        ]:
            if field_name not in cs or not isinstance(cs[field_name], list):
                cs[field_name] = [str(cs[field_name])] if cs.get(field_name) else []

        # 校验 distribution_strategy
        ds: Dict[str, Any] = data["distribution_strategy"]
        for field_name in ["best_timing", "channel_suggestion"]:
            if field_name not in ds or not isinstance(ds[field_name], str):
                ds[field_name] = "待定"

        if "follow_up_sequence" not in ds or not isinstance(
            ds["follow_up_sequence"], list
        ):
            ds["follow_up_sequence"] = []

        # 校验 conversion_prediction
        cp: Dict[str, Any] = data["conversion_prediction"]
        for field_name in ["estimated_conversion_rate", "confidence_level"]:
            if field_name not in cp or not isinstance(cp[field_name], str):
                cp[field_name] = "未知"

        # 置信度枚举校验
        valid_confidence_levels: List[str] = ["低", "中", "高"]
        if cp["confidence_level"] not in valid_confidence_levels:
            logger.warning(
                "confidence_level 值 '%s' 无效，应为 %s，已重置为 '中'",
                cp["confidence_level"],
                valid_confidence_levels,
            )
            cp["confidence_level"] = "中"

        for field_name in ["key_success_factors", "potential_blockers"]:
            if field_name not in cp or not isinstance(cp[field_name], list):
                cp[field_name] = [str(cp[field_name])] if cp.get(field_name) else []

        # 校验 a_b_test_suggestion（更完善的字段校验）
        ab: Dict[str, Any] = data["a_b_test_suggestion"]

        # 补全缺失字段
        for field_name, default_value in _AB_TEST_REQUIRED_FIELDS.items():
            if field_name not in ab or not ab[field_name]:
                ab[field_name] = default_value

        # 确保 variant_a 和 variant_b 为非空字符串
        for variant_key in ["variant_a", "variant_b"]:
            value = ab[variant_key]
            if not isinstance(value, str) or not value.strip():
                logger.warning("A/B测试字段 '%s' 无效，使用默认值", variant_key)
                ab[variant_key] = _AB_TEST_REQUIRED_FIELDS[variant_key]

        # 确保 test_metric 为非空字符串
        if not isinstance(ab["test_metric"], str) or not ab["test_metric"].strip():
            logger.warning("A/B测试字段 'test_metric' 无效，使用默认值 '转化率'")
            ab["test_metric"] = "转化率"

        # 确保 recommended_sample_size 为非空字符串
        if (
            not isinstance(ab["recommended_sample_size"], str)
            or not ab["recommended_sample_size"].strip()
        ):
            logger.warning("A/B测试字段 'recommended_sample_size' 无效，使用默认值")
            ab["recommended_sample_size"] = _AB_TEST_REQUIRED_FIELDS[
                "recommended_sample_size"
            ]

        return data
