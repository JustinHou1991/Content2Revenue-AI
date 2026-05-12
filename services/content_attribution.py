"""
内容归因分析模块 - 多触点归因与客户旅程追踪

参考 Highspot 和 HubSpot 的归因分析功能，提供以下能力：
- 多触点归因模型（首次/最后/线性/时间衰减/U型）
- 客户旅程追踪与可视化就绪的数据输出
- 渠道与内容维度的归因得分报告
"""

import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class AttributionModel(str, Enum):
    """归因模型枚举"""
    FIRST_TOUCH = "first_touch"      # 首次触点归因
    LAST_TOUCH = "last_touch"        # 最后触点归因
    LINEAR = "linear"                # 线性归因
    TIME_DECAY = "time_decay"        # 时间衰减归因
    U_SHAPED = "u_shaped"            # U型归因


class TouchpointType(str, Enum):
    """触点类型枚举"""
    CONTENT_VIEW = "content_view"              # 内容浏览
    LEAD_CONVERSION = "lead_conversion"        # 线索转化
    STRATEGY_EXECUTION = "strategy_execution"  # 策略执行
    EMAIL_OPEN = "email_open"                  # 邮件打开
    WEBINAR_ATTEND = "webinar_attend"          # 研讨会参加
    DEMO_REQUEST = "demo_request"              # 演示请求
    SOCIAL_ENGAGEMENT = "social_engagement"    # 社交互动
    DIRECT_VISIT = "direct_visit"              # 直接访问
    OTHER = "other"                            # 其他


class JourneyStage(str, Enum):
    """客户旅程阶段枚举"""
    AWARENESS = "awareness"          # 认知阶段
    CONSIDERATION = "consideration"  # 考虑阶段
    DECISION = "decision"            # 决策阶段
    RETENTION = "retention"          # 留存阶段


@dataclass
class Touchpoint:
    """触点数据类 - 记录客户旅程中的单次交互"""
    touchpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    touchpoint_type: TouchpointType = TouchpointType.OTHER
    channel: str = ""               # 渠道名称，如 "微信公众号"、"官网博客"
    content_id: str = ""            # 关联的内容ID
    content_title: str = ""         # 内容标题
    stage: JourneyStage = JourneyStage.AWARENESS
    timestamp: datetime = field(default_factory=datetime.now)
    value: float = 0.0              # 该触点的直接价值（如产生的线索分数）
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "touchpoint_id": self.touchpoint_id,
            "touchpoint_type": self.touchpoint_type.value,
            "channel": self.channel, "content_id": self.content_id,
            "content_title": self.content_title, "stage": self.stage.value,
            "timestamp": self.timestamp.isoformat(), "value": self.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Touchpoint":
        """从字典反序列化"""
        return cls(
            touchpoint_id=data.get("touchpoint_id", str(uuid.uuid4())),
            touchpoint_type=TouchpointType(data.get("touchpoint_type", "other")),
            channel=data.get("channel", ""), content_id=data.get("content_id", ""),
            content_title=data.get("content_title", ""),
            stage=JourneyStage(data.get("stage", "awareness")),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data else datetime.now()
            ),
            value=float(data.get("value", 0)), metadata=data.get("metadata", {}),
        )


@dataclass
class AttributionScore:
    """归因得分数据类 - 单个渠道或内容的归因结果"""
    name: str = ""              # 渠道名称或内容ID
    score: float = 0.0          # 归因得分（0-1之间）
    touch_count: int = 0        # 触点数量
    converted_count: int = 0    # 关联的转化次数
    total_value: float = 0.0    # 关联的总价值

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self.name, "score": round(self.score, 4),
            "touch_count": self.touch_count, "converted_count": self.converted_count,
            "total_value": round(self.total_value, 2),
        }


