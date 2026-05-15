"""页面基类 - 提供公共的页面功能"""
import streamlit as st
from typing import Optional, Dict, Any, List, Callable
from abc import ABC, abstractmethod


class BasePage(ABC):
    """页面基类 - 提供统一的页面结构和公共功能"""

    def __init__(self, title: str, icon: str, description: str = ""):
        self.title = title
        self.icon = icon
        self.description = description

    def render(self):
        """渲染页面（模板方法）"""
        self._render_header()
        self._render_content()

    def _render_header(self):
        """渲染页面头部"""
        from ui.components.design_system import page_header
        page_header(title=f"{self.icon} {self.title}", subtitle=self.description)

    @abstractmethod
    def _render_content(self):
        """子类实现：渲染页面内容"""
        pass

    def _check_initialization(self) -> bool:
        """检查系统是否已初始化"""
        if not st.session_state.get("initialized"):
            from ui.components.design_system import callout
            callout(
                "请先在「系统设置」中配置API Key。配置好API Key后，系统会自动保存配置，刷新页面也不会丢失。",
                type="warning",
                icon="⚠️",
            )
            return False
        return True

    def _get_orchestrator(self):
        """获取编排器实例"""
        return st.session_state.get("orchestrator")

    def _render_empty_state(self, title: str, description: str, icon: str = "📭"):
        """渲染空状态"""
        from ui.components.design_system import empty_state
        empty_state(title=title, description=description, icon=icon)

    def _render_metric_cards(self, metrics: List[Dict[str, Any]]):
        """渲染指标卡片组"""
        from ui.components.design_system import metric_row
        metric_row(metrics)

    def _render_divider(self):
        """渲染分隔线"""
        from ui.components.design_system import divider
        divider()

    def _render_callout(self, message: str, type_: str = "info", icon: str = None):
        """渲染提示框"""
        from ui.components.design_system import callout
        callout(message=message, type=type_, icon=icon)

    def _handle_error(self, error: Exception, context: str = ""):
        """统一错误处理"""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self._render_callout(error_msg, type="error")
        st.info("请检查API Key是否有效，或稍后重试。")

    def _get_pagination_state_key(self, prefix: str) -> str:
        """获取分页状态键"""
        return f"{prefix}_page"

    def _get_current_page(self, prefix: str) -> int:
        """获取当前页码"""
        key = self._get_pagination_state_key(prefix)
        return st.session_state.get(key, 0)

    def _set_page(self, prefix: str, page: int):
        """设置当前页码"""
        key = self._get_pagination_state_key(prefix)
        st.session_state[key] = page

    def _render_pagination(self, total_count: int, page_size: int, prefix: str):
        """渲染分页控件"""
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        current_page = self._get_current_page(prefix)

        if total_pages <= 1:
            return

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button(
                "上一页",
                disabled=(current_page <= 0),
                key=f"{prefix}_prev",
            ):
                self._set_page(prefix, current_page - 1)
                st.rerun()
        with col2:
            st.caption(f"第 {current_page + 1} / {total_pages} 页（共 {total_count} 条）")
        with col3:
            if st.button(
                "下一页",
                disabled=(current_page >= total_pages - 1),
                key=f"{prefix}_next",
            ):
                self._set_page(prefix, current_page + 1)
                st.rerun()


