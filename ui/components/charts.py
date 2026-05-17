"""
Content2Revenue AI - 图表样式工具
基于 Plotly 的统一图表主题和常用图表组件。

所有图表遵循统一的深色主题设计语言，
与全局 CSS 样式系统保持一致。
"""

from typing import List, Optional, Dict, Any
import streamlit as st


# ============================================================
# 统一颜色方案
# ============================================================
COLORS = {
    "primary": "#6366F1",      # Indigo - 品牌主色
    "secondary": "#8B5CF6",    # Violet - 辅助色
    "success": "#10B981",      # Emerald - 成功/增长
    "warning": "#F59E0B",      # Amber - 警告
    "error": "#EF4444",        # Red - 错误/下降
    "info": "#3B82F6",         # Blue - 信息
    "cyan": "#06B6D4",         # Cyan
    "pink": "#EC4899",         # Pink
    "orange": "#F97316",       # Orange
    "teal": "#14B8A6",         # Teal
}

# 图表序列色（用于多数据系列）
CHART_PALETTE = [
    "#6366F1",  # Indigo
    "#8B5CF6",  # Violet
    "#06B6D4",  # Cyan
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#EC4899",  # Pink
    "#3B82F6",  # Blue
    "#F97316",  # Orange
]

# 渐变色对（用于面积图等）
GRADIENT_PAIRS = {
    "primary": ("rgba(99, 102, 241, 0.3)", "rgba(99, 102, 241, 0.01)"),
    "success": ("rgba(16, 185, 129, 0.3)", "rgba(16, 185, 129, 0.01)"),
    "warning": ("rgba(245, 158, 11, 0.3)", "rgba(245, 158, 11, 0.01)"),
    "error": ("rgba(239, 68, 68, 0.3)", "rgba(239, 68, 68, 0.01)"),
    "info": ("rgba(59, 130, 246, 0.3)", "rgba(59, 130, 246, 0.01)"),
}

# 背景色
BG_BASE = "#0F0F11"
BG_SURFACE = "#1A1A2E"
BG_ELEVATED = "#16161A"

# 文字色
TEXT_PRIMARY = "#E2E8F0"
TEXT_SECONDARY = "#94A3B8"
TEXT_TERTIARY = "#64748B"

# 边框色
BORDER_COLOR = "#2D2D3D"
GRID_COLOR = "rgba(255, 255, 255, 0.05)"


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _empty_figure(message: str = "暂无数据") -> Any:
    """返回空数据占位图"""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None
    fig = go.Figure()
    fig.add_annotation(
        text=f"📊 {message}",
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(size=16, color=TEXT_TERTIARY),
    )
    fig.update_layout(
        **create_chart_theme(),
        height=200,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


# ============================================================
# 创建统一 Plotly 图表主题
# ============================================================
def create_chart_theme() -> Dict[str, Any]:
    """
    创建统一的 Plotly 图表主题配置。

    特性:
        - 深色背景，与全局主题一致
        - 隐藏网格线，保持界面简洁
        - 统一字体 (Inter)
        - 统一颜色方案
        - 精致的悬停交互效果
        - 性能优化：禁用拖拽、限制缩放

    返回:
        Plotly layout 配置字典

    使用示例:
        import plotly.express as px
        fig = px.line(x=[1,2,3], y=[4,5,6])
        fig.update_layout(**create_chart_theme())
        st.plotly_chart(fig, use_container_width=True)
    """
    return {
        # === 背景 ===
        "paper_bgcolor": "rgba(0, 0, 0, 0)",
        "plot_bgcolor": "rgba(0, 0, 0, 0)",

        # === 字体 ===
        "font": {
            "family": "Inter, system-ui, -apple-system, sans-serif",
            "color": TEXT_PRIMARY,
            "size": 12,
        },

        # === 标题 ===
        "title": {
            "font": {
                "size": 15,
                "color": TEXT_PRIMARY,
                "family": "Inter, system-ui, sans-serif",
            },
            "x": 0,
            "xanchor": "left",
            "pad": {"b": 20},
        },

        # === 图例 ===
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {
                "size": 11,
                "color": TEXT_SECONDARY,
            },
            "bgcolor": "rgba(0, 0, 0, 0)",
            "borderwidth": 0,
        },

        # === 边距 ===
        "margin": {
            "l": 0,
            "r": 0,
            "t": 10,
            "b": 0,
        },

        # === 坐标轴通用 ===
        "xaxis": {
            "gridcolor": GRID_COLOR,
            "zerolinecolor": GRID_COLOR,
            "linecolor": BORDER_COLOR,
            "tickfont": {
                "size": 11,
                "color": TEXT_TERTIARY,
            },
            "title": {
                "font": {
                    "size": 11,
                    "color": TEXT_SECONDARY,
                },
            },
        },

        "yaxis": {
            "gridcolor": GRID_COLOR,
            "zerolinecolor": GRID_COLOR,
            "linecolor": BORDER_COLOR,
            "tickfont": {
                "size": 11,
                "color": TEXT_TERTIARY,
            },
            "title": {
                "font": {
                    "size": 11,
                    "color": TEXT_SECONDARY,
                },
            },
        },

        # === 悬停模式 ===
        "hovermode": "x unified",

        # === 悬停标签 ===
        "hoverlabel": {
            "bgcolor": BG_SURFACE,
            "bordercolor": BORDER_COLOR,
            "font": {
                "size": 12,
                "color": TEXT_PRIMARY,
                "family": "Inter, system-ui, sans-serif",
            },
        },

        # === 模式栏 ===
        "modebar": {
            "bgcolor": "transparent",
            "color": TEXT_TERTIARY,
            "activecolor": TEXT_PRIMARY,
        },

        # === 性能优化：禁用拖拽和缩放 ===
        "dragmode": False,  # 禁用拖拽，提升渲染性能
        "scrollzoom": False,  # 禁用滚轮缩放
    }