@dataclass
class AttributionReport:
    """归因报告数据类 - 完整的归因分析结果"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model: AttributionModel = AttributionModel.LINEAR
    generated_at: datetime = field(default_factory=datetime.now)
    total_revenue: float = 0.0
    total_conversions: int = 0
    total_touchpoints: int = 0
    channel_scores: List[AttributionScore] = field(default_factory=list)
    content_scores: List[AttributionScore] = field(default_factory=list)
    journey_count: int = 0
    avg_journey_length: float = 0.0
    avg_journey_duration_days: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典，输出可视化就绪的结构"""
        return {
            "report_id": self.report_id, "model": self.model.value,
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_revenue": round(self.total_revenue, 2),
                "total_conversions": self.total_conversions,
                "total_touchpoints": self.total_touchpoints,
                "journey_count": self.journey_count,
                "avg_journey_length": round(self.avg_journey_length, 1),
                "avg_journey_duration_days": round(self.avg_journey_duration_days, 1),
            },
            "channel_attribution": [s.to_dict() for s in self.channel_scores],
            "content_attribution": [s.to_dict() for s in self.content_scores],
        }

    def get_top_channels(self, top_k: int = 5) -> List[AttributionScore]:
        """获取归因得分最高的前K个渠道"""
        return sorted(self.channel_scores, key=lambda x: x.score, reverse=True)[:top_k]

    def get_top_contents(self, top_k: int = 5) -> List[AttributionScore]:
        """获取归因得分最高的前K个内容"""
        return sorted(self.content_scores, key=lambda x: x.score, reverse=True)[:top_k]


