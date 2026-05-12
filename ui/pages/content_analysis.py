"""
内容分析页面 - 抖音脚本特征提取
使用新设计系统组件 (design_system.py + styles.py)
继承自 AnalysisPage 基类
"""

import streamlit as st
import threading

from ui.base_page import AnalysisPage
from ui.components.forms import render_text_area, render_action_buttons
from ui.components.data_display import (
    render_content_analysis_details,
    render_list_section,
    render_tags,
)
from ui.components.design_system import (
    page_header,
    metric_card,
    status_badge,
    divider,
    callout,
    empty_state,
)
from ui.styles import COLORS

MAX_CSV_SIZE = 10 * 1024 * 1024  # 10MB


class ContentAnalysisPage(AnalysisPage):
    """内容分析页面类"""

    def __init__(self):
        super().__init__(
            title="内容智能分析",
            icon="&#128221;",
            description="分析抖音脚本，提取Hook类型、情感基调、叙事结构、CTA等特征",
            page_prefix="content"
        )

    def _render_single_input(self):
        """渲染单个脚本输入界面（支持文件上传）"""
        st.subheader("输入抖音脚本")

        # 文件上传
        uploaded_file = st.file_uploader(
            "上传文件（支持 PDF、Word、TXT）",
            type=["pdf", "docx", "doc", "txt", "md"],
            key="content_single_file"
        )

        # 如果有文件上传，解析内容
        file_text = ""
        if uploaded_file is not None:
            try:
                from utils.file_parser import parse_file, extract_text_for_analysis
                parse_result = parse_file(uploaded_file)
                file_text = extract_text_for_analysis(parse_result, max_length=3000)
                st.success(f"✅ 文件「{uploaded_file.name}」解析成功")
            except Exception as e:
                st.error(f"文件解析失败: {str(e)}")
                st.info("支持的格式：PDF、Word(.docx)、TXT、Markdown")

        # 文本输入框（文件内容自动填充）
        default_text = file_text if file_text else ""
        script_text = render_text_area(
            "粘贴脚本内容或直接编辑上传的文件内容",
            value=default_text,
            placeholder="例：你是不是还在用传统方式获客？每天花500块投流，一个询盘都没有？...",
            height=200
        )

        analyze_btn, _ = render_action_buttons("开始分析")

        if analyze_btn:
            if not script_text:
                callout("请先输入脚本内容或上传文件", type="warning")
                return

            with st.spinner("AI正在分析脚本..."):
                try:
                    result = self._get_orchestrator().analyze_content(script_text)
                    self._display_result(result)
                except Exception as e:
                    callout(f"分析失败: {str(e)}", type="error")
                    st.info("请检查API Key是否有效，或稍后重试。")

    def _render_batch_input(self):
        """渲染批量导入界面（支持 CSV/Excel）"""
        st.subheader("批量导入脚本")

        uploaded_file = st.file_uploader(
            "上传文件（支持 CSV、Excel .xlsx）",
            type=["csv", "xlsx", "xls"],
            key="content_batch_file"
        )

        # 字段映射状态管理
        if "content_field_mapping" not in st.session_state:
            st.session_state.content_field_mapping = None
        if "content_df" not in st.session_state:
            st.session_state.content_df = None

        if uploaded_file is not None:
            if uploaded_file.size > MAX_CSV_SIZE:
                callout(f"文件大小超过限制（最大 {MAX_CSV_SIZE // (1024*1024)}MB）", type="error")
                return

            import pandas as pd
            from utils.field_mapping import (
                detect_columns,
                show_mapping_preview,
                validate_mapping_for_analysis,
            )

            # 读取CSV或Excel并显示字段映射
            if st.session_state.content_df is None:
                import io
                file_type = uploaded_file.name.lower().split(".")[-1]
                if file_type in ["xlsx", "xls"]:
                    st.session_state.content_df = pd.read_excel(uploaded_file)
                else:
                    # CSV文件：先将内容读入内存，再用BytesIO解析
                    file_bytes = uploaded_file.getvalue()
                    csv_file = io.BytesIO(file_bytes)
                    
                    # 尝试多种编码和分隔符读取CSV
                    success = False
                    for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
                        if success:
                            break
                        for sep in [",", ";", "\t", "|"]:
                            try:
                                csv_file.seek(0)
                                df = pd.read_csv(csv_file, encoding=encoding, sep=sep, engine="python", on_bad_lines="skip")
                                if len(df.columns) > 1:
                                    st.session_state.content_df = df
                                    success = True
                                    break
                            except Exception:
                                continue
                    
                    if not success:
                        st.error("无法解析CSV文件，请检查文件格式或尝试使用Excel格式(.xlsx)")
                        return

            df = st.session_state.content_df

            # 显示字段映射预览
            st.markdown("---")
            auto_mapping = detect_columns(df.columns.tolist())
            user_mapping = show_mapping_preview(auto_mapping, df.columns.tolist())

            # 验证映射
            is_valid, missing_fields = validate_mapping_for_analysis(
                user_mapping, "content"
            )

            if not is_valid:
                callout(f"缺少必需字段: {', '.join(missing_fields)}", type="error")
                st.info("请在上方映射表中选择'脚本内容'对应的CSV列")
            else:
                st.session_state.content_field_mapping = user_mapping

            # 批量分析按钮
            batch_btn = st.button("开始批量分析", type="primary", use_container_width=True)

            if batch_btn:
                self._handle_batch_analysis()
        else:
            st.session_state.content_df = None
            st.session_state.content_field_mapping = None

    def _handle_batch_analysis(self):
        """处理批量分析逻辑"""
        from utils.field_mapping import normalize_columns

        if st.session_state.content_field_mapping is None:
            callout("请先完成字段映射", type="error")
            return

        mapping = st.session_state.content_field_mapping
        df = st.session_state.content_df

        # 检查必需的脚本内容字段
        if "脚本内容" not in mapping:
            callout("缺少必需的'脚本内容'字段映射", type="error")
            return

        # 标准化列名
        df_normalized = normalize_columns(df, {k: v for k, v in mapping.items()})

        # 准备脚本数据
        scripts = []
        for idx, row in df_normalized.iterrows():
            script_text = str(row.get("脚本内容", ""))
            if script_text and script_text.strip() and script_text.lower() != "nan":
                scripts.append({
                    "script_text": script_text,
                    "script_id": str(idx),
                })

        if not scripts:
            callout("未找到有效的脚本内容，请检查字段映射", type="error")
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
            for i, script in enumerate(scripts):
                # 检查取消事件
                if cancel_event.is_set():
                    callout(f"分析已取消，已完成 {i}/{len(scripts)} 条", type="warning")
                    break

                try:
                    single_result = self._get_orchestrator().analyze_content(
                        script["script_text"]
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
                    (i + 1) / len(scripts),
                    text=f"正在分析... ({i + 1}/{len(scripts)})",
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
                    f"批量分析已取消！成功 {success_count}/{processed_count} 条（共 {len(scripts)} 条）",
                    type="warning",
                )
            else:
                callout(
                    f"批量分析完成！成功 {success_count}/{len(scripts)} 条",
                    type="success",
                    icon="&#10003;",
                )

            # 保存结果到数据库
            saved_count = 0
            for r in results:
                if r.get("success"):
                    try:
                        self._get_orchestrator().db.save_content_analysis(r["data"])
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
                    with st.expander(
                        f"脚本 #{r['index']+1} - 评分 {r['data']['analysis'].get('content_score', 'N/A')}/10"
                    ):
                        self._display_analysis(r["data"]["analysis"])
                else:
                    with st.expander(f"脚本 #{r['index']+1} - 分析失败"):
                        st.error(r.get("error", "未知错误"))

        except Exception as e:
            callout(f"批量分析失败: {str(e)}", type="error")

        # 清理状态
        st.session_state.content_df = None
        st.session_state.content_field_mapping = None

    def _display_result(self, result: dict):
        """展示单个分析结果"""
        analysis = result["analysis"]
        content_id = result["content_id"]

        callout(f"分析完成！ID: {content_id[:8]}...", type="success", icon="&#10003;")

        # 核心指标
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card(
                title="综合评分",
                value=f"{analysis.get('content_score', 'N/A')}/10",
                subtitle="综合转化潜力评分",
                icon="&#128202;",
                border_color="#6366F1",
            )
        with col2:
            metric_card(
                title="Hook强度",
                value=f"{analysis.get('hook_strength', 'N/A')}/10",
                subtitle="开场钩子吸引力",
                icon="&#127908;",
                border_color="#10B981",
            )
        with col3:
            metric_card(
                title="CTA清晰度",
                value=f"{analysis.get('cta_clarity', 'N/A')}/10",
                subtitle="行动号召清晰程度",
                icon="&#128227;",
                border_color="#F59E0B",
            )

        divider()
        self._display_analysis(analysis)

    def _display_analysis(self, analysis: dict):
        """展示分析详情"""
        render_content_analysis_details(analysis)

        divider()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 话题标签")
            tags = analysis.get("topic_tags", [])
            render_tags(tags)

        with col2:
            st.markdown("#### 目标受众")
            st.write(analysis.get("target_audience", "未知"))

        divider()

        render_list_section("核心卖点", analysis.get("key_selling_points", []))
        render_list_section("改进建议", analysis.get("improvement_suggestions", []))

    def _render_history(self):
        """展示历史分析记录"""
        st.subheader("历史分析记录")
        try:
            # 分页参数
            page_size = 10
            page = self._get_current_page("content_history")

            # 获取总数
            total_count = self._get_orchestrator().db.get_content_analyses_count()

            if total_count == 0:
                empty_state(
                    title="暂无历史记录",
                    description="去上方输入脚本开始分析吧！",
                    icon="&#128218;",
                )
                return

            # 获取当前页数据
            offset = page * page_size
            records = self._get_orchestrator().db.get_all_content_analyses(
                limit=page_size, offset=offset
            )

            if not records:
                empty_state(
                    title="暂无历史记录",
                    description="没有找到匹配的记录。",
                    icon="&#128218;",
                )
                return

            for record in records:
                analysis = record.get("analysis_json", {})
                score = analysis.get("content_score", "N/A")
                hook_type = analysis.get("hook_type", "未知")
                raw_text = record.get("raw_text", "")[:60] + "..."

                with st.expander(
                    f"评分 {score}/10 | {hook_type} | {record['created_at'][:10]}"
                ):
                    st.write(raw_text)
                    if st.button("查看详情", key=f"detail_{record['id']}"):
                        self._display_analysis(analysis)

            # 分页控制
            self._render_pagination(total_count, page_size, "content_history")

        except Exception as e:
            callout(f"加载历史记录失败: {str(e)}", type="error")


def render_content_analysis():
    """页面入口函数"""
    page = ContentAnalysisPage()
    page.render()
