"""
Content2Revenue AI - UI 组件库
设计语言参考: Linear + Databox + Anthropic

所有组件均基于 Streamlit 原生元素构建，
通过 HTML/CSS 注入实现精致的视觉设计。
"""

import streamlit as st
from typing import Optional, Callable, List, Dict, Any


def _html(html: str) -> None:
    """安全渲染 HTML 字符串。

    Streamlit 的 st.markdown 使用 CommonMarkdown 解析器，会将 4 空格缩进的行
    当作代码块。本函数将 HTML 中的换行和多余空白压缩为单行，彻底避免此问题。
    """
    import re
    # 将所有连续空白（含换行、制表符）压缩为单个空格
    collapsed = re.sub(r'\s+', ' ', html).strip()
    st.markdown(collapsed, unsafe_allow_html=True)


# ============================================================
# 指标卡片组件 (Databox 风格)
# ============================================================
def metric_card(
    title: str,
    value: str,
    subtitle: str = "",
    delta: str = "",
    icon: str = "",
    trend: str = "up",
    border_color: Optional[str] = None,
    key: Optional[str] = None,
) -> None:
    """
    Databox 风格的 KPI 指标卡片。

    参数:
        title:       指标名称 (如 "总收入")
        value:       指标值 (如 "$12,345")
        subtitle:    补充说明文字
        delta:       变化值 (如 "+12.5%")
        icon:        图标 emoji 或 HTML
        trend:       趋势方向 "up" | "down" | "neutral"
        border_color: 自定义顶部边框颜色 (CSS 色值)
        key:         Streamlit 唯一键

    使用示例:
        metric_card(
            title="月度收入",
            value="$48,250",
            delta="+12.5%",
            trend="up",
            icon="💰"
        )
    """
    border_style = ""
    if border_color:
        border_style = f"border-top: 2px solid {border_color};"

    # 趋势样式
    if trend == "up" and delta:
        delta_class = "c2r-metric-delta--up"
        arrow = "&#9650;"  # 上箭头
    elif trend == "down" and delta:
        delta_class = "c2r-metric-delta--down"
        arrow = "&#9660;"  # 下箭头
    else:
        delta_class = ""
        arrow = ""

    # 构建图标 HTML
    icon_html = ""
    if icon:
        icon_html = f"""
        <div style="
            width: 40px; height: 40px;
            display: flex; align-items: center; justify-content: center;
            background: var(--brand-primary-muted);
            border-radius: var(--radius-md);
            font-size: 1.25rem;
            margin-bottom: 12px;
        ">{icon}</div>
        """

    # 构建 delta HTML
    delta_html = ""
    if delta:
        delta_html = f"""
        <span class="c2r-metric-delta {delta_class}">
            {arrow} {delta}
        </span>
        """

    # 构建 subtitle HTML
    subtitle_html = ""
    if subtitle:
        subtitle_html = f"""
        <div style="
            font-size: 0.8125rem;
            color: var(--text-tertiary);
            margin-top: 8px;
            line-height: 1.4;
        ">{subtitle}</div>
        """

    html = f"""
    <div class="c2r-metric-card c2r-animate-slide-up" style="{border_style}">
        {icon_html}
        <div class="c2r-metric-title">{title}</div>
        <div style="display: flex; align-items: baseline; gap: 12px;">
            <div class="c2r-metric-value">{value}</div>
            {delta_html}
        </div>
        {subtitle_html}
    </div>
    """

    _html(html)


