"""
编排器 - 端到端流程编排
串联 ContentAnalyzer → LeadAnalyzer → MatchEngine → StrategyAdvisor
"""

import logging
from typing import Dict, Any, List, Optional

from .llm_client import LLMClient
from .content_analyzer import ContentAnalyzer
from .lead_analyzer import LeadAnalyzer
from .match_engine import MatchEngine
from .strategy_advisor import StrategyAdvisor
from .database import Database

logger = logging.getLogger(__name__)


class Orchestrator:
    """端到端流程编排器"""

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        db_path: str = "data/c2r.db",
    ):
        """
        初始化编排器

        Args:
            model: LLM模型名称
            api_key: API密钥
            db_path: 数据库路径
        """
        self.llm = LLMClient(model=model, api_key=api_key)
        self.db = Database(db_path=db_path)

        # 初始化各模块
        self.content_analyzer = ContentAnalyzer(llm_client=self.llm)
        self.lead_analyzer = LeadAnalyzer(llm_client=self.llm)
        self.match_engine = MatchEngine(llm_client=self.llm)
        self.strategy_advisor = StrategyAdvisor(llm_client=self.llm)

        logger.info("Orchestrator 初始化完成 (model=%s, db_path=%s)", model, db_path)

    def analyze_content(self, script_text: str) -> Dict[str, Any]:
        """
        分析单个脚本（端到端：分析 → 保存）

        Args:
            script_text: 脚本文本

        Returns:
            分析结果
        """
        logger.info("开始分析内容 (文本长度=%d)", len(script_text))
        result = self.content_analyzer.analyze(script_text)
        self.db.save_content_analysis(result)
        logger.info("内容分析完成, content_id=%s", result.get("content_id"))
        return result

    def analyze_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单条线索（端到端：分析 → 保存）

        Args:
            lead_data: 线索数据

        Returns:
            分析结果
        """
        logger.info("开始分析线索")
        result = self.lead_analyzer.analyze(lead_data)
        self.db.save_lead_analysis(result)
        logger.info("线索分析完成, lead_id=%s", result.get("lead_id"))
        return result

    def match_content_lead(self, content_id: str, lead_id: str) -> Dict[str, Any]:
        """
        匹配内容与线索（端到端：查询 → 匹配 → 保存）

        Args:
            content_id: 内容ID
            lead_id: 线索ID

        Returns:
            匹配结果

        Raises:
            ValueError: 内容或线索不存在
        """
        logger.info("开始匹配 content_id=%s, lead_id=%s", content_id, lead_id)

        # 从数据库获取分析结果
        content_data = self.db.get_content_analysis(content_id)
        lead_data = self.db.get_lead_analysis(lead_id)

        if not content_data:
            raise ValueError(f"内容分析 {content_id} 不存在")
        if not lead_data:
            raise ValueError(f"线索分析 {lead_id} 不存在")

        # 执行匹配
        match_result = self.match_engine.match(
            content_data["analysis_json"], lead_data["profile_json"]
        )

        # 注入 content_id 和 lead_id 到 snapshot 中，供 save_match_result 使用
        match_result["content_snapshot"]["content_id"] = content_id
        match_result["lead_snapshot"]["lead_id"] = lead_id

        # 保存结果
        self.db.save_match_result(match_result)
        logger.info(
            "匹配完成, match_id=%s, overall_score=%s",
            match_result.get("match_id"),
            match_result.get("match_result", {}).get("overall_score"),
        )
        return match_result

    def generate_strategy(self, match_id: str) -> Dict[str, Any]:
        """
        生成策略建议（端到端：查询匹配 → 生成策略 → 保存）

        Args:
            match_id: 匹配结果ID

        Returns:
            策略建议

        Raises:
            ValueError: 匹配结果不存在
        """
        logger.info("开始生成策略, match_id=%s", match_id)

        # 直接按ID查询，避免加载全部数据
        match_data = self.db.get_match_result(match_id)

        if not match_data:
            raise ValueError(f"匹配结果 {match_id} 不存在")

        # 生成策略
        strategy = self.strategy_advisor.advise(match_data)
        self.db.save_strategy_advice(strategy)
        logger.info("策略生成完成, strategy_id=%s", strategy.get("strategy_id"))
        return strategy

    def full_pipeline(
        self, script_text: str, lead_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        完整Pipeline：脚本 → 内容分析 + 线索分析 → 匹配 → 策略建议

        Args:
            script_text: 脚本文本
            lead_data: 线索数据

        Returns:
            完整的Pipeline结果
        """
        logger.info("开始完整 Pipeline")

        # Step 1: 分析内容
        content_result = self.analyze_content(script_text)
        content_id: str = content_result["content_id"]

        # Step 2: 分析线索
        lead_result = self.analyze_lead(lead_data)
        lead_id: str = lead_result["lead_id"]

        # Step 3: 匹配
        match_result = self.match_engine.match(
            content_result["analysis"],
            lead_result["profile"],
            content_id=content_result["content_id"],
            lead_id=lead_result["lead_id"],
        )

        # 注入 content_id 和 lead_id 到 snapshot 中
        match_result["content_snapshot"]["content_id"] = content_id
        match_result["lead_snapshot"]["lead_id"] = lead_id

        self.db.save_match_result(match_result)
        match_id: str = match_result["match_id"]

        # Step 4: 生成策略
        strategy_result = self.strategy_advisor.advise(
            match_result,
            content_feature=content_result["analysis"],
            lead_profile=lead_result["profile"],
        )
        self.db.save_strategy_advice(strategy_result)

        logger.info(
            "完整 Pipeline 完成, content_id=%s, lead_id=%s, match_id=%s",
            content_id,
            lead_id,
            match_id,
        )

        return {
            "content": content_result,
            "lead": lead_result,
            "match": match_result,
            "strategy": strategy_result,
        }

    def batch_analyze_contents(
        self, scripts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量分析脚本

        Args:
            scripts: 脚本列表

        Returns:
            分析结果列表
        """
        logger.info("开始批量分析内容, 数量=%d", len(scripts))
        results = self.content_analyzer.batch_analyze(scripts)
        # 批量保存（单事务）
        success_data = [r["data"] for r in results if r.get("success")]
        try:
            saved_count = self.db.save_content_analyses_batch(success_data)
        except Exception as e:
            logger.error("批量保存内容分析结果失败: %s", e, exc_info=True)
            saved_count = 0
        logger.info("批量内容分析完成, 成功=%d/%d", saved_count, len(scripts))
        return results

    def batch_analyze_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量分析线索

        Args:
            leads: 线索列表

        Returns:
            分析结果列表
        """
        logger.info("开始批量分析线索, 数量=%d", len(leads))
        results = self.lead_analyzer.batch_analyze(leads)
        # 批量保存（单事务）
        success_data = [r["data"] for r in results if r.get("success")]
        try:
            saved_count = self.db.save_lead_analyses_batch(success_data)
        except Exception as e:
            logger.error("批量保存线索分析结果失败: %s", e, exc_info=True)
            saved_count = 0
        logger.info("批量线索分析完成, 成功=%d/%d", saved_count, len(leads))
        return results

    def batch_match(self, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        批量匹配：所有内容 × 所有线索

        Args:
            top_k: 每个线索返回的匹配数量

        Returns:
            匹配结果列表
        """
        logger.info("开始批量匹配, top_k=%d", top_k)
        contents = self.db.get_all_content_analyses()
        leads = self.db.get_all_lead_analyses()

        if not contents or not leads:
            logger.warning(
                "批量匹配跳过: 无内容或线索数据 (contents=%d, leads=%d)",
                len(contents),
                len(leads),
            )
            return []

        # 转换格式
        content_list = [
            {"analysis": c["analysis_json"], "content_id": c["id"]} for c in contents
        ]
        lead_list = [
            {
                "profile": lead["profile_json"],
                "lead_id": lead["id"],
                "raw_data": lead.get("raw_data_json", {}),
            }
            for lead in leads
        ]

        results = self.match_engine.batch_match(content_list, lead_list, top_k)

        # 收集匹配结果，注入 content_id 和 lead_id
        match_results_to_save = []
        for r in results:
            lead_id = r.get("lead_id", "unknown")
            for match in r.get("top_matches", []):
                if "error" in match:
                    logger.warning(
                        "跳过失败的匹配: lead_id=%s, error=%s",
                        lead_id,
                        match.get("error"),
                    )
                    continue
                if "match_id" not in match:
                    continue

                # 注入 content_id 和 lead_id 到 snapshot 中
                match.setdefault("content_snapshot", {})["content_id"] = match.get(
                    "content_id", ""
                )
                match.setdefault("lead_snapshot", {})["lead_id"] = lead_id
                match_results_to_save.append(match)

        # 批量保存匹配结果（单事务）
        try:
            saved_count = self.db.save_match_results_batch(match_results_to_save)
        except Exception as e:
            logger.error("批量保存匹配结果失败: %s", e, exc_info=True)
            saved_count = 0

        logger.info("批量匹配完成, 保存=%d 条结果", saved_count)
        return results

    def get_dashboard_data(self, recent_limit: int = 5) -> Dict[str, Any]:
        """
        获取仪表盘数据（优化版）

        Args:
            recent_limit: 获取最近记录的数量

        Returns:
            仪表盘数据字典，包含统计信息、平均分和最近记录
        """
        logger.info("获取仪表盘数据, recent_limit=%d", recent_limit)

        # 使用优化的单连接查询获取统计数据
        stats = self.db.get_dashboard_stats_optimized()

        # 只在需要详细数据时才查询列表（使用分页查询）
        recent_contents, _ = self.db.get_content_analyses_paginated(page=1, page_size=recent_limit)
        recent_leads, _ = self.db.get_lead_analyses_paginated(page=1, page_size=recent_limit)
        recent_matches = self.db.get_all_match_results(limit=recent_limit)

        dashboard = {
            "stats": {
                "content_count": stats["content_count"],
                "lead_count": stats["lead_count"],
                "match_count": stats["match_count"],
                "strategy_count": stats["strategy_count"],
            },
            "avg_content_score_recent": stats["avg_content_score"],
            "avg_lead_score_recent": stats["avg_lead_score"],
            "avg_match_score_recent": stats["avg_match_score"],
            "score_basis_count": recent_limit,
            "recent_contents": recent_contents[:3],
            "recent_leads": recent_leads[:3],
            "recent_matches": recent_matches[:3],
        }

        logger.info(
            "仪表盘数据: 内容均分=%.1f, 线索均分=%.1f, 匹配均分=%.1f",
            dashboard["avg_content_score_recent"],
            dashboard["avg_lead_score_recent"],
            dashboard["avg_match_score_recent"],
        )
        return dashboard

    def close(self) -> None:
        """关闭连接"""
        logger.info("关闭 Orchestrator 连接")
        self.db.close()
