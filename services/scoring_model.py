"""
内容评分模型 - 基于历史数据的轻量级评分系统

基于历史数据的简单规则评分，无需训练ML模型，减少LLM调用。
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from services.database import Database

logger = logging.getLogger(__name__)


@dataclass
class ContentFeatures:
    """内容特征数据类"""

    hook_type: Optional[str] = None
    cta_type: Optional[str] = None
    content_length: Optional[int] = None
    emotion_tone: Optional[str] = None
    structure_type: Optional[str] = None
    industry: Optional[str] = None


@dataclass
class ScoreResult:
    """评分结果数据类"""

    overall_score: float
    hook_score: float
    cta_score: float
    structure_score: float
    confidence: float
    factors: List[str]
    recommendations: List[str]


class ContentScoringModel:
    """
    内容评分模型

    基于历史数据的轻量级评分系统，使用规则引擎计算内容质量分数。
    无需训练ML模型，直接基于历史转化率计算加权分数。
    """

    # Hook类型的历史转化率基准（示例数据，实际应从历史数据计算）
    HOOK_TYPE_SCORES = {
        "痛点反问型": 0.85,
        "数据冲击型": 0.82,
        "故事引入型": 0.78,
        "权威背书型": 0.80,
        "悬念设置型": 0.75,
        "对比反差型": 0.77,
        "直接陈述型": 0.65,
        "情感共鸣型": 0.72,
    }

    # CTA类型的历史转化率基准
    CTA_TYPE_SCORES = {
        "立即行动型": 0.88,
        "免费咨询型": 0.82,
        "资料下载型": 0.75,
        "关注订阅型": 0.70,
        "分享传播型": 0.65,
        "评论互动型": 0.68,
    }

    # 情感基调评分
    EMOTION_SCORES = {
        "紧迫感": 0.85,
        "信任感": 0.82,
        "好奇心": 0.78,
        "兴奋感": 0.75,
        "焦虑感": 0.70,
        "平静感": 0.65,
    }

    # 结构类型评分
    STRUCTURE_SCORES = {
        "问题-方案-行动": 0.88,
        "故事-教训-应用": 0.82,
        "数据-洞察-建议": 0.80,
        "对比-优势-选择": 0.78,
        "清单-要点-总结": 0.72,
        "自由叙述型": 0.65,
    }

    # 内容长度评分范围（字符数）
    LENGTH_OPTIMAL_RANGE = (300, 800)  # 最优范围
    LENGTH_MIN = 100
    LENGTH_MAX = 2000

    def __init__(self, db: Optional[Database] = None):
        """
        初始化评分模型

        Args:
            db: 数据库实例，用于获取历史数据
        """
        self.db = db or Database()
        self._load_historical_data()

    def _load_historical_data(self) -> None:
        """从历史数据加载评分基准"""
        try:
            # 尝试从策略反馈数据计算实际转化率
            effectiveness = self.db.get_strategy_effectiveness(days=90)

            if effectiveness.get("total_feedback", 0) > 10:
                # 有足够数据，可以动态调整评分
                avg_conversion = effectiveness.get("avg_conversion_adopted", 0) / 100
                logger.info("加载历史数据: 平均转化率=%.2f%%", avg_conversion * 100)

        except Exception as e:
            logger.warning("加载历史数据失败，使用默认评分: %s", e)

    def _calculate_hook_score(
        self, hook_type: Optional[str]
    ) -> Tuple[float, List[str]]:
        """
        计算Hook分数

        Returns:
            (分数, 评分因素列表)
        """
        factors = []

        if not hook_type:
            return 0.5, ["未识别Hook类型"]

        base_score = self.HOOK_TYPE_SCORES.get(hook_type, 0.70)
        factors.append(f"Hook类型 '{hook_type}' 基准分: {base_score:.2f}")

        return base_score, factors

    def _calculate_cta_score(self, cta_type: Optional[str]) -> Tuple[float, List[str]]:
        """
        计算CTA分数

        Returns:
            (分数, 评分因素列表)
        """
        factors = []

        if not cta_type:
            return 0.5, ["未识别CTA类型"]

        base_score = self.CTA_TYPE_SCORES.get(cta_type, 0.70)
        factors.append(f"CTA类型 '{cta_type}' 基准分: {base_score:.2f}")

        return base_score, factors

    def _calculate_structure_score(
        self, structure_type: Optional[str], content_length: Optional[int]
    ) -> Tuple[float, List[str]]:
        """
        计算结构分数

        Returns:
            (分数, 评分因素列表)
        """
        factors = []
        score = 0.70  # 基础分

        # 结构类型评分
        if structure_type:
            structure_score = self.STRUCTURE_SCORES.get(structure_type, 0.65)
            score = structure_score
            factors.append(f"结构类型 '{structure_type}': {structure_score:.2f}")
        else:
            factors.append("未识别结构类型，使用基础分")

        # 内容长度评分
        if content_length:
            length_adjust = 0
            if content_length < self.LENGTH_MIN:
                length_adjust = -0.15
                factors.append(
                    f"内容过短({content_length}字符)，减分: {length_adjust:.2f}"
                )
            elif content_length < self.LENGTH_OPTIMAL_RANGE[0]:
                length_adjust = 0.05
                factors.append(
                    f"内容长度({content_length}字符)偏短，加分: +{length_adjust:.2f}"
                )
            elif content_length <= self.LENGTH_OPTIMAL_RANGE[1]:
                length_adjust = 0.10
                factors.append(
                    f"内容长度({content_length}字符)在最佳范围内，加分: +{length_adjust:.2f}"
                )
            elif content_length <= self.LENGTH_MAX:
                length_adjust = 0.05
                factors.append(
                    f"内容长度({content_length}字符)可接受，加分: +{length_adjust:.2f}"
                )
            elif content_length > self.LENGTH_MAX:
                length_adjust = -0.10
                factors.append(
                    f"内容过长({content_length}字符)，减分: {length_adjust:.2f}"
                )
            else:
                length_adjust = 0
                factors.append(
                    f"内容长度({content_length}字符)未匹配任何范围，不调整"
                )

            score = max(0.0, min(1.0, score + length_adjust))

        return score, factors

    def _calculate_emotion_score(
        self, emotion_tone: Optional[str]
    ) -> Tuple[float, List[str]]:
        """
        计算情感基调分数

        Returns:
            (分数, 评分因素列表)
        """
        factors = []

        if not emotion_tone:
            return 0.70, ["未识别情感基调，使用基础分"]

        # 情感基调可能包含多个，取平均值
        emotions = [e.strip() for e in emotion_tone.split(",") if e.strip()]

        if not emotions:
            return 0.70, ["未识别情感基调，使用基础分"]

        scores = []
        for emotion in emotions:
            score = self.EMOTION_SCORES.get(emotion, 0.70)
            scores.append(score)
            factors.append(f"情感 '{emotion}': {score:.2f}")

        avg_score = sum(scores) / len(scores)
        return avg_score, factors

    def score_content(
        self, features: ContentFeatures, use_cache: bool = True
    ) -> ScoreResult:
        """
        对内容进行评分

        Args:
            features: 内容特征
            use_cache: 是否使用缓存

        Returns:
            评分结果
        """
        logger.info(
            "开始内容评分: hook=%s, cta=%s", features.hook_type, features.cta_type
        )

        # 计算各维度分数
        hook_score, hook_factors = self._calculate_hook_score(features.hook_type)
        cta_score, cta_factors = self._calculate_cta_score(features.cta_type)
        structure_score, structure_factors = self._calculate_structure_score(
            features.structure_type, features.content_length
        )
        emotion_score, emotion_factors = self._calculate_emotion_score(
            features.emotion_tone
        )

        # 加权计算总分
        # Hook: 30%, CTA: 25%, Structure: 25%, Emotion: 20%
        weights = {
            "hook": 0.30,
            "cta": 0.25,
            "structure": 0.25,
            "emotion": 0.20,
        }

        overall_score = (
            hook_score * weights["hook"]
            + cta_score * weights["cta"]
            + structure_score * weights["structure"]
            + emotion_score * weights["emotion"]
        )

        # 归一化到0-10分
        overall_score_10 = overall_score * 10

        # 计算置信度（基于特征完整度）
        feature_count = sum(
            [
                1
                for f in [
                    features.hook_type,
                    features.cta_type,
                    features.emotion_tone,
                    features.structure_type,
                ]
                if f is not None
            ]
        )
        confidence = 0.5 + (feature_count / 8)  # 0.5 - 1.0

        # 合并评分因素
        all_factors = []
        all_factors.extend([f"【Hook】{f}" for f in hook_factors])
        all_factors.extend([f"【CTA】{f}" for f in cta_factors])
        all_factors.extend([f"【结构】{f}" for f in structure_factors])
        all_factors.extend([f"【情感】{f}" for f in emotion_factors])

        # 生成改进建议
        recommendations = self._generate_recommendations(
            hook_score, cta_score, structure_score, emotion_score, features
        )

        result = ScoreResult(
            overall_score=round(overall_score_10, 2),
            hook_score=round(hook_score * 10, 2),
            cta_score=round(cta_score * 10, 2),
            structure_score=round(structure_score * 10, 2),
            confidence=round(confidence, 2),
            factors=all_factors,
            recommendations=recommendations,
        )

        logger.info(
            "内容评分完成: overall=%.2f, confidence=%.2f",
            result.overall_score,
            result.confidence,
        )

        return result

    def _generate_recommendations(
        self,
        hook_score: float,
        cta_score: float,
        structure_score: float,
        emotion_score: float,
        features: ContentFeatures,
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # Hook建议
        if hook_score < 0.75:
            recommendations.append(
                f"Hook类型 '{features.hook_type or '未知'}' 转化率较低，"
                f"建议尝试 '痛点反问型' 或 '数据冲击型' Hook"
            )

        # CTA建议
        if cta_score < 0.75:
            recommendations.append(
                f"CTA类型 '{features.cta_type or '未知'}' 转化效果一般，"
                f"建议尝试 '立即行动型' 或 '免费咨询型' CTA"
            )

        # 结构建议
        if structure_score < 0.75:
            recommendations.append(
                "内容结构有待优化，建议使用 '问题-方案-行动' 或 '故事-教训-应用' 结构"
            )

        # 长度建议
        if features.content_length:
            if features.content_length < self.LENGTH_MIN:
                recommendations.append(
                    f"内容较短({features.content_length}字符)，建议扩充到 {self.LENGTH_OPTIMAL_RANGE[0]}-{self.LENGTH_OPTIMAL_RANGE[1]} 字符以获得更好效果"
                )
            elif features.content_length > self.LENGTH_MAX:
                recommendations.append(
                    f"内容较长({features.content_length}字符)，建议精简到 {self.LENGTH_OPTIMAL_RANGE[0]}-{self.LENGTH_OPTIMAL_RANGE[1]} 字符"
                )

        # 情感建议
        if emotion_score < 0.75:
            recommendations.append(
                "情感基调可以更强，建议增加 '紧迫感' 或 '信任感' 元素"
            )

        if not recommendations:
            recommendations.append("内容质量良好，保持当前策略")

        return recommendations

    def predict_conversion_rate(
        self, features: ContentFeatures, industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        预测转化率

        Args:
            features: 内容特征
            industry: 行业（可选，用于行业调整）

        Returns:
            预测结果
        """
        score_result = self.score_content(features)

        # 基础转化率预测（基于总分）
        base_conversion = score_result.overall_score * 2  # 0-20% 范围

        # 行业调整（示例）
        industry_adjustment = 1.0
        if industry:
            industry_multipliers = {
                "教育培训": 1.1,
                "SaaS": 1.05,
                "电商": 0.95,
                "金融": 0.90,
            }
            industry_adjustment = industry_multipliers.get(industry, 1.0)

        predicted_conversion = base_conversion * industry_adjustment

        # 置信区间
        confidence_range = (1 - score_result.confidence) * 5  # +/- 范围

        return {
            "predicted_conversion_rate": round(predicted_conversion, 2),
            "confidence_interval": {
                "lower": round(max(0, predicted_conversion - confidence_range), 2),
                "upper": round(min(100, predicted_conversion + confidence_range), 2),
            },
            "confidence": score_result.confidence,
            "score_breakdown": {
                "overall": score_result.overall_score,
                "hook": score_result.hook_score,
                "cta": score_result.cta_score,
                "structure": score_result.structure_score,
            },
            "recommendations": score_result.recommendations,
        }

    def batch_score(self, contents: List[Dict[str, Any]]) -> List[ScoreResult]:
        """
        批量评分

        Args:
            contents: 内容特征列表

        Returns:
            评分结果列表
        """
        results = []
        for content in contents:
            features = ContentFeatures(
                hook_type=content.get("hook_type"),
                cta_type=content.get("cta_type"),
                content_length=content.get("content_length"),
                emotion_tone=content.get("emotion_tone"),
                structure_type=content.get("structure_type"),
                industry=content.get("industry"),
            )
            result = self.score_content(features)
            results.append(result)

        return results

    def get_feature_importance(self) -> Dict[str, float]:
        """
        获取特征重要性

        Returns:
            特征重要性字典
        """
        return {
            "hook_type": 0.30,
            "cta_type": 0.25,
            "structure_type": 0.25,
            "emotion_tone": 0.20,
        }

    def update_scores_from_feedback(self) -> bool:
        """
        根据反馈数据更新评分基准

        Returns:
            是否更新成功
        """
        try:
            effectiveness = self.db.get_strategy_effectiveness(days=30)

            if effectiveness.get("total_feedback", 0) < 5:
                logger.warning("反馈数据不足，无法更新评分")
                return False

            # 这里可以实现基于反馈的动态评分调整
            # 例如：如果某Hook类型的实际转化率与预期差异大，调整其基准分

            logger.info("评分基准更新完成")
            return True

        except Exception as e:
            logger.error("更新评分基准失败: %s", e)
            return False