# ============================================================
# 数据卡片组件 (Linear 风格)
# ============================================================
def data_card(
    title: str,
    content: str,
    icon: str = "",
    actions: Optional[List[Dict[str, str]]] = None,
    border_color: Optional[str] = None,
    footer: str = "",
    key: Optional[str] = None,
) -> None:
    """
    Linear 风格的数据卡片，包含标题行、内容区域和可选底部栏。

    参数:
        title:        卡片标题
        content:      卡片内容 (支持 HTML)
        icon:         标题前的图标
        actions:      操作按钮列表 [{"label": "...", "onclick": "..."}]
        border_color: 左侧边框颜色
        footer:       底部栏文字
        key:          Streamlit 唯一键

    使用示例:
        data_card(
            title="内容质量评分",
            content="<div style='font-size:2rem;font-weight:700'>87/100</div>",
            icon="📊",
            actions=[{"label": "查看详情", "onclick": "..."}]
        )
    """
    border_style = ""
    if border_color:
        border_style = f"border-left: 3px solid {border_color};"

    # 图标
    icon_html = ""
    if icon:
        icon_html = f'<span style="margin-right: 8px;">{icon}</span>'

    # 操作按钮
    actions_html = ""
    if actions:
        btns = []
        for action in actions:
            label = action.get("label", "")
            btns.append(
                f'<button class="c2r-btn-ghost" onclick="{action.get("onclick", "")}" '
                f'style="font-size:0.8125rem;padding:6px 12px;">{label}</button>'
            )
        actions_html = f'<div style="display:flex;gap:4px;">{"".join(btns)}</div>'

    # 底部栏
    footer_html = ""
    if footer:
        footer_html = f"""
        <div class="c2r-data-card-footer">
            <span style="font-size:0.8125rem;color:var(--text-tertiary);">{footer}</span>
        </div>
        """

    html = f"""
    <div class="c2r-data-card c2r-animate-scale-in" style="{border_style}">
        <div class="c2r-data-card-header">
            <div class="c2r-data-card-title">
                {icon_html}{title}
            </div>
            {actions_html}
        </div>
        <div class="c2r-data-card-body">
            {content}
        </div>
        {footer_html}
    </div>
    """

    _html(html)


# ============================================================
# 状态徽章组件
# ============================================================
def status_badge(
    text: str,
    color: str = "blue",
    size: str = "sm",
    pulse: bool = False,
    key: Optional[str] = None,
) -> None:
    """
    精致的状态徽章，低饱和度背景色 + 药丸形状。

    参数:
        text:  徽章文字
        color: 颜色 "blue" | "green" | "yellow" | "red" | "purple" | "gray"
        size:  尺寸 "sm" | "md" | "lg"
        pulse: 是否显示脉冲动画点
        key:   Streamlit 唯一键

    使用示例:
        status_badge("已发布", color="green")
        status_badge("处理中", color="yellow", pulse=True)
    """
    size_class = ""
    if size == "lg":
        size_class = "c2r-badge--lg"
    elif size == "sm":
        size_class = "c2r-badge--sm"

    pulse_class = "c2r-badge--pulse" if pulse else ""

    # 脉冲点
    dot_html = ""
    if pulse:
        dot_html = '<span class="c2r-badge-dot"></span>'

    html = f"""
    <span class="c2r-badge c2r-badge--{color} {size_class} {pulse_class}">
        {dot_html}{text}
    </span>
    """

    _html(html)


# ============================================================
# 空状态组件
# ============================================================
def empty_state(
    title: str,
    description: str,
    icon: str = "",
    action_label: str = "",
    action_callback: Optional[Callable] = None,
    key: Optional[str] = None,
) -> None:
    """
    友好的空状态提示组件。

    参数:
        title:           标题文字
        description:     描述文字
        icon:            图标 (emoji 或 SVG)
        action_label:    操作按钮文字
        action_callback: 点击回调 (Streamlit 按钮)
        key:             Streamlit 唯一键

    使用示例:
        empty_state(
            title="暂无内容",
            description="开始创建你的第一篇内容，AI 将帮你优化变现策略。",
            icon="📝",
            action_label="创建内容",
            action_callback=lambda: st.session_state.page = "create"
        )
    """
    icon_display = icon if icon else "&#9744;"

    html = f"""
    <div class="c2r-empty-state c2r-animate-fade-in">
        <div class="c2r-empty-state-icon">{icon_display}</div>
        <div class="c2r-empty-state-title">{title}</div>
        <div class="c2r-empty-state-desc">{description}</div>
    </div>
    """

    _html(html)

    if action_label:
        if action_callback:
            clicked = st.button(
                action_label,
                key=f"empty_state_btn_{key}" if key else None,
                use_container_width=False,
            )
            if clicked:
                action_callback()
        else:
            st.button(
                action_label,
                key=f"empty_state_btn_{key}" if key else None,
                use_container_width=False,
            )


