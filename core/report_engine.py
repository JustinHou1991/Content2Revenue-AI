#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报表引擎 ReportEngine - 数据分析与报表生成系统

设计灵感:
- Pandas: 数据分组与聚合
- SQL GROUP BY: 多维度分析
- Tableau: 可视化配置模式

核心特性:
1. 多维度分析 - 支持行列交叉分析
2. 聚合函数 - SUM, AVG, COUNT, MIN, MAX等
3. 数据透视 - 动态透视表生成
4. 图表生成 - 支持多种图表类型
5. 模板系统 - 可复用的报表模板
6. 导出功能 - JSON, CSV, HTML, Markdown
7. 实时计算 - 流式数据实时统计
8. 缓存机制 - 报表结果缓存

作者: AI Assistant
创建日期: 2026-05-09
版本: 1.0.0
"""

import json
import csv
import io
import hashlib
import html as html_module
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


class AggregationType(Enum):
    """聚合函数类型"""
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    STD = "std"
    FIRST = "first"
    LAST = "last"
    UNIQUE_COUNT = "unique_count"


class ChartType(Enum):
    """图表类型"""
    TABLE = "table"
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"
    SCATTER = "scatter"


@dataclass
class ReportField:
    """报表字段定义"""
    name: str
    display_name: str = ""
    data_type: str = "string"  # string, number, date, boolean
    format: Optional[str] = None  # 格式化字符串
    width: Optional[int] = None  # 列宽
    sortable: bool = True
    visible: bool = True
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name


@dataclass
class ReportMetric:
    """报表指标定义"""
    field: str
    aggregation: AggregationType
    display_name: str = ""
    format: Optional[str] = None
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = f"{self.aggregation.value}_{self.field}"


@dataclass
class ReportDimension:
    """报表维度定义"""
    field: str
    display_name: str = ""
    sort_order: Optional[str] = None  # asc, desc
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.field


@dataclass
class ReportFilter:
    """报表筛选条件"""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, between, contains
    value: Any


@dataclass
class ReportConfig:
    """
    报表配置
    
    属性:
        name: 报表名称
        description: 报表描述
        dimensions: 维度字段列表
        metrics: 指标定义列表
        filters: 筛选条件列表
        sort_by: 排序字段
        limit: 结果限制
        chart_type: 图表类型
        chart_config: 图表配置
    """
    name: str
    description: str = ""
    dimensions: List[ReportDimension] = field(default_factory=list)
    metrics: List[ReportMetric] = field(default_factory=list)
    filters: List[ReportFilter] = field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    limit: Optional[int] = None
    chart_type: ChartType = ChartType.TABLE
    chart_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "dimensions": [
                {"field": d.field, "display_name": d.display_name, "sort_order": d.sort_order}
                for d in self.dimensions
            ],
            "metrics": [
                {
                    "field": m.field,
                    "aggregation": m.aggregation.value,
                    "display_name": m.display_name,
                    "format": m.format
                }
                for m in self.metrics
            ],
            "filters": [
                {"field": f.field, "operator": f.operator, "value": f.value}
                for f in self.filters
            ],
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "limit": self.limit,
            "chart_type": self.chart_type.value,
            "chart_config": self.chart_config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportConfig':
        """从字典创建配置"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            dimensions=[
                ReportDimension(**d) for d in data.get("dimensions", [])
            ],
            metrics=[
                ReportMetric(
                    field=m["field"],
                    aggregation=AggregationType(m["aggregation"]),
                    display_name=m.get("display_name", ""),
                    format=m.get("format")
                )
                for m in data.get("metrics", [])
            ],
            filters=[
                ReportFilter(**f) for f in data.get("filters", [])
            ],
            sort_by=data.get("sort_by"),
            sort_order=data.get("sort_order", "desc"),
            limit=data.get("limit"),
            chart_type=ChartType(data.get("chart_type", "table")),
            chart_config=data.get("chart_config", {})
        )


@dataclass
class ReportResult:
    """报表结果"""
    config: ReportConfig
    data: List[Dict[str, Any]]
    total_rows: int
    summary: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "config": self.config.to_dict(),
            "data": self.data,
            "total_rows": self.total_rows,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "execution_time_ms": self.execution_time_ms
        }


