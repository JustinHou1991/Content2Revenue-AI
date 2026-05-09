"""
线索分析页面 - 销售线索画像构建
使用新设计系统组件 (design_system.py + styles.py)
"""

import streamlit as st
import threading

from ui.components.design_system import (
    page_header,
    metric_card,
    divider,
    callout,
    empty_state,
)
from ui.styles import COLORS

MAX_CSV_SIZE = 10 * 1024 * 1024  # 10MB


def render_lead_analysis():
    """渲染线索分析页面"""
    # 页面头部
    page_header(
        title="线索智能分析",
        subtitle="分析销售线索，构建客户画像：行业、痛点、购买阶段、意向度等",
    )

    if not st.session_state.get("initialized"):
        callout(
            "请先在「系统设置」中配置API Key。配置好API Key后，系统会自动保存配置，刷新页面也不会丢失。",
            type="warning",
            icon="&#9888;",
        )
        return

    # 输入区域
    st.subheader("录入线索信息")

    tab1, tab2 = st.tabs(["手动录入", "批量导入"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("联系人姓名", placeholder="张总")
            company = st.text_input("公司名称", placeholder="XX教育科技")
            industry = st.text_input("所属行业", placeholder="教育培训")
            title = st.text_input("职位/角色", placeholder="创始人/总监")

        with col2:
            source = st.selectbox(
                "线索来源", ["抖音私信", "抖音评论", "官网", "转介绍", "展会", "其他"]
            )
            company_size = st.selectbox(
                "公司规模", ["1-10人", "10-50人", "50-200人", "200-500人", "500+人"]
            )
            intent_level = st.selectbox("初步意向", ["高", "中", "低", "未知"])

        conversation = st.text_area(
            "对话记录 / 需求描述",
            height=120,
            placeholder="例：看了你们的视频，我们公司目前获客成本太高了，想了解一下你们的方案...",
        )
        remark = st.text_area("备注", height=60, placeholder="其他补充信息...")

        analyze_btn = st.button("开始分析", type="primary", use_container_width=True)

    with tab2:
        uploaded_file = st.file_uploader(
            "上传CSV文件（支持自动识别'需求描述'、'对话记录'、'requirement'等列）",
            type=["csv"],
        )

        # 字段映射状态管理
        if "lead_field_mapping" not in st.session_state:
            st.session_state.lead_field_mapping = None
        if "lead_df" not in st.session_state:
            st.session_state.lead_df = None

        if uploaded_file is not None:
            if uploaded_file.size > MAX_CSV_SIZE:
                callout(f"文件大小超过限制（最大 {MAX_CSV_SIZE // (1024*1024)}MB）", type="error")
                batch_btn = False
            else:
                import pandas as pd
                from utils.field_mapping import (
                    detect_columns,
                    show_mapping_preview,
                    validate_mapping_for_analysis,
                )

                # 读取CSV并显示字段映射
                if st.session_state.lead_df is None:
                    st.session_state.lead_df = pd.read_csv(uploaded_file)

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
                batch_btn = st.button(
                    "开始批量分析", type="primary", use_container_width=True
                )
        else:
            batch_btn = False
            st.session_state.lead_df = None
            st.session_state.lead_field_mapping = None

    divider()

    # 处理手动录入
    if analyze_btn:
        if not company and not conversation:
            callout("请至少填写公司名称或对话记录", type="warning")
            return

        lead_data = {
            "name": name,
            "company": company,
            "industry": industry,
            "title": title,
            "source": source,
            "company_size": company_size,
            "intent_level": intent_level,
            "conversation": conversation,
            "remark": remark,
        }

        with st.spinner("AI正在分析线索..."):
            try:
                result = st.session_state.orchestrator.analyze_lead(lead_data)
                _display_result(result)
            except Exception as e:
                callout(f"分析失败: {str(e)}", type="error")
                st.info("请检查API Key是否有效，或稍后重试。")

    # 处理批量导入
    elif batch_btn and uploaded_file:
        _handle_batch_analysis()

    elif batch_btn and not uploaded_file:
        callout("请先上传CSV文件", type="warning")

    # 历史记录
    divider()
    _display_history()


def _handle_batch_analysis():
    """处理批量分析逻辑"""
    import pandas as pd
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
            leads.append(
                {
                    "lead_data": lead_data,
                    "lead_id": str(idx),
                }
            )

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
                single_result = st.session_state.orchestrator.analyze_lead(
                    lead["lead_data"]
                )
                results.append(
                    {
                        "success": True,
                        "index": i,
                        "data": single_result,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "success": False,
                        "index": i,
                        "error": str(e),
                    }
                )

            # 更新进度
            progress_bar.progress(
                (i + 1) / len(leads),
                text=f"正在分析... ({i + 1}/{len(leads)})",
            )

            # 检查取消按钮是否被点击（通过session_state）
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
                    st.session_state.orchestrator.db.save_lead_analysis(
                        r["data"]
                    )
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
                    _display_profile(profile)
            else:
                with st.expander(f"线索 #{r['index']+1} - 分析失败"):
                    st.error(r.get("error", "未知错误"))

    except Exception as e:
        callout(f"批量分析失败: {str(e)}", type="error")

    # 清理状态
    st.session_state.lead_df = None
    st.session_state.lead_field_mapping = None


def _display_result(result: dict):
    """展示单个分析结果"""
    profile = result["profile"]
    lead_id = result["lead_id"]

    callout(f"分析完成！ID: {lead_id[:8]}...", type="success", icon="&#10003;")

    # 核心指标 - 使用新的 metric_card 组件
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
    _display_profile(profile)


def _display_profile(profile: dict):
    """展示线索画像详情"""
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

    divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 决策标准")
        for criteria in profile.get("decision_criteria", []):
            st.write(f"- {criteria}")

    with col2:
        st.markdown("#### 异议风险")
        for risk in profile.get("objection_risks", []):
            st.write(f"- {risk}")

    divider()

    st.markdown("#### 互动策略建议")
    st.info(profile.get("engagement_strategy", "暂无建议"))
    st.write(f"推荐内容类型: **{profile.get('recommended_content_type', '未知')}**")
    st.write(f"推荐CTA类型: **{profile.get('recommended_cta', '未知')}**")


def _display_history():
    """展示历史记录（带分页）"""
    st.subheader("历史分析记录")
    try:
        # 分页参数
        page_size = 10
        if "lead_history_page" not in st.session_state:
            st.session_state.lead_history_page = 0

        # 获取总数
        total_count = st.session_state.orchestrator.db.get_lead_analyses_count()

        if total_count == 0:
            empty_state(
                title="暂无历史记录",
                description="去上方录入线索开始分析吧！",
                icon="&#128101;",
            )
            return

        # 获取当前页数据
        offset = st.session_state.lead_history_page * page_size
        records = st.session_state.orchestrator.db.get_all_lead_analyses(
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
                _display_profile(profile)

        # 分页控制
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button(
                    "上一页",
                    disabled=(st.session_state.lead_history_page <= 0),
                    key="lead_prev",
                ):
                    st.session_state.lead_history_page -= 1
                    st.rerun()
            with col2:
                st.caption(
                    f"第 {st.session_state.lead_history_page + 1} / {total_pages} 页（共 {total_count} 条）"
                )
            with col3:
                if st.button(
                    "下一页",
                    disabled=(st.session_state.lead_history_page >= total_pages - 1),
                    key="lead_next",
                ):
                    st.session_state.lead_history_page += 1
                    st.rerun()

    except Exception as e:
        callout(f"加载历史记录失败: {str(e)}", type="error")