# ============================================================
# 页面头部组件
# ============================================================
def page_header(
    title: str,
    subtitle: str = "",
    actions: Optional[List[Dict[str, str]]] = None,
    key: Optional[str] = None,
) -> None:
    """
    统一的页面头部，包含标题、副标题和操作按钮区域。

    参数:
        title:    页面标题
        subtitle: 副标题/描述
        actions:  操作按钮列表 [{"label": "...", "type": "primary|secondary|ghost"}]
        key:      Streamlit 唯一键

    使用示例:
        page_header(
            title="内容仪表盘",
            subtitle="监控你的内容表现和变现数据",
            actions=[
                {"label": "新建内容", "type": "primary"},
                {"label": "导出报告", "type": "secondary"},
            ]
        )
    """
    # 操作按钮
    actions_html = ""
    if actions:
        btns = []
        for action in actions:
            label = action.get("label", "")
            btn_type = action.get("type", "secondary")
            btn_class = f"c2r-btn-{btn_type}"
            btns.append(
                f'<button class="{btn_class}">{label}</button>'
            )
        actions_html = f"""
        <div class="c2r-page-actions">
            {"".join(btns)}
        </div>
        """

    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="c2r-page-subtitle">{subtitle}</div>'

    html = f"""
    <div class="c2r-page-header c2r-animate-fade-in">
        <div class="c2r-page-header-info">
            <h1 class="c2r-page-title">{title}</h1>
            {subtitle_html}
        </div>
        {actions_html}
    </div>
    """

    _html(html)


# ============================================================
# 标签页组件
# ============================================================
def tabs(
    options: List[str],
    default: Optional[str] = None,
    key: Optional[str] = None,
) -> str:
    """
    自定义标签页组件，替代 st.tabs，支持底部指示线动画。

    参数:
        options: 选项列表
        default: 默认选中项
        key:     Streamlit 唯一键

    返回:
        当前选中的标签名

    使用示例:
        selected = tabs(["概览", "分析", "设置"], default="概览")
        if selected == "概览":
            st.write("概览页面")
    """
    if not options:
        return ""

    _key = f"tabs_{key}" if key else "tabs_default"
    if _key not in st.session_state:
        st.session_state[_key] = default if default else options[0]

    # 构建标签 HTML
    tabs_html = '<div class="c2r-tabs">'
    for option in options:
        is_active = st.session_state[_key] == option
        active_class = "c2r-tab--active" if is_active else ""
        tabs_html += f"""
        <button class="c2r-tab {active_class}"
                onclick="document.querySelectorAll('.c2r-tab').forEach(t => t.classList.remove('c2r-tab--active')); this.classList.add('c2r-tab--active');"
                data-tab="{option}">
            {option}
        </button>
        """
    tabs_html += '</div>'

    st.markdown(tabs_html, unsafe_allow_html=True)

    # 使用 Streamlit 的 columns 来实现点击切换
    cols = st.columns(len(options))
    for i, option in enumerate(options):
        with cols[i]:
            if st.button(
                option,
                key=f"{_key}_{option}",
                use_container_width=True,
                disabled=(st.session_state[_key] == option),
            ):
                st.session_state[_key] = option
                st.rerun()

    return st.session_state[_key]


# ============================================================
# 进度指示器组件
# ============================================================
def progress_indicator(
    label: str,
    value: float,
    max_value: float = 100,
    color: str = "blue",
    show_percentage: bool = True,
    key: Optional[str] = None,
) -> None:
    """
    进度条组件，支持颜色渐变和百分比显示。

    参数:
        label:           标签文字
        value:           当前值
        max_value:       最大值
        color:           颜色 "blue" | "green" | "yellow" | "red" | "purple"
        show_percentage: 是否显示百分比
        key:             Streamlit 唯一键

    使用示例:
        progress_indicator("SEO 优化度", 78, color="green")
        progress_indicator("内容完成度", 45, max_value=50, color="purple")
    """
    percentage = min((value / max_value) * 100, 100) if max_value > 0 else 0
    display_value = f"{percentage:.0f}%" if show_percentage else f"{value}/{max_value}"

    html = f"""
    <div class="c2r-progress-wrapper c2r-animate-slide-up">
        <div class="c2r-progress-label">
            <span class="c2r-progress-label-text">{label}</span>
            <span class="c2r-progress-label-value">{display_value}</span>
        </div>
        <div class="c2r-progress-track">
            <div class="c2r-progress-fill c2r-progress-fill--{color}"
                 style="width: {percentage}%"></div>
        </div>
    </div>
    """

    _html(html)


