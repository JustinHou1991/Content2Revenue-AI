"""
匹配引擎模块 - 内容与线索的语义匹配
"""

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base_analyzer import BaseAnalyzer
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class MatchEngine(BaseAnalyzer):
    """内容-线索匹配引擎"""

    def __init__(self, llm_client: LLMClient) -> None:
        """初始化匹配引擎

        Args:
            llm_client: LLM客户端实例
        """
        super().__init__(llm_client)

    def _get_system_prompt(self) -> str:
        """获取系统Prompt"""
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
        """单对匹配：评估一个内容对一个线索的适配度

        Args:
            content_feature: ContentAnalyzer的输出（analysis部分）
            lead_profile: LeadAnalyzer的输出（profile部分）
            content_id: 内容ID，会写入 content_snapshot 以便数据库保存外键
            lead_id: 线索ID，会写入 lead_snapshot 以便数据库保存外键

        Returns:
            匹配结果
        """
        # 使用基类的analyze方法，但传入包含所有匹配信息的字典
        input_data = {
            "content_feature": content_feature,
            "lead_profile": lead_profile,
            "content_id": content_id,
            "lead_id": lead_id,
        }
        return super().analyze(input_data)

    def _validate_input(self, input_data: Any) -> None:
        """验证输入数据

        Args:
            input_data: 输入数据字典

        Raises:
            ValueError: 输入数据无效时
        """
        if not isinstance(input_data, dict):
            raise ValueError("输入数据必须是字典类型")
        content_feature = input_data.get("content_feature")
        lead_profile = input_data.get("lead_profile")
        if not content_feature:
            raise ValueError("内容特征不能为空")
        if not lead_profile:
            raise ValueError("线索画像不能为空")

    def _build_prompt_from_input(self, input_data: Any) -> str:
        """根据输入数据构建提示词

        Args:
            input_data: 包含content_feature和lead_profile的字典

        Returns:
            用户提示词字符串
        """
        content_feature = input_data.get("content_feature", {})
        lead_profile = input_data.get("lead_profile", {})
        return self._build_prompt(content_feature, lead_profile)

    def _build_prompt(
        self, content: Dict[str, Any], lead: Dict[str, Any]
    ) -> str:
        """构建匹配Prompt

        Args:
            content: 内容特征字典
            lead: 线索画像字典

        Returns:
            用户提示词字符串
        """
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

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析LLM响应

        Args:
            response: LLM返回的原始JSON数据

        Returns:
            解析后的结构化数据
        """
        # 直接返回响应，验证逻辑在_validate_output中处理
        return response

    def _validate_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """校验匹配结果

        Args:
            output: LLM返回的原始数据

        Returns:
            校验后的数据
        """
        output = super()._validate_output(output)

        # 补全缺失字段
        if "overall_score" not in output:
            output["overall_score"] = 5.0
        if "dimension_scores" not in output:
            output["dimension_scores"] = {}
        if "match_reason" not in output:
            output["match_reason"] = ""
        if "risk_factors" not in output:
            output["risk_factors"] = []
        if "recommended_follow_up" not in output:
            output["recommended_follow_up"] = ""

        # 确保总分在0-10
        self._ensure_numeric_range(output, "overall_score", 0.0, 10.0, 5.0)

        # 确保各维度分数在0-10
        dimension_keys = [
            "audience_fit",
            "pain_point_relevance",
            "stage_alignment",
            "cta_appropriateness",
            "emotion_resonance",
        ]
        for key in dimension_keys:
            if key not in output["dimension_scores"]:
                output["dimension_scores"][key] = 5.0
            else:
                try:
                    output["dimension_scores"][key] = max(
                        0, min(10, float(output["dimension_scores"][key]))
                    )
                except (ValueError, TypeError):
                    output["dimension_scores"][key] = 5.0

        # 确保列表字段
        self._ensure_list_field(output, "risk_factors")

        return output

    def _build_result(
        self, validated_output: Dict[str, Any], input_data: Any
    ) -> Dict[str, Any]:
        """构建最终结果

        Args:
            validated_output: 验证后的输出数据
            input_data: 原始输入数据

        Returns:
            最终结果字典
        """
        content_feature = input_data.get("content_feature", {})
        lead_profile = input_data.get("lead_profile", {})
        content_id = input_data.get("content_id")
        lead_id = input_data.get("lead_id")

        match_result: Dict[str, Any] = {
            "match_id": str(uuid.uuid4()),
            "match_result": validated_output,
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
            validated_output.get("overall_score"),
        )
        return match_result

    def batch_match(
        self,
        contents: List[Dict[str, Any]],
        leads: List[Dict[str, Any]],
        top_k: int = 3,
        max_workers: int = 3,
    ) -> List[Dict[str, Any]]:
        """批量匹配：每个线索找到最合适的top_k个内容（并发优化版）

        Args:
            contents: ContentAnalyzer输出列表（每个含analysis字段，可选content_id字段）
            leads: LeadAnalyzer输出列表（每个含profile字段，可选lead_id和raw_data字段）
            top_k: 每个线索返回的匹配内容数量
            max_workers: 并发线程数，默认3，避免LLM API限流

        Returns:
            匹配结果列表（顺序与输入leads顺序一致）
        """
        logger.info(
            "开始批量匹配: %d 条内容 x %d 条线索, top_k=%d, max_workers=%d",
            len(contents),
            len(leads),
            top_k,
            max_workers,
        )

        if not contents:
            logger.warning("内容列表为空，跳过批量匹配")
            return []
        if not leads:
            logger.warning("线索列表为空，跳过批量匹配")
            return []

        # ---- 构建所有待匹配任务（带原始索引，保证结果顺序） ----
        tasks: List[tuple] = []
        for lead_idx, lead in enumerate(leads):
            lead_profile = lead.get("profile", lead)
            lead_id = lead.get("lead_id")
            for content_idx, content in enumerate(contents):
                content_feature = content.get("analysis", content)
                content_id = content.get("content_id")
                tasks.append((lead_idx, content_idx, content_feature, lead_profile, content_id, lead_id))

        total_tasks = len(tasks)
        logger.info("共生成 %d 个匹配任务，开始并发执行", total_tasks)

        # ---- 并发执行所有匹配任务 ----
        # 使用字典按 lead_idx 分组存储匹配结果，保证线程安全
        matches_by_lead: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(len(leads))}
        lock = threading.Lock()
        completed_count = 0
        error_count = 0
        count_lock = threading.Lock()

        def _do_match(
            lead_idx: int,
            content_idx: int,
            content_feature: Dict[str, Any],
            lead_profile: Dict[str, Any],
            content_id: Optional[str],
            lead_id: Optional[str],
        ) -> None:
            """执行单个匹配任务，结果写入共享字典"""
            nonlocal completed_count, error_count
            try:
                result = self.match(
                    content_feature,
                    lead_profile,
                    content_id=content_id,
                    lead_id=lead_id,
                )
                with lock:
                    matches_by_lead[lead_idx].append(result)
            except RuntimeError as e:
                with count_lock:
                    error_count += 1
                logger.warning(
                    "单对匹配失败 content_id=%s, lead_id=%s, error=%s",
                    content_id,
                    lead_id,
                    e,
                )
                with lock:
                    matches_by_lead[lead_idx].append(
                        {
                            "error": str(e),
                            "content_id": content_id,
                            "lead_id": lead_id,
                        }
                    )
            except Exception as e:
                with count_lock:
                    error_count += 1
                logger.error(
                    "单对匹配发生未预期异常 content_id=%s, lead_id=%s, error=%s",
                    content_id,
                    lead_id,
                    e,
                    exc_info=True,
                )
                with lock:
                    matches_by_lead[lead_idx].append(
                        {
                            "error": f"未预期错误: {str(e)}",
                            "content_id": content_id,
                            "lead_id": lead_id,
                        }
                    )
            finally:
                with count_lock:
                    completed_count += 1
                if completed_count % 10 == 0 or completed_count == total_tasks:
                    logger.info(
                        "匹配进度: %d/%d (成功: %d, 失败: %d)",
                        completed_count,
                        total_tasks,
                        completed_count - error_count,
                        error_count,
                    )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _do_match, lead_idx, content_idx, content_feature,
                    lead_profile, content_id, lead_id,
                )
                for lead_idx, content_idx, content_feature, lead_profile, content_id, lead_id in tasks
            ]
            # 等待所有任务完成，捕获可能的取消异常
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error("线程池任务执行异常: %s", e, exc_info=True)

        logger.info(
            "所有匹配任务完成: 总计 %d, 成功 %d, 失败 %d",
            total_tasks,
            completed_count - error_count,
            error_count,
        )

        # ---- 按线索聚合结果，保持与输入leads一致的顺序 ----
        results: List[Dict[str, Any]] = []
        for lead_idx, lead in enumerate(leads):
            lead_profile = lead.get("profile", lead)
            lead_id = lead.get("lead_id")
            matches = matches_by_lead[lead_idx]

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

    def get_gap_analysis(
        self, content_summaries: Dict[str, Any], lead_summaries: Dict[str, Any]
    ) -> Dict[str, Any]:
        """GAP分析：对比内容侧和线索侧的分布特征，找到差距

        Args:
            content_summaries: ContentAnalyzer.get_content_summary()的输出，
                               包含 hook_type_distribution 和 cta_type_distribution
            lead_summaries: LeadAnalyzer.get_lead_summary()的输出，
                            包含 industry_distribution 和 buying_stage_distribution

        Returns:
            GAP分析结果
        """
        logger.info("开始GAP分析")

        # 提取内容侧的Hook类型分布
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
