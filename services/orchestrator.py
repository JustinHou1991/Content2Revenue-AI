"""
编排器 - 端到端流程编排
串联 ContentAnalyzer → LeadAnalyzer → MatchEngine → StrategyAdvisor
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        db_path: str = "",
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

    def analyze_content(self, script_text: str, conn=None) -> Dict[str, Any]:
        """
        分析单个脚本（端到端：分析 → 保存）

        Args:
            script_text: 脚本文本
            conn: 可选的外部数据库连接，用于事务控制

        Returns:
            分析结果
        """
        logger.info("开始分析内容 (文本长度=%d)", len(script_text))
        result = self.content_analyzer.analyze(script_text)
        try:
            self.db.save_content_analysis(result, conn=conn)
        except Exception as e:
            logger.error("保存内容分析结果失败: %s", e, exc_info=True)
        logger.info("内容分析完成, content_id=%s", result.get("content_id"))
        return result

    def analyze_lead(self, lead_data: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """
        分析单条线索（端到端：分析 → 保存）

        Args:
            lead_data: 线索数据
            conn: 可选的外部数据库连接，用于事务控制

        Returns:
            分析结果
        """
        logger.info("开始分析线索")
        result = self.lead_analyzer.analyze(lead_data)
        try:
            self.db.save_lead_analysis(result, conn=conn)
        except Exception as e:
            logger.error("保存线索分析结果失败: %s", e, exc_info=True)
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
        try:
            match_result = self.match_engine.match(
                content_data["analysis_json"], lead_data["profile_json"]
            )
        except Exception as e:
            logger.error("匹配执行失败: %s", e, exc_info=True)
            raise RuntimeError(f"匹配失败: {str(e)}") from e

        # 注入 content_id 和 lead_id 到 snapshot 中，供 save_match_result 使用
        match_result.setdefault("content_snapshot", {})["content_id"] = content_id
        match_result.setdefault("lead_snapshot", {})["lead_id"] = lead_id

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

    def batch_generate_strategies(
        self, match_ids: Optional[List[str]] = None, max_workers: int = 4,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """批量生成策略建议（并发优化版）

        Args:
            match_ids: 匹配结果ID列表，为None时自动获取所有匹配结果
            max_workers: 并发线程数，默认4（策略生成较重，不宜过高）
            progress_callback: 进度回调，签名为 callback(completed: int, total: int)

        Returns:
            策略生成结果列表（含成功/失败标记）
        """
        if match_ids is None:
            all_matches = self.db.get_all_match_results(limit=500)
            match_ids = [m["id"] for m in all_matches]

        if not match_ids:
            logger.warning("没有可用的匹配结果，跳过批量策略生成")
            return []

        logger.info("开始批量策略生成: %d 条匹配结果, max_workers=%d", len(match_ids), max_workers)

        total = len(match_ids)
        results = [None] * total
        completed = 0
        lock = threading.Lock()

        def generate_one(index: int, match_id: str):
            retries = 3
            delay = 1
            for attempt in range(retries):
                try:
                    strategy = self.generate_strategy(match_id)
                    return index, {"success": True, "data": strategy, "match_id": match_id}
                except Exception as e:
                    if "频率超限" in str(e) or "rate limit" in str(e).lower() or "429" in str(e):
                        if attempt < retries - 1:
                            logger.warning("策略生成限流 match_id=%s, 等待 %ds 后重试 (%d/%d)",
                                           match_id, delay, attempt + 1, retries)
                            time.sleep(delay)
                            delay *= 2
                            continue
                    logger.error("策略生成失败 match_id=%s: %s", match_id, e)
                    return index, {"success": False, "error": str(e), "match_id": match_id}

        actual_workers = min(max_workers, total)
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            futures = {
                executor.submit(generate_one, i, match_ids[i]): i
                for i in range(total)
            }
            for future in as_completed(futures):
                try:
                    idx, result = future.result(timeout=300)
                except TimeoutError:
                    logger.error("策略生成超时 (item in batch)")
                    idx = futures[future]
                    result = {"success": False, "error": "策略生成超时(5分钟)", "match_id": "unknown"}
                except Exception as exc:
                    logger.error(f"策略生成线程异常: {exc}")
                    idx = futures[future]
                    result = {"success": False, "error": str(exc), "match_id": "unknown"}
                results[idx] = result
                with lock:
                    completed += 1
                    current = completed
                if progress_callback:
                    try:
                        progress_callback(current, total)
                    except Exception:
                        pass

        success_count = sum(1 for r in results if r and r.get("success"))
        logger.info("批量策略生成完成: 成功=%d/%d", success_count, total)
        return results

    def full_pipeline(
        self, script_text: str, lead_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        完整Pipeline：脚本 → 内容分析 + 线索分析 → 匹配 → 策略建议

        使用单一事务保证数据一致性，任一步骤失败则全部回滚。

        Args:
            script_text: 脚本文本
            lead_data: 线索数据

        Returns:
            完整的Pipeline结果
        """
        logger.info("开始完整 Pipeline")

        try:
            with self.db._get_conn() as conn:
                conn.execute("BEGIN IMMEDIATE")

                content_result = self.analyze_content(script_text, conn=conn)
                content_id: str = content_result["content_id"]

                lead_result = self.analyze_lead(lead_data, conn=conn)
                lead_id: str = lead_result["lead_id"]

                match_result = self.match_engine.match(
                    content_result["analysis"],
                    lead_result["profile"],
                    content_id=content_result["content_id"],
                    lead_id=lead_result["lead_id"],
                )

                match_result["content_snapshot"]["content_id"] = content_id
                match_result["lead_snapshot"]["lead_id"] = lead_id

                self.db.save_match_result(match_result, conn=conn)
                match_id: str = match_result["match_id"]

                strategy_result = self.strategy_advisor.advise(
                    match_result,
                    content_feature=content_result["analysis"],
                    lead_profile=lead_result["profile"],
                )
                self.db.save_strategy_advice(strategy_result, conn=conn)

                conn.commit()

        except Exception as e:
            logger.error("Pipeline 执行失败，正在回滚: %s", e)
            raise

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
        success_data = [r.get("data") for r in results if r.get("success") and r.get("data")]
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
        success_data = [r.get("data") for r in results if r.get("success") and r.get("data")]
        try:
            saved_count = self.db.save_lead_analyses_batch(success_data)
        except Exception as e:
            logger.error("批量保存线索分析结果失败: %s", e, exc_info=True)
            saved_count = 0
        logger.info("批量线索分析完成, 成功=%d/%d", saved_count, len(leads))
        return results

    def batch_match(self, top_k: int = 3, progress_callback=None) -> List[Dict[str, Any]]:
        """
        批量匹配：所有内容 × 所有线索

        Args:
            top_k: 每个线索返回的匹配数量
            progress_callback: 进度回调 callback(completed, total)

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
            {"analysis": c.get("analysis_json", {}), "content_id": c.get("id", "")}
            for c in contents
            if c.get("analysis_json")
        ]
        lead_list = [
            {
                "profile": lead.get("profile_json", {}),
                "lead_id": lead.get("id", ""),
                "raw_data": lead.get("raw_data_json", {}),
            }
            for lead in leads
            if lead.get("profile_json")
        ]

        results = self.match_engine.batch_match(
            content_list, lead_list, top_k, progress_callback=progress_callback
        )

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

        try:
            stats = self.db.get_dashboard_stats_optimized()
        except Exception as e:
            logger.error("获取仪表盘统计失败: %s", e, exc_info=True)
            stats = {"content_count": 0, "lead_count": 0, "match_count": 0,
                     "strategy_count": 0, "avg_content_score": 0, "avg_lead_quality": 0}

        try:
            recent_contents, _ = self.db.get_content_analyses_paginated(page=1, page_size=recent_limit)
        except Exception as e:
            logger.error("获取最近内容分析失败: %s", e, exc_info=True)
            recent_contents = []

        try:
            recent_leads, _ = self.db.get_lead_analyses_paginated(page=1, page_size=recent_limit)
        except Exception as e:
            logger.error("获取最近线索分析失败: %s", e, exc_info=True)
            recent_leads = []

        try:
            recent_matches = self.db.get_all_match_results(limit=recent_limit)
        except Exception as e:
            logger.error("获取最近匹配结果失败: %s", e, exc_info=True)
            recent_matches = []

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
