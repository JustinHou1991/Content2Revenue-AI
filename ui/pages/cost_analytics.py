"""
成本分析页面 - API使用统计与成本监控
设计语言: Linear + Databox + Anthropic 深色主题
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pandas as pd

from services.database import Database
from services.llm_client import LLMClient
from ui.styles import inject_custom_css, COLORS, PLOTLY_LAYOUT
from ui.components.design_system import (
    page_header,
    metric_card,
    metric_row,
    divider,
    callout,
    empty_state,
    status_badge,
    chart_container,
)
from ui.components.charts import (
    create_chart_theme,
    apply_chart_theme,
    trend_chart,
    distribution_chart,
    donut_chart,
    CHART_PALETTE,
)


# ============================================================
# 辅助函数
# ============================================================

def init_database():
    """初始化数据库连接"""
    if "db" not in st.session_state:
        st.session_state.db = Database()
    return st.session_state.db


def get_model_color_map():
    """获取模型颜色映射 - 使用设计系统调色板"""
    return {
        "deepseek-chat": CHART_PALETTE[0],
        "deepseek-reasoner": CHART_PALETTE[1],
        "qwen-turbo": CHART_PALETTE[3],
        "qwen-plus": CHART_PALETTE[4],
        "qwen-max": CHART_PALETTE[2],
    }


# ============================================================
# 页面区域渲染函数
# ============================================================

def render_summary_cards(db: Database):
    """渲染汇总统计卡片"""
    st.markdown(
        '<div class="c2r-page-title" style="font-size:1.125rem;font-weight:600;margin-bottom:16px;">成本概览</div>',
        unsafe_allow_html=True,
    )

    today_stats = db.get_today_api_stats()
    week_stats = db.get_week_api_stats()
    month_stats = db.get_month_api_stats()
    total_cost = db.get_total_cost()

    metric_row([
        {
            "title": "今日调用次数",
            "value": f"{today_stats['total_calls']:,}",
            "delta": f"¥{today_stats['total_cost']:.2f}" if today_stats["total_cost"] > 0 else "",
            "trend": "up" if today_stats["total_cost"] > 0 else "neutral",
            "icon": "📊",
            "border_color": COLORS["info"],
        },
        {
            "title": "本周调用次数",
            "value": f"{week_stats['total_calls']:,}",
            "delta": f"¥{week_stats['total_cost']:.2f}" if week_stats["total_cost"] > 0 else "",
            "trend": "up" if week_stats["total_cost"] > 0 else "neutral",
            "icon": "📈",
            "border_color": COLORS["brand_primary"],
        },
        {
            "title": "本月调用次数",
            "value": f"{month_stats['total_calls']:,}",
            "delta": f"¥{month_stats['total_cost']:.2f}" if month_stats["total_cost"] > 0 else "",
            "trend": "up" if month_stats["total_cost"] > 0 else "neutral",
            "icon": "📅",
            "border_color": COLORS["tag_purple"],
        },
        {
            "title": "累计总成本",
            "value": f"¥{total_cost:.2f}",
            "subtitle": "自开始使用以来的所有API调用成本",
            "icon": "💰",
            "border_color": COLORS["success"],
        },
    ])

    divider()


def render_token_stats(db: Database):
    """渲染Token消耗统计"""
    st.markdown(
        '<div class="c2r-page-title" style="font-size:1.125rem;font-weight:600;margin-bottom:16px;">Token 消耗统计</div>',
        unsafe_allow_html=True,
    )

    today_stats = db.get_today_api_stats()
    week_stats = db.get_week_api_stats()
    month_stats = db.get_month_api_stats()

    metric_row([
        {
            "title": "今日 Token 消耗",
            "value": f"{today_stats['total_tokens']:,}",
            "subtitle": f"输入: {today_stats['total_input_tokens']:,} | 输出: {today_stats['total_output_tokens']:,}",
            "icon": "📝",
            "border_color": COLORS["info"],
        },
        {
            "title": "本周 Token 消耗",
            "value": f"{week_stats['total_tokens']:,}",
            "subtitle": f"输入: {week_stats['total_input_tokens']:,} | 输出: {week_stats['total_output_tokens']:,}",
            "icon": "📋",
            "border_color": COLORS["brand_primary"],
        },
        {
            "title": "本月 Token 消耗",
            "value": f"{month_stats['total_tokens']:,}",
            "subtitle": f"输入: {month_stats['total_input_tokens']:,} | 输出: {month_stats['total_output_tokens']:,}",
            "icon": "📑",
            "border_color": COLORS["tag_purple"],
        },
    ], columns=3)

    divider()


def render_model_distribution(db: Database):
    """渲染模型调用分布"""
    st.markdown(
        '<div class="c2r-page-title" style="font-size:1.125rem;font-weight:600;margin-bottom:16px;">模型调用分布</div>',
        unsafe_allow_html=True,
    )

    month_stats = db.get_month_api_stats()
    model_data = month_stats.get("by_model", [])

    if not model_data:
        empty_state(
            title="暂无模型调用数据",
            description="当您开始使用API后，模型调用分布将在此展示。",
            icon="🤖",
        )
        return

    df = pd.DataFrame(model_data)

    col1, col2 = st.columns(2)

    with col1:
        chart_container(
            title="各模型调用次数占比",
            chart_func=lambda: _render_calls_pie(df),
        )

    with col2:
        chart_container(
            title="各模型成本占比",
            chart_func=lambda: _render_cost_pie(df),
        )

    # 模型详细数据表
    with st.expander("查看详细数据"):
        df_display = df.copy()
        df_display["cost"] = df_display["cost"].apply(lambda x: f"¥{x:.4f}")
        df_display["input_tokens"] = df_display["input_tokens"].apply(
            lambda x: f"{x:,}"
        )
        df_display["output_tokens"] = df_display["output_tokens"].apply(
            lambda x: f"{x:,}"
        )
        df_display.columns = ["模型", "调用次数", "输入Token", "输出Token", "成本"]
        st.dataframe(df_display, use_container_width=True)

    divider()


def _render_calls_pie(df: pd.DataFrame):
    """渲染调用次数饼图"""
    fig = donut_chart(
        values=df["calls"].tolist(),
        labels=df["model"].tolist(),
        title="",
        height=320,
    )
    if fig:
        st.plotly_chart(fig, use_container_width=True)


def _render_cost_pie(df: pd.DataFrame):
    """渲染成本饼图"""
    fig = donut_chart(
        values=df["cost"].tolist(),
        labels=df["model"].tolist(),
        title="",
        height=320,
    )
    if fig:
        st.plotly_chart(fig, use_container_width=True)


def render_trend_charts(db: Database):
    """渲染趋势图表"""
    st.markdown(
        '<div class="c2r-page-title" style="font-size:1.125rem;font-weight:600;margin-bottom:16px;">成本与Token趋势</div>',
        unsafe_allow_html=True,
    )

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    daily_stats = db.get_api_usage_stats(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    ).get("by_date", [])

    if not daily_stats:
        empty_state(
            title="暂无趋势数据",
            description="积累更多使用数据后，趋势图表将在此展示。",
            icon="📈",
        )
        return

    df = pd.DataFrame(daily_stats)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    dates = df["date"].dt.strftime("%m-%d").tolist()

    col1, col2 = st.columns(2)

    with col1:
        chart_container(
            title="每日成本趋势",
            subtitle="最近 30 天",
            chart_func=lambda: _render_cost_trend(dates, df["cost"].tolist()),
        )

    with col2:
        chart_container(
            title="每日Token消耗趋势",
            subtitle="最近 30 天",
            chart_func=lambda: _render_token_trend(dates, df["total_tokens"].tolist()),
        )

    divider()


def _render_cost_trend(dates, costs):
    """渲染成本趋势图"""
    fig = trend_chart(
        dates=dates,
        values=costs,
        title="",
        series_name="成本 (¥)",
        color="error",
        show_area=True,
        height=300,
    )
    if fig:
        st.plotly_chart(fig, use_container_width=True)


def _render_token_trend(dates, tokens):
    """渲染Token趋势图"""
    fig = trend_chart(
        dates=dates,
        values=tokens,
        title="",
        series_name="Token消耗",
        color="info",
        show_area=True,
        height=300,
    )
    if fig:
        st.plotly_chart(fig, use_container_width=True)


def render_cost_optimization(db: Database):
    """渲染成本优化建议"""
    st.markdown(
        '<div class="c2r-page-title" style="font-size:1.125rem;font-weight:600;margin-bottom:16px;">成本优化建议</div>',
        unsafe_allow_html=True,
    )

    suggestions = db.get_cost_optimization_suggestions()

    if not suggestions:
        callout(
            message="暂无优化建议，您的API使用效率良好！",
            type="success",
            icon="✅",
        )
        return

    for suggestion in suggestions:
        priority = suggestion.get("priority", "low")
        title = suggestion.get("title", "")
        description = suggestion.get("description", "")
        recommendation = suggestion.get("recommendation", "")

        # 根据优先级设置样式
        if priority == "high":
            callout_type = "error"
            icon = "🔴"
            border_color = COLORS["danger"]
        elif priority == "medium":
            callout_type = "warning"
            icon = "🟡"
            border_color = COLORS["warning"]
        else:
            callout_type = "success"
            icon = "🟢"
            border_color = COLORS["success"]

        st.markdown(
            f"""
            <div class="c2r-card c2r-animate-slide-up" style="border-left: 3px solid {border_color}; margin-bottom: 12px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span>{icon}</span>
                    <span style="font-size:0.9375rem;font-weight:600;color:var(--text-primary);">{title}</span>
                    {f'<span class="c2r-badge c2r-badge--{"red" if priority == "high" else "yellow" if priority == "medium" else "green"}">{priority.upper()}</span>'}
                </div>
                <p style="font-size:0.875rem;color:var(--text-secondary);margin-bottom:4px;">
                    <strong style="color:var(--text-primary);">问题描述：</strong>{description}
                </p>
                <p style="font-size:0.875rem;color:var(--text-secondary);">
                    <strong style="color:var(--text-primary);">优化建议：</strong>{recommendation}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    divider()


