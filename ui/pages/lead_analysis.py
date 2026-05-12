"""
线索分析页面 - 销售线索画像构建
使用新设计系统组件 (design_system.py + styles.py)
继承自 AnalysisPage 基类
"""

import streamlit as st
import threading
import pandas as pd

from ui.base_page import AnalysisPage
from ui.components.forms import render_lead_form, render_action_buttons
from ui.components.data_display import (
    render_lead_profile_details,
    render_list_section,
)
from ui.components.design_system import (
    page_header,
    metric_card,
    divider,
    callout,
    empty_state,
)
from ui.styles import COLORS

MAX_CSV_SIZE = 10 * 1024 * 1024  # 10MB


class LeadAnalysisPage(AnalysisPage):
    """线索分析页面类"""

    def __init__(self):
        super().__init__(
            title="线索智能分析",
            icon="&#128100;",
            description="分析销售线索，构建客户画像：行业、痛点、购买阶段、意向度等",
            page_prefix="lead"
        )

    def _render_single_input(self):
        """渲染单个线索录入界面"""
        st.subheader("录入线索信息")

        lead_data = render_lead_form()

        analyze_btn, _ = render_action_buttons("开始分析")

        if analyze_btn:
            if not lead_data.get("company") and not lead_data.get("conversation"):
                callout("请至少填写公司名称或对话记录", type="warning")
                return

            with st.spinner("AI正在分析线索..."):
                try:
                    result = self._get_orchestrator().analyze_lead(lead_data)
                    self._display_result(result)
                except Exception as e:
                    callout(f"分析失败: {str(e)}", type="error")
                    st.info("请检查API Key是否有效，或稍后重试。")

    def _render_batch_input(self):
        """渲染批量导入界面（支持 CSV/Excel）"""
        st.subheader("批量导入线索")

        uploaded_file = st.file_uploader(
            "上传文件（支持 CSV、Excel .xlsx）",
            type=["csv", "xlsx", "xls"],
            key="lead_batch_file"
        )

        # 字段映射状态管理
        if "lead_field_mapping" not in st.session_state:
            st.session_state.lead_field_mapping = None
        if "lead_df" not in st.session_state:
            st.session_state.lead_df = None

        if uploaded_file is not None:
            if uploaded_file.size > MAX_CSV_SIZE:
                callout(f"文件大小超过限制（最大 {MAX_CSV_SIZE // (1024*1024)}MB）", type="error")
                return

            from utils.field_mapping import (
                detect_columns,
                show_mapping_preview,
                validate_mapping_for_analysis,
            )

            # 读取CSV或Excel并显示字段映射
            if st.session_state.lead_df is None:
                file_type = uploaded_file.name.lower().split(".")[-1]
                if file_type in ["xlsx", "xls"]:
                    st.session_state.lead_df = pd.read_excel(uploaded_file)
                else:
                    # 尝试多种编码读取CSV
                    try:
                        st.session_state.lead_df = pd.read_csv(uploaded_file, encoding="utf-8")
                    except UnicodeDecodeError:
                        try:
                            st.session_state.lead_df = pd.read_csv(uploaded_file, encoding="gbk")
                        except UnicodeDecodeError:
                            st.session_state.lead_df = pd.read_csv(uploaded_file, encoding="latin-1")

            df = st.session_state.lead_df

            # 显示字段映射预览
            st.markdown("---")
            auto_mapping = detect_columns(df.columns.tolist())
            user_mapping = show_mapping_preview(auto_mapping, df.columns.tolist())

            # 验证映射
            is_valid, missing_fields = validate_mapping_for_analysis(
                user_mapping, "lead"
            )

            if not is_valid:
                callout(f"缺少必需字段: {', '.join(missing_fields)}", type="error")
                st.info("请在上方映射表中选择'需求描述'对应的CSV列")
            else:
                st.session_state.lead_field_mapping = user_mapping

            # 批量分析按钮
            batch_btn = st.button("开始批量分析", type="primary", use_container_width=True)

            if batch_btn:
                self._handle_batch_analysis()
        else:
            st.session_state.lead_df = None
            st.session_state.lead_field_mapping = None

    def _handle_batch_analysis(self):
        """处理批量分析逻辑"""
        from utils.field_mapping import normalize_columns

        if st.session_state.lead_field_mapping is None:
            callout("请先完成字段映射", type="error")
            return

        mapping = st.session_state.lead_field_mapping
        df = st.session_state.lead_df

        # 检查必需的需求描述字段
        if "需求描述" not in mapping:
            callout("缺少必需的'需求描述'字段映射", type="error")
            return

        # 标准化列名
        df_normalized = normalize_columns(df, {k: v for k, v in mapping.items()})

        # 准备线索数据
        leads = []
        for idx, row in df_normalized.iterrows():
            lead_data = {}

            # 优先使用需求描述字段
            if "需求描述" in mapping:
                conversation = str(row.get("需求描述", ""))
                if conversation and conversation.strip() and conversation.lower() != "nan":
                    lead_data["conversation"] = conversation

            # 添加其他字段
            for standard_field, original_col in mapping.items():
                if original_col in df.columns:
                    value = row.get(standard_field, "")
                    if pd.notna(value) and str(value).lower() != "nan":
                        # 映射标准字段到lead_data的键名
                        field_key_map = {
                            "联系人": "name",
                            "公司名称": "company",
                            "行业": "industry",
                            "需求描述": "conversation",
                        }
                        key = field_key_map.get(standard_field, standard_field)
                        lead_data[key] = str(value)

            if lead_data:
                leads.append({
                    "lead_data": lead_data,
                    "lead_id": str(idx),
                })

        if not leads:
            callout("未找到有效的线索数据，请检查字段映射", type="error")
            return

        # 创建取消事件
        cancel_event = threading.Event()

        # 显示进度和取消按钮
        progress_container = st.container()
        with progress_container:
            col1, col2 = st.columns([4, 1])
            with col1:
                progress_bar = st.progress(0, text="准备开始批量分析...")
            with col2:
                cancel_btn = st.button(
                    "取消分析", type="secondary", use_container_width=True
                )

        if cancel_btn:
            cancel_event.set()
            callout("已取消分析", type="warning")
            return

        # 执行批量分析
        results = []
        try:
            for i, lead in enumerate(leads):
                # 检查取消事件
                if cancel_event.is_set():
                    callout(f"分析已取消，已完成 {i}/{len(leads)} 条", type="warning")
                    break

                try:
                    single_result = self._get_orchestrator().analyze_lead(
                        lead["lead_data"]
                    )
                    results.append({
                        "success": True,
                        "index": i,
                        "data": single_result,
                    })
                except Exception as e:
                    results.append({
                        "success": False,
                        "index": i,
                        "error": str(e),
                    })

                # 更新进度
                progress_bar.progress(
                    (i + 1) / len(leads),
                    text=f"正在分析... ({i + 1}/{len(leads)})",
                )

                # 检查取消按钮是否被点击
                if st.session_state.get("cancel_batch_analysis"):
                    break

            progress_bar.empty()

            # 显示结果统计
            success_count = sum(1 for r in results if r.get("success"))
            processed_count = len(results)

            if cancel_event.is_set() or st.session_state.get("cancel_batch_analysis"):
                callout(
                    f"批量分析已取消！成功 {success_count}/{processed_count} 条（共 {len(leads)} 条）",
                    type="warning",
                )
            else:
                callout(
                    f"批量分析完成！成功 {success_count}/{len(leads)} 条",
                    type="success",
                    icon="&#10003;",
                )

            # 保存结果到数据库
            saved_count = 0
            for r in results:
                if r.get("success"):
                    try:
                        self._get_orchestrator().db.save_lead_analysis(r["data"])
                        saved_count += 1
                    except Exception as e:
                        st.warning(f"保存结果失败: {e}")

            if saved_count > 0:
                st.info(f"已保存 {saved_count} 条分析结果到数据库")

            # 展示结果
            divider()
            st.subheader("分析结果")

            for r in results:
                if r.get("success"):
                    profile = r["data"]["profile"]
                    with st.expander(
                        f"线索 #{r['index']+1} - 评分 {profile.get('lead_score', 'N/A')}/100 ({profile.get('lead_grade', 'N/A')})"
                    ):
                        self._display_profile(profile)
                else:
                    with st.expander(f"线索 #{r['index']+1} - 分析失败"):
                        st.error(r.get("error", "未知错误"))

        except Exception as e:
            callout(f"批量分析失败: {str(e)}", type="error")

        # 清理状态
        st.session_state.lead_df = None
        st.session_state.lead_field_mapping = None

    def _display_result(self, result: dict):
        """展示单个分析结果"""
        profile = result["profile"]
        lead_id = result["lead_id"]

        callout(f"分析完成！ID: {lead_id[:8]}...", type="success", icon="&#10003;")

        # 核心指标
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card(
                title="线索评分",
                value=f"{profile.get('lead_score', 'N/A')}/100",
                subtitle="线索质量综合评分",
                icon="&#128200;",
                border_color="#6366F1",
            )
        with col2:
            metric_card(
                title="线索等级",
                value=profile.get("lead_grade", "N/A"),
                subtitle="A(85+) / B+(70+) / B(55+) / C(40+) / D(<40)",
                icon="&#127942;",
                border_color="#10B981",
            )
        with col3:
            metric_card(
                title="购买意向",
                value=f"{profile.get('intent_level', 'N/A')}/10",
                subtitle="购买意向度",
                icon="&#128065;",
                border_color="#F59E0B",
            )

        divider()
        self._display_profile(profile)

    def _display_profile(self, profile: dict):
        """展示线索画像详情"""
        render_lead_profile_details(profile)

        divider()

        col1, col2 = st.columns(2)
        with col1:
            render_list_section("决策标准", profile.get("decision_criteria", []))

        with col2:
            render_list_section("异议风险", profile.get("objection_risks", []))

        divider()

        st.markdown("#### 互动策略建议")
        st.info(profile.get("engagement_strategy", "暂无建议"))
        st.write(f"推荐内容类型: **{profile.get('recommended_content_type', '未知')}**")
        st.write(f"推荐CTA类型: **{profile.get('recommended_cta', '未知')}**")

    def _render_history(self):
        """展示历史记录"""
        st.subheader("历史分析记录")
        try:
            # 分页参数
            page_size = 10
            page = self._get_current_page("lead_history")

            # 获取总数
            total_count = self._get_orchestrator().db.get_lead_analyses_count()

            if total_count == 0:
                empty_state(
                    title="暂无历史记录",
                    description="去上方录入线索开始分析吧！",
                    icon="&#128101;",
                )
                return

            # 获取当前页数据
            offset = page * page_size
            records = self._get_orchestrator().db.get_all_lead_analyses(
                limit=page_size, offset=offset
            )

            if not records:
                empty_state(
                    title="暂无历史记录",
                    description="没有找到匹配的记录。",
                    icon="&#128101;",
                )
                return

            for record in records:
                profile = record.get("profile_json", {})
                score = profile.get("lead_score", "N/A")
                grade = profile.get("lead_grade", "N/A")
                industry = profile.get("industry", "未知")
                raw = record.get("raw_data_json", {})
                company = raw.get("company", raw.get("公司名称", "未知"))

                with st.expander(f"{grade} | {score}/100 | {industry} | {company}"):
                    self._display_profile(profile)

            # 分页控制
            self._render_pagination(total_count, page_size, "lead_history")

        except Exception as e:
            callout(f"加载历史记录失败: {str(e)}", type="error")


def render_lead_analysis():
    """页面入口函数"""
    page = LeadAnalysisPage()
    page.render()
