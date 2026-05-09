"""
策略建议页面 - AI生成内容策略
使用新设计系统组件 (design_system.py + styles.py)
"""

import streamlit as st

from ui.components.design_system import (
    page_header,
    metric_card,
    status_badge,
    divider,
    callout,
    empty_state,
)
from ui.styles import COLORS


def _safe_badge(label, icon=None):
    """安全渲染标签，兼容旧版 Streamlit（< 1.37）。

    st.badge() 从 Streamlit 1.37 开始支持，旧版本使用 markdown 标签样式作为降级方案。
    """
    try:
        st.badge(label, icon=icon)
    except (AttributeError, Exception):
        # 降级：使用新设计系统的 status_badge 组件
        status_badge(label, color="purple", size="sm")


def render_strategy():
    """渲染策略建议页面"""
    # 页面头部
    page_header(
        title="AI策略建议",
        subtitle="基于匹配结果，生成具体可执行的内容策略、分发策略、转化预测和A/B测试建议",
    )

    if not st.session_state.get("initialized"):
        callout(
            "请先在「系统设置」中配置API Key。配置好API Key后，系统会自动保存配置，刷新页面也不会丢失。",
            type="warning",
            icon="&#9888;",
        )
        return

    # 选择匹配结果
    try:
        match_results = st.session_state.orchestrator.db.get_all_match_results(limit=20)
    except Exception as e:
        callout(f"加载匹配记录失败: {str(e)}", type="error")
        return

    if not match_results:
        callout("暂无匹配记录，请先去「匹配中心」进行内容-线索匹配", type="info")
        return

    # 构建选项
    match_options = {}
    for m in match_results:
        mr = m.get("match_result_json", {})
        score = mr.get("overall_score", "?")
        cs = m.get("content_snapshot_json", {})
        ls = m.get("lead_snapshot_json", {})
        label = f"[{score}/10] {cs.get('industry', ls.get('industry', '未知'))} | {m['created_at'][:10]}"
        match_options[label] = m["id"]

    selected = st.selectbox("选择匹配结果", list(match_options.keys()))

    if st.button("生成策略建议", type="primary", use_container_width=True):
        match_id = match_options[selected]

        with st.spinner("AI正在生成策略建议..."):
            try:
                result = st.session_state.orchestrator.generate_strategy(match_id)
                _display_strategy(result)
            except Exception as e:
                callout(f"策略生成失败: {str(e)}", type="error")
                st.info("请检查匹配结果是否有效，或稍后重试。")

    # 历史策略
    divider()
    _display_history()


def _display_strategy(result: dict):
    """展示策略建议"""
    strategy = result.get("strategy", {})

    callout("策略建议已生成！", type="success", icon="&#10003;")

    # 内容策略
    cs = strategy.get("content_strategy", {})
    divider()
    st.markdown("#### 内容策略")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**推荐Hook:**")
        hook = cs.get("recommended_hook", "")
        st.code(hook, language=None)
        if st.button("复制Hook", key="copy_hook"):
            st.clipboard_copy(hook)
            st.toast("已复制！")

        st.markdown(f"**理由:** {cs.get('hook_rationale', '')}")
        st.markdown(f"**推荐结构:** {cs.get('recommended_structure', '')}")

    with col2:
        st.markdown("**核心话术要点:**")
        for point in cs.get("talking_points", []):
            st.write(f"- {point}")

        st.markdown(f"**语气指导:** {cs.get('tone_guidance', '')}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**建议包含的关键词:**")
        for kw in cs.get("keywords_to_include", []):
            _safe_badge(kw)

    with col2:
        st.markdown("**建议避免的关键词:**")
        for kw in cs.get("keywords_to_avoid", []):
            _safe_badge(kw)

    # 分发策略
    ds = strategy.get("distribution_strategy", {})
    divider()
    st.markdown("#### 分发策略")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**最佳时间:** {ds.get('best_timing', '未知')}")
        st.write(f"**渠道建议:** {ds.get('channel_suggestion', '未知')}")

    with col2:
        st.markdown("**跟进节奏:**")
        for step in ds.get("follow_up_sequence", []):
            st.write(f"- {step}")

    # 转化预测 - 使用新的 metric_card 组件
    cp = strategy.get("conversion_prediction", {})
    divider()
    st.markdown("#### 转化预测")

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

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**关键成功因素:**")
        for factor in cp.get("key_success_factors", []):
            st.write(f"[OK] {factor}")

    with col2:
        st.markdown("**潜在障碍:**")
        for blocker in cp.get("potential_blockers", []):
            st.write(f"[!] {blocker}")

    # A/B测试建议
    ab = strategy.get("a_b_test_suggestion", {})
    divider()
    st.markdown("#### A/B测试建议")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**方案A:**")
        st.info(ab.get("variant_a", ""))
    with col2:
        st.markdown("**方案B:**")
        st.info(ab.get("variant_b", ""))

    st.write(f"**测试指标:** {ab.get('test_metric', '未知')}")

    # 导出按钮
    divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("复制完整策略", key="copy_full"):
            import json

            st.clipboard_copy(json.dumps(strategy, ensure_ascii=False, indent=2))
            st.toast("已复制到剪贴板！")
    with col2:
        if st.button("重新生成", key="regenerate"):
            st.rerun()

    # 策略反馈表单
    divider()
    _render_feedback_form(result)