def apply_chart_theme(fig) -> Any:
    """
    将统一主题应用到已有的 Plotly Figure 对象上。

    参数:
        fig: Plotly Figure 对象

    返回:
        应用主题后的 Figure 对象

    使用示例:
        import plotly.express as px
        fig = px.bar(...)
        fig = apply_chart_theme(fig)
        st.plotly_chart(fig)
    """
    theme = create_chart_theme()
    fig.update_layout(**theme)

    # 统一 trace 样式
    for trace in fig.data:
        trace.update(
            hovertemplate=(
                "<b>%{label}</b><br>"
                "%{value}<extra></extra>"
            )
        )

    # 隐藏模式栏中不必要的按钮
    fig.update_config(
        displayModeBar=False,
        responsive=True,
    )

    return fig


# ============================================================
# 雷达图 (匹配维度展示)
# ============================================================
def radar_chart(
    values: List[float],
    labels: List[str],
    title: str = "",
    fill_color: str = "primary",
    show_values: bool = True,
    height: int = 350,
    key: Optional[str] = None,
) -> Any:
    """
    雷达图组件，适用于多维度匹配度展示。

    参数:
        values:      各维度的值 (0-100)
        labels:      各维度的标签
        title:       图表标题
        fill_color:  填充颜色 "primary" | "success" | "warning" | "error" | "info"
        show_values: 是否在节点上显示数值
        height:      图表高度 (px)
        key:         Streamlit 唯一键

    返回:
        Plotly Figure 对象

    使用示例:
        fig = radar_chart(
            values=[85, 72, 90, 65, 78],
            labels=["SEO", "可读性", "原创性", "结构", "关键词"],
            title="内容质量维度"
        )
        st.plotly_chart(fig, use_container_width=True)
    """
    if not values:
        return _empty_figure("暂无数据")
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("请安装 plotly: pip install plotly")
        return None

    color = COLORS.get(fill_color, COLORS["primary"])
    gradient = GRADIENT_PAIRS.get(fill_color, GRADIENT_PAIRS["primary"])

    # 闭合雷达图
    r_values = values + [values[0]]
    r_labels = labels + [labels[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=r_values,
        theta=r_labels,
        fill="toself",
        fillcolor=hex_to_rgba(color, 0.2),
        line=dict(
            color=color,
            width=2,
        ),
        marker=dict(
            color=color,
            size=6,
            line=dict(
                color=BG_SURFACE,
                width=2,
            ),
        ),
        hovertemplate=(
            "<b>%{theta}</b><br>"
            "得分: %{r:.0f}<extra></extra>"
        ),
    ))

    # 显示数值标注
    annotations = []
    if show_values:
        for i, (label, val) in enumerate(zip(labels, values)):
            annotations.append(dict(
                text=str(int(val)),
                showarrow=False,
                font=dict(
                    size=10,
                    color=TEXT_SECONDARY,
                ),
                x=label,
                y=val,
            ))

    fig.update_layout(
        annotations=annotations,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(
                    size=9,
                    color=TEXT_TERTIARY,
                ),
                gridcolor=GRID_COLOR,
                linecolor=BORDER_COLOR,
                angle=90,
                dtick=25,
            ),
            angularaxis=dict(
                tickfont=dict(
                    size=11,
                    color=TEXT_SECONDARY,
                ),
                linecolor=BORDER_COLOR,
                gridcolor=GRID_COLOR,
                rotation=45,
            ),
            bgcolor="rgba(0, 0, 0, 0)",
        ),
        **create_chart_theme(),
        height=height,
        title=dict(
            text=title,
            font=dict(
                size=14,
                color=TEXT_PRIMARY,
            ),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=60, r=40, t=40 if title else 10, b=40),
        showlegend=False,
    )

    fig.update_config(displayModeBar=False)

    return fig


