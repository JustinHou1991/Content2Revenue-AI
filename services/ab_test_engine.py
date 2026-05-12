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
            Prompt修饰符字符串，如果变体不存在则返回空字符串
        """
        try:
            # 从数据库查询变体配置
            variants = self.db.get_ab_test_variants_by_id(variant_id)
            if variants:
                config = variants.get("variant_config_json", {})
                # variant_config_json 可能是已解析的字典或JSON字符串
                if isinstance(config, str):
                    config = json.loads(config)
                return config.get("prompt_modifier", "")
        except Exception as e:
            logger.warning("获取变体Prompt修饰符失败: variant_id=%s, error=%s", variant_id, e)

        # 回退：尝试从预定义模板中查找
        # 通过遍历所有match下的变体来定位（兼容无直接查询方法的场景）
        try:
            all_tests = self._query_variant_by_id(variant_id)
            if all_tests:
                config = all_tests.get("variant_config_json", {})
                if isinstance(config, str):
                    config = json.loads(config)
                modifier = config.get("prompt_modifier", "")
                if modifier:
                    return modifier
        except Exception:
            pass

        return ""

    def _query_variant_by_id(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        内部方法：通过variant_id直接查询数据库获取变体记录

        Args:
            variant_id: 变体ID

        Returns:
            变体记录字典，未找到则返回None
        """
        import sqlite3

        try:
            with self.db._get_conn() as conn:
                row = conn.execute(
                    "SELECT * FROM ab_tests WHERE id = ?", (variant_id,)
                ).fetchone()
                if row:
                    return self.db._row_to_dict(row)
        except Exception as e:
            logger.warning("查询变体记录失败: variant_id=%s, error=%s", variant_id, e)
        return None

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
            变体统计信息字典，包含转化率、样本量、收入等指标；
            如果变体不存在则返回None
        """
        # 通过内部方法从数据库获取变体记录
        variant_record = self._query_variant_by_id(variant_id)
        if not variant_record:
            logger.warning("未找到变体记录: variant_id=%s", variant_id)
            return None

        # 解析变体配置
        config = variant_record.get("variant_config_json", {})
        if isinstance(config, str):
            config = json.loads(config)

        # 解析测试结果
        results = variant_record.get("test_results_json", {})
        if isinstance(results, str):
            results = json.loads(results) if results else {}

        # 构建统计信息
        stats = {
            "variant_id": variant_record["id"],
            "match_id": variant_record.get("match_id", ""),
            "variant_name": variant_record.get("variant_name", ""),
            "variant_type": config.get("type", "unknown"),
            "is_control": bool(variant_record.get("is_control", 0)),
            "status": "completed" if variant_record.get("completed_at") else "running",
            "created_at": variant_record.get("created_at", ""),
            "completed_at": variant_record.get("completed_at"),
            # 测试指标
            "conversion_rate": results.get("conversion_rate", 0),
            "sample_size": results.get("sample_size", 0),
            "recorded_at": results.get("recorded_at", ""),
        }

        # 如果有收入数据，一并返回
        if "revenue" in results:
            stats["revenue"] = results["revenue"]
            stats["revenue_per_user"] = results.get("revenue_per_user", 0)

        # 合并其他附加指标
        additional_keys = {
            "revenue", "revenue_per_user", "conversion_rate",
            "sample_size", "recorded_at",
        }
        for key, value in results.items():
            if key not in additional_keys:
                stats[key] = value

        return stats

    def calculate_statistical_significance(
        self,
        variant_a_conversions: int,
        variant_a_visitors: int,
        variant_b_conversions: int,
        variant_b_visitors: int,
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        """
        计算统计显著性（使用双比例Z检验）

        采用合并标准误（pooled standard error）方法进行双尾Z检验，
        适用于两个独立比例的假设检验。

        原假设 H0: p_A = p_B（两变体转化率无差异）
        备择假设 H1: p_A != p_B（两变体转化率有差异）

        Args:
            variant_a_conversions: 变体A（通常为对照组）转化数
            variant_a_visitors: 变体A访问数
            variant_b_conversions: 变体B（通常为实验组）转化数
            variant_b_visitors: 变体B访问数
            confidence_level: 置信水平（默认0.95）

        Returns:
            统计检验结果字典，包含转化率、Z分数、p值、置信区间、效应量等
        """
        import math
        from math import erf, sqrt

        # --- 输入校验 ---
        if variant_a_visitors <= 0 or variant_b_visitors <= 0:
            return {
                "conversion_rate_a": 0,
                "conversion_rate_b": 0,
                "relative_improvement": 0,
                "z_score": 0,
                "p_value": 1.0,
                "is_significant": False,
                "confidence_level": f"{confidence_level * 100:.0f}%",
                "confidence_interval": {"lower": 0, "upper": 0},
                "effect_size": 0,
                "test_valid": False,
                "warning": "访问数必须大于0",
                "recommendation": "数据不足，无法判断",
            }

        if (
            variant_a_conversions < 0
            or variant_b_conversions < 0
            or variant_a_conversions > variant_a_visitors
            or variant_b_conversions > variant_b_visitors
        ):
            return {
                "conversion_rate_a": 0,
                "conversion_rate_b": 0,
                "relative_improvement": 0,
                "z_score": 0,
                "p_value": 1.0,
                "is_significant": False,
                "confidence_level": f"{confidence_level * 100:.0f}%",
                "confidence_interval": {"lower": 0, "upper": 0},
                "effect_size": 0,
                "test_valid": False,
                "warning": "转化数不能为负数或超过访问数",
                "recommendation": "数据异常，无法判断",
            }

        # --- 计算转化率 ---
        rate_a = variant_a_conversions / variant_a_visitors
        rate_b = variant_b_conversions / variant_b_visitors

        # --- 特殊情况：两转化率完全相同 ---
        if rate_a == rate_b:
            return {
                "conversion_rate_a": round(rate_a * 100, 2),
                "conversion_rate_b": round(rate_b * 100, 2),
                "relative_improvement": 0,
                "z_score": 0,
                "p_value": 1.0,
                "is_significant": False,
                "confidence_level": f"{confidence_level * 100:.0f}%",
                "confidence_interval": {"lower": 0, "upper": 0},
                "effect_size": 0,
                "test_valid": True,
                "recommendation": "两变体表现完全相同",
            }

        # --- 合并转化率（pooled proportion） ---
        total_conversions = variant_a_conversions + variant_b_conversions
        total_visitors = variant_a_visitors + variant_b_visitors
        pooled_rate = total_conversions / total_visitors

        # --- 计算合并标准误 ---
        # 公式: SE = sqrt(p_pool * (1-p_pool) * (1/n_A + 1/n_B))
        if 0 < pooled_rate < 1:
            se = sqrt(
                pooled_rate
                * (1 - pooled_rate)
                * (1 / variant_a_visitors + 1 / variant_b_visitors)
            )
        else:
            # 极端情况：合并转化率为0或1时，使用独立标准误
            se_a = sqrt(rate_a * (1 - rate_a) / variant_a_visitors) if 0 < rate_a < 1 else 0
            se_b = sqrt(rate_b * (1 - rate_b) / variant_b_visitors) if 0 < rate_b < 1 else 0
            se = sqrt(se_a ** 2 + se_b ** 2)

        # --- 计算Z分数 ---
        z_score = (rate_b - rate_a) / se if se > 0 else 0

        # --- 计算p值（双尾检验） ---
        # 使用误差函数(erf)计算标准正态分布的累积概率
        # P(Z > |z|) = 1 - Phi(|z|)，其中 Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))
        if se > 0:
            # 双尾p值 = 2 * P(Z > |z_score|)
            p_value = 2 * (1 - 0.5 * (1 + erf(abs(z_score) / sqrt(2))))
        else:
            p_value = 1.0

        # 确保p值在合理范围内
        p_value = max(0.0, min(1.0, p_value))

        # --- 判断显著性 ---
        alpha = 1 - confidence_level
        is_significant = p_value < alpha

        # --- 计算置信区间（基于差异的标准误） ---
        # 使用对应的Z临界值
        z_critical = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }.get(confidence_level, 1.96)

        margin_of_error = z_critical * se
        ci_lower = (rate_b - rate_a) - margin_of_error
        ci_upper = (rate_b - rate_a) + margin_of_error

        # --- 计算效应量（Cohen's h） ---
        # Cohen's h = 2 * arcsin(sqrt(p1)) - 2 * arcsin(sqrt(p2))
        # 用于衡量两个比例之间的差异大小
        def _arcsin_transform(p: float) -> float:
            """反正弦变换（Freeman-Tukey变换）"""
            p_clamped = max(0, min(1, p))  # 防止数值越界
            return 2 * math.asin(sqrt(p_clamped))

        cohens_h = abs(_arcsin_transform(rate_a) - _arcsin_transform(rate_b))

        # 效应量大小判断（Cohen's h 的经验标准）
        if cohens_h < 0.2:
            effect_label = "极小"
        elif cohens_h < 0.5:
            effect_label = "小"
        elif cohens_h < 0.8:
            effect_label = "中等"
        else:
            effect_label = "大"

        # --- 生成建议 ---
        if is_significant and rate_b > rate_a:
            recommendation = "B优于A（统计显著）"
        elif is_significant and rate_a > rate_b:
            recommendation = "A优于B（统计显著）"
        else:
            recommendation = "无显著差异"

        return {
            "conversion_rate_a": round(rate_a * 100, 2),
            "conversion_rate_b": round(rate_b * 100, 2),
            "absolute_difference": round((rate_b - rate_a) * 100, 2),
            "relative_improvement": (
                round((rate_b - rate_a) / rate_a * 100, 2) if rate_a > 0 else 0
            ),
            "z_score": round(z_score, 4),
            "p_value": round(p_value, 6),
            "is_significant": is_significant,
            "alpha": round(alpha, 4),
            "confidence_level": f"{confidence_level * 100:.0f}%",
            "confidence_interval": {
                "lower": round(ci_lower * 100, 2),
                "upper": round(ci_upper * 100, 2),
            },
            "effect_size": round(cohens_h, 4),
            "effect_label": effect_label,
            "pooled_rate": round(pooled_rate * 100, 2),
            "standard_error": round(se, 6),
            "test_valid": True,
            "recommendation": recommendation,
        }

    def get_active_tests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取进行中的A/B测试

        查询数据库中 completed_at 为空的记录，即尚未记录结果的活跃测试。

        Args:
            limit: 最大返回数量

        Returns:
            进行中的测试列表，每项包含变体基本信息和配置
        """
        try:
            with self.db._get_conn() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM ab_tests
                    WHERE completed_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

                active_tests = []
                for row in rows:
                    record = self.db._row_to_dict(row)

                    # 解析变体配置
                    config = record.get("variant_config_json", {})
                    if isinstance(config, str):
                        config = json.loads(config)

                    test_info = {
                        "variant_id": record["id"],
                        "match_id": record.get("match_id", ""),
                        "variant_name": record.get("variant_name", ""),
                        "variant_type": config.get("type", "unknown"),
                        "is_control": bool(record.get("is_control", 0)),
                        "created_at": record.get("created_at", ""),
                        "status": "active",
                    }
                    active_tests.append(test_info)

                logger.info("获取活跃A/B测试: 共%d条", len(active_tests))
                return active_tests

        except Exception as e:
            logger.error("获取活跃A/B测试失败: error=%s", e)
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

    def calculate_sample_size(
        self,
        baseline_conversion: float,
        minimum_detectable_effect: float = 0.2,
        confidence_level: float = 0.95,
        power: float = 0.8,
        num_variants: int = 2,
    ) -> Dict[str, Any]:
        """
        使用标准统计功效分析公式计算A/B测试所需样本量

        基于双比例Z检验的功效分析，采用更精确的逆正态累积分布函数
        计算临界Z值，支持任意置信水平和统计功效。

        公式推导：
            n = (Z_{1-α/2} * sqrt(2 * p_avg * (1-p_avg))
               + Z_{1-β} * sqrt(p1*(1-p1) + p2*(1-p2)))^2 / (p2 - p1)^2

        Args:
            baseline_conversion: 基准转化率（0-1之间，如0.05表示5%）
            minimum_detectable_effect: 最小可检测效应（相对提升比例，如0.2表示20%）
            confidence_level: 置信水平（默认0.95，即95%置信区间）
            power: 统计功效（默认0.8，即80%的检出能力）
            num_variants: 变体数量（默认2，用于Bonferroni校正）

        Returns:
            包含详细计算结果的字典：
            - sample_size_per_variant: 每组所需样本量
            - total_sample_size: 总样本量
            - baseline_rate: 基准转化率
            - expected_rate: 预期转化率
            - absolute_effect: 绝对效应量
            - relative_effect: 相对效应量
            - confidence_level: 使用的置信水平
            - power: 使用的统计功效
            - bonferroni_correction: 是否应用了Bonferroni校正
        """
        import math
        from math import erf, sqrt

        # --- 参数校验 ---
        if not (0 < baseline_conversion < 1):
            raise ValueError(
                f"基准转化率必须在(0,1)之间，当前值: {baseline_conversion}"
            )
        if minimum_detectable_effect <= 0:
            raise ValueError(
                f"最小可检测效应必须大于0，当前值: {minimum_detectable_effect}"
            )

        # --- 计算精确Z值（使用逆正态累积分布函数的近似公式） ---
        def _inverse_normal_cdf(p: float) -> float:
            """
            逆正态累积分布函数（Probit函数）的近似计算
            使用 Abramowitz and Stegun 的近似公式，精度约1.5e-7

            Args:
                p: 概率值（0,1）

            Returns:
                对应的标准正态分位数Z值
            """
            if p <= 0:
                return float("-inf")
            if p >= 1:
                return float("inf")

            # 对接近0.5的值使用直接近似
            if p < 0.5:
                return -_inverse_normal_cdf(1 - p)

            # Abramowitz and Stegun 近似公式 26.2.23
            t = sqrt(-2 * math.log(1 - p))
            c0 = 2.515517
            c1 = 0.802853
            c2 = 0.010328
            d1 = 1.432788
            d2 = 0.189269
            d3 = 0.001308

            return (
                t
                - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)
            )

        # --- Bonferroni校正 ---
        # 当有多个变体时，需要进行多重比较校正以控制族错误率（FWER）
        bonferroni_correction = num_variants > 2
        if bonferroni_correction:
            # 校正后的alpha = 原始alpha / 比较次数
            # 比较次数 = num_variants - 1（每个实验组与对照组比较）
            adjusted_confidence = 1 - (1 - confidence_level) / (num_variants - 1)
            logger.info(
                "应用Bonferroni校正: 原始置信水平=%.2f, 校正后=%.4f, 比较次数=%d",
                confidence_level,
                adjusted_confidence,
                num_variants - 1,
            )
        else:
            adjusted_confidence = confidence_level

        # --- 计算临界Z值 ---
        # Z_{1-α/2}: 双尾检验的临界值
        z_alpha = _inverse_normal_cdf(1 - (1 - adjusted_confidence) / 2)
        # Z_{1-β}: 功效对应的临界值
        z_beta = _inverse_normal_cdf(power)

        # --- 计算转化率参数 ---
        p1 = baseline_conversion
        p2 = baseline_conversion * (1 + minimum_detectable_effect)

        # 确保p2不超过1
        if p2 >= 1:
            logger.warning(
                "预期转化率p2=%.4f超过1，已自动调整为0.99。"
                "建议减小minimum_detectable_effect或baseline_conversion。",
                p2,
            )
            p2 = 0.99

        # 平均转化率（用于合并标准误计算）
        p_avg = (p1 + p2) / 2

        # --- 样本量计算（基于双比例Z检验功效分析公式） ---
        # 分子：Z_alpha项 + Z_beta项 的平方
        se_pooled = sqrt(2 * p_avg * (1 - p_avg))
        se_separate = sqrt(p1 * (1 - p1) + p2 * (1 - p2))

        numerator = (z_alpha * se_pooled + z_beta * se_separate) ** 2
        denominator = (p2 - p1) ** 2

        if denominator == 0:
            sample_size_per_variant = 1000  # 效应量为0时返回默认值
        else:
            sample_size_per_variant = int(math.ceil(numerator / denominator))

        # 至少100个样本，避免过小的样本导致统计不可靠
        sample_size_per_variant = max(100, sample_size_per_variant)

        total_sample_size = sample_size_per_variant * num_variants

        return {
            "sample_size_per_variant": sample_size_per_variant,
            "total_sample_size": total_sample_size,
            "baseline_rate": round(p1, 6),
            "expected_rate": round(p2, 6),
            "absolute_effect": round(p2 - p1, 6),
            "relative_effect": round(minimum_detectable_effect, 4),
            "confidence_level": confidence_level,
            "adjusted_confidence_level": round(adjusted_confidence, 6) if bonferroni_correction else None,
            "power": power,
            "z_alpha": round(z_alpha, 4),
            "z_beta": round(z_beta, 4),
            "bonferroni_correction": bonferroni_correction,
            "num_variants": num_variants,
        }


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
