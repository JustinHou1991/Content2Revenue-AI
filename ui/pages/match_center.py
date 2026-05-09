"""
匹配中心页面 - 内容与线索的语义匹配
使用新设计系统组件 (design_system.py + styles.py)
"""

import streamlit as st

from ui.components.design_system import (
    page_header,
    metric_card,
    divider,
    callout,
    empty_state,
    progress_indicator,
)
from ui.styles import COLORS


def render_match_center():
    """渲染匹配中心页面"""
    # 页面头部
    page_header(
        title="匹配中心",
        subtitle="将内容特征与线索画像进行语义匹配，找到最合适的内容-线索组合",
    )

    if not st.session_state.get("initialized"):
        callout(
            "请先在「系统设置」中配置API Key。配置好API Key后，系统会自动保存配置，刷新页面也不会丢失。",
            type="warning",
            icon="&#9888;",
        )
        return

    tab1, tab2 = st.tabs(["单对匹配", "批量匹配"])

    with tab1:
        _render_single_match()

    with tab2:
        _render_batch_match()

    # 历史匹配记录
    divider()
    _display_history()


def _render_single_match():
    """单对匹配"""
    st.subheader("选择匹配对象")

    try:
        contents = st.session_state.orchestrator.db.get_all_content_analyses(limit=50)
        leads = st.session_state.orchestrator.db.get_all_lead_analyses(limit=50)
    except Exception as e:
        callout(f"加载数据失败: {str(e)}", type="error")
        return

    if not contents:
        callout("暂无内容分析记录，请先去「内容分析」页面分析脚本", type="warning")
        st.info("提示：你可以在「系统设置」中点击「加载示例数据」快速体验。")
        return
    if not leads:
        callout("暂无线索分析记录，请先去「线索分析」页面分析线索", type="warning")
        st.info("提示：你可以在「系统设置」中点击「加载示例数据」快速体验。")
        return

    # 构建选项
    content_options = {}
    for c in contents:
        analysis = c.get("analysis_json", {})
        label = (
            f"[{analysis.get('content_score', '?')}/10] {c.get('raw_text', '')[:40]}..."
        )
        content_options[label] = c["id"]

    lead_options = {}
    for lead in leads:
        profile = lead.get("profile_json", {})
        raw = lead.get("raw_data_json", {})
        company = raw.get("company", raw.get("公司名称", "未知"))
        label = f"[{profile.get('lead_grade', '?')}] {company} - {profile.get('industry', '未知')}"
        lead_options[label] = lead["id"]

    col1, col2 = st.columns(2)
    with col1:
        selected_content = st.selectbox("选择内容", list(content_options.keys()))
    with col2:
        selected_lead = st.selectbox("选择线索", list(lead_options.keys()))

    if st.button("开始匹配", type="primary", use_container_width=True):
        content_id = content_options[selected_content]
        lead_id = lead_options[selected_lead]

        with st.spinner("AI正在计算匹配度..."):
            try:
                result = st.session_state.orchestrator.match_content_lead(
                    content_id, lead_id
                )
                _display_match_result(result)
            except Exception as e:
                callout(f"匹配失败: {str(e)}", type="error")
                st.info("请检查内容分析和线索分析是否都已完成。")


def _render_batch_match():
    """批量匹配"""
    st.subheader("批量匹配所有内容与线索")

    top_k = st.slider("每个线索返回的匹配数量", 1, 10, 3)

    if st.button("开始批量匹配", type="primary", use_container_width=True):
        progress_bar = st.progress(0, text="正在批量匹配...")
        with st.spinner("正在批量匹配，这可能需要一些时间..."):
            try:
                results = st.session_state.orchestrator.batch_match(top_k=top_k)
                progress_bar.progress(1.0, text="匹配完成！")
                progress_bar.empty()

                if not results:
                    callout("没有可匹配的内容或线索", type="warning")
                    st.info("提示：请确保已存在至少一条内容分析和一条线索分析记录。")
                    return

                callout(
                    f"批量匹配完成！共匹配 {len(results)} 条线索",
                    type="success",
                    icon="&#10003;",
                )

                for r in results:
                    company = r.get("lead_snapshot", {}).get("company", "未知")
                    industry = r.get("lead_snapshot", {}).get("industry", "未知")

                    with st.expander(f"线索: {company} ({industry})"):
                        for i, match in enumerate(r.get("top_matches", [])):
                            mr = match.get("match_result", {})
                            score = mr.get("overall_score", 0)
                            reason = mr.get("match_reason", "")

                            st.markdown(f"**#{i+1} 匹配度: {score}/10**")
                            st.write(reason)

                            # 维度评分
                            ds = mr.get("dimension_scores", {})
                            if ds:
                                cols = st.columns(5)
                                dims = [
                                    ("受众匹配", "audience_fit"),
                                    ("痛点相关", "pain_point_relevance"),
                                    ("阶段对齐", "stage_alignment"),
                                    ("CTA适当", "cta_appropriateness"),
                                    ("情感共鸣", "emotion_resonance"),
                                ]
                                for col, (label, key) in zip(cols, dims):
                                    with col:
                                        val = ds.get(key, 0)
                                        st.metric(label, f"{val}/10")

                            if i < len(r.get("top_matches", [])) - 1:
                                st.markdown("---")

            except Exception as e:
                progress_bar.empty()
                callout(f"批量匹配失败: {str(e)}", type="error")


def _display_match_result(result: dict):
    """展示匹配结果"""
    mr = result.get("match_result", {})

    callout("匹配完成！", type="success", icon="&#10003;")

    # 总分 - 使用新的 metric_card 组件
    col1, col2 = st.columns([1, 3])
    with col1:
        score = mr.get("overall_score", 0)
        color = "#10B981" if score >= 7 else "#F59E0B" if score >= 5 else "#EF4444"
        metric_card(
            title="综合匹配度",
            value=f"{score}/10",
            subtitle="强匹配" if score >= 7 else "中等匹配" if score >= 5 else "弱匹配",
            icon="&#127919;",
            border_color=color,
        )

    with col2:
        st.write(f"**匹配理由**: {mr.get('match_reason', '')}")

    divider()

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
    for col, (label, key) in zip(cols, dims):
        with col:
            val = ds.get(key, 0)
            color = "#10B981" if val >= 7 else "#F59E0B" if val >= 5 else "#EF4444"
            metric_card(
                title=label,
                value=f"{val}/10",
                border_color=color,
            )

    # 风险因素和建议
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 风险因素")
        for risk in mr.get("risk_factors", []):
            st.write(f"- {risk}")

    with col2:
        st.markdown("#### 跟进建议")
        st.info(mr.get("recommended_follow_up", "暂无建议"))


def _display_history():
    """展示历史匹配记录"""
    st.subheader("历史匹配记录")
    try:
        records = st.session_state.orchestrator.db.get_all_match_results(limit=10)
        if records:
            for record in records:
                mr = record.get("match_result_json", {})
                score = mr.get("overall_score", "N/A")
                reason = mr.get("match_reason", "")[:80] + "..."

                with st.expander(f"匹配度 {score}/10 | {record['created_at'][:10]}"):
                    st.write(reason)
        else:
            empty_state(
                title="暂无匹配记录",
                description="请先进行内容-线索匹配",
                icon="&#127919;",
            )
    except Exception as e:
        callout(f"加载失败: {str(e)}", type="error")
