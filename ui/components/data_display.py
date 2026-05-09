"""数据展示组件 - 统一的结果展示"""
import streamlit as st
from typing import Dict, Any, List, Optional, Callable


def render_score_badge(
    score: float,
    max_score: float = 100,
    label: str = "评分",
    size: str = "md"
) -> None:
    """渲染评分徽章

    Args:
        score: 分数值
        max_score: 最高分
        label: 标签文本
        size: 尺寸 (sm, md, lg)
    """
    percentage = (score / max_score) * 100 if max_score > 0 else 0

    if percentage >= 80:
        color_class = "green"
        color_hex = "#10B981"
    elif percentage >= 60:
        color_class = "yellow"
        color_hex = "#F59E0B"
    else:
        color_class = "red"
        color_hex = "#EF4444"

    font_size = {"sm": "0.75rem", "md": "0.875rem", "lg": "1rem"}.get(size, "0.875rem")

    st.markdown(f"""
    <div style="
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        background: {color_hex}20;
        border: 1px solid {color_hex};
        color: {color_hex};
        font-size: {font_size};
        font-weight: 600;
    ">
        {label}: {score:.1f}/{max_score}
    </div>
    """, unsafe_allow_html=True)


def render_dimension_grid(
    dimensions: Dict[str, Any],
    columns: int = 3,
    title: Optional[str] = None
) -> None:
    """渲染维度网格

    Args:
        dimensions: 维度数据字典
        columns: 列数
        title: 网格标题
    """
    if title:
        st.markdown(f"#### {title}")

    items = list(dimensions.items())
    rows = [items[i:i+columns] for i in range(0, len(items), columns)]

    for row in rows:
        cols = st.columns(columns)
        for idx, (key, value) in enumerate(row):
            with cols[idx]:
                st.markdown(f"""
                <div style="
                    background: var(--bg-card, #1a1a1a);
                    border: 1px solid var(--border-subtle, #2a2a2a);
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 8px;
                ">
                    <div style="
                        font-size: 0.75rem;
                        color: var(--text-secondary, #888);
                        margin-bottom: 4px;
                    ">{key}</div>
                    <div style="
                        font-size: 1rem;
                        font-weight: 600;
                        color: var(--text-primary, #fff);
                    ">{value}</div>
                </div>
                """, unsafe_allow_html=True)


def render_analysis_result(
    result: Dict[str, Any],
    title: str = "分析结果",
    expanded: bool = True
) -> None:
    """渲染分析结果卡片

    Args:
        result: 分析结果字典
        title: 卡片标题
        expanded: 是否默认展开
    """
    with st.expander(title, expanded=expanded):
        for key, value in result.items():
            if isinstance(value, list):
                st.markdown(f"**{key}:**")
                for item in value:
                    st.markdown(f"- {item}")
            elif isinstance(value, dict):
                st.markdown(f"**{key}:**")
                for k, v in value.items():
                    st.markdown(f"  - {k}: {v}")
            else:
                st.markdown(f"**{key}:** {value}")


def render_metric_group(
    metrics: List[Dict[str, Any]],
    columns: int = 3
) -> None:
    """渲染指标组

    Args:
        metrics: 指标列表，每个指标包含title, value, subtitle等
        columns: 列数
    """
    from ui.components.design_system import metric_card

    cols = st.columns(columns)
    for idx, metric in enumerate(metrics):
        with cols[idx % columns]:
            metric_card(
                title=metric.get("title", ""),
                value=metric.get("value", ""),
                subtitle=metric.get("subtitle", ""),
                icon=metric.get("icon"),
                border_color=metric.get("border_color"),
            )


def render_list_section(
    title: str,
    items: List[str],
    icon: str = "-",
    empty_message: str = "暂无数据"
) -> None:
    """渲染列表区块

    Args:
        title: 标题
        items: 列表项
        icon: 列表项图标
        empty_message: 空列表提示
    """
    st.markdown(f"#### {title}")

    if not items:
        st.write(empty_message)
        return

    for item in items:
        st.markdown(f"{icon} {item}")