class DataAggregator:
    """数据聚合器"""
    
    @staticmethod
    def aggregate(values: List[Any], agg_type: AggregationType) -> Any:
        """执行聚合计算"""
        if not values:
            return None
        
        # 过滤None值
        clean_values = [v for v in values if v is not None]
        if not clean_values:
            return None
        
        if agg_type == AggregationType.COUNT:
            return len(clean_values)
        
        if agg_type == AggregationType.UNIQUE_COUNT:
            return len(set(clean_values))
        
        # 数值型聚合
        numeric_values = []
        for v in clean_values:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                continue
        
        if not numeric_values:
            return None
        
        if agg_type == AggregationType.SUM:
            return sum(numeric_values)
        elif agg_type == AggregationType.AVG:
            return sum(numeric_values) / len(numeric_values)
        elif agg_type == AggregationType.MIN:
            return min(numeric_values)
        elif agg_type == AggregationType.MAX:
            return max(numeric_values)
        elif agg_type == AggregationType.MEDIAN:
            return statistics.median(numeric_values)
        elif agg_type == AggregationType.STD:
            return statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
        elif agg_type == AggregationType.FIRST:
            return numeric_values[0]
        elif agg_type == AggregationType.LAST:
            return numeric_values[-1]
        
        return None


class ReportEngine:
    """
    报表引擎
    
    功能特性:
    1. 数据筛选 - 多条件组合筛选
    2. 分组聚合 - 多维度分组统计
    3. 排序分页 - 灵活排序和结果限制
    4. 格式导出 - 多种格式导出
    5. 图表生成 - 可视化图表配置
    6. 模板管理 - 报表模板保存和加载
    
    使用示例:
        engine = ReportEngine()
        
        config = ReportConfig(
            name="销售报表",
            dimensions=[ReportDimension("category"), ReportDimension("region")],
            metrics=[ReportMetric("amount", AggregationType.SUM)],
            filters=[ReportFilter("date", "gte", "2024-01-01")]
        )
        
        result = engine.generate(data, config)
        html = engine.export_to_html(result)
    """
    
    def __init__(self):
        self.templates: Dict[str, ReportConfig] = {}
        self.cache: Dict[str, Tuple[ReportResult, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)
    
    # ==================== 数据筛选 ====================
    
    def _apply_filters(self, data: List[Dict], filters: List[ReportFilter]) -> List[Dict]:
        """应用筛选条件"""
        if not filters:
            return data
        
        def match_filter(row: Dict, filter_: ReportFilter) -> bool:
            value = row.get(filter_.field)
            op = filter_.operator
            target = filter_.value
            
            if op == "eq":
                return value == target
            elif op == "ne":
                return value != target
            elif op == "gt":
                return value is not None and target is not None and value > target
            elif op == "lt":
                return value is not None and target is not None and value < target
            elif op == "gte":
                return value is not None and target is not None and value >= target
            elif op == "lte":
                return value is not None and target is not None and value <= target
            elif op == "in":
                return value in target if isinstance(target, (list, tuple, set)) else False
            elif op == "between":
                if isinstance(target, (list, tuple)) and len(target) == 2:
                    return target[0] <= value <= target[1] if value is not None else False
                return False
            elif op == "contains":
                return target in str(value) if value is not None else False
            
            return True
        
        return [row for row in data if all(match_filter(row, f) for f in filters)]
    
    # ==================== 分组聚合 ====================
    
    def _group_and_aggregate(
        self,
        data: List[Dict],
        dimensions: List[ReportDimension],
        metrics: List[ReportMetric]
    ) -> List[Dict]:
        """分组聚合数据"""
        if not dimensions:
            # 无维度时整体聚合
            result = {}
            for metric in metrics:
                values = [row.get(metric.field) for row in data]
                result[metric.display_name] = DataAggregator.aggregate(values, metric.aggregation)
            return [result]
        
        # 分组
        groups = defaultdict(list)
        for row in data:
            key = tuple(row.get(d.field) for d in dimensions)
            groups[key].append(row)
        
        # 聚合每个组
        results = []
        for key, rows in groups.items():
            result = {}
            
            # 添加维度值
            for i, dim in enumerate(dimensions):
                result[dim.display_name] = key[i]
            
            # 计算指标
            for metric in metrics:
                values = [row.get(metric.field) for row in rows]
                result[metric.display_name] = DataAggregator.aggregate(values, metric.aggregation)
            
            results.append(result)
        
        return results
    
    # ==================== 排序和限制 ====================
    
    def _sort_and_limit(
        self,
        data: List[Dict],
        sort_by: Optional[str],
        sort_order: str,
        limit: Optional[int]
    ) -> List[Dict]:
        """排序和限制结果"""
        if sort_by:
            reverse = sort_order == "desc"
            data = sorted(
                data,
                key=lambda x: (x.get(sort_by) is None, x.get(sort_by)),
                reverse=reverse
            )
        
        if limit:
            data = data[:limit]
        
        return data
    
    # ==================== 报表生成 ====================
    
    def generate(
        self,
        data: List[Dict],
        config: ReportConfig,
        use_cache: bool = False
    ) -> ReportResult:
        """
        生成报表
        
        Args:
            data: 原始数据
            config: 报表配置
            use_cache: 是否使用缓存
            
        Returns:
            报表结果
        """
        start_time = datetime.now()
        
        # 检查缓存
        if use_cache:
            cache_key = self._get_cache_key(data, config)
            if cache_key in self.cache:
                result, cached_time = self.cache[cache_key]
                if datetime.now() - cached_time < self.cache_ttl:
                    logger.debug("返回缓存的报表结果")
                    return result
        
        # 1. 筛选数据
        filtered_data = self._apply_filters(data, config.filters)
        total_rows = len(filtered_data)
        
        # 2. 分组聚合
        aggregated_data = self._group_and_aggregate(
            filtered_data, config.dimensions, config.metrics
        )
        
        # 3. 排序和限制
        final_data = self._sort_and_limit(
            aggregated_data,
            config.sort_by,
            config.sort_order,
            config.limit
        )
        
        # 4. 计算汇总
        summary = self._calculate_summary(final_data, config.metrics)
        
        # 5. 构建结果
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = ReportResult(
            config=config,
            data=final_data,
            total_rows=total_rows,
            summary=summary,
            execution_time_ms=execution_time
        )
        
        # 缓存结果
        if use_cache:
            self.cache[cache_key] = (result, datetime.now())
        
        logger.info(f"报表生成完成: {config.name} ({len(final_data)} 行, {execution_time:.2f}ms)")
        return result
    
    def _get_cache_key(self, data: List[Dict], config: ReportConfig) -> str:
        """生成缓存键"""
        data_hash = hashlib.md5(str(data).encode()).hexdigest()[:16]
        config_hash = hashlib.md5(json.dumps(config.to_dict(), sort_keys=True).encode()).hexdigest()[:16]
        return f"{data_hash}_{config_hash}"
    
    def _calculate_summary(
        self,
        data: List[Dict],
        metrics: List[ReportMetric]
    ) -> Dict[str, Any]:
        """计算汇总统计"""
        summary = {"total_rows": len(data)}
        
        for metric in metrics:
            values = [row.get(metric.display_name) for row in data if row.get(metric.display_name) is not None]
            if values:
                summary[f"{metric.display_name}_total"] = sum(values) if all(isinstance(v, (int, float)) for v in values) else len(values)
                if all(isinstance(v, (int, float)) for v in values):
                    summary[f"{metric.display_name}_avg"] = sum(values) / len(values)
        
        return summary
    
    # ==================== 导出功能 ====================
    
    def export_to_json(self, result: ReportResult, indent: int = 2) -> str:
        """导出为JSON"""
        return json.dumps(result.to_dict(), indent=indent, ensure_ascii=False, default=str)
    
    def export_to_csv(self, result: ReportResult) -> str:
        """导出为CSV"""
        if not result.data:
            return ""
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        headers = list(result.data[0].keys())
        writer.writerow(headers)
        
        # 写入数据
        for row in result.data:
            writer.writerow([row.get(h, "") for h in headers])
        
        return output.getvalue()
    
    def export_to_html(self, result: ReportResult) -> str:
        """导出为HTML表格"""
        if not result.data:
            return "<p>无数据</p>"
        
        headers = list(result.data[0].keys())
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{html_module.escape(result.config.name)}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .summary {{ margin-top: 20px; padding: 10px; background-color: #f9f9f9; }}
        .meta {{ color: #666; font-size: 12px; margin-top: 10px; }}
    </style>
</head>
<body>
    <h1>{html_module.escape(result.config.name)}</h1>
    <p>{result.config.description}</p>
    
    <table>
        <thead>
            <tr>
                {''.join(f'<th>{h}</th>' for h in headers)}
            </tr>
        </thead>
        <tbody>
"""
        
        for row in result.data:
            html += "            <tr>\n"
            for h in headers:
                value = row.get(h, "")
                html += f"                <td>{html_module.escape(str(value))}</td>\n"
            html += "            </tr>\n"
        
        html += f"""
        </tbody>
    </table>
    
    <div class="summary">
        <strong>汇总:</strong> 共 {result.total_rows} 行数据
    </div>
    
    <div class="meta">
        生成时间: {result.generated_at} | 执行时间: {result.execution_time_ms:.2f}ms
    </div>
</body>
</html>
"""
        return html
    
    def export_to_markdown(self, result: ReportResult) -> str:
        """导出为Markdown"""
        if not result.data:
            return "# 无数据\n"
        
        md = f"# {result.config.name}\n\n"
        if result.config.description:
            md += f"{result.config.description}\n\n"
        
        headers = list(result.data[0].keys())
        
        # 表头
        md += "| " + " | ".join(headers) + " |\n"
        md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        # 数据
        for row in result.data:
            values = [str(row.get(h, "")) for h in headers]
            md += "| " + " | ".join(values) + " |\n"
        
        md += f"\n**汇总:** 共 {result.total_rows} 行数据\n"
        md += f"\n*生成时间: {result.generated_at}*\n"
        
        return md
    
    # ==================== 模板管理 ====================
    
    def save_template(self, name: str, config: ReportConfig) -> None:
        """保存报表模板"""
        self.templates[name] = config
        logger.info(f"报表模板已保存: {name}")
    
    def load_template(self, name: str) -> Optional[ReportConfig]:
        """加载报表模板"""
        return self.templates.get(name)
    
    def delete_template(self, name: str) -> bool:
        """删除报表模板"""
        if name in self.templates:
            del self.templates[name]
            return True
        return False
    
    def list_templates(self) -> List[str]:
        """列出所有模板"""
        return list(self.templates.keys())
    
    def export_template(self, name: str) -> Optional[str]:
        """导出模板为JSON"""
        config = self.templates.get(name)
        if config:
            return json.dumps(config.to_dict(), indent=2, ensure_ascii=False)
        return None
    
    def import_template(self, name: str, json_str: str) -> bool:
        """从JSON导入模板"""
        try:
            data = json.loads(json_str)
            config = ReportConfig.from_dict(data)
            self.templates[name] = config
            return True
        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            return False


# ==================== 便捷函数 ====================

def create_simple_report(
    name: str,
    dimension_field: str,
    metric_field: str,
    aggregation: AggregationType = AggregationType.SUM
) -> ReportConfig:
    """创建简单报表配置"""
    return ReportConfig(
        name=name,
        dimensions=[ReportDimension(field=dimension_field)],
        metrics=[ReportMetric(field=metric_field, aggregation=aggregation)]
    )


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例数据
    sales_data = [
        {"date": "2024-01-01", "category": "电子产品", "region": "北京", "amount": 5000, "quantity": 10},
        {"date": "2024-01-01", "category": "服装", "region": "上海", "amount": 3000, "quantity": 20},
        {"date": "2024-01-02", "category": "电子产品", "region": "北京", "amount": 8000, "quantity": 15},
        {"date": "2024-01-02", "category": "食品", "region": "广州", "amount": 2000, "quantity": 50},
        {"date": "2024-01-03", "category": "服装", "region": "北京", "amount": 4500, "quantity": 25},
        {"date": "2024-01-03", "category": "电子产品", "region": "上海", "amount": 6000, "quantity": 12},
    ]
    
    # 创建报表引擎
    engine = ReportEngine()
    
    # 配置报表
    config = ReportConfig(
        name="销售分析报表",
        description="按类别和地区统计销售额",
        dimensions=[
            ReportDimension(field="category", display_name="产品类别"),
            ReportDimension(field="region", display_name="地区")
        ],
        metrics=[
            ReportMetric(field="amount", aggregation=AggregationType.SUM, display_name="销售额"),
            ReportMetric(field="quantity", aggregation=AggregationType.SUM, display_name="销量")
        ],
        sort_by="销售额",
        sort_order="desc"
    )
    
    # 生成报表
    result = engine.generate(sales_data, config)
    
    print("报表结果:")
    print(json.dumps(result.data, indent=2, ensure_ascii=False))
    
    print("\n汇总信息:")
    print(json.dumps(result.summary, indent=2, ensure_ascii=False))
    
    # 导出为不同格式
    print("\nCSV格式:")
    print(engine.export_to_csv(result))