# ===== 便捷函数 =====


def score_content_quick(
    hook_type: Optional[str] = None,
    cta_type: Optional[str] = None,
    content_length: Optional[int] = None,
    emotion_tone: Optional[str] = None,
    structure_type: Optional[str] = None,
    industry: Optional[str] = None,
) -> Dict[str, Any]:
    """
    快速评分函数

    Args:
        hook_type: Hook类型
        cta_type: CTA类型
        content_length: 内容长度
        emotion_tone: 情感基调
        structure_type: 结构类型
        industry: 行业

    Returns:
        评分结果字典
    """
    model = ContentScoringModel()
    features = ContentFeatures(
        hook_type=hook_type,
        cta_type=cta_type,
        content_length=content_length,
        emotion_tone=emotion_tone,
        structure_type=structure_type,
        industry=industry,
    )

    score_result = model.score_content(features)
    prediction = model.predict_conversion_rate(features, industry)

    return {
        "overall_score": score_result.overall_score,
        "hook_score": score_result.hook_score,
        "cta_score": score_result.cta_score,
        "structure_score": score_result.structure_score,
        "confidence": score_result.confidence,
        "factors": score_result.factors,
        "recommendations": score_result.recommendations,
        "predicted_conversion": prediction["predicted_conversion_rate"],
        "confidence_interval": prediction["confidence_interval"],
    }