def render_two_column_info(
    left_items: Dict[str, Any],
    right_items: Dict[str, Any],
    left_title: Optional[str] = None,
    right_title: Optional[str] = None
) -> None:
    """渲染两列信息展示

    Args:
        left_items: 左侧项目
        right_items: 右侧项目
        left_title: 左侧标题
        right_title: 右侧标题
    """
    col1, col2 = st.columns(2)

    with col1:
        if left_title:
            st.markdown(f"#### {left_title}")
        for key, value in left_items.items():
            if isinstance(value, list):
                st.markdown(f"**{key}:**")
                for item in value:
                    st.write(f"- {item}")
            else:
                st.write(f"**{key}:** {value}")

    with col2:
        if right_title:
            st.markdown(f"#### {right_title}")
        for key, value in right_items.items():
            if isinstance(value, list):
                st.markdown(f"**{key}:**")
                for item in value:
                    st.write(f"- {item}")
            else:
                st.write(f"**{key}:** {value}")


def render_content_analysis_details(analysis: Dict[str, Any]) -> None:
    """渲染内容分析详情

    Args:
        analysis: 分析结果字典
    """
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Hook分析")
        st.write(f"**类型**: {analysis.get('hook_type', '未知')}")
        st.write(f"**关键词**: {', '.join(analysis.get('hook_keywords', []))}")

        st.markdown("#### 叙事结构")
        st.write(f"**结构**: {analysis.get('narrative_structure', '未知')}")
        st.write(f"**内容类型**: {analysis.get('content_category', '未知')}")
        st.write(f"**转化阶段**: {analysis.get('estimated_conversion_stage', '未知')}")

    with col2:
        st.markdown("#### 情感分析")
        st.write(f"**基调**: {analysis.get('emotion_tone', '未知')}")
        if analysis.get("emotion_curve"):
            for stage in analysis["emotion_curve"]:
                st.write(f"  - {stage}")

        st.markdown("#### CTA分析")
        st.write(f"**类型**: {analysis.get('cta_type', '未知')}")


def render_lead_profile_details(profile: Dict[str, Any]) -> None:
    """渲染线索画像详情

    Args:
        profile: 画像数据字典
    """
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 基础画像")
        st.write(f"**行业**: {profile.get('industry', '未知')}")
        st.write(f"**公司阶段**: {profile.get('company_stage', '未知')}")
        st.write(f"**决策角色**: {profile.get('role', '未知')}")
        st.write(f"**购买阶段**: {profile.get('buying_stage', '未知')}")
        st.write(f"**紧迫程度**: {profile.get('urgency', '未知')}")
        st.write(f"**预算准备**: {profile.get('budget_readiness', '未知')}")

    with col2:
        st.markdown("#### 核心痛点")
        for pain in profile.get("pain_points", []):
            st.write(f"- {pain}")

        st.markdown("#### 意向信号")
        for signal in profile.get("intent_signals", []):
            st.write(f"- {signal}")


def render_match_result_details(match_result: Dict[str, Any]) -> None:
    """渲染匹配结果详情

    Args:
        match_result: 匹配结果字典
    """
    mr = match_result.get("match_result", {})

    # 总分
    col1, col2 = st.columns([1, 3])
    with col1:
        score = mr.get("overall_score", 0)
        color = "#10B981" if score >= 7 else "#F59E0B" if score >= 5 else "#EF4444"
        from ui.components.design_system import metric_card
        metric_card(
            title="综合匹配度",
            value=f"{score}/10",
            subtitle="强匹配" if score >= 7 else "中等匹配" if score >= 5 else "弱匹配",
            icon="&#127919;",
            border_color=color,
        )

    with col2:
        st.write(f"**匹配理由**: {mr.get('match_reason', '')}")

    # 维度评分
    st.markdown("#### 维度评分")
    ds = mr.get("dimension_scores", {})
    cols = st.columns(5)
    dims = [
        ("受众匹配", "audience_fit"),
        ("痛点相关", "pain_point_relevance"),
        ("阶段对齐", "stage_alignment"),
        ("CTA适当", "cta_appropriateness"),
        ("情感共鸣", "emotion_resonance"),
    ]
    from ui.components.design_system import metric_card
    for col, (label, key) in zip(cols, dims):
        with col:
            val = ds.get(key, 0)
            color = "#10B981" if val >= 7 else "#F59E0B" if val >= 5 else "#EF4444"
            metric_card(
                title=label,
                value=f"{val}/10",
                border_color=color,
            )

    # 风险和建议
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 风险因素")
        for risk in mr.get("risk_factors", []):
            st.write(f"- {risk}")

    with col2:
        st.markdown("#### 跟进建议")
        st.info(mr.get("recommended_follow_up", "暂无建议"))