# ============================================================
# 指标卡片行组件
# ============================================================
def metric_row(
    metrics: List[Dict[str, Any]],
    columns: int = 4,
    key: Optional[str] = None,
) -> None:
    """
    一行排列多个指标卡片。

    参数:
        metrics: 指标列表，每个元素为 metric_card 的参数字典
        columns: 列数 (1-4)
        key:     Streamlit 唯一键

    使用示例:
        metric_row([
            {"title": "总收入", "value": "$48,250", "delta": "+12.5%", "trend": "up", "icon": "💰"},
            {"title": "内容数", "value": "156", "delta": "+8", "trend": "up", "icon": "📝"},
            {"title": "转化率", "value": "3.2%", "delta": "-0.3%", "trend": "down", "icon": "📊"},
            {"title": "订阅者", "value": "2,847", "delta": "+156", "trend": "up", "icon": "👥"},
        ])
    """
    cols = st.columns(columns)
    for i, m in enumerate(metrics):
        with cols[i % columns]:
            metric_card(
                title=m.get("title", ""),
                value=m.get("value", ""),
                subtitle=m.get("subtitle", ""),
                delta=m.get("delta", ""),
                icon=m.get("icon", ""),
                trend=m.get("trend", "up"),
                border_color=m.get("border_color"),
                key=f"{key}_{i}" if key else f"metric_row_{i}",
            )


# ============================================================
# 分隔线组件
# ============================================================
def divider(thick: bool = False, margin: bool = True) -> None:
    """
    分隔线组件。

    参数:
        thick:  是否使用加粗分隔线
        margin: 是否添加上下间距
    """
    cls = "c2r-divider--thick" if thick else "c2r-divider"
    style = f"margin: 24px 0;" if margin else ""
    st.markdown(f'<div class="{cls}" style="{style}"></div>', unsafe_allow_html=True)


# ============================================================
# 提示框组件
# ============================================================
def callout(
    message: str,
    type: str = "info",
    icon: str = "",
    key: Optional[str] = None,
) -> None:
    """
    提示框组件，用于展示重要信息。

    参数:
        message: 提示消息
        type:    类型 "info" | "success" | "warning" | "error"
        icon:    自定义图标
        key:     Streamlit 唯一键

    使用示例:
        callout("内容已保存成功", type="success", icon="✅")
        callout("请先配置 API 密钥", type="warning", icon="⚠️")
    """
    color_map = {
        "info": ("var(--color-info-muted)", "var(--color-info)"),
        "success": ("var(--color-success-muted)", "var(--color-success)"),
        "warning": ("var(--color-warning-muted)", "var(--color-warning)"),
        "error": ("var(--color-error-muted)", "var(--color-error)"),
    }

    bg_color, text_color = color_map.get(type, color_map["info"])

    default_icons = {
        "info": "&#8505;",
        "success": "&#10003;",
        "warning": "&#9888;",
        "error": "&#10007;",
    }

    display_icon = icon if icon else default_icons.get(type, "")

    html = f"""
    <div style="
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 16px;
        background: {bg_color};
        border: 1px solid {text_color};
        border-radius: var(--radius-lg);
        border-opacity: 0.3;
    ">
        <span style="font-size: 1.125rem; flex-shrink: 0; color: {text_color};">{display_icon}</span>
        <span style="font-size: 0.875rem; color: var(--text-primary); line-height: 1.5;">{message}</span>
    </div>
    """

    _html(html)


# ============================================================
# 侧边栏 Logo 组件
# ============================================================
def sidebar_logo(
    name: str = "Content2Revenue",
    subtitle: str = "AI",
    icon: str = "&#9670;",
) -> None:
    """
    侧边栏 Logo 展示组件。

    参数:
        name:    产品名称
        subtitle: 副标题
        icon:    Logo 图标
    """
    html = f"""
    <div class="c2r-sidebar-logo">
        <span style="font-size: 1.5rem; color: var(--brand-primary);">{icon}</span>
        <div>
            <div class="c2r-sidebar-logo-text">{name}</div>
            <div class="c2r-sidebar-logo-sub">{subtitle}</div>
        </div>
    </div>
    """
    _html(html)


# ============================================================
# 侧边栏导航组件
# ============================================================
def sidebar_nav(
    items: List[Dict[str, str]],
    active_key: Optional[str] = None,
    key: Optional[str] = None,
) -> Optional[str]:
    """
    侧边栏导航菜单组件。

    参数:
        items:      导航项列表 [{"label": "...", "icon": "...", "key": "..."}]
        active_key: 当前激活的导航项 key
        key:        Streamlit 唯一键

    返回:
        被点击的导航项 key

    使用示例:
        clicked = sidebar_nav([
            {"label": "仪表盘", "icon": "📊", "key": "dashboard"},
            {"label": "内容管理", "icon": "📝", "key": "content"},
            {"label": "数据分析", "icon": "📈", "key": "analytics"},
        ], active_key="dashboard")
    """
    clicked_key = None

    for item in items:
        is_active = active_key == item.get("key")
        active_class = "c2r-nav-item--active" if is_active else ""

        html = f"""
        <div class="c2r-nav-item {active_class}">
            <span>{item.get("icon", "")}</span>
            <span>{item.get("label", "")}</span>
        </div>
        """

        col1, col2 = st.columns([1, 4])
        with col1:
            _html(html)
        with col2:
            if st.button(
                item.get("label", ""),
                key=f"nav_{item.get('key', '')}_{key}",
                use_container_width=True,
            ):
                clicked_key = item.get("key")

    return clicked_key


