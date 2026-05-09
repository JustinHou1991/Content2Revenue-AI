"""
A/B测试框架 - 生成和对比多版本策略

支持为同一匹配结果生成多个策略变体，并追踪对比效果。
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.database import Database

logger = logging.getLogger(__name__)


class ABTestEngine:
    """
    A/B测试引擎

    为同一内容-线索匹配生成多个策略变体，支持效果对比分析。
    """

    # 预定义的策略变体模板
    VARIANT_TEMPLATES = {
        "control": {
            "name": "对照组",
            "description": "标准策略建议",
            "prompt_modifier": "",
            "style": "balanced",
        },
        "aggressive": {
            "name": "激进型",
            "description": "更直接、更具侵略性的转化策略",
            "prompt_modifier": "生成一个更直接、更具说服力的策略，强调紧迫感和稀缺性",
            "style": "aggressive",
        },
        "educational": {
            "name": "教育型",
            "description": "侧重价值传递和教育引导",
            "prompt_modifier": "生成一个侧重教育引导的策略，强调知识分享和价值传递",
            "style": "educational",
        },
        "social_proof": {
            "name": "社交证明型",
            "description": "强调案例和口碑",
            "prompt_modifier": "生成一个强调社交证明的策略，多使用客户案例和成功故事",
            "style": "social_proof",
        },
        "question_based": {
            "name": "提问引导型",
            "description": "通过提问引导客户思考",
            "prompt_modifier": "生成一个以提问为主的策略，通过问题引导客户自我发现需求",
            "style": "question_based",
        },
    }

    def __init__(self, db: Optional[Database] = None):
        """
        初始化A/B测试引擎

        Args:
            db: 数据库实例，如果为None则创建新实例
        """
        self.db = db or Database()

    def generate_variants(
        self,
        match_result: Dict[str, Any],
        count: int = 2,
        variant_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        为匹配结果生成多个策略变体

        Args:
            match_result: 匹配结果数据
            count: 生成的变体数量（2-4）
            variant_types: 指定变体类型列表，如 ["control", "aggressive"]

        Returns:
            变体配置列表，每个包含变体ID和配置信息
        """
        count = max(2, min(4, count))  # 限制2-4个变体
        match_id = match_result.get("match_id", "")

        # 确定变体类型
        if variant_types is None:
            # 默认选择对照组 + 前N-1个其他类型
            all_types = list(self.VARIANT_TEMPLATES.keys())
            variant_types = ["control"] + all_types[1:count]
        else:
            variant_types = variant_types[:count]
            if "control" not in variant_types:
                variant_types.insert(0, "control")  # 确保有对照组

        variants = []
        for i, variant_type in enumerate(variant_types[:count]):
            template = self.VARIANT_TEMPLATES.get(
                variant_type, self.VARIANT_TEMPLATES["control"]
            )

            variant_config = {
                "type": variant_type,
                "name": template["name"],
                "description": template["description"],
                "prompt_modifier": template["prompt_modifier"],
                "style": template["style"],
                "is_control": (variant_type == "control"),
                "variant_index": i,
            }

            # 保存到数据库
            variant_id = self.db.save_ab_test_variant(
                match_id=match_id,
                variant_name=chr(65 + i),  # A, B, C, D
                variant_config=variant_config,
                is_control=variant_config["is_control"],
            )

            variant_config["id"] = variant_id
            variant_config["match_id"] = match_id
            variants.append(variant_config)

            logger.info(
                "生成A/B测试变体: match_id=%s, variant=%s, type=%s",
                match_id,
                variant_config["name"],
                variant_type,
            )

        return variants

    def get_variant_prompt_modifier(self, variant_id: str) -> str:
        """
        获取指定变体的Prompt修饰符

        Args:
            variant_id: 变体ID

        Returns:
            Prompt修饰符字符串
        """
        # 从数据库获取变体配置
        # 这里简化处理，实际应该查询数据库
        return ""

    def record_test_results(
        self,
        variant_id: str,
        conversion_rate: float,
        sample_size: int,
        revenue: Optional[float] = None,
        additional_metrics: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        记录A/B测试结果

        Args:
            variant_id: 变体ID
            conversion_rate: 转化率（0-100）
            sample_size: 样本量
            revenue: 产生的收入（可选）
            additional_metrics: 其他指标（可选）

        Returns:
            是否记录成功
        """
        test_results = {
            "conversion_rate": conversion_rate,
            "sample_size": sample_size,
            "recorded_at": datetime.now().isoformat(),
        }

        if revenue is not None:
            test_results["revenue"] = revenue
            test_results["revenue_per_user"] = (
                revenue / sample_size if sample_size > 0 else 0
            )

        if additional_metrics:
            test_results.update(additional_metrics)

        success = self.db.update_ab_test_results(variant_id, test_results)

        if success:
            logger.info(
                "记录A/B测试结果: variant_id=%s, conversion=%.2f%%, sample=%d",
                variant_id,
                conversion_rate,
                sample_size,
            )

        return success

    def compare_results(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        对比同一匹配的所有变体结果

        Args:
            match_id: 匹配结果ID

        Returns:
            对比结果，包含获胜者、提升率等统计信息
        """
        return self.db.get_ab_test_comparison(match_id)

    def get_variant_stats(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个变体的统计信息

        Args:
            variant_id: 变体ID

        Returns:
            变体统计信息
        """
        # 从数据库获取变体详情
        # 这里简化处理
        return None

    def calculate_statistical_significance(
        self,
        variant_a_conversions: int,
        variant_a_visitors: int,
        variant_b_conversions: int,
        variant_b_visitors: int,
    ) -> Dict[str, Any]:
        """
        计算统计显著性（使用Z检验）

        Args:
            variant_a_conversions: 变体A转化数
            variant_a_visitors: 变体A访问数
            variant_b_conversions: 变体B转化数
            variant_b_visitors: 变体B访问数

        Returns:
            统计检验结果
        """
        import math

        # 计算转化率
        rate_a = (
            variant_a_conversions / variant_a_visitors if variant_a_visitors > 0 else 0
        )
        rate_b = (
            variant_b_conversions / variant_b_visitors if variant_b_visitors > 0 else 0
        )

        # 合并转化率
        total_conversions = variant_a_conversions + variant_b_conversions
        total_visitors = variant_a_visitors + variant_b_visitors
        pooled_rate = total_conversions / total_visitors if total_visitors > 0 else 0

        # 计算标准误
        se = (
            math.sqrt(
                pooled_rate
                * (1 - pooled_rate)
                * (1 / variant_a_visitors + 1 / variant_b_visitors)
            )
            if pooled_rate > 0
            else 0
        )

        # 计算Z分数
        z_score = (rate_b - rate_a) / se if se > 0 else 0

        # 计算p值（双尾检验）
        from math import erf

        p_value = 2 * (1 - 0.5 * (1 + erf(abs(z_score) / math.sqrt(2))))

        # 判断显著性
        is_significant = p_value < 0.05

        # 计算置信区间（95%）
        margin_of_error = 1.96 * se
        ci_lower = (rate_b - rate_a) - margin_of_error
        ci_upper = (rate_b - rate_a) + margin_of_error

        return {
            "conversion_rate_a": round(rate_a * 100, 2),
            "conversion_rate_b": round(rate_b * 100, 2),
            "relative_improvement": (
                round((rate_b - rate_a) / rate_a * 100, 2) if rate_a > 0 else 0
            ),
            "z_score": round(z_score, 4),
            "p_value": round(p_value, 4),
            "is_significant": is_significant,
            "confidence_level": "95%",
            "confidence_interval": {
                "lower": round(ci_lower * 100, 2),
                "upper": round(ci_upper * 100, 2),
            },
            "recommendation": (
                "B优于A"
                if is_significant and rate_b > rate_a
                else "A优于B" if is_significant and rate_a > rate_b else "无显著差异"
            ),
        }

    def get_active_tests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取进行中的A/B测试

        Args:
            limit: 最大返回数量

        Returns:
            进行中的测试列表
        """
        # 这里简化处理，实际应该查询数据库
        return []

    def generate_test_report(self, match_id: str) -> Dict[str, Any]:
        """
        生成完整的A/B测试报告

        Args:
            match_id: 匹配结果ID

        Returns:
            完整的测试报告
        """
        comparison = self.compare_results(match_id)

        if not comparison:
            return {
                "status": "incomplete",
                "message": "测试尚未完成或数据不足",
                "match_id": match_id,
            }

        variants = comparison.get("variants", [])

        report = {
            "status": "complete",
            "match_id": match_id,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_variants": len(variants),
                "winner": comparison.get("winner"),
                "improvement": comparison.get("improvement"),
            },
            "variants": variants,
        }

        # 如果有两个变体，计算统计显著性
        if len(variants) == 2:
            control = next((v for v in variants if v.get("is_control")), variants[0])
            treatment = next(
                (v for v in variants if not v.get("is_control")), variants[1]
            )

            # 假设样本量和转化率计算显著性
            # 实际应该使用真实的转化数和访问数
            stats = self.calculate_statistical_significance(
                variant_a_conversions=int(
                    control.get("conversion_rate", 0)
                    * control.get("sample_size", 100)
                    / 100
                ),
                variant_a_visitors=control.get("sample_size", 100),
                variant_b_conversions=int(
                    treatment.get("conversion_rate", 0)
                    * treatment.get("sample_size", 100)
                    / 100
                ),
                variant_b_visitors=treatment.get("sample_size", 100),
            )
            report["statistical_analysis"] = stats

        return report

    def suggest_sample_size(
        self,
        baseline_conversion: float,
        minimum_detectable_effect: float = 0.2,
        confidence_level: float = 0.95,
        power: float = 0.8,
    ) -> int:
        """
        建议A/B测试所需样本量

        使用标准样本量计算公式

        Args:
            baseline_conversion: 基准转化率（0-1）
            minimum_detectable_effect: 最小可检测效应（相对提升，如0.2表示20%）
            confidence_level: 置信水平（默认0.95）
            power: 统计功效（默认0.8）

        Returns:
            每组建议样本量
        """
        import math

        # Z值
        z_alpha = 1.96 if confidence_level == 0.95 else 2.576  # 95%或99%
        z_beta = 0.84 if power == 0.8 else 1.28  # 80%或90%

        # 预期转化率
        p1 = baseline_conversion
        p2 = baseline_conversion * (1 + minimum_detectable_effect)

        # 平均转化率
        p_avg = (p1 + p2) / 2

        # 样本量计算公式
        numerator = (
            z_alpha * math.sqrt(2 * p_avg * (1 - p_avg))
            + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        ) ** 2
        denominator = (p2 - p1) ** 2

        sample_size = int(numerator / denominator) if denominator > 0 else 1000

        return max(100, sample_size)  # 至少100个样本


# ===== 便捷函数 =====


def create_ab_test(
    match_result: Dict[str, Any], variant_count: int = 2, db: Optional[Database] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：为匹配结果创建A/B测试

    Args:
        match_result: 匹配结果
        variant_count: 变体数量
        db: 数据库实例

    Returns:
        变体配置列表
    """
    engine = ABTestEngine(db)
    return engine.generate_variants(match_result, count=variant_count)


def record_variant_result(
    variant_id: str,
    conversion_rate: float,
    sample_size: int,
    db: Optional[Database] = None,
) -> bool:
    """
    便捷函数：记录变体测试结果

    Args:
        variant_id: 变体ID
        conversion_rate: 转化率
        sample_size: 样本量
        db: 数据库实例

    Returns:
        是否记录成功
    """
    engine = ABTestEngine(db)
    return engine.record_test_results(variant_id, conversion_rate, sample_size)


# ===== 使用示例 =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 示例匹配结果
    test_match = {
        "match_id": "test-match-001",
        "match_result": {
            "overall_score": 85,
            "match_level": "高度匹配",
        },
        "content_snapshot": {
            "content_id": "content-001",
            "title": "CRM系统选型指南",
        },
        "lead_snapshot": {
            "lead_id": "lead-001",
            "company_name": "杭州某某科技",
        },
    }

    # 创建A/B测试
    engine = ABTestEngine()
    variants = engine.generate_variants(test_match, count=2)

    print("生成的变体:")
    for v in variants:
        print(f"  {v['name']} ({v['type']}): {v['id']}")

    # 模拟记录结果
    if variants:
        engine.record_test_results(
            variant_id=variants[0]["id"],
            conversion_rate=15.5,
            sample_size=200,
        )
        engine.record_test_results(
            variant_id=variants[1]["id"],
            conversion_rate=18.2,
            sample_size=200,
        )

        # 对比结果
        comparison = engine.compare_results(test_match["match_id"])
        print("\n对比结果:")
        print(json.dumps(comparison, ensure_ascii=False, indent=2))

        # 生成报告
        report = engine.generate_test_report(test_match["match_id"])
        print("\n测试报告:")
        print(json.dumps(report, ensure_ascii=False, indent=2))

        # 样本量建议
        suggested_n = engine.suggest_sample_size(
            baseline_conversion=0.155, minimum_detectable_effect=0.15
        )
        print(f"\n建议每组样本量: {suggested_n}")