def render_strategy_content(strategy: Dict[str, Any]) -> None:
    """渲染策略内容

    Args:
        strategy: 策略数据字典
    """
    # 内容策略
    cs = strategy.get("content_strategy", {})
    st.markdown("#### 内容策略")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**推荐Hook:**")
        hook = cs.get("recommended_hook", "")
        st.code(hook, language=None)

        st.markdown(f"**理由:** {cs.get('hook_rationale', '')}")
        st.markdown(f"**推荐结构:** {cs.get('recommended_structure', '')}")

    with col2:
        st.markdown("**核心话术要点:**")
        for point in cs.get("talking_points", []):
            st.write(f"- {point}")

        st.markdown(f"**语气指导:** {cs.get('tone_guidance', '')}")

    # 分发策略
    ds = strategy.get("distribution_strategy", {})
    st.markdown("#### 分发策略")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**最佳时间:** {ds.get('best_timing', '未知')}")
        st.write(f"**渠道建议:** {ds.get('channel_suggestion', '未知')}")

    with col2:
        st.markdown("**跟进节奏:**")
        for step in ds.get("follow_up_sequence", []):
            st.write(f"- {step}")

    # 转化预测
    cp = strategy.get("conversion_prediction", {})
    st.markdown("#### 转化预测")

    from ui.components.design_system import metric_card
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card(
            title="预估转化率",
            value=cp.get("estimated_conversion_rate", "未知"),
            icon="&#128200;",
            border_color="#10B981",
        )
    with col2:
        metric_card(
            title="置信度",
            value=cp.get("confidence_level", "未知"),
            icon="&#128170;",
            border_color="#6366F1",
        )
    with col3:
        metric_card(
            title="建议样本量",
            value=cp.get("recommended_sample_size", "未知"),
            icon="&#128202;",
            border_color="#F59E0B",
        )


def render_history_list(
    records: List[Dict[str, Any]],
    title_key: str,
    expander_title_func: Callable[[Dict[str, Any]], str],
    content_func: Callable[[Dict[str, Any]], None],
    empty_title: str = "暂无记录",
    empty_description: str = "开始分析后将显示历史记录",
    empty_icon: str = "&#128218;"
) -> None:
    """渲染历史记录列表

    Args:
        records: 记录列表
        title_key: 标题键
        expander_title_func: 生成expander标题的函数
        content_func: 渲染内容的函数
        empty_title: 空状态标题
        empty_description: 空状态描述
        empty_icon: 空状态图标
    """
    if not records:
        from ui.components.design_system import empty_state
        empty_state(
            title=empty_title,
            description=empty_description,
            icon=empty_icon,
        )
        return

    for record in records:
        with st.expander(expander_title_func(record)):
            content_func(record)


def render_tags(
    tags: List[str],
    color: str = "purple",
    size: str = "sm"
) -> None:
    """渲染标签组

    Args:
        tags: 标签列表
        color: 颜色
        size: 尺寸
    """
    from ui.components.design_system import status_badge

    if not tags:
        st.write("无")
        return

    html_tags = ""
    for tag in tags:
        try:
            # 尝试使用badge
            st.badge(tag)
        except (AttributeError, Exception):
            # 降级使用status_badge
            status_badge(tag, color=color, size=size)
