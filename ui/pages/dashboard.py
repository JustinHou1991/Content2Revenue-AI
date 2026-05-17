"""
仪表盘页面 - 全局概览
使用新设计系统组件 (design_system.py + styles.py)

性能优化：
- 使用 @st.cache_data 缓存数据加载结果
- TTL: 60秒（仪表盘数据更新频率）
"""

import streamlit as st

from ui.components.design_system import (
    page_header,
    metric_row,
    metric_card,
    empty_state,
    divider,
    callout,
)
from ui.styles import COLORS
from ui.components.charts import score_gauge, funnel_chart, distribution_chart, trend_chart
from services.sample_data_loader import load_sample_data


@st.cache_data(ttl=60, show_spinner=False)
def _get_cached_dashboard_data(orchestrator) -> dict:
    """缓存的仪表盘数据加载函数（60秒 TTL）"""
    return orchestrator.get_dashboard_data()


def render_trend_section(data: dict):
    """渲染趋势折线图（7天数据分析活动趋势）"""
    trend = data.get("trend", {})
    dates = trend.get("dates", [])
    if not dates:
        return

    has_data = any(
        sum(trend.get(k, [])) > 0
        for k in ["content_counts", "lead_counts", "match_counts"]
    )
    if not has_data:
        return

    st.subheader("7日分析活动趋势")

    fig = trend_chart(
        dates=dates,
        values=trend.get("content_counts", []),
        title="每日分析量",
        series_name="内容分析",
        color="primary",
        height=280,
    )
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    total_7d = sum(trend.get("content_counts", []))
    if total_7d > 0:
        st.caption(f"📝 过去 7 天共分析 {total_7d} 条内容，平均每日 {total_7d // 7} 条")


def render_quick_actions():
    """渲染快速操作区（决策导向设计）"""
    st.markdown("### ⚡ 快速操作")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 新建内容分析", use_container_width=True, type="primary"):
            st.switch_page("pages/2_内容智能分析.py")
    
    with col2:
        if st.button("👤 新建线索分析", use_container_width=True):
            st.switch_page("pages/3_线索智能分析.py")
    
    with col3:
        if st.button("🔗 打开匹配中心", use_container_width=True):
            st.switch_page("pages/4_匹配中心.py")
    
    with col4:
        if st.button("📋 查看策略报告", use_container_width=True):
            st.switch_page("pages/5_策略中心.py")


def render_decision_support(data: dict):
    """渲染决策支持区域（基于学习的最佳实践）
    
    每个指标都应支持特定的决策，而非仅仅展示数字。
    """
    stats = data.get("stats", {})
    if not stats:
        return
    
    content_count = stats.get("content_count", 0)
    lead_count = stats.get("lead_count", 0)
    match_count = stats.get("match_count", 0)
    
    st.markdown("### 🎯 决策支持")
    
    # 根据数据状态提供行动建议
    suggestions = []
    
    if content_count == 0:
        suggestions.append({
            "icon": "📝",
            "title": "开始分析内容",
            "description": "上传您的抖音脚本，AI将提取特征并评分",
            "action": "pages/2_内容智能分析.py",
            "priority": "high"
        })
    
    if lead_count == 0:
        suggestions.append({
            "icon": "👤",
            "title": "录入销售线索",
            "description": "构建客户画像，了解目标受众特征",
            "action": "pages/3_线索智能分析.py",
            "priority": "high"
        })
    
    if content_count > 0 and lead_count > 0 and match_count == 0:
        suggestions.append({
            "icon": "🔗",
            "title": "进行内容-线索匹配",
            "description": "找到最匹配您线索的内容策略",
            "action": "pages/4_匹配中心.py",
            "priority": "high"
        })
    
    if match_count > 0:
        suggestions.append({
            "icon": "💡",
            "title": "生成个性化策略",
            "description": "基于匹配结果，生成针对性的获客策略",
            "action": "pages/5_策略中心.py",
            "priority": "medium"
        })
    
    # 渲染行动建议卡片
    if suggestions:
        for i, suggestion in enumerate(suggestions):
            with st.container():
                col_icon, col_content = st.columns([1, 5])
                with col_icon:
                    st.markdown(f"### {suggestion['icon']}")
                with col_content:
                    st.markdown(f"**{suggestion['title']}**")
                    st.caption(suggestion['description'])
                
                priority_color = {
                    "high": "🔴 高优先级",
                    "medium": "🟡 中优先级",
                    "low": "🟢 低优先级"
                }.get(suggestion['priority'], "")
                
                st.markdown(f"_{priority_color}_")
                
                if i < len(suggestions) - 1:
                    st.markdown("---")


