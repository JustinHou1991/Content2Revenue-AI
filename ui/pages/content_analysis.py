"""
内容分析页面 - 抖音脚本特征提取
使用新设计系统组件 (design_system.py + styles.py)
继承自 AnalysisPage 基类
"""

import streamlit as st
import threading
import logging

logger = logging.getLogger(__name__)

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
        """渲染批量导入界面（支持 CSV/Excel/Word/PDF）"""
        st.subheader("批量导入脚本")

        uploaded_file = st.file_uploader(
            "上传文件（支持 CSV、Excel、Word、PDF）",
            type=["csv", "xlsx", "xls", "docx", "doc", "pdf"],
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

            # 读取文件并显示字段映射
            if st.session_state.content_df is None:
                import io
                file_type = uploaded_file.name.lower().split(".")[-1]

                if file_type in ["xlsx", "xls"]:
                    st.session_state.content_df = pd.read_excel(uploaded_file)
                elif file_type == "pdf":
                    st.session_state.content_df = self._parse_pdf(uploaded_file)
                elif file_type in ["docx", "doc"]:
                    st.session_state.content_df = self._parse_word(uploaded_file)
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

            if df is None or len(df) == 0:
                callout("文件解析失败或无有效内容", type="error")
                return

            # ===== 简化的字段映射：只需选择"脚本内容"列 =====
            st.markdown("---")
            st.subheader("📋 选择脚本内容列")
            st.caption("系统需要知道哪一列包含脚本/文案内容")

            # 自动检测最可能的"脚本内容"列
            from utils.field_mapping import REVERSE_MAPPING
            auto_col = None
            for col in df.columns:
                col_lower = str(col).lower().strip()
                if col_lower in REVERSE_MAPPING and REVERSE_MAPPING[col_lower] == "脚本内容":
                    auto_col = col
                    break
                for keyword in ["脚本", "文案", "内容", "正文", "text", "content"]:
                    if keyword in col_lower:
                        auto_col = col
                        break
                if auto_col:
                    break

            # 如果没找到，选第一个文本内容较长的列
            if auto_col is None:
                for col in df.columns:
                    if df[col].dtype == "object" and df[col].notna().any():
                        sample = str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else ""
                        if len(sample) > 20:
                            auto_col = col
                            break

            col_options = ["-- 请选择 --"] + list(df.columns)
            default_idx = col_options.index(auto_col) if auto_col and auto_col in col_options else 0

            selected_col = st.selectbox(
                "脚本内容列",
                col_options,
                index=default_idx,
                help="选择包含脚本/文案内容的列",
            )

            if selected_col != "-- 请选择 --":
                st.session_state.content_field_mapping = {"脚本内容": selected_col}
                st.success(f"✅ 已选择「{selected_col}」作为脚本内容列（共 {len(df)} 条记录）")

                with st.expander("预览数据"):
                    st.dataframe(df[[selected_col]].head(3), use_container_width=True)

                batch_btn = st.button(
                    f"开始批量分析（{len(df)} 条脚本）",
                    type="primary",
                    use_container_width=True,
                )

                if batch_btn or st.session_state.get("batch_state", {}).get("running"):
                    self._handle_batch_analysis()
            else:
                st.warning("请选择包含脚本内容的列")
        else:
            st.session_state.content_df = None
            st.session_state.content_field_mapping = None

    def _handle_batch_analysis(self):
        """处理批量分析逻辑（状态机模式，逐条分析避免超时）"""
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

        total = len(scripts)

        # 初始化批量分析状态
        if "batch_state" not in st.session_state or st.session_state.batch_state.get("total") != total:
            st.session_state.batch_state = {
                "scripts": scripts,
                "total": total,
                "current": 0,
                "results": [],
                "running": True,
            }
            logger.info("初始化批量分析状态，共 %d 条脚本", total)

        state = st.session_state.batch_state

        # 如果已经完成，直接展示结果
        if not state["running"]:
            self._show_batch_results(state)
            return

        # 显示进度
        current = state["current"]
        progress_bar = st.progress(current / total, text=f"正在分析第 {current + 1}/{total} 条...")

        # 取消按钮
        if st.button("取消分析", type="secondary"):
            state["running"] = False
            callout(f"分析已取消，已完成 {current}/{total} 条", type="warning")
            progress_bar.empty()
            self._show_batch_results(state)
            return

        # 分析当前脚本
        if current < total:
            script = state["scripts"][current]
            try:
                logger.info("正在分析第 %d/%d 条脚本 (script_id=%s)", current + 1, total, script.get("script_id"))

                single_result = self._get_orchestrator().content_analyzer.analyze(
                    script_text=script["script_text"],
                    script_id=script["script_id"],
                )

                logger.info("第 %d 条脚本分析完成，content_id=%s", current + 1, single_result.get("content_id"))

                # 保存到数据库
                self._get_orchestrator().db.save_content_analysis(single_result)
                state["results"].append({
                    "success": True,
                    "index": current,
                    "data": single_result,
                })
            except Exception as e:
                logger.error("第 %d 条脚本分析失败: %s", current + 1, e)
                state["results"].append({
                    "success": False,
                    "index": current,
                    "error": str(e),
                })

            # 更新进度并触发下一次分析
            state["current"] = current + 1
            if state["current"] >= total:
                state["running"] = False
            st.rerun()

        # 完成
        progress_bar.empty()
        self._show_batch_results(state)

    def _show_batch_results(self, state: dict):
        """展示批量分析结果"""
        results = state["results"]
        total = state["total"]
        success_count = sum(1 for r in results if r.get("success"))
        fail_count = sum(1 for r in results if not r.get("success"))

        # 验证数据库实际保存数量
        try:
            db_count = len(self._get_orchestrator().db.get_all_content_analyses())
        except Exception:
            db_count = -1

        msg = f"批量分析完成！成功 {success_count}/{total} 条"
        if fail_count > 0:
            msg += f"（{fail_count} 条失败）"
        if db_count >= 0:
            msg += f" | 数据库共 {db_count} 条记录"
        callout(msg, type="success", icon="&#10003;")

        # 展示结果
        divider()
        st.subheader("分析结果")

        for r in results:
            if r.get("success"):
                cid = r["data"].get("content_id", "")[:8]
                with st.expander(
                    f"#{r['index']+1} [{cid}] - 评分 {r['data']['analysis'].get('content_score', 'N/A')}/10"
                ):
                    self._display_analysis(r["data"]["analysis"])
            else:
                with st.expander(f"脚本 #{r['index']+1} - 分析失败"):
                    st.error(r.get("error", "未知错误"))

        # 清理状态
        st.session_state.content_df = None
        st.session_state.content_field_mapping = None
        if "batch_state" in st.session_state:
            del st.session_state.batch_state

    def _parse_pdf(self, uploaded_file) -> "pd.DataFrame":
        """解析 PDF 文件，提取文本内容

        优先提取表格，其次按页提取文本
        """
        import pandas as pd
        import io

        try:
            # 优先使用 pdfplumber（更好的表格支持）
            try:
                import pdfplumber

                with pdfplumber.open(uploaded_file) as pdf:
                    # 1. 尝试提取所有表格
                    all_tables = []
                    for page in pdf.pages:
                        tables = page.extract_tables()
                        for table in tables:
                            # 清理表格数据
                            cleaned = []
                            for row in table:
                                cleaned_row = [
                                    (cell or "").strip() for cell in row
                                ]
                                if any(cleaned_row):
                                    cleaned.append(cleaned_row)
                            if cleaned:
                                all_tables.extend(cleaned)

                    if all_tables and len(all_tables) > 1:
                        # 有表格数据，第一行作为表头
                        df = pd.DataFrame(all_tables[1:], columns=all_tables[0])
                        # 过滤掉全空行
                        df = df.dropna(how="all")
                        st.success(f"✅ 成功从 PDF 表格提取 {len(df)} 条记录")
                        return df

                    # 2. 没有表格，按页提取文本
                    texts = []
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text()
                        if text and text.strip():
                            texts.append({
                                "脚本内容": text.strip(),
                                "页码": i + 1,
                            })

                    if texts:
                        df = pd.DataFrame(texts)
                        st.success(f"✅ 成功从 PDF 提取 {len(df)} 页内容")
                        return df

            except ImportError:
                pass

            # 回退到 PyPDF2
            from PyPDF2 import PdfReader

            pdf_reader = PdfReader(uploaded_file)
            texts = []
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    texts.append({
                        "脚本内容": text.strip(),
                        "页码": i + 1,
                    })

            if not texts:
                st.warning("PDF 文件未提取到有效文本内容")
                return pd.DataFrame()

            df = pd.DataFrame(texts)
            st.success(f"✅ 成功从 PDF 提取 {len(df)} 页内容")
            return df

        except Exception as e:
            st.error(f"PDF 解析失败: {str(e)}")
            return pd.DataFrame()

    def _parse_word(self, uploaded_file) -> "pd.DataFrame":
        """解析 Word 文件，提取文本内容

        支持两种模式：
        1. 每个 Word 段落作为一条脚本（如果段落较长）
        2. 如果文档包含表格，尝试提取为结构化数据
        """
        import pandas as pd
        from docx import Document
        import io

        try:
            doc = Document(uploaded_file)

            # 先尝试提取表格
            tables_data = []
            for table in doc.tables:
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    if any(row_data):  # 跳过空行
                        tables_data.append(row_data)

            if tables_data and len(tables_data) > 1:
                # 有表格数据，第一行作为表头
                df = pd.DataFrame(tables_data[1:], columns=tables_data[0])
                st.success(f"✅ 成功从 Word 表格提取 {len(df)} 条记录")
                return df

            # 没有表格，提取段落文本
            paragraphs = []
            for i, para in enumerate(doc.paragraphs):
                text = para.text.strip()
                # 只保留较长的段落（可能是脚本内容）
                if text and len(text) > 20:
                    paragraphs.append({
                        "脚本内容": text,
                        "段落": i + 1,
                    })

            if not paragraphs:
                st.warning("Word 文档未提取到有效文本内容")
                return pd.DataFrame()

            df = pd.DataFrame(paragraphs)
            st.success(f"✅ 成功从 Word 提取 {len(df)} 个段落")
            return df

        except Exception as e:
            st.error(f"Word 解析失败: {str(e)}")
            return pd.DataFrame()

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
                rid = record.get("id", "")[:8]

                with st.expander(
                    f"[{rid}] 评分 {score}/10 | {hook_type} | {record['created_at'][:10]}"
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
