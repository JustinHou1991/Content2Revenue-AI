"""
Content2Revenue AI - 主入口
AI驱动的内容-商业转化智能平台
"""

import streamlit as st
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 页面配置 — 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="Content2Revenue AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 初始化统一日志系统
from utils.logger import setup_logging, get_logger

try:
    _cfg_log_level = os.environ.get("C2R_LOG_LEVEL", "INFO")
    _cfg_log_dir = os.environ.get("C2R_LOG_DIR", "data/logs")
    setup_logging(level=_cfg_log_level, log_dir=_cfg_log_dir)
except Exception:
    setup_logging()

logger = get_logger(__name__)

# ============================================================
# 固化模型配置（面试展示用，无需手动配置）
# ============================================================
DEFAULT_MODEL = "LongCat-Flash-Lite"
DEFAULT_API_KEY = "ak_28d06A0NE4BA8hu9ok17L5Nj3pt5N"

# 初始化session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "initialized" not in st.session_state:
    st.session_state.initialized = False


def _safe_error_message(error: Exception) -> str:
    """将内部错误转换为用户友好的消息"""
    error_str = str(error)
    if "401" in error_str or "Authentication" in error_str:
        return "API Key 无效或已过期"
    if "timeout" in error_str.lower():
        return "请求超时，请稍后重试"
    if "rate" in error_str.lower():
        return "API 调用频率超限，请稍后重试"
    return "操作失败，请稍后重试"


def _auto_init_orchestrator():
    """使用固化配置自动初始化编排器"""
    if st.session_state.orchestrator is not None:
        return True

    try:
        from services.orchestrator import Orchestrator
        from services.llm_client import LLMClient

        model = DEFAULT_MODEL
        api_key = DEFAULT_API_KEY

        if model not in LLMClient.MODEL_CONFIGS:
            logger.warning("模型 %s 不在支持列表中", model)
            st.session_state.initialized = False
            return False

        st.session_state.orchestrator = Orchestrator(model=model, api_key=api_key)
        st.session_state.initialized = True
        return True
    except Exception as e:
        import traceback
        err_trace = traceback.format_exc()
        logger.error("初始化失败: %s", e, exc_info=True)
        # 用用户友好的错误提示，不泄露敏感信息
        st.session_state.initialized = False
        st.error(f"⚠️ 系统初始化失败: {str(e)}")
        with st.expander("查看技术详情（供调试用）"):
            st.code(err_trace)
        return False


def main():
    """主入口"""

    # 自动初始化编排器
    _auto_init_orchestrator()

    # 处理页面跳转（从其他页面通过按钮跳转过来）
    nav_target = st.session_state.pop("nav_target", None)
    if nav_target:
        nav_map = {
            "settings": "⚙️ 系统设置",
            "content": "📝 内容分析",
            "lead": "👤 线索分析",
            "match": "🎯 匹配中心",
            "strategy": "💡 策略建议",
            "cost": "💰 成本分析",
            "dashboard": "📊 仪表盘",
        }
        if nav_target in nav_map:
            st.session_state.current_page = nav_map[nav_target]

    # 确定当前页面
    current_page = st.session_state.get("current_page", "📊 仪表盘")

    # 页面选项列表
    page_options = ["📊 仪表盘", "📝 内容分析", "👤 线索分析",
                    "🎯 匹配中心", "💡 策略建议", "💰 成本分析", "⚙️ 系统设置"]

    if current_page not in page_options:
        current_page = "📊 仪表盘"

    try:
        default_index = page_options.index(current_page)
    except ValueError:
        default_index = 0

    # ============ 侧边栏 ============
    with st.sidebar:
        st.markdown("## Content2Revenue AI")
        st.markdown("---")

        page = st.radio(
            "导航菜单",
            page_options,
            label_visibility="collapsed",
            index=default_index,
        )

        st.session_state.current_page = page

        st.markdown("---")

        # 系统状态
        if st.session_state.initialized:
            st.success("✅ 系统已连接")
        else:
            st.warning("⚠️ 系统未连接")

    # ============ 页面路由 ============
    try:
        if page == "📊 仪表盘":
            from ui.pages.dashboard import render_dashboard
            render_dashboard()
        elif page == "📝 内容分析":
            from ui.pages.content_analysis import render_content_analysis
            render_content_analysis()
        elif page == "👤 线索分析":
            from ui.pages.lead_analysis import render_lead_analysis
            render_lead_analysis()
        elif page == "🎯 匹配中心":
            from ui.pages.match_center import render_match_center
            render_match_center()
        elif page == "💡 策略建议":
            from ui.pages.strategy import render_strategy
            render_strategy()
        elif page == "💰 成本分析":
            from ui.pages.cost_analytics import render_cost_analytics
            render_cost_analytics()
        elif page == "⚙️ 系统设置":
            from ui.pages.settings import render_settings
            render_settings()
    except Exception as e:
        import traceback
        logger.error("页面渲染异常: %s", e, exc_info=True)
        st.error(f"页面加载出错: {_safe_error_message(e)}")
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
