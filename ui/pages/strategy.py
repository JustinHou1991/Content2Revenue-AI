"""
策略建议页面 - AI生成内容策略
使用新设计系统组件 (design_system.py + styles.py)
继承自 BasePage 基类
"""

import streamlit as st
import json

from ui.base_page import BasePage
from ui.components.data_display import render_strategy_content, render_tags
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
    """安全渲染标签，兼容旧版 Streamlit（< 1.37）"""
    try:
        st.badge(label, icon=icon)
    except (AttributeError, Exception):
        status_badge(label, color="purple", size="sm")


class StrategyPage(BasePage):
    """策略建议页面类"""

    def __init__(self):
        super().__init__(
            title="AI策略建议",
            icon="💡",
            description="基于匹配结果，生成具体可执行的内容策略、分发策略、转化预测和A/B测试建议"
        )

    def _render_content(self):
        """渲染页面内容"""
        if not self._check_initialization():
            return

        # 选择匹配结果
        try:
            match_results = self._get_orchestrator().db.get_all_match_results(limit=20)
        except Exception as e:
            callout(f"加载匹配记录失败: {str(e)}", type="error")
            return

        if not match_results:
            callout("暂无匹配记录，请先去「匹配中心」进行内容-线索匹配", type="info")
            return

        # 构建选项（优化：显示内容和线索关键信息）
        match_options = {}
        for m in match_results:
            mr = m.get("match_result_json", {})
            score = mr.get("overall_score", "?")
            cs = m.get("content_snapshot_json", {})
            ls = m.get("lead_snapshot_json", {})

            # 内容信息
            c_hook = cs.get("hook_type", "")
            c_category = cs.get("content_category", "")
            c_parts = []
            if c_hook and c_hook != "未知":
                c_parts.append(c_hook)
            if c_category and c_category != "未知":
                c_parts.append(c_category)
            c_info = "·".join(c_parts) if c_parts else "未知内容"

            # 线索信息
            l_industry = ls.get("industry", "未知")
            l_grade = ls.get("lead_grade", "?")
            l_intent = ls.get("intent_level", "?")
            l_info = f"{l_grade}级·{l_industry}(意向{l_intent})" if l_industry != "未知" else f"{l_grade}级"

            label = f"[匹配{score}/10] 📝{c_info} ↔ 👤{l_info} | {m['created_at'][:10]}"
            match_options[label] = m["id"]

        selected = st.selectbox("选择匹配结果", list(match_options.keys()))

        if st.button("生成策略建议", type="primary", use_container_width=True):
            match_id = match_options[selected]

            with st.spinner("AI正在生成策略建议..."):
                try:
                    result = self._get_orchestrator().generate_strategy(match_id)
                    self._display_strategy(result)
                except Exception as e:
                    callout(f"策略生成失败: {str(e)}", type="error")
                    st.info("请检查匹配结果是否有效，或稍后重试。")

        # 历史策略
        divider()
        self._render_history()

    def _display_strategy(self, result: dict):
        """展示策略建议"""
        strategy = result.get("strategy", {})
        strategy_id = result.get("strategy_id", "")[:8]

        callout(f"策略建议已生成！ID: {strategy_id}...", type="success", icon="✅")

        # 顶部：内容和线索摘要（让用户知道是为谁生成的策略）
        match_id = result.get("match_id", "")
        content_id = result.get("content_id", "")
        lead_id = result.get("lead_id", "")

        # 尝试获取匹配的快照信息
        content_snap = {}
        lead_snap = {}
        try:
            match_data = self._get_orchestrator().db.get_match_result(match_id) if match_id else None
            if match_data:
                content_snap = match_data.get("content_snapshot_json", {})
                lead_snap = match_data.get("lead_snapshot_json", {})
        except Exception:
            pass

        if content_snap or lead_snap:
            divider()
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📝 策略针对的内容**")
                c_hook = content_snap.get("hook_type", "未知")
                c_cat = content_snap.get("content_category", "未知")
                c_score = content_snap.get("content_score", "?")
                c_audience = content_snap.get("target_audience", "未知")
                c_tags = content_snap.get("topic_tags", [])
                st.info(f"**{c_hook}** · {c_cat} | 评分 {c_score}/10 | 受众: {c_audience}")
                if c_tags:
                    st.caption(f"话题: {', '.join(c_tags)}")
            with col_b:
                st.markdown("**👤 策略针对的线索**")
                l_industry = lead_snap.get("industry", "未知")
                l_stage = lead_snap.get("company_stage", "未知")
                l_grade = lead_snap.get("lead_grade", "?")
                l_intent = lead_snap.get("intent_level", "?")
                l_pains = lead_snap.get("pain_points", [])
                st.info(f"**{l_industry}** · {l_stage} | {l_grade}级 | 意向 {l_intent}/10")
                if l_pains:
                    st.caption(f"痛点: {', '.join(l_pains[:3])}")
            divider()

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

        # 转化预测
        cp = strategy.get("conversion_prediction", {})
        divider()
        st.markdown("#### 转化预测")

        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card(
                title="预估转化率",
                value=cp.get("estimated_conversion_rate", "未知"),
                icon="📈",
                border_color="#10B981",
            )
        with col2:
            metric_card(
                title="置信度",
                value=cp.get("confidence_level", "未知"),
                icon="💪",
                border_color="#6366F1",
            )
        with col3:
            metric_card(
                title="建议样本量",
                value=cp.get("recommended_sample_size", "未知"),
                icon="📊",
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
                st.clipboard_copy(json.dumps(strategy, ensure_ascii=False, indent=2))
                st.toast("已复制到剪贴板！")
        with col2:
            if st.button("重新生成", key="regenerate"):
                st.rerun()

        # 策略反馈表单
        divider()
        self._render_feedback_form(result)

    def _render_feedback_form(self, result: dict):
        """渲染策略反馈表单"""
        st.subheader("策略效果反馈")
        st.caption("帮助我们改进策略建议质量，请反馈您是否采纳了此策略及实际效果")

        strategy_id = result.get("strategy_id", "")

        # 检查是否已有反馈
        try:
            existing_feedback = self._get_orchestrator().db.get_strategy_feedback(
                strategy_id
            )
        except Exception:
            existing_feedback = None

        if existing_feedback:
            callout("您已提交过反馈", type="success", icon="✅")
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
                    self._get_orchestrator().db.save_strategy_feedback(
                        strategy_id=strategy_id,
                        was_adopted=(was_adopted == "是"),
                        actual_conversion=(
                            actual_conversion if actual_conversion > 0 else None
                        ),
                        feedback_notes=feedback_notes if feedback_notes else None,
                    )
                    callout("反馈提交成功！感谢您的参与。", type="success", icon="🎉")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    callout(f"提交反馈失败: {str(e)}", type="error")

    def _render_history(self):
        """展示历史策略（完整内容 + 反馈入口）"""
        st.subheader("历史策略建议")
        try:
            strategies = self._get_orchestrator().db.get_all_strategy_advices(limit=10)
            if strategies:
                for s in strategies:
                    strategy = s.get("strategy_json", {})
                    cs = strategy.get("content_strategy", {})
                    ds = strategy.get("distribution_strategy", {})
                    cp = strategy.get("conversion_prediction", {})
                    ab = strategy.get("a_b_test_suggestion", {})

                    hook = cs.get("recommended_hook", "未知")
                    structure = cs.get("recommended_structure", "未知")
                    conv_rate = cp.get("estimated_conversion_rate", "未知")
                    confidence = cp.get("confidence_level", "未知")

                    # 反馈状态
                    try:
                        feedback = self._get_orchestrator().db.get_strategy_feedback(
                            s["id"]
                        )
                        if feedback and feedback.get("was_adopted"):
                            fb_icon = "✅"
                            fb_text = "已采纳"
                        elif feedback:
                            fb_icon = "📝"
                            fb_text = "已反馈(未采纳)"
                        else:
                            fb_icon = "⏳"
                            fb_text = "待反馈"
                    except Exception:
                        feedback = None
                        fb_icon = "⏳"
                        fb_text = "待反馈"

                    sid = s.get("id", "")[:8]
                    title = f"[{sid}] {fb_icon} {fb_text} | 转化预测 {conv_rate} | {s['created_at'][:10]}"

                    with st.expander(title):
                        # === 内容策略 ===
                        st.markdown("#### 📝 内容策略")
                        st.markdown("**推荐Hook:**")
                        st.code(hook, language=None)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**推荐结构**: {structure}")
                            st.write(f"**语气指导**: {cs.get('tone_guidance', '未知')}")
                        with col2:
                            st.markdown("**核心话术要点:**")
                            for point in cs.get("talking_points", []):
                                st.write(f"- {point}")

                        kws_include = cs.get("keywords_to_include", [])
                        kws_avoid = cs.get("keywords_to_avoid", [])
                        if kws_include or kws_avoid:
                            col1, col2 = st.columns(2)
                            with col1:
                                if kws_include:
                                    st.markdown("**建议关键词:**")
                                    for kw in kws_include:
                                        _safe_badge(kw)
                            with col2:
                                if kws_avoid:
                                    st.markdown("**避免关键词:**")
                                    for kw in kws_avoid:
                                        _safe_badge(kw)

                        # === 分发策略 ===
                        if ds:
                            st.markdown("---")
                            st.markdown("#### 📤 分发策略")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**最佳时间**: {ds.get('best_timing', '未知')}")
                                st.write(f"**渠道建议**: {ds.get('channel_suggestion', '未知')}")
                            with col2:
                                steps = ds.get("follow_up_sequence", [])
                                if steps:
                                    st.markdown("**跟进节奏:**")
                                    for step in steps:
                                        st.write(f"- {step}")

                        # === 转化预测 ===
                        if cp:
                            st.markdown("---")
                            st.markdown("#### 📈 转化预测")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                metric_card(
                                    title="预估转化率",
                                    value=conv_rate,
                                    icon="📈",
                                    border_color="#10B981",
                                )
                            with col2:
                                metric_card(
                                    title="置信度",
                                    value=confidence,
                                    icon="💪",
                                    border_color="#6366F1",
                                )
                            with col3:
                                sample = cp.get("recommended_sample_size", "未知")
                                metric_card(
                                    title="建议样本量",
                                    value=sample,
                                    icon="📊",
                                    border_color="#F59E0B",
                                )

                            factors = cp.get("key_success_factors", [])
                            blockers = cp.get("potential_blockers", [])
                            if factors or blockers:
                                col1, col2 = st.columns(2)
                                with col1:
                                    if factors:
                                        st.markdown("**成功因素:**")
                                        for f in factors:
                                            st.write(f"✅ {f}")
                                with col2:
                                    if blockers:
                                        st.markdown("**潜在障碍:**")
                                        for b in blockers:
                                            st.write(f"⚠️ {b}")

                        # === A/B测试建议 ===
                        if ab:
                            st.markdown("---")
                            st.markdown("#### 🧪 A/B测试建议")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**方案A:**")
                                st.info(ab.get("variant_a", ""))
                            with col2:
                                st.markdown("**方案B:**")
                                st.info(ab.get("variant_b", ""))
                            test_metric = ab.get("test_metric", "")
                            if test_metric:
                                st.write(f"**测试指标**: {test_metric}")

                        # === 已有反馈展示 ===
                        if feedback:
                            st.markdown("---")
                            st.markdown("#### 📋 反馈记录")
                            col1, col2 = st.columns(2)
                            with col1:
                                adopted = "已采纳" if feedback.get("was_adopted") else "未采纳"
                                st.metric("采纳状态", adopted)
                            with col2:
                                actual_conv = feedback.get("actual_conversion")
                                if actual_conv is not None:
                                    st.metric("实际转化率", f"{actual_conv}%")
                            if feedback.get("feedback_notes"):
                                st.info(f"**备注**: {feedback['feedback_notes']}")

                        # === 反馈入口 ===
                        st.markdown("---")
                        if not feedback:
                            self._render_feedback_form(s)
                        else:
                            st.caption("✅ 已提交反馈，感谢您的参与！")
            else:
                empty_state(
                    title="暂无策略建议记录",
                    description="请先选择匹配结果生成策略",
                    icon="💡",
                )
        except Exception as e:
            callout(f"加载失败: {str(e)}", type="error")


def render_strategy():
    """页面入口函数"""
    page = StrategyPage()
    page.render()
