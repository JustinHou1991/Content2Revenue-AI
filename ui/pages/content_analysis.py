"""
内容分析页面 - 抖音脚本特征提取
使用新设计系统组件 (design_system.py + styles.py)
"""

import streamlit as st
import threading

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


def _safe_badge(label, icon=None):
    """安全渲染标签，兼容旧版 Streamlit（< 1.37）。

    st.badge() 从 Streamlit 1.37 开始支持，旧版本使用 markdown 标签样式作为降级方案。
    """
    try:
        st.badge(label, icon=icon)
    except (AttributeError, Exception):
        # 降级：使用新设计系统的 status_badge 组件
        status_badge(label, color="purple", size="sm")


def render_content_analysis():
    """渲染内容分析页面"""
    # 页面头部
    page_header(
        title="内容智能分析",
        subtitle="分析抖音脚本，提取Hook类型、情感基调、叙事结构、CTA等特征",
    )

    if not st.session_state.get("initialized"):
        callout(
            "请先在「系统设置」中配置API Key。配置好API Key后，系统会自动保存配置，刷新页面也不会丢失。",
            type="warning",
            icon="&#9888;",
        )
        return

    # 输入区域
    st.subheader("输入抖音脚本")

    tab1, tab2 = st.tabs(["手动输入", "批量导入"])

    with tab1:
        script_text = st.text_area(
            "粘贴脚本内容",
            height=200,
            placeholder="例：你是不是还在用传统方式获客？每天花500块投流，一个询盘都没有？...",
        )
        analyze_btn = st.button("开始分析", type="primary", use_container_width=True)

    with tab2:
        uploaded_file = st.file_uploader(
            "上传CSV文件（支持自动识别'完整脚本'、'脚本'、'content'、'text'等列）",
            type=["csv"],
        )

        # 字段映射状态管理
        if "content_field_mapping" not in st.session_state:
            st.session_state.content_field_mapping = None
        if "content_df" not in st.session_state:
            st.session_state.content_df = None

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
                if st.session_state.content_df is None:
                    st.session_state.content_df = pd.read_csv(uploaded_file)

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
                batch_btn = st.button(
                    "开始批量分析", type="primary", use_container_width=True
                )
        else:
            batch_btn = False
            st.session_state.content_df = None
            st.session_state.content_field_mapping = None

    divider()

    # 分析结果展示
    if analyze_btn and script_text:
        with st.spinner("AI正在分析脚本..."):
            try:
                result = st.session_state.orchestrator.analyze_content(script_text)
                _display_result(result)
            except Exception as e:
                callout(f"分析失败: {str(e)}", type="error")
                st.info("请检查API Key是否有效，或稍后重试。")

    elif analyze_btn and not script_text:
        callout("请先输入脚本内容", type="warning")

    elif batch_btn and uploaded_file:
        _handle_batch_analysis()

    elif batch_btn and not uploaded_file:
        callout("请先上传CSV文件", type="warning")

    # 历史记录
    divider()
    _display_history()


def _handle_batch_analysis():
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
            scripts.append(
                {
                    "script_text": script_text,
                    "script_id": str(idx),
                }
            )

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
                single_result = st.session_state.orchestrator.analyze_content(
                    script["script_text"]
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
                (i + 1) / len(scripts),
                text=f"正在分析... ({i + 1}/{len(scripts)})",
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
                    st.session_state.orchestrator.db.save_content_analysis(
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
                with st.expander(
                    f"脚本 #{r['index']+1} - 评分 {r['data']['analysis'].get('content_score', 'N/A')}/10"
                ):
                    _display_analysis(r["data"]["analysis"])
            else:
                with st.expander(f"脚本 #{r['index']+1} - 分析失败"):
                    st.error(r.get("error", "未知错误"))

    except Exception as e:
        callout(f"批量分析失败: {str(e)}", type="error")

    # 清理状态
    st.session_state.content_df = None
    st.session_state.content_field_mapping = None


def _display_result(result: dict):
    """展示单个分析结果"""
    analysis = result["analysis"]
    content_id = result["content_id"]

    callout(f"分析完成！ID: {content_id[:8]}...", type="success", icon="&#10003;")

    # 核心指标 - 使用新的 metric_card 组件
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
    _display_analysis(analysis)


def _display_analysis(analysis: dict):
    """展示分析详情"""
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

    divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 话题标签")
        tags = analysis.get("topic_tags", [])
        if tags:
            for tag in tags:
                _safe_badge(tag)
        else:
            st.write("无")

    with col2:
        st.markdown("#### 目标受众")
        st.write(analysis.get("target_audience", "未知"))

    divider()

    st.markdown("#### 核心卖点")
    for point in analysis.get("key_selling_points", []):
        st.write(f"- {point}")

    st.markdown("#### 改进建议")
    for suggestion in analysis.get("improvement_suggestions", []):
        st.write(f"- {suggestion}")


def _display_history():
    """展示历史分析记录（带分页）"""
    st.subheader("历史分析记录")
    try:
        # 分页参数
        page_size = 10
        if "content_history_page" not in st.session_state:
            st.session_state.content_history_page = 0

        # 获取总数
        total_count = st.session_state.orchestrator.db.get_content_analyses_count()

        if total_count == 0:
            empty_state(
                title="暂无历史记录",
                description="去上方输入脚本开始分析吧！",
                icon="&#128218;",
            )
            return

        # 获取当前页数据
        offset = st.session_state.content_history_page * page_size
        records = st.session_state.orchestrator.db.get_all_content_analyses(
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
                    _display_analysis(analysis)

        # 分页控制
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button(
                    "上一页",
                    disabled=(st.session_state.content_history_page <= 0),
                    key="content_prev",
                ):
                    st.session_state.content_history_page -= 1
                    st.rerun()
            with col2:
                st.caption(
                    f"第 {st.session_state.content_history_page + 1} / {total_pages} 页（共 {total_count} 条）"
                )
            with col3:
                if st.button(
                    "下一页",
                    disabled=(st.session_state.content_history_page >= total_pages - 1),
                    key="content_next",
                ):
                    st.session_state.content_history_page += 1
                    st.rerun()

    except Exception as e:
        callout(f"加载历史记录失败: {str(e)}", type="error")