class AnalysisPage(BasePage):
    """分析页面基类 - 用于内容分析和线索分析等具有相似结构的页面"""

    def __init__(self, title: str, icon: str, description: str, page_prefix: str):
        super().__init__(title, icon, description)
        self.page_prefix = page_prefix
        self.max_csv_size = 10 * 1024 * 1024  # 10MB

    def _render_content(self):
        """分析页面的通用内容结构"""
        if not self._check_initialization():
            return

        tab1, tab2 = st.tabs(["手动输入", "批量导入"])

        with tab1:
            self._render_single_input()

        with tab2:
            self._render_batch_input()

        self._render_divider()
        self._render_history()

    @abstractmethod
    def _render_single_input(self):
        """渲染单个输入界面"""
        pass

    @abstractmethod
    def _render_batch_input(self):
        """渲染批量输入界面"""
        pass

    @abstractmethod
    def _render_history(self):
        """渲染历史记录"""
        pass

    def _handle_file_upload(self, file_type: str = "csv") -> Optional[Any]:
        """处理文件上传"""
        uploaded = st.file_uploader(
            f"上传{file_type.upper()}文件",
            type=[file_type],
        )

        if uploaded is None:
            return None

        if uploaded.size > self.max_csv_size:
            self._render_callout(
                f"文件大小超过限制（最大 {self.max_csv_size // (1024*1024)}MB）",
                type="error"
            )
            return None

        return uploaded

    def _render_field_mapping(self, df, mapping_key: str, analysis_type: str):
        """渲染字段映射界面"""
        from utils.field_mapping import (
            detect_columns,
            show_mapping_preview,
            validate_mapping_for_analysis,
        )

        # 初始化状态
        if mapping_key not in st.session_state:
            st.session_state[mapping_key] = None

        st.markdown("---")
        auto_mapping = detect_columns(df.columns.tolist())
        user_mapping = show_mapping_preview(auto_mapping, df.columns.tolist())

        # 验证映射
        is_valid, missing_fields = validate_mapping_for_analysis(
            user_mapping, analysis_type
        )

        if not is_valid:
            self._render_callout(
                f"缺少必需字段: {', '.join(missing_fields)}",
                type="error"
            )
            st.info("请在上方映射表中选择对应字段")
            return None

        st.session_state[mapping_key] = user_mapping
        return user_mapping

    def _render_batch_progress(self, total: int, current: int, prefix: str = ""):
        """渲染批量处理进度（兼容旧版Streamlit）"""
        progress_text = f"{prefix} ({current}/{total})" if prefix else f"正在处理... ({current}/{total})"
        ratio = current / total if total > 0 else 0
        try:
            return st.progress(ratio, text=progress_text)
        except TypeError:
            bar = st.progress(ratio)
            st.caption(progress_text)
            return bar


class MatchPage(BasePage):
    """匹配页面基类 - 用于匹配中心等页面"""

    def __init__(self, title: str, icon: str, description: str):
        super().__init__(title, icon, description)

    def _render_content(self):
        """匹配页面的通用内容结构"""
        if not self._check_initialization():
            return

        tab1, tab2 = st.tabs(["单对匹配", "批量匹配"])

        with tab1:
            self._render_single_match()

        with tab2:
            self._render_batch_match()

        self._render_divider()
        self._render_history()

    @abstractmethod
    def _render_single_match(self):
        """渲染单对匹配界面"""
        pass

    @abstractmethod
    def _render_batch_match(self):
        """渲染批量匹配界面"""
        pass

    @abstractmethod
    def _render_history(self):
        """渲染历史记录"""
        pass

    def _render_match_score_card(self, score: float, title: str = "综合匹配度"):
        """渲染匹配分数卡片"""
        from ui.components.design_system import metric_card

        color = "#10B981" if score >= 7 else "#F59E0B" if score >= 5 else "#EF4444"
        level = "强匹配" if score >= 7 else "中等匹配" if score >= 5 else "弱匹配"

        metric_card(
            title=title,
            value=f"{score}/10",
            subtitle=level,
            icon="🎯",
            border_color=color,
        )

    def _render_dimension_scores(self, dimension_scores: Dict[str, float], columns: int = 5):
        """渲染维度评分网格"""
        from ui.components.design_system import metric_card

        dims = [
            ("受众匹配", "audience_fit"),
            ("痛点相关", "pain_point_relevance"),
            ("阶段对齐", "stage_alignment"),
            ("CTA适当", "cta_appropriateness"),
            ("情感共鸣", "emotion_resonance"),
        ]

        cols = st.columns(columns)
        for col, (label, key) in zip(cols, dims):
            with col:
                val = dimension_scores.get(key, 0)
                color = "#10B981" if val >= 7 else "#F59E0B" if val >= 5 else "#EF4444"
                metric_card(
                    title=label,
                    value=f"{val}/10",
                    border_color=color,
                )