# ============================================================
# 趋势图 (7天趋势)
# ============================================================
def trend_chart(
    dates: List[str],
    values: List[float],
    title: str = "",
    series_name: str = "",
    color: str = "primary",
    show_area: bool = True,
    height: int = 300,
    key: Optional[str] = None,
) -> Any:
    """
    趋势折线图组件，适用于时间序列数据展示。

    参数:
        dates:       日期列表
        values:      数值列表
        title:       图表标题
        series_name: 数据系列名称
        color:       线条颜色 "primary" | "success" | "warning" | "error" | "info"
        show_area:   是否显示面积填充
        height:      图表高度 (px)
        key:         Streamlit 唯一键

    返回:
        Plotly Figure 对象

    使用示例:
        fig = trend_chart(
            dates=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            values=[1200, 1900, 1500, 2100, 1800, 2400, 2200],
            title="页面浏览量趋势",
            series_name="PV",
            color="primary"
        )
        st.plotly_chart(fig, use_container_width=True)
    """
    if not values:
        return _empty_figure("暂无数据")
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("请安装 plotly: pip install plotly")
        return None

    line_color = COLORS.get(color, COLORS["primary"])
    gradient = GRADIENT_PAIRS.get(color, GRADIENT_PAIRS["primary"])

    fig = go.Figure()

    # 面积填充
    if show_area:
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            fill="tozeroy",
            fillgradient=dict(
                type="vertical",
                color1=gradient[0],
                color2=gradient[1],
            ),
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        ))

    # 主线条
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines+markers",
        name=series_name or "数值",
        line=dict(
            color=line_color,
            width=2.5,
            shape="spline",
            smoothing=1.2,
        ),
        marker=dict(
            color=line_color,
            size=5,
            line=dict(
                color=BG_SURFACE,
                width=2,
            ),
        ),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "%{y:,.0f}<extra></extra>"
        ),
    ))

    fig.update_layout(
        **create_chart_theme(),
        height=height,
        title=dict(
            text=title,
            font=dict(size=14, color=TEXT_PRIMARY),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=0, r=0, t=40 if title else 10, b=0),
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            showline=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRID_COLOR,
            gridwidth=1,
            zeroline=False,
        ),
    )

    fig.update_config(displayModeBar=False)

    return fig


