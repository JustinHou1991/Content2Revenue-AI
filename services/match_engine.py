"""
匹配引擎模块 - 内容与线索的语义匹配
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class MatchEngine:
    """内容-线索匹配引擎"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.system_prompt = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        return """你是一位内容营销策略匹配专家，擅长判断特定内容对特定客户的适配度。

评分维度（每项0-10分）：
- audience_fit: 目标受众匹配度（内容面向的人群 vs 线索画像）
- pain_point_relevance: 痛点相关性（内容解决的问题 vs 线索的痛点）
- stage_alignment: 阶段对齐度（内容的转化阶段 vs 线索的购买阶段）
- cta_appropriateness: CTA适当性（CTA类型 vs 线索当前信任程度）
- emotion_resonance: 情感共鸣度（内容情感基调 vs 线索心理状态）

请严格按照要求的JSON格式输出。"""

    def match(
        self,
        content_feature: Dict[str, Any],
        lead_profile: Dict[str, Any],
        content_id: Optional[str] = None,
        lead_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        单对匹配：评估一个内容对一个线索的适配度

        Args:
            content_feature: ContentAnalyzer的输出（analysis部分）
            lead_profile: LeadAnalyzer的输出（profile部分）
            content_id: 内容ID，会写入 content_snapshot 以便数据库保存外键
            lead_id: 线索ID，会写入 lead_snapshot 以便数据库保存外键

        Returns:
            匹配结果
        """
        logger.info("开始匹配分析 content_id=%s, lead_id=%s", content_id, lead_id)
        user_prompt = self._build_match_prompt(content_feature, lead_profile)

        try:
            result = self.llm.chat_json(
                system_prompt=self.system_prompt,
                user_content=user_prompt,
                temperature=0.3,
            )
        except Exception as e:
            logger.error(
                "匹配分析失败 content_id=%s, lead_id=%s, error=%s",
                content_id,
                lead_id,
                e,
                exc_info=True,
            )
            raise RuntimeError(f"匹配分析失败: {str(e)}")

        validated = self._validate_output(result)

        match_result: Dict[str, Any] = {
            "match_id": str(uuid.uuid4()),
            "match_result": validated,
            "content_snapshot": {
                "content_id": content_id,
                "hook_type": content_feature.get("hook_type"),
                "topic_tags": content_feature.get("topic_tags", [])[:3],
                "content_score": content_feature.get("content_score"),
            },
            "lead_snapshot": {
                "lead_id": lead_id,
                "industry": lead_profile.get("industry"),
                "pain_points": lead_profile.get("pain_points", [])[:3],
                "buying_stage": lead_profile.get("buying_stage"),
                "lead_score": lead_profile.get("lead_score"),
            },
            "created_at": datetime.now().isoformat(),
            "model": self.llm.model,
        }

        logger.info(
            "匹配完成 match_id=%s, overall_score=%s",
            match_result["match_id"],
            validated.get("overall_score"),
        )
        return match_result

    def batch_match(
        self,
        contents: List[Dict[str, Any]],
        leads: List[Dict[str, Any]],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        批量匹配：每个线索找到最合适的top_k个内容

        Args:
            contents: ContentAnalyzer输出列表（每个含analysis字段，可选content_id字段）
            leads: LeadAnalyzer输出列表（每个含profile字段，可选lead_id和raw_data字段）
            top_k: 每个线索返回的匹配内容数量

        Returns:
            匹配结果列表
        """
        logger.info(
            "开始批量匹配: %d 条内容 x %d 条线索, top_k=%d",
            len(contents),
            len(leads),
            top_k,
        )

        if not contents:
            logger.warning("内容列表为空，跳过批量匹配")
            return []
        if not leads:
            logger.warning("线索列表为空，跳过批量匹配")
            return []

        results: List[Dict[str, Any]] = []
        for lead in leads:
            lead_profile = lead.get("profile", lead)
            lead_id = lead.get("lead_id")
            matches: List[Dict[str, Any]] = []

            for content in contents:
                content_feature = content.get("analysis", content)
                content_id = content.get("content_id")
                try:
                    result = self.match(
                        content_feature,
                        lead_profile,
                        content_id=content_id,
                        lead_id=lead_id,
                    )
                    matches.append(result)
                except RuntimeError as e:
                    logger.warning(
                        "单对匹配失败 content_id=%s, lead_id=%s, error=%s",
                        content_id,
                        lead_id,
                        e,
                    )
                    matches.append(
                        {
                            "error": str(e),
                            "content_id": content_id,
                            "lead_id": lead_id,
                        }
                    )
                except Exception as e:
                    logger.error(
                        "单对匹配发生未预期异常 content_id=%s, lead_id=%s, error=%s",
                        content_id,
                        lead_id,
                        e,
                        exc_info=True,
                    )
                    matches.append(
                        {
                            "error": f"未预期错误: {str(e)}",
                            "content_id": content_id,
                            "lead_id": lead_id,
                        }
                    )

            # 按分数排序
            matches.sort(
                key=lambda x: x.get("match_result", {}).get("overall_score", 0),
                reverse=True,
            )

            lead_result: Dict[str, Any] = {
                "lead_id": lead_id or "unknown",
                "lead_snapshot": {
                    "industry": lead_profile.get("industry"),
                    "company": lead.get("raw_data", {}).get("company", ""),
                },
                "top_matches": matches[:top_k],
                "total_content_scored": len(contents),
            }
            results.append(lead_result)

        logger.info("批量匹配完成: 共 %d 条线索的匹配结果", len(results))
        return results

    def _build_match_prompt(self, content: Dict[str, Any], lead: Dict[str, Any]) -> str:
        """构建匹配Prompt"""
        return f"""请评估以下内容与线索的匹配程度：

【内容特征】
- Hook类型: {content.get('hook_type', '未知')}
- 情感基调: {content.get('emotion_tone', '未知')}
- 叙事结构: {content.get('narrative_structure', '未知')}
- CTA类型: {content.get('cta_type', '未知')}
- 目标受众: {content.get('target_audience', '未知')}
- 内容类型: {content.get('content_category', '未知')}
- 转化阶段: {content.get('estimated_conversion_stage', '未知')}
- 话题标签: {', '.join(content.get('topic_tags', []))}
- 核心卖点: {', '.join(content.get('key_selling_points', []))}

【线索画像】
- 行业: {lead.get('industry', '未知')}
- 公司阶段: {lead.get('company_stage', '未知')}
- 决策角色: {lead.get('role', '未知')}
- 核心痛点: {', '.join(lead.get('pain_points', []))}
- 购买阶段: {lead.get('buying_stage', '未知')}
- 紧迫程度: {lead.get('urgency', '未知')}
- 意向度: {lead.get('intent_level', '未知')}/10
- 推荐内容类型: {lead.get('recommended_content_type', '未知')}
- 推荐CTA: {lead.get('recommended_cta', '未知')}

【输出格式要求】
请严格按照以下JSON格式输出：
{{
  "overall_score": "0-10的综合匹配分数",
  "dimension_scores": {{
    "audience_fit": "目标受众匹配度 0-10",
    "pain_point_relevance": "痛点相关性 0-10",
    "stage_alignment": "阶段对齐度 0-10",
    "cta_appropriateness": "CTA适当性 0-10",
    "emotion_resonance": "情感共鸣度 0-10"
  }},
  "match_reason": "2-3句话说明匹配/不匹配的核心原因",
  "risk_factors": ["可能影响转化效果的风险因素"],
  "recommended_follow_up": "1句话的跟进建议"
}}"""

    def _validate_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """校验匹配结果"""
        # 补全缺失字段
        if "overall_score" not in data:
            data["overall_score"] = 5.0
        if "dimension_scores" not in data:
            data["dimension_scores"] = {}
        if "match_reason" not in data:
            data["match_reason"] = ""
        if "risk_factors" not in data:
            data["risk_factors"] = []
        if "recommended_follow_up" not in data:
            data["recommended_follow_up"] = ""

        # 确保总分在0-10
        try:
            data["overall_score"] = max(0, min(10, float(data["overall_score"])))
        except (ValueError, TypeError):
            data["overall_score"] = 5.0

        # 确保各维度分数在0-10
        for key in [
            "audience_fit",
            "pain_point_relevance",
            "stage_alignment",
            "cta_appropriateness",
            "emotion_resonance",
        ]:
            if key not in data["dimension_scores"]:
                data["dimension_scores"][key] = 5.0
            else:
                try:
                    data["dimension_scores"][key] = max(
                        0, min(10, float(data["dimension_scores"][key]))
                    )
                except (ValueError, TypeError):
                    data["dimension_scores"][key] = 5.0

        # 确保列表字段
        if not isinstance(data["risk_factors"], list):
            data["risk_factors"] = (
                [str(data["risk_factors"])] if data["risk_factors"] else []
            )

        return data

    def get_gap_analysis(
        self, content_summaries: Dict[str, Any], lead_summaries: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        GAP分析：对比内容侧和线索侧的分布特征，找到差距

        Args:
            content_summaries: ContentAnalyzer.get_content_summary()的输出，
                               包含 hook_type_distribution 和 cta_type_distribution
            lead_summaries: LeadAnalyzer.get_lead_summary()的输出，
                            包含 industry_distribution 和 buying_stage_distribution

        Returns:
            GAP分析结果
        """
        logger.info("开始GAP分析")

        # 提取内容侧的Hook类型分布（原代码错误引用了不存在的 topic_distribution）
        content_hook_distribution = content_summaries.get("hook_type_distribution", {})
        # 提取内容侧的CTA类型分布
        content_cta_distribution = content_summaries.get("cta_type_distribution", {})
        # 提取线索侧的行业分布
        lead_industries = lead_summaries.get("industry_distribution", {})
        # 提取线索侧的购买阶段分布
        lead_stages = lead_summaries.get("buying_stage_distribution", {})

        # 计算内容覆盖的Hook类型数量
        total_hook_types = sum(content_hook_distribution.values())
        # 计算内容覆盖的CTA类型数量
        total_cta_types = sum(content_cta_distribution.values())

        # 找出线索需求中行业分布最多的前3个
        top_demand_industries = sorted(
            lead_industries.items(), key=lambda x: x[1], reverse=True
        )[:3]

        gap_result: Dict[str, Any] = {
            "content_supply": {
                "hook_type_distribution": content_hook_distribution,
                "cta_type_distribution": content_cta_distribution,
                "total_hook_types": total_hook_types,
                "total_cta_types": total_cta_types,
            },
            "lead_demand": {
                "industry_distribution": lead_industries,
                "buying_stage_distribution": lead_stages,
                "total_leads": lead_summaries.get("total", 0),
                "top_demand_industries": [
                    {"industry": ind, "count": cnt}
                    for ind, cnt in top_demand_industries
                ],
            },
            "gap_analysis": {
                "description": "对比内容供给与线索需求之间的差距",
                "content_hook_types": list(content_hook_distribution.keys()),
                "content_cta_types": list(content_cta_distribution.keys()),
                "lead_demand_industries": list(lead_industries.keys()),
                "lead_demand_stages": list(lead_stages.keys()),
            },
            "recommendation": "建议优先增加需求量大但内容供给不足的行业方向的内容",
        }

        logger.info(
            "GAP分析完成: 内容Hook类型数=%d, 线索行业数=%d",
            len(content_hook_distribution),
            len(lead_industries),
        )
        return gap_result