# ============================================================
# 图表容器组件
# ============================================================
def chart_container(
    title: str,
    subtitle: str = "",
    chart_func: Optional[Callable] = None,
    key: Optional[str] = None,
) -> None:
    """
    图表容器组件，提供统一的图表外框样式。

    参数:
        title:      图表标题
        subtitle:   图表副标题
        chart_func: 渲染图表的回调函数
        key:        Streamlit 唯一键

    使用示例:
        chart_container(
            title="收入趋势",
            subtitle="最近 7 天",
            chart_func=lambda: st.line_chart(data)
        )
    """
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="c2r-chart-subtitle">{subtitle}</div>'

    html = f"""
    <div class="c2r-chart-container c2r-animate-scale-in">
        <div class="c2r-chart-header">
            <div>
                <div class="c2r-chart-title">{title}</div>
                {subtitle_html}
            </div>
        </div>
    </div>
    """

    _html(html)

    if chart_func:
        chart_func()


# ============================================================
# 骨架屏加载组件
# ============================================================
def skeleton_loader(
    rows: int = 3,
    type: str = "card",
    key: Optional[str] = None,
) -> None:
    """
    骨架屏加载占位组件。

    参数:
        rows: 行数
        type: 类型 "card" | "text" | "table"
        key:  Streamlit 唯一键

    使用示例:
        if loading:
            skeleton_loader(rows=4, type="card")
        else:
            # 渲染真实内容
    """
    if type == "card":
        for _ in range(rows):
            html = """
            <div style="margin-bottom: 16px;">
                <div class="c2r-skeleton c2r-skeleton--title"></div>
                <div class="c2r-skeleton c2r-skeleton--text"></div>
                <div class="c2r-skeleton c2r-skeleton--text" style="width: 80%;"></div>
            </div>
            """
            _html(html)

    elif type == "text":
        for _ in range(rows):
            html = '<div class="c2r-skeleton c2r-skeleton--text"></div>'
            _html(html)

    elif type == "table":
        # 表头
        header_html = """
        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px;">
            <div class="c2r-skeleton c2r-skeleton--text"></div>
            <div class="c2r-skeleton c2r-skeleton--text"></div>
            <div class="c2r-skeleton c2r-skeleton--text"></div>
            <div class="c2r-skeleton c2r-skeleton--text"></div>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
        for _ in range(rows):
            row_html = """
            <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 16px; margin-bottom: 8px;">
                <div class="c2r-skeleton c2r-skeleton--text"></div>
                <div class="c2r-skeleton c2r-skeleton--text"></div>
                <div class="c2r-skeleton c2r-skeleton--text"></div>
                <div class="c2r-skeleton c2r-skeleton--text"></div>
            </div>
            """
            st.markdown(row_html, unsafe_allow_html=True)


# ============================================================
# 统计摘要组件
# ============================================================
def stat_row(
    items: List[Dict[str, str]],
    key: Optional[str] = None,
) -> None:
    """
    紧凑的统计摘要行，用于在卡片内展示多个关键指标。

    参数:
        items: 统计项列表 [{"label": "...", "value": "..."}]
        key:   Streamlit 唯一键

    使用示例:
        stat_row([
            {"label": "平均阅读", "value": "2.4 min"},
            {"label": "分享率", "value": "12.3%"},
            {"label": "收藏数", "value": "89"},
        ])
    """
    items_html = ""
    for item in items:
        items_html += f"""
        <div style="text-align: center; flex: 1;">
            <div style="
                font-size: 1.125rem;
                font-weight: 700;
                color: var(--text-primary);
                font-variant-numeric: tabular-nums;
            ">{item.get('value', '')}</div>
            <div style="
                font-size: 0.75rem;
                color: var(--text-tertiary);
                margin-top: 2px;
            ">{item.get('label', '')}</div>
        </div>
        """

    html = f"""
    <div style="
        display: flex;
        align-items: center;
        padding: 16px 0;
        border-top: 1px solid var(--border-subtle);
        border-bottom: 1px solid var(--border-subtle);
    ">
        {items_html}
    </div>
    """

    _html(html)