def render_insight_narrative(data: dict):
    """数据叙事：将核心指标转化为可读的业务洞察"""
    stats = data.get("stats", {})
    if not stats:
        return

    parts = []

    content_count = stats.get("content_count", 0)
    lead_count = stats.get("lead_count", 0)
    match_count = stats.get("match_count", 0)
    strategy_count = stats.get("strategy_count", 0)

    if content_count > 0:
        avg_score = data.get("avg_content_score_recent", 0)
        parts.append(f"已分析 {content_count} 条内容，平均评分 {avg_score}/10")

    if lead_count > 0:
        avg_lead = data.get("avg_lead_score_recent", 0)
        parts.append(f"已录入 {lead_count} 条线索，平均质量 {avg_lead}/100")

    if match_count > 0:
        avg_match = data.get("avg_match_score_recent", 0)
        parts.append(f"已完成 {match_count} 次匹配，平均匹配度 {avg_match}/10")

    if strategy_count > 0:
        parts.append(f"已生成 {strategy_count} 份策略报告")

    if parts:
        insight = "💡 " + "；".join(parts) + "。"
        st.info(insight)


def render_score_gauges(data: dict):
    """渲染评分仪表盘"""
    st.subheader("核心评分指标")

    avg_content = data.get("avg_content_score_recent", 0)
    avg_lead = data.get("avg_lead_score_recent", 0)
    avg_match = data.get("avg_match_score_recent", 0)

    col1, col2, col3 = st.columns(3)

    with col1:
        content_val = float(avg_content) if isinstance(avg_content, (int, float)) else 0
        if content_val > 0:
            fig = score_gauge(
                value=content_val,
                max_value=10,
                title="内容评分",
                size=200,
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        lead_val = float(avg_lead) if isinstance(avg_lead, (int, float)) else 0
        if lead_val > 0:
            fig = score_gauge(
                value=lead_val,
                max_value=100,
                title="线索评分",
                size=200,
            )
            st.plotly_chart(fig, use_container_width=True)

    with col3:
        match_val = float(avg_match) if isinstance(avg_match, (int, float)) else 0
        if match_val > 0:
            fig = score_gauge(
                value=match_val,
                max_value=10,
                title="匹配度",
                size=200,
            )
            st.plotly_chart(fig, use_container_width=True)


def render_score_distribution(data: dict):
    """渲染评分分布图"""
    try:
        contents = data.get("recent_contents", [])
        if not contents:
            return

        scores = []
        for item in contents:
            analysis = item.get("analysis_json", {})
            score = analysis.get("content_score", 0)
            try:
                scores.append(float(score))
            except (ValueError, TypeError):
                pass

        if not scores:
            return

        buckets = {"1-2": 0, "3-4": 0, "5-6": 0, "7-8": 0, "9-10": 0}
        for s in scores:
            if s <= 2:
                buckets["1-2"] += 1
            elif s <= 4:
                buckets["3-4"] += 1
            elif s <= 6:
                buckets["5-6"] += 1
            elif s <= 8:
                buckets["7-8"] += 1
            else:
                buckets["9-10"] += 1

        fig = distribution_chart(
            values=list(buckets.values()),
            labels=list(buckets.keys()),
            title="内容评分分布",
            color="primary",
        )
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass


def render_lead_distribution(data: dict):
    """渲染线索等级分布图"""
    try:
        leads = data.get("recent_leads", [])
        if not leads:
            return

        grades = {"A": 0, "B+": 0, "B": 0, "C+": 0, "C": 0, "D": 0}
        for item in leads:
            profile = item.get("profile_json", {})
            grade = profile.get("lead_grade", "")
            if grade in grades:
                grades[grade] += 1

        valid_grades = {k: v for k, v in grades.items() if v > 0}
        if not valid_grades:
            return

        fig = distribution_chart(
            values=list(valid_grades.values()),
            labels=list(valid_grades.keys()),
            title="线索等级分布",
            color="success",
        )
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass


def render_dashboard():
    """渲染仪表盘页面"""
    # 页面头部
    page_header(
        title="数据概览",
        subtitle="实时追踪内容营销与线索转化核心指标",
    )

    is_initialized = st.session_state.get("initialized", False)

    # 未初始化时显示配置提示（但不阻断页面渲染）
    if not is_initialized:
        callout(
            "请先在「系统设置」中配置API Key。配置好API Key后，系统会自动保存配置，刷新页面也不会丢失。",
            type="warning",
            icon="⚠️",
        )

    # 加载业务数据（仅在已初始化时，使用缓存优化）
    data = None
    stats = None
    if is_initialized:
        try:
            # 使用缓存的数据加载函数（60秒 TTL）
            data = _get_cached_dashboard_data(st.session_state.orchestrator)
            stats = data["stats"]
        except Exception as e:
            callout(f"加载失败: {str(e)}", type="error", icon="❌")
            st.info("如果是首次使用，请先在「系统设置」中配置API Key并加载示例数据。")
            stats = None

    # ---- 快速操作区（决策导向设计）----
    if is_initialized:
        render_quick_actions()
        divider()

    # ---- 核心指标卡片（始终渲染） ----
    if stats is not None:
        metric_row([
            {
                "title": "已分析内容",
                "value": str(stats["content_count"]),
                "subtitle": "篇内容",
                "icon": "📝",
                "trend": "up",
                "border_color": COLORS.get("brand_primary", "#6366F1"),
            },
            {
                "title": "已分析线索",
                "value": str(stats["lead_count"]),
                "subtitle": "条线索",
                "icon": "👤",
                "trend": "up",
                "border_color": "#10B981",
            },
            {
                "title": "匹配次数",
                "value": str(stats["match_count"]),
                "subtitle": "次匹配",
                "icon": "🎯",
                "trend": "up",
                "border_color": "#F59E0B",
            },
            {
                "title": "策略报告",
                "value": str(stats["strategy_count"]),
                "subtitle": "份报告",
                "icon": "📈",
                "trend": "up",
                "border_color": "#3B82F6",
            },
        ], key="dashboard_top")
    else:
        # 未初始化 / 加载失败时显示占位卡片
        metric_row([
            {
                "title": "已分析内容",
                "value": "-",
                "subtitle": "篇内容",
                "icon": "📝",
                "trend": "neutral",
                "border_color": COLORS.get("brand_primary", "#6366F1"),
            },
            {
                "title": "已分析线索",
                "value": "-",
                "subtitle": "条线索",
                "icon": "👤",
                "trend": "neutral",
                "border_color": "#10B981",
            },
            {
                "title": "匹配次数",
                "value": "-",
                "subtitle": "次匹配",
                "icon": "🎯",
                "trend": "neutral",
                "border_color": "#F59E0B",
            },
            {
                "title": "策略报告",
                "value": "-",
                "subtitle": "份报告",
                "icon": "📈",
                "trend": "neutral",
                "border_color": "#3B82F6",
            },
        ], key="dashboard_top_empty")

    # 空状态引导（仅未初始化时显示配置提示）
    if not is_initialized or stats is None:
        divider()

        if st.button(
            "前往系统设置",
            type="primary",
            use_container_width=True,
            key="dashboard_goto_settings",
        ):
            st.session_state.nav_target = "settings"
            st.rerun()

        st.info("请在「系统设置」中配置 API Key 后开始使用。")
        return

    # 已初始化但暂无数据 — 显示引导
    if all(v == 0 for v in stats.values()):
        divider()

        st.info("🎉 系统已就绪！前往「内容分析」或「线索分析」开始你的第一个分析任务。")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📝 分析新内容", use_container_width=True, type="primary", key="dashboard_empty_goto_content"):
                st.session_state.nav_target = "content"
                st.rerun()
        with col2:
            if st.button("👤 录入新线索", use_container_width=True, type="primary", key="dashboard_empty_goto_lead"):
                st.session_state.nav_target = "lead"
                st.rerun()
        with col3:
            if st.button("🚀 加载示例数据", use_container_width=True, type="primary", key="dashboard_load_samples"):
                load_sample_data()
        return

    divider()

    # 评分仪表盘（可视化环形进度条）
    render_score_gauges(data)

    divider()

    # 数据叙事
    render_insight_narrative(data)

    # 决策支持（基于学习的最佳实践）
    render_decision_support(data)

    # 7日趋势图
    render_trend_section(data)

    divider()

    # 快速操作
    st.subheader("快速操作")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("分析新脚本", use_container_width=True, type="primary", key="dashboard_quick_content"):
            st.session_state.nav_target = "content"
            st.rerun()
    with col2:
        if st.button("录入新线索", use_container_width=True, type="primary", key="dashboard_quick_lead"):
            st.session_state.nav_target = "lead"
            st.rerun()

    divider()

    # 最近记录
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("最近分析的内容")
        if data["recent_contents"]:
            for item in data["recent_contents"]:
                analysis = item.get("analysis_json", {})
                score = analysis.get("content_score", "N/A")
                hook_type = analysis.get("hook_type", "未知")
                raw_text = item.get("raw_text", "")[:50] + "..."

                with st.expander(f"评分 {score}/10 | {hook_type}"):
                    st.write(raw_text)
                    st.caption(f"ID: {item['id'][:8]}... | {item['created_at'][:10]}")
        else:
            st.info("暂无内容分析记录，去「内容分析」页面开始吧！")

    with col2:
        st.subheader("最近分析的线索")
        if data["recent_leads"]:
            for item in data["recent_leads"]:
                profile = item.get("profile_json", {})
                score = profile.get("lead_score", "N/A")
                grade = profile.get("lead_grade", "N/A")
                industry = profile.get("industry", "未知")
                raw = item.get("raw_data_json", {})
                company = raw.get("company", raw.get("公司名称", "未知"))

                with st.expander(f"评分 {score}/100 ({grade}) | {industry}"):
                    st.write(f"公司: {company}")
                    st.caption(f"ID: {item['id'][:8]}... | {item['created_at'][:10]}")
        else:
            st.info("暂无线索分析记录，去「线索分析」页面开始吧！")