# ============================================================
# 分布图 (评分分布)
# ============================================================
def distribution_chart(
    values: List[float],
    labels: List[str],
    title: str = "",
    color: str = "primary",
    orientation: str = "h",
    height: int = 300,
    key: Optional[str] = None,
) -> Any:
    """
    分布图组件，适用于评分分布、分类统计等场景。

    参数:
        values:      数值列表
        labels:      标签列表
        title:       图表标题
        color:       柱状颜色
        orientation: 方向 "h" (水平) | "v" (垂直)
        height:      图表高度 (px)
        key:         Streamlit 唯一键

    返回:
        Plotly Figure 对象

    使用示例:
        fig = distribution_chart(
            values=[12, 25, 38, 18, 7],
            labels=["1星", "2星", "3星", "4星", "5星"],
            title="内容评分分布",
            color="primary"
        )
        st.plotly_chart(fig, use_container_width=True)
    """
    if not values:
        return _empty_figure("暂无数据")
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("请安装 plotly: pip install plotly")
        return None

    bar_color = COLORS.get(color, COLORS["primary"])

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=values if orientation == "v" else labels,
        y=labels if orientation == "h" else values,
        orientation=orientation,
        marker=dict(
            color=bar_color,
            cornerradius=4,
            line=dict(
                color="rgba(0,0,0,0)",
                width=0,
            ),
        ),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "数量: %{value}<extra></extra>"
        ) if orientation == "h" else (
            "<b>%{x}</b><br>"
            "数量: %{y}<extra></extra>"
        ),
        textposition="outside",
        textfont=dict(
            size=11,
            color=TEXT_SECONDARY,
        ),
    ))

    is_horizontal = orientation == "h"

    fig.update_layout(
        **create_chart_theme(),
        height=height,
        title=dict(
            text=title,
            font=dict(size=14, color=TEXT_PRIMARY),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=0, r=0, t=40 if title else 10, b=0),
        showlegend=False,
        bargap=0.35,
        xaxis=dict(
            showgrid=False if is_horizontal else True,
            showline=False,
            gridcolor=GRID_COLOR if not is_horizontal else None,
        ) if not is_horizontal else dict(
            showgrid=False,
            showline=False,
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
        ) if is_horizontal else dict(
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
    )

    fig.update_config(displayModeBar=False)

    return fig


# ============================================================
# 多系列趋势图
# ============================================================
def multi_trend_chart(
    dates: List[str],
    series: Dict[str, List[float]],
    title: str = "",
    height: int = 350,
    key: Optional[str] = None,
) -> Any:
    """
    多系列趋势图组件，适用于对比多个指标的时间变化。

    参数:
        dates:  日期列表
        series: 数据系列字典 {"系列名": [值1, 值2, ...]}
        title:  图表标题
        height: 图表高度 (px)
        key:    Streamlit 唯一键

    返回:
        Plotly Figure 对象

    使用示例:
        fig = multi_trend_chart(
            dates=["Mon", "Tue", "Wed", "Thu", "Fri"],
            series={
                "浏览量": [1200, 1900, 1500, 2100, 1800],
                "互动量": [300, 450, 380, 520, 410],
            },
            title="流量与互动趋势"
        )
        st.plotly_chart(fig, use_container_width=True)
    """
    if not series:
        return _empty_figure("暂无数据")
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("请安装 plotly: pip install plotly")
        return None

    fig = go.Figure()

    for i, (name, values) in enumerate(series.items()):
        color = CHART_PALETTE[i % len(CHART_PALETTE)]
        gradient = (
            hex_to_rgba(color, 0.15),
            hex_to_rgba(color, 0.01),
        )

        # 面积
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            fill="tozeroy",
            fillgradient=dict(type="vertical", color1=gradient[0], color2=gradient[1]),
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        ))

        # 线条
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            mode="lines",
            name=name,
            line=dict(
                color=color,
                width=2,
                shape="spline",
                smoothing=1.2,
            ),
            hovertemplate=(
                f"<b>{name}</b><br>"
                "%{x}<br>"
                "%{y:,.0f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        **create_chart_theme(),
        height=height,
        title=dict(
            text=title,
            font=dict(size=14, color=TEXT_PRIMARY),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=0, r=0, t=40 if title else 10, b=0),
        xaxis=dict(showgrid=False, showline=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False),
    )

    fig.update_config(displayModeBar=False)

    return fig


