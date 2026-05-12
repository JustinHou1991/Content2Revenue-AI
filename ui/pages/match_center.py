"""
匹配中心页面 - 内容与线索的语义匹配
使用新设计系统组件 (design_system.py + styles.py)
继承自 MatchPage 基类
"""

import streamlit as st

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


class MatchCenterPage(MatchPage):
    """匹配中心页面类"""

    def __init__(self):
        super().__init__(
            title="匹配中心",
            icon="&#127919;",
            description="将内容特征与线索画像进行语义匹配，找到最合适的内容-线索组合"
        )

    def _render_single_match(self):
        """单对匹配"""
        st.subheader("选择匹配对象")

        try:
            contents = self._get_orchestrator().db.get_all_content_analyses(limit=50)
            leads = self._get_orchestrator().db.get_all_lead_analyses(limit=50)
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
            label = f"[{analysis.get('content_score', '?')}/10] {c.get('raw_text', '')[:40]}..."
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
                    result = self._get_orchestrator().match_content_lead(
                        content_id, lead_id
                    )
                    self._display_match_result(result)
                except Exception as e:
                    callout(f"匹配失败: {str(e)}", type="error")
                    st.info("请检查内容分析和线索分析是否都已完成。")

    def _render_batch_match(self):
        """批量匹配"""
        st.subheader("批量匹配所有内容与线索")

        top_k = st.slider("每个线索返回的匹配数量", 1, 10, 3)

        if st.button("开始批量匹配", type="primary", use_container_width=True):
            progress_bar = st.progress(0, text="正在批量匹配...")
            with st.spinner("正在批量匹配，这可能需要一些时间..."):
                try:
                    results = self._get_orchestrator().batch_match(top_k=top_k)
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
                                    self._render_dimension_scores(ds, columns=5)

                                if i < len(r.get("top_matches", [])) - 1:
                                    st.markdown("---")

                except Exception as e:
                    progress_bar.empty()
                    callout(f"批量匹配失败: {str(e)}", type="error")

    def _display_match_result(self, result: dict):
        """展示匹配结果"""
        render_match_result_details(result)

    def _render_history(self):
        """展示历史匹配记录"""
        st.subheader("历史匹配记录")
        try:
            records = self._get_orchestrator().db.get_all_match_results(limit=10)
            if records:
                for record in records:
                    mr = record.get("match_result_json", {})
                    score = mr.get("overall_score", "N/A")
                    reason = mr.get("match_reason", "")

                    # 提取内容和线索信息
                    content_snap = record.get("content_snapshot_json", {})
                    lead_snap = record.get("lead_snapshot_json", {})
                    content_text = content_snap.get("raw_text", "")[:60]
                    company = lead_snap.get("company", lead_snap.get("公司名称", "未知"))
                    industry = lead_snap.get("industry", "未知")

                    # 标题：评分 + 公司 + 内容摘要
                    title = f"匹配度 {score}/10 | {company}"
                    if industry and industry != "未知":
                        title += f" ({industry})"

                    # 评分颜色
                    score_icon = "🟢" if score >= 7 else "🟡" if score >= 5 else "🔴"

                    with st.expander(f"{score_icon} {title}"):
                        # 内容和线索来源
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown("**📝 匹配内容**")
                            st.caption(content_text + "..." if len(content_snap.get("raw_text", "")) > 60 else content_text)
                        with col_b:
                            st.markdown("**👤 匹配线索**")
                            st.write(f"公司: {company}")
                            if industry and industry != "未知":
                                st.write(f"行业: {industry}")

                        st.markdown("---")

                        # 完整匹配原因（不截断）
                        st.markdown("**匹配分析**")
                        st.write(reason)

                        # 维度评分
                        ds = mr.get("dimension_scores", {})
                        if ds:
                            st.markdown("**维度评分**")
                            self._render_dimension_scores(ds, columns=5)

                        # 匹配建议
                        suggestion = mr.get("suggestion", "")
                        if suggestion:
                            st.markdown("---")
                            st.markdown("**💡 建议**")
                            st.write(suggestion)
            else:
                empty_state(
                    title="暂无匹配记录",
                    description="请先进行内容-线索匹配",
                    icon="&#127919;",
                )
        except Exception as e:
            callout(f"加载失败: {str(e)}", type="error")


def render_match_center():
    """页面入口函数"""
    page = MatchCenterPage()
    page.render()
