"""
匹配中心页面 - 内容与线索的语义匹配
使用新设计系统组件 (design_system.py + styles.py)
继承自 MatchPage 基类
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)

from ui.base_page import MatchPage
from ui.components.data_display import render_match_result_details
from ui.components.design_system import (
    page_header,
    metric_card,
    divider,
    callout,
    empty_state,
)
from ui.styles import COLORS


def _render_content_snapshot(snap: dict):
    """渲染内容快照摘要"""
    if not snap:
        st.write("暂无内容信息")
        return

    score = snap.get("content_score", "N/A")
    hook = snap.get("hook_type", "未知")
    category = snap.get("content_category", "未知")
    cta = snap.get("cta_type", "未知")
    tone = snap.get("emotion_tone", "未知")
    audience = snap.get("target_audience", "未知")
    tags = snap.get("topic_tags", [])
    keywords = snap.get("hook_keywords", [])
    selling = snap.get("key_selling_points", [])

    st.write(f"**内容评分**: {score}/10")
    st.write(f"**Hook类型**: {hook}")
    st.write(f"**内容分类**: {category}")
    st.write(f"**CTA类型**: {cta}")
    st.write(f"**情感基调**: {tone}")
    st.write(f"**目标受众**: {audience}")

    if tags:
        st.write(f"**话题标签**: {', '.join(tags)}")
    if keywords:
        st.write(f"**Hook关键词**: {', '.join(keywords)}")
    if selling:
        st.write(f"**核心卖点**: {', '.join(selling)}")


def _render_lead_snapshot(snap: dict):
    """渲染线索快照摘要"""
    if not snap:
        st.write("暂无线索信息")
        return

    industry = snap.get("industry", "未知")
    stage = snap.get("company_stage", "未知")
    role = snap.get("role", "未知")
    buying = snap.get("buying_stage", "未知")
    score = snap.get("lead_score", "N/A")
    grade = snap.get("lead_grade", "N/A")
    intent = snap.get("intent_level", "N/A")
    pains = snap.get("pain_points", [])

    st.write(f"**行业**: {industry}")
    st.write(f"**公司阶段**: {stage}")
    st.write(f"**决策角色**: {role}")
    st.write(f"**购买阶段**: {buying}")
    st.write(f"**线索评分**: {score}/100 ({grade}级)")
    st.write(f"**购买意向**: {intent}/10")

    if pains:
        st.write(f"**核心痛点**: {', '.join(pains)}")


class MatchCenterPage(MatchPage):
    """匹配中心页面类"""

    def __init__(self):
        super().__init__(
        title="匹配中心",
        icon="🎯",
        description="将内容特征与线索画像进行语义匹配，找到最合适的内容-线索组合"
    )

    def _render_single_match(self):
        """单对匹配"""
        st.subheader("选择匹配对象")

        try:
            contents = self._get_orchestrator().db.get_all_content_analyses(limit=500)
            leads = self._get_orchestrator().db.get_all_lead_analyses(limit=500)
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

        st.caption(f"📊 可选内容: {len(contents)} 条 | 可选线索: {len(leads)} 条")

        # 构建选项（优化：显示更多关键信息）
        content_options = {}
        for c in contents:
            analysis = c.get("analysis_json", {})
            raw_text = c.get("raw_text", "")
            preview = raw_text[:40].replace("\n", " ") + "..." if len(raw_text) > 40 else raw_text
            score = analysis.get("content_score", "?")
            hook = analysis.get("hook_type", "")
            category = analysis.get("content_category", "")
            # 格式：[评分] Hook类型·分类 | 脚本前40字
            info_parts = []
            if hook and hook != "未知":
                info_parts.append(hook)
            if category and category != "未知":
                info_parts.append(category)
            info_str = "·".join(info_parts)
            label = f"[{score}/10] {info_str} | {preview}" if info_str else f"[{score}/10] {preview}"
            content_options[label] = c["id"]

        lead_options = {}
        for lead in leads:
            profile = lead.get("profile_json", {})
            raw = lead.get("raw_data_json", {})
            company = raw.get("company", raw.get("公司名称", "未知"))
            grade = profile.get("lead_grade", "?")
            industry = profile.get("industry", "未知")
            intent = profile.get("intent_level", "?")
            pains = profile.get("pain_points", [])
            pain_str = pains[0][:15] + "..." if pains else ""
            # 格式：[等级] 公司·行业(意向X/10) | 痛点摘要
            info = f"{company}·{industry}" if industry and industry != "未知" else company
            label = f"[{grade}级] {info} (意向{intent}/10)"
            if pain_str:
                label += f" | {pain_str}"
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
                    result = self._get_orchestrator().match_content_lead(
                        content_id, lead_id
                    )
                    self._display_match_result(result)
                except Exception as e:
                    callout(f"匹配失败: {str(e)}", type="error")
                    st.info("请检查内容分析和线索分析是否都已完成。")

    def _render_batch_match(self):
        st.subheader("批量匹配所有内容与线索")

        top_k = st.slider("每个线索返回的匹配数量", 1, 10, 3)

        if st.button("开始批量匹配", type="primary", use_container_width=True):
            orchestrator = self._get_orchestrator()

            contents = orchestrator.db.get_all_content_analyses(limit=500)
            leads = orchestrator.db.get_all_lead_analyses(limit=500)

            if not contents:
                callout("未找到内容分析记录，请先进行内容分析", type="warning")
                return
            if not leads:
                callout("未找到线索分析记录，请先进行线索分析", type="warning")
                return

            total_leads = len(leads)
            total_tasks = len(contents) * len(leads)
            st.warning("⚠️ **匹配中，请勿切换页面**，完成后将自动显示结果。")
            st.info(f"共 {total_leads} 条线索 × {len(contents)} 条内容 = {total_tasks} 次匹配，并发处理中...")

            with st.spinner(f"正在并发匹配 {total_tasks} 对内容-线索组合..."):
                results = orchestrator.batch_match(top_k)

            valid_results = [r for r in results if r is not None]
            self._render_batch_match_results(valid_results)

    def _render_batch_match_results(self, results):
        """渲染批量匹配结果"""
        if not results:
            callout("没有可匹配的有效线索", type="warning")
            st.info("""提示：