# ============================================================
# 环形图
# ============================================================
def donut_chart(
    values: List[float],
    labels: List[str],
    title: str = "",
    center_text: str = "",
    height: int = 300,
    key: Optional[str] = None,
) -> Any:
    """
    环形图组件，适用于占比展示。

    参数:
        values:      数值列表
        labels:      标签列表
        title:       图表标题
        center_text: 中心显示文字
        height:      图表高度 (px)
        key:         Streamlit 唯一键

    返回:
        Plotly Figure 对象

    使用示例:
        fig = donut_chart(
            values=[45, 30, 15, 10],
            labels=["直接访问", "搜索引擎", "社交媒体", "推荐"],
            title="流量来源",
            center_text="10.2K"
        )
        st.plotly_chart(fig, use_container_width=True)
    """
    if not values:
        return _empty_figure("暂无数据")
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("请安装 plotly: pip install plotly")
        return None

    colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(values))]

    fig = go.Figure()

    fig.add_trace(go.Pie(
        values=values,
        labels=labels,
        hole=0.7,
        marker=dict(
            colors=colors,
            line=dict(
                color=BG_SURFACE,
                width=2,
            ),
        ),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "%{value}<br>"
            "%{percent}<extra></extra>"
        ),
        textinfo="none",
    ))

    # 中心文字
    if center_text:
        fig.add_annotation(
            text=center_text,
            x=0.5,
            y=0.5,
            font=dict(
                size=20,
                color=TEXT_PRIMARY,
                family="Inter, system-ui, sans-serif",
            ),
            showarrow=False,
        )

    fig.update_layout(
        **create_chart_theme(),
        height=height,
        title=dict(
            text=title,
            font=dict(size=14, color=TEXT_PRIMARY),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=0, r=0, t=40 if title else 10, b=0),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05,
            font=dict(size=11, color=TEXT_SECONDARY),
        ),
    )

    fig.update_config(displayModeBar=False)

    return fig