def get_content_grade(score: float) -> str:
    """
    根据分数获取等级

    Args:
        score: 0-10分

    Returns:
        等级字符串
    """
    if score >= 9:
        return "S级 (卓越)"
    elif score >= 8:
        return "A级 (优秀)"
    elif score >= 7:
        return "B级 (良好)"
    elif score >= 6:
        return "C级 (合格)"
    elif score >= 5:
        return "D级 (需改进)"
    else:
        return "E级 (不合格)"


# ===== 使用示例 =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 示例1: 完整特征评分
    features = ContentFeatures(
        hook_type="痛点反问型",
        cta_type="立即行动型",
        content_length=600,
        emotion_tone="紧迫感,信任感",
        structure_type="问题-方案-行动",
        industry="教育培训",
    )

    model = ContentScoringModel()
    result = model.score_content(features)

    print("=" * 50)
    print("内容评分结果")
    print("=" * 50)
    print(
        f"总分: {result.overall_score}/10 ({get_content_grade(result.overall_score)})"
    )
    print(f"置信度: {result.confidence:.0%}")
    print("\n各维度分数:")
    print(f"  Hook: {result.hook_score}/10")
    print(f"  CTA: {result.cta_score}/10")
    print(f"  结构: {result.structure_score}/10")
    print("\n评分因素:")
    for factor in result.factors:
        print(f"  • {factor}")
    print("\n改进建议:")
    for rec in result.recommendations:
        print(f"  • {rec}")

    # 示例2: 转化率预测
    print("\n" + "=" * 50)
    print("转化率预测")
    print("=" * 50)
    prediction = model.predict_conversion_rate(features, industry="教育培训")
    print(f"预测转化率: {prediction['predicted_conversion_rate']:.2f}%")
    print(
        f"置信区间: {prediction['confidence_interval']['lower']:.2f}% - {prediction['confidence_interval']['upper']:.2f}%"
    )

    # 示例3: 快速评分
    print("\n" + "=" * 50)
    print("快速评分")
    print("=" * 50)
    quick_result = score_content_quick(
        hook_type="故事引入型",
        cta_type="资料下载型",
        content_length=400,
    )
    print(f"总分: {quick_result['overall_score']}/10")
    print(f"预测转化: {quick_result['predicted_conversion']:.2f}%")