def render_model_pricing():
    """渲染模型定价参考"""
    st.markdown(
        '<div class="c2r-page-title" style="font-size:1.125rem;font-weight:600;margin-bottom:16px;">模型定价参考</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="c2r-card">', unsafe_allow_html=True)

    pricing_data = []
    for model, config in LLMClient.MODEL_CONFIGS.items():
        pricing_data.append(
            {
                "模型": model,
                "输入价格 (¥/1K tokens)": f"¥{config['cost_per_1k_input']:.4f}",
                "输出价格 (¥/1K tokens)": f"¥{config['cost_per_1k_output']:.4f}",
                "JSON模式": "✅" if config["supports_json_mode"] else "❌",
                "默认Max Tokens": config["max_tokens_default"],
            }
        )

    df = pd.DataFrame(pricing_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    callout(
        message=(
            "**成本计算说明：**\n"
            "- 成本 = (输入Token数 / 1000 × 输入单价) + (输出Token数 / 1000 × 输出单价)\n"
            "- 实际成本可能因模型版本更新而有所变化\n"
            "- 建议定期关注各模型提供商的最新定价"
        ),
        type="info",
        icon="💡",
    )

    st.markdown("</div>", unsafe_allow_html=True)


def render_export_section(db: Database):
    """渲染数据导出区域"""
    st.markdown(
        '<div class="c2r-page-title" style="font-size:1.125rem;font-weight:600;margin-bottom:16px;">数据导出</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="c2r-card">', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.9375rem;font-weight:600;color:var(--text-primary);margin-bottom:16px;">导出成本明细</div>',
            unsafe_allow_html=True,
        )
        start_date = st.date_input(
            "开始日期", value=datetime.now() - timedelta(days=30), key="export_start"
        )
        end_date = st.date_input("结束日期", value=datetime.now(), key="export_end")

        if st.button("导出成本报表", use_container_width=True, key="export_btn"):
            try:
                stats = db.get_api_usage_stats(
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                )

                export_df = pd.DataFrame(stats.get("by_date", []))
                if not export_df.empty:
                    csv = export_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="下载 CSV",
                        data=csv,
                        file_name=f"cost_report_{start_date}_{end_date}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                else:
                    callout("所选时间段内无数据", type="warning", icon="⚠️")
            except Exception as e:
                callout(f"导出失败: {e}", type="error", icon="❌")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="c2r-card">', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.9375rem;font-weight:600;color:var(--text-primary);margin-bottom:16px;">重置统计</div>',
            unsafe_allow_html=True,
        )
        callout(
            message="此操作将清空当前会话的内存统计，但不会删除数据库中的历史记录。",
            type="warning",
            icon="⚠️",
        )
        if st.button("重置会话统计", use_container_width=True, key="reset_btn"):
            if "llm_client" in st.session_state:
                st.session_state.llm_client.reset_usage_stats()
                st.success("会话统计已重置")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_real_time_monitor():
    """渲染实时监控区域"""
    st.markdown(
        '<div class="c2r-page-title" style="font-size:1.125rem;font-weight:600;margin-bottom:16px;">实时监控</div>',
        unsafe_allow_html=True,
    )

    if "orchestrator" in st.session_state and st.session_state.orchestrator:
        llm = st.session_state.orchestrator.llm_client
        summary = llm.get_usage_summary()

        metric_row([
            {
                "title": "当前会话调用",
                "value": str(summary["total_calls"]),
                "icon": "⚡",
                "border_color": COLORS["info"],
            },
            {
                "title": "当前会话Token",
                "value": f"{summary['total_tokens']:,}",
                "icon": "🔢",
                "border_color": COLORS["brand_primary"],
            },
            {
                "title": "当前会话成本",
                "value": f"¥{summary['total_cost']:.4f}",
                "icon": "💵",
                "border_color": COLORS["success"],
            },
            {
                "title": "当前模型",
                "value": summary["model"],
                "icon": "🤖",
                "border_color": COLORS["tag_purple"],
            },
        ])
    else:
        empty_state(
            title="暂无活跃的LLM客户端会话",
            description="开始使用AI功能后，实时监控数据将在此展示。",
            icon="⚡",
        )


# ============================================================
# 主入口函数
# ============================================================

def render_cost_analytics():
    """成本分析页面主入口"""
    # 页面头部
    page_header(
        title="API 成本分析中心",
        subtitle="实时监控 API 调用成本，优化资源使用效率",
    )

    # 初始化数据库
    db = init_database()

    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(
        ["成本概览", "趋势分析", "优化建议", "高级设置"]
    )

    with tab1:
        render_summary_cards(db)
        render_token_stats(db)
        render_model_distribution(db)
        render_real_time_monitor()

    with tab2:
        render_trend_charts(db)

    with tab3:
        render_cost_optimization(db)

    with tab4:
        render_model_pricing()
        render_export_section(db)

    # 页脚
    divider()
    st.markdown(
        f'<div style="text-align:center;font-size:0.8125rem;color:var(--text-tertiary);">'
        f'Content2Revenue AI - 成本分析中心 | 数据更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        f'</div>',
        unsafe_allow_html=True,
    )