# ============================================================
# 评分环形进度条
# ============================================================
def score_gauge(
    value: float,
    max_value: float = 10,
    title: str = "",
    subtitle: str = "",
    size: int = 200,
    key: Optional[str] = None,
) -> Any:
    """
    评分环形进度条组件，适用于单指标评分展示。

    参数:
        value:      评分值
        max_value:  满分值
        title:      指标名称
        subtitle:   补充说明
        size:       图表尺寸
        key:        Streamlit 唯一键

    返回:
        Plotly Figure 对象
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("请安装 plotly: pip install plotly")
        return None

    percentage = (value / max_value) * 100 if max_value > 0 else 0

    if percentage >= 80:
        color = COLORS["success"]
        level = "优秀"
    elif percentage >= 60:
        color = COLORS["warning"]
        level = "良好"
    elif percentage >= 40:
        color = COLORS["orange"]
        level = "一般"
    else:
        color = COLORS["error"]
        level = "需改进"

    fig = go.Figure()

    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"size": 14, "color": TEXT_SECONDARY}},
        number={"font": {"size": 36, "color": color, "family": "Inter, system-ui, sans-serif"}},
        delta={"reference": max_value * 0.6, "relative": True, "font": {"size": 12, "color": TEXT_TERTIARY}},
        gauge={
            "axis": {
                "range": [0, max_value],
                "tickwidth": 0,
                "tickcolor": "transparent",
                "visible": False,
            },
            "bar": {
                "color": color,
                "thickness": 0.75,
            },
            "bgcolor": "transparent",
            "borderwidth": 0,
            "bordercolor": "transparent",
            "steps": [
                {"range": [0, max_value * 0.4], "color": "rgba(239, 68, 68, 0.15)"},
                {"range": [max_value * 0.4, max_value * 0.6], "color": "rgba(249, 115, 22, 0.15)"},
                {"range": [max_value * 0.6, max_value * 0.8], "color": "rgba(245, 158, 11, 0.15)"},
                {"range": [max_value * 0.8, max_value], "color": "rgba(16, 185, 129, 0.15)"},
            ],
        },
    ))

    fig.update_layout(
        **create_chart_theme(),
        height=size,
        width=size,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    fig.update_config(displayModeBar=False)

    return fig


# ============================================================
# 热力图
# ============================================================
def heatmap_chart(
    z: List[List[float]],
    x: List[str],
    y: List[str],
    title: str = "",
    colorscale: str = "Blues",
    height: int = 350,
    key: Optional[str] = None,
) -> Any:
    """
    热力图组件，适用于相关性矩阵、时间热力图等。

    参数:
        z:          数据矩阵
        x:          x 轴标签
        y:          y 轴标签
        title:      图表标题
        colorscale: 颜色方案
        height:     图表高度 (px)
        key:        Streamlit 唯一键

    返回:
        Plotly Figure 对象

    使用示例:
        fig = heatmap_chart(
            z=[[1, 0.8, 0.3], [0.8, 1, 0.5], [0.3, 0.5, 1]],
            x=["SEO", "可读性", "原创性"],
            y=["SEO", "可读性", "原创性"],
            title="指标相关性矩阵"
        )
        st.plotly_chart(fig, use_container_width=True)
    """
    if not z:
        return _empty_figure("暂无数据")
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("请安装 plotly: pip install plotly")
        return None

    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=z,
        x=x,
        y=y,
        colorscale=[
            [0, BG_SURFACE],
            [0.5, hex_to_rgba(COLORS["primary"], 0.5)],
            [1, COLORS["primary"]],
        ],
        showscale=False,
        hovertemplate=(
            "<b>%{y} x %{x}</b><br>"
            "值: %{z}<extra></extra>"
        ),
        xgap=3,
        ygap=3,
    ))

    fig.update_layout(
        **create_chart_theme(),
        height=height,
        title=dict(
            text=title,
            font=dict(size=14, color=TEXT_PRIMARY),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=0, r=0, t=40 if title else 10, b=0),
        xaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(size=11, color=TEXT_SECONDARY),
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(size=11, color=TEXT_SECONDARY),
            autorange="reversed",
        ),
    )

    fig.update_config(displayModeBar=False)

    return fig


# ============================================================
# 漏斗图
# ============================================================
def funnel_chart(
    values: List[float],
    labels: List[str],
    title: str = "",
    height: int = 350,
    key: Optional[str] = None,
) -> Any:
    """
    漏斗图组件，适用于转化漏斗展示。

    参数:
        values:  各阶段数值
        labels:  各阶段标签
        title:   图表标题
        height:  图表高度 (px)
        key:     Streamlit 唯一键

    返回:
        Plotly Figure 对象

    使用示例:
        fig = funnel_chart(
            values=[10000, 6000, 3000, 1500, 450],
            labels=["浏览", "点击", "注册", "试用", "付费"],
            title="用户转化漏斗"
        )
        st.plotly_chart(fig, use_container_width=True)
    """
    if not values:
        return _empty_figure("暂无数据")
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("请安装 plotly: pip install plotly")
        return None

    fig = go.Figure()

    fig.add_trace(go.Funnel(
        y=labels,
        x=values,
        marker=dict(
            color=CHART_PALETTE[:len(values)],
            line=dict(
                color=BG_SURFACE,
                width=1,
            ),
        ),
        textinfo="value+percent initial+percent previous",
        textfont=dict(
            size=11,
            color=TEXT_PRIMARY,
        ),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "数量: %{value:,.0f}<br>"
            "占总数: %{percentInitial:.1%}<extra></extra>"
        ),
    ))

    fig.update_layout(
        **create_chart_theme(),
        height=height,
        title=dict(
            text=title,
            font=dict(size=14, color=TEXT_PRIMARY),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=0, r=0, t=40 if title else 10, b=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    fig.update_config(displayModeBar=False)

    return fig


# ============================================================
# 通用图表渲染辅助函数
# ============================================================
def render_chart(fig, use_container_width: bool = True, key: Optional[str] = None) -> None:
    """
    通用图表渲染函数，自动应用主题并渲染到 Streamlit。

    参数:
        fig:                Plotly Figure 对象
        use_container_width: 是否自适应容器宽度
        key:                Streamlit 唯一键

    使用示例:
        import plotly.express as px
        fig = px.line(x=[1,2,3], y=[4,5,6])
        render_chart(fig)
    """
    fig = apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=use_container_width, key=key)