def _render_feedback_form(result: dict):
    """渲染策略反馈表单"""
    st.subheader("策略效果反馈")
    st.caption("帮助我们改进策略建议质量，请反馈您是否采纳了此策略及实际效果")

    strategy_id = result.get("strategy_id", "")

    # 检查是否已有反馈
    try:
        existing_feedback = st.session_state.orchestrator.db.get_strategy_feedback(
            strategy_id
        )
    except Exception:
        existing_feedback = None

    if existing_feedback:
        callout("您已提交过反馈", type="success", icon="&#10003;")
        col1, col2 = st.columns(2)
        with col1:
            adopted = "已采纳" if existing_feedback.get("was_adopted") else "未采纳"
            st.metric("采纳状态", adopted)
        with col2:
            actual_conv = existing_feedback.get("actual_conversion")
            if actual_conv is not None:
                st.metric("实际转化率", f"{actual_conv}%")
        if existing_feedback.get("feedback_notes"):
            st.info(f"**反馈备注:** {existing_feedback['feedback_notes']}")
        return

    with st.form(key=f"feedback_form_{strategy_id}"):
        col1, col2 = st.columns(2)

        with col1:
            was_adopted = st.radio(
                "您是否采纳了此策略建议？",
                options=["是", "否"],
                index=0,
                horizontal=True,
            )

        with col2:
            actual_conversion = st.number_input(
                "实际转化率 (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.1,
                help="如果您已执行此策略，请输入实际观察到的转化率",
            )

        feedback_notes = st.text_area(
            "反馈备注（可选）",
            placeholder="请描述策略执行效果、遇到的问题或改进建议...",
            max_chars=500,
        )

        submitted = st.form_submit_button(
            "提交反馈", use_container_width=True, type="primary"
        )

        if submitted:
            try:
                st.session_state.orchestrator.db.save_strategy_feedback(
                    strategy_id=strategy_id,
                    was_adopted=(was_adopted == "是"),
                    actual_conversion=(
                        actual_conversion if actual_conversion > 0 else None
                    ),
                    feedback_notes=feedback_notes if feedback_notes else None,
                )
                callout("反馈提交成功！感谢您的参与。", type="success", icon="&#127881;")
                st.balloons()
                st.rerun()
            except Exception as e:
                callout(f"提交反馈失败: {str(e)}", type="error")


def _display_history():
    """展示历史策略"""
    st.subheader("历史策略建议")
    try:
        strategies = st.session_state.orchestrator.db.get_all_strategy_advices(limit=10)
        if strategies:
            for s in strategies:
                strategy = s.get("strategy_json", {})
                cs = strategy.get("content_strategy", {})
                hook = cs.get("recommended_hook", "未知")[:30]

                # 检查是否有反馈
                try:
                    feedback = st.session_state.orchestrator.db.get_strategy_feedback(
                        s["id"]
                    )
                    feedback_indicator = (
                        "[OK]"
                        if feedback and feedback.get("was_adopted")
                        else "[NOTE]" if feedback else "[WAIT]"
                    )
                except Exception:
                    feedback_indicator = "[WAIT]"

                with st.expander(
                    f"{feedback_indicator} 策略 {s['id'][:8]}... | {s['created_at'][:10]}"
                ):
                    st.write(f"**推荐Hook:** {hook}")
                    st.write(
                        f"**转化预测:** {strategy.get('conversion_prediction', {}).get('estimated_conversion_rate', '未知')}"
                    )
                    if feedback:
                        st.write(
                            f"**采纳状态:** {'已采纳' if feedback.get('was_adopted') else '未采纳'}"
                        )
                        if feedback.get("actual_conversion"):
                            st.write(f"**实际转化:** {feedback['actual_conversion']}%")
        else:
            empty_state(
                title="暂无策略建议记录",
                description="请先选择匹配结果生成策略",
                icon="&#128161;",
            )
    except Exception as e:
        callout(f"加载失败: {str(e)}", type="error")