1. 请确保已存在至少一条内容分析和一条线索分析记录
2. 线索分析可能未完成或数据为空，建议重新进行线索分析
3. 检查线索数据是否包含有效的需求描述或对话内容""")
            return

        callout(
            f"批量匹配完成！共匹配 {len(results)} 条线索",
            type="success",
            icon="✅",
        )

        divider()
        st.subheader("✅ 当前匹配结果")

        for idx, r in enumerate(results, 1):
            lead_snap = r.get("lead_snapshot", {})
            lid = lead_snap.get("lead_id", "")[:8]
            company = lead_snap.get("company", "未知")
            industry = lead_snap.get("industry", "未知")
            grade = lead_snap.get("lead_grade", "?")

            grade_icon = "🟢" if grade in ["A", "B+"] else "🟡" if grade == "B" else "🔴"
            title = f"**#{idx}** [{lid}] {grade_icon} {grade}级 | {company}"
            if industry and industry != "未知":
                title += f" ({industry})"

            with st.expander(title):
                # 线索摘要
                with st.container():
                    st.markdown("**👤 线索信息**")
                    _render_lead_snapshot(lead_snap)

                for i, match in enumerate(r.get("top_matches", [])):
                    mr = match.get("match_result", {})
                    score = mr.get("overall_score", 0)
                    content_snap = match.get("content_snapshot", {})

                    st.markdown("---")
                    try:
                        score_val = float(score)
                        score_icon = "🟢" if score_val >= 7 else "🟡" if score_val >= 5 else "🔴"
                    except (ValueError, TypeError):
                        score_icon = "⚪"
                    st.markdown(f"**{score_icon} #{i+1} 匹配度: {score}/10**")

                    # 内容摘要
                    st.markdown("**📝 匹配内容**")
                    _render_content_snapshot(content_snap)

                    # 匹配原因
                    reason = mr.get("match_reason", "")
                    if reason:
                        st.markdown("**匹配分析**")
                        st.write(reason)

                    # 维度评分
                    ds = mr.get("dimension_scores", {})
                    if ds:
                        self._render_dimension_scores(ds, columns=5)

    def _display_match_result(self, result: dict):
        """展示单对匹配结果（含内容和线索详情）"""
        mr = result.get("match_result", {})
        content_snap = result.get("content_snapshot", {})
        lead_snap = result.get("lead_snapshot", {})
        score = mr.get("overall_score", 0)
        match_id = result.get("match_id", "")[:8]

        # 顶部：ID 和综合评分
        if match_id:
            st.caption(f"匹配ID: {match_id}...")

        # 综合评分
        color = "#10B981" if score >= 7 else "#F59E0B" if score >= 5 else "#EF4444"
        metric_card(
            title="综合匹配度",
            value=f"{score}/10",
            subtitle="强匹配" if score >= 7 else "中等匹配" if score >= 5 else "弱匹配",
            icon="🎯",
            border_color=color,
        )

        divider()

        # 内容和线索摘要卡片（对比视图）
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 📝 匹配的内容")
            # 一句话摘要
            hook = content_snap.get("hook_type", "未知")
            category = content_snap.get("content_category", "未知")
            c_score = content_snap.get("content_score", "?")
            audience = content_snap.get("target_audience", "未知")
            tags = content_snap.get("topic_tags", [])
            st.info(f"**{hook}** · {category} | 评分 {c_score}/10 | 受众: {audience}")
            if tags:
                st.caption(f"话题: {', '.join(tags)}")
            # 详细信息折叠
            with st.expander("查看完整内容画像"):
                _render_content_snapshot(content_snap)
        with col_b:
            st.markdown("#### 👤 匹配的线索")
            industry = lead_snap.get("industry", "未知")
            stage = lead_snap.get("company_stage", "未知")
            l_score = lead_snap.get("lead_score", "?")
            grade = lead_snap.get("lead_grade", "?")
            intent = lead_snap.get("intent_level", "?")
            pains = lead_snap.get("pain_points", [])
            st.info(f"**{industry}** · {stage} | {grade}级 {l_score}/100 | 意向 {intent}/10")
            if pains:
                st.caption(f"痛点: {', '.join(pains[:3])}")
            with st.expander("查看完整线索画像"):
                _render_lead_snapshot(lead_snap)

        divider()

        # 匹配分析
        reason = mr.get("match_reason", "")
        if reason:
            st.markdown("#### 匹配分析")
            st.write(reason)

        # 维度评分
        ds = mr.get("dimension_scores", {})
        if ds:
            st.markdown("#### 维度评分")
            self._render_dimension_scores(ds, columns=5)

        # 风险和建议
        risks = mr.get("risk_factors", [])
        follow_up = mr.get("recommended_follow_up", "")
        if risks or follow_up:
            divider()
            col1, col2 = st.columns(2)
            with col1:
                if risks:
                    st.markdown("#### ⚠️ 风险因素")
                    for risk in risks:
                        st.write(f"- {risk}")
            with col2:
                if follow_up:
                    st.markdown("#### 💡 跟进建议")
                    st.info(follow_up)

    def _render_history(self):
        """展示历史匹配记录"""
        st.subheader("历史匹配记录")
        try:
            records = self._get_orchestrator().db.get_all_match_results(limit=10)
            if records:
                for idx, record in enumerate(records, 1):
                    mr = record.get("match_result_json", {})
                    score = mr.get("overall_score", "N/A")
                    reason = mr.get("match_reason", "")

                    # 提取快照信息
                    content_snap = record.get("content_snapshot_json", {})
                    lead_snap = record.get("lead_snapshot_json", {})

                    # 构建标题（带编号）
                    match_no = f"#{idx}"
                    content_score = content_snap.get("content_score", "?")
                    hook = content_snap.get("hook_type", "")
                    category = content_snap.get("content_category", "")
                    content_label = f"{hook}"
                    if category and category != "未知":
                        content_label += f" · {category}"
                    content_label += f" (评分{content_score})"

                    lead_grade = lead_snap.get("lead_grade", "?")
                    industry = lead_snap.get("industry", "未知")
                    intent = lead_snap.get("intent_level", "?")
                    lead_label = f"{lead_grade}级"
                    if industry and industry != "未知":
                        lead_label += f" · {industry}"
                    lead_label += f" (意向{intent}/10)"

                    score_icon = "🟢" if score >= 7 else "🟡" if score >= 5 else "🔴"
                    created = record.get("created_at", "")[:10]
                    match_id_short = record.get("id", "")[:8]

                    with st.expander(f"**{match_no}** [{match_id_short}] {score_icon} 匹配度 {score}/10 | {created}"):
                        # 创建时间
                        st.caption(f"创建时间: {record.get('created_at', '未知')}")
                        # 双列：内容 vs 线索
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown(f"**📝 内容**: {content_label}")
                            tags = content_snap.get("topic_tags", [])
                            if tags:
                                st.caption(f"话题: {', '.join(tags)}")
                            cta = content_snap.get("cta_type", "")
                            if cta:
                                st.caption(f"CTA: {cta}")
                        with col_b:
                            st.markdown(f"**👤 线索**: {lead_label}")
                            pains = lead_snap.get("pain_points", [])
                            if pains:
                                st.caption(f"痛点: {', '.join(pains[:3])}")

                        st.markdown("---")

                        # 完整匹配原因
                        if reason:
                            st.markdown("**匹配分析**")
                            st.write(reason)

                        # 维度评分
                        ds = mr.get("dimension_scores", {})
                        if ds:
                            self._render_dimension_scores(ds, columns=5)

                        # 跟进建议
                        follow_up = mr.get("recommended_follow_up", "")
                        if follow_up:
                            st.markdown("---")
                            st.markdown("**💡 跟进建议**")
                            st.info(follow_up)
            else:
                empty_state(
                    title="暂无匹配记录",
                    description="请先进行内容-线索匹配",
                    icon="🎯",
                )
        except Exception as e:
            callout(f"加载失败: {str(e)}", type="error")


def render_match_center():
    """页面入口函数"""
    page = MatchCenterPage()
    page.render()
