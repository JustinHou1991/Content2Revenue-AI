"""
Content2Revenue AI - UI 组件模块
包含设计系统组件和图表工具。
"""

from ui.components.design_system import (
    metric_card,
    data_card,
    status_badge,
    empty_state,
    page_header,
    tabs,
    progress_indicator,
    metric_row,
    divider,
    callout,
    sidebar_logo,
    sidebar_nav,
    chart_container,
    skeleton_loader,
    stat_row,
)

from ui.components.charts import (
    create_chart_theme,
    apply_chart_theme,
    radar_chart,
    trend_chart,
    distribution_chart,
    multi_trend_chart,
    donut_chart,
    heatmap_chart,
    funnel_chart,
    render_chart,
    COLORS,
    CHART_PALETTE,
)

__all__ = [
    # 设计系统组件
    "metric_card",
    "data_card",
    "status_badge",
    "empty_state",
    "page_header",
    "tabs",
    "progress_indicator",
    "metric_row",
    "divider",
    "callout",
    "sidebar_logo",
    "sidebar_nav",
    "chart_container",
    "skeleton_loader",
    "stat_row",
    # 图表工具
    "create_chart_theme",
    "apply_chart_theme",
    "radar_chart",
    "trend_chart",
    "distribution_chart",
    "multi_trend_chart",
    "donut_chart",
    "heatmap_chart",
    "funnel_chart",
    "render_chart",
    # 常量
    "COLORS",
    "CHART_PALETTE",
]