class CustomerJourney:
    """客户旅程类 - 记录客户从首次接触到成交的完整路径"""

    def __init__(
        self, customer_id: str = "", customer_name: str = "",
        converted: bool = False, conversion_value: float = 0.0,
    ) -> None:
        """初始化客户旅程

        Args:
            customer_id: 客户唯一标识
            customer_name: 客户名称
            converted: 是否已转化
            conversion_value: 转化价值（如成交金额）
        """
        self.customer_id = customer_id or str(uuid.uuid4())
        self.customer_name = customer_name
        self.converted = converted
        self.conversion_value = conversion_value
        self.touchpoints: List[Touchpoint] = []

    def add_touchpoint(self, touchpoint: Touchpoint) -> None:
        """添加触点到旅程中，触点将按时间戳自动排序"""
        self.touchpoints.append(touchpoint)
        self.touchpoints.sort(key=lambda tp: tp.timestamp)
        logger.debug(
            "添加触点: customer=%s, type=%s, channel=%s",
            self.customer_id, touchpoint.touchpoint_type.value, touchpoint.channel,
        )

    def add_touchpoint_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典添加触点"""
        self.add_touchpoint(Touchpoint.from_dict(data))

    @property
    def journey_duration(self) -> timedelta:
        """旅程时长：从首次触点到末次触点的时间差"""
        if len(self.touchpoints) < 2:
            return timedelta(0)
        return self.touchpoints[-1].timestamp - self.touchpoints[0].timestamp

    @property
    def journey_duration_days(self) -> float:
        """旅程时长（天）"""
        return self.journey_duration.total_seconds() / 86400

    @property
    def touchpoint_count(self) -> int:
        """触点数量"""
        return len(self.touchpoints)

    @property
    def unique_channels(self) -> List[str]:
        """去重后的渠道列表（保持出现顺序）"""
        seen: set = set()
        return [
            tp.channel for tp in self.touchpoints
            if tp.channel and not (tp.channel in seen or seen.add(tp.channel))
        ]

    @property
    def unique_contents(self) -> List[str]:
        """去重后的内容ID列表（保持出现顺序）"""
        seen: set = set()
        return [
            tp.content_id for tp in self.touchpoints
            if tp.content_id and not (tp.content_id in seen or seen.add(tp.content_id))
        ]

    @property
    def conversion_rate(self) -> float:
        """单条旅程的转化率：已转化为 1.0，未转化为 0.0"""
        return 1.0 if self.converted else 0.0

    @property
    def stage_progression(self) -> List[str]:
        """旅程的阶段推进路径，如 ['awareness', 'consideration', 'decision']"""
        seen: set = set()
        return [
            tp.stage.value for tp in self.touchpoints
            if tp.stage.value not in seen and not seen.add(tp.stage.value)
        ]

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "customer_id": self.customer_id, "customer_name": self.customer_name,
            "converted": self.converted, "conversion_value": self.conversion_value,
            "touchpoint_count": self.touchpoint_count,
            "journey_duration_days": round(self.journey_duration_days, 2),
            "unique_channels": self.unique_channels, "unique_contents": self.unique_contents,
            "stage_progression": self.stage_progression,
            "touchpoints": [tp.to_dict() for tp in self.touchpoints],
        }


class AttributionEngine:
    """内容归因引擎 - 支持多种多触点归因模型

    参考 Highspot 的内容影响力分析和 HubSpot 的多触点归因报告，
    提供五种主流归因模型，并生成渠道/内容维度的归因得分。
    """

    # 时间衰减模型的半衰期（天），即7天前的触点权重减半
    TIME_DECAY_HALF_LIFE_DAYS = 7.0

    def __init__(self) -> None:
        """初始化归因引擎"""
        self._journeys: List[CustomerJourney] = []

    def add_journey(self, journey: CustomerJourney) -> None:
        """添加客户旅程"""
        self._journeys.append(journey)
        logger.info(
            "添加客户旅程: customer=%s, touchpoints=%d, converted=%s",
            journey.customer_id, journey.touchpoint_count, journey.converted,
        )

    def add_journey_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典添加客户旅程，格式同 CustomerJourney.to_dict()"""
        journey = CustomerJourney(
            customer_id=data.get("customer_id", ""),
            customer_name=data.get("customer_name", ""),
            converted=data.get("converted", False),
            conversion_value=float(data.get("conversion_value", 0)),
        )
        for tp_data in data.get("touchpoints", []):
            journey.add_touchpoint_from_dict(tp_data)
        self.add_journey(journey)

    @property
    def journey_count(self) -> int:
        """已添加的旅程数量"""
        return len(self._journeys)

    @property
    def total_conversions(self) -> int:
        """已转化的旅程数量"""
        return sum(1 for j in self._journeys if j.converted)

    @property
    def overall_conversion_rate(self) -> float:
        """整体转化率：转化旅程数 / 总旅程数"""
        if not self._journeys:
            return 0.0
        return self.total_conversions / len(self._journeys)

    def _calculate_weights(
        self, touchpoints: List[Touchpoint], model: AttributionModel,
    ) -> List[float]:
        """根据归因模型计算各触点的权重，权重之和为 1.0

        Args:
            touchpoints: 触点列表（已按时间排序）
            model: 归因模型
        Returns:
            与触点列表等长的权重列表
        Raises:
            ValueError: 触点列表为空时
        """
        n = len(touchpoints)
        if n == 0:
            raise ValueError("触点列表不能为空")
        if n == 1:
            return [1.0]
        if model == AttributionModel.FIRST_TOUCH:
            weights = [0.0] * n
            weights[0] = 1.0
            return weights
        if model == AttributionModel.LAST_TOUCH:
            weights = [0.0] * n
            weights[-1] = 1.0
            return weights
        if model == AttributionModel.LINEAR:
            return [1.0 / n] * n
        if model == AttributionModel.TIME_DECAY:
            # 时间衰减归因：越接近转化的触点权重越高
            # 使用指数衰减公式: w_i = 2^(-days_ago / half_life)
            last_ts = touchpoints[-1].timestamp
            raw_weights: List[float] = []
            for tp in touchpoints:
                days_ago = (last_ts - tp.timestamp).total_seconds() / 86400
                raw_weights.append(
                    math.pow(2, -days_ago / self.TIME_DECAY_HALF_LIFE_DAYS)
                )
            total_w = sum(raw_weights)
            return [w / total_w for w in raw_weights]
        if model == AttributionModel.U_SHAPED:
            # U型归因：首次和末次触点各占40%，中间触点平分20%
            weights = [0.0] * n
            weights[0] = 0.4
            weights[-1] = 0.4
            if n > 2:
                middle_weight = 0.2 / (n - 2)
                for i in range(1, n - 1):
                    weights[i] = middle_weight
            return weights
        return [1.0 / n] * n

    @staticmethod
    def _update_score_map(
        score_map: Dict[str, Tuple[float, int, int, float]],
        key: str, weight: float, value: float,
    ) -> None:
        """更新得分聚合字典 {名称: (累计得分, 触点数, 转化数, 总价值)}"""
        if key in score_map:
            prev_score, prev_touch, prev_conv, prev_value = score_map[key]
            score_map[key] = (
                prev_score + weight, prev_touch + 1,
                prev_conv + 1, prev_value + value * weight,
            )
        else:
            score_map[key] = (weight, 1, 1, value * weight)

    @staticmethod
    def _aggregate_scores(
        score_map: Dict[str, Tuple[float, int, int, float]],
    ) -> List[AttributionScore]:
        """聚合归因得分并按得分降序排列"""
        scores: List[AttributionScore] = []
        for name, (score, touch_count, conv_count, value) in score_map.items():
            scores.append(AttributionScore(
                name=name, score=score, touch_count=touch_count,
                converted_count=conv_count, total_value=value,
            ))
        scores.sort(key=lambda s: s.score, reverse=True)
        return scores

    def analyze(
        self, model: AttributionModel = AttributionModel.LINEAR,
    ) -> AttributionReport:
        """执行归因分析，遍历所有已转化的客户旅程计算归因得分

        Args:
            model: 归因模型，默认为线性归因
        Returns:
            归因报告对象
        """
        logger.info("开始归因分析: model=%s, journeys=%d", model.value, len(self._journeys))
        converted_journeys = [j for j in self._journeys if j.converted]
        if not converted_journeys:
            logger.warning("没有已转化的客户旅程，返回空报告")
            return AttributionReport(model=model)

        channel_map: Dict[str, Tuple[float, int, int, float]] = {}
        content_map: Dict[str, Tuple[float, int, int, float]] = {}
        total_revenue = 0.0
        total_touchpoints = 0
        journey_lengths: List[int] = []
        journey_durations: List[float] = []

        for journey in converted_journeys:
            if journey.touchpoint_count == 0:
                continue
            total_revenue += journey.conversion_value
            total_touchpoints += journey.touchpoint_count
            journey_lengths.append(journey.touchpoint_count)
            journey_durations.append(journey.journey_duration_days)
            weights = self._calculate_weights(journey.touchpoints, model)
            for tp, weight in zip(journey.touchpoints, weights):
                if tp.channel:
                    self._update_score_map(
                        channel_map, tp.channel, weight, journey.conversion_value,
                    )
                content_key = tp.content_id or tp.content_title or "未知内容"
                self._update_score_map(
                    content_map, content_key, weight, journey.conversion_value,
                )

        avg_length = sum(journey_lengths) / len(journey_lengths) if journey_lengths else 0
        avg_duration = sum(journey_durations) / len(journey_durations) if journey_durations else 0
        report = AttributionReport(
            model=model, total_revenue=total_revenue,
            total_conversions=len(converted_journeys),
            total_touchpoints=total_touchpoints,
            channel_scores=self._aggregate_scores(channel_map),
            content_scores=self._aggregate_scores(content_map),
            journey_count=len(converted_journeys),
            avg_journey_length=avg_length, avg_journey_duration_days=avg_duration,
        )
        logger.info(
            "归因分析完成: conversions=%d, revenue=%.2f, top_channel=%s",
            report.total_conversions, report.total_revenue,
            report.channel_scores[0].name if report.channel_scores else "无",
        )
        return report

    def compare_models(self) -> Dict[str, Any]:
        """对比所有归因模型的结果，汇总各模型下渠道排名差异

        Returns:
            包含各模型报告、渠道排名对比和排名波动性的字典
        """
        logger.info("开始多模型对比分析")
        model_reports: Dict[str, AttributionReport] = {}
        for model in AttributionModel:
            model_reports[model.value] = self.analyze(model=model)

        # 构建渠道在各模型下的排名对比
        channel_comparison: Dict[str, Dict[str, int]] = {}
        for model_value, report in model_reports.items():
            for rank, score in enumerate(report.channel_scores, start=1):
                channel_comparison.setdefault(score.name, {})[model_value] = rank

        # 计算排名波动（标准差），波动大说明不同模型对其评价差异大
        ranking_volatility: Dict[str, float] = {}
        for channel, rankings in channel_comparison.items():
            if len(rankings) >= 2:
                ranks = list(rankings.values())
                mean = sum(ranks) / len(ranks)
                variance = sum((r - mean) ** 2 for r in ranks) / len(ranks)
                ranking_volatility[channel] = round(math.sqrt(variance), 2)
            else:
                ranking_volatility[channel] = 0.0

        volatility_sorted = sorted(
            ranking_volatility.items(), key=lambda x: x[1], reverse=True
        )
        return {
            "model_reports": {k: v.to_dict() for k, v in model_reports.items()},
            "channel_ranking_comparison": channel_comparison,
            "ranking_volatility": dict(volatility_sorted),
            "insight": (
                "排名波动较大的渠道在不同归因模型下差异显著，"
                "建议结合业务场景选择合适的归因模型。"
            ),
        }

    def get_journey_summary(self) -> Dict[str, Any]:
        """获取所有客户旅程的汇总统计信息

        Returns:
            包含旅程统计、渠道分布、阶段分布、类型分布的字典
        """
        if not self._journeys:
            return {"total_journeys": 0, "message": "暂无客户旅程数据"}

        total = len(self._journeys)
        durations = [j.journey_duration_days for j in self._journeys]
        touch_counts = [j.touchpoint_count for j in self._journeys]
        channel_counts: Dict[str, int] = {}
        stage_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}

        for journey in self._journeys:
            for tp in journey.touchpoints:
                if tp.channel:
                    channel_counts[tp.channel] = channel_counts.get(tp.channel, 0) + 1
                stage_counts[tp.stage.value] = stage_counts.get(tp.stage.value, 0) + 1
                type_counts[tp.touchpoint_type.value] = (
                    type_counts.get(tp.touchpoint_type.value, 0) + 1
                )

        def _sort_desc(d: Dict[str, int]) -> Dict[str, int]:
            return dict(sorted(d.items(), key=lambda x: x[1], reverse=True))

        return {
            "total_journeys": total,
            "converted_journeys": self.total_conversions,
            "conversion_rate": round(self.overall_conversion_rate, 4),
            "avg_touchpoints": round(sum(touch_counts) / total, 1),
            "avg_duration_days": round(sum(durations) / total, 1),
            "max_duration_days": round(max(durations), 1),
            "min_duration_days": round(min(durations), 1),
            "channel_distribution": _sort_desc(channel_counts),
            "stage_distribution": _sort_desc(stage_counts),
            "type_distribution": _sort_desc(type_counts),
        }

    def clear(self) -> None:
        """清空所有已添加的旅程数据"""
        self._journeys.clear()
        logger.info("已清空所有客户旅程数据")


def quick_attribution(
    journeys_data: List[Dict[str, Any]],
    model: AttributionModel = AttributionModel.LINEAR,
) -> Dict[str, Any]:
    """快速归因分析便捷函数

    Args:
        journeys_data: 客户旅程数据列表（字典格式）
        model: 归因模型
    Returns:
        归因报告字典
    """
    engine = AttributionEngine()
    for jd in journeys_data:
        engine.add_journey_from_dict(jd)
    return engine.analyze(model=model).to_dict()
