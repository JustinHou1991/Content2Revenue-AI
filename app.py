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

# 初始化session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "initialized" not in st.session_state:
    st.session_state.initialized = False
if "page" not in st.session_state:
    st.session_state.page = "dashboard"


def _safe_error_message(error: Exception) -> str:
    """将内部错误转换为用户友好的消息"""
    error_str = str(error)
    if "401" in error_str or "Authentication" in error_str:
        return "API Key 无效或已过期，请在设置页面重新配置"
    if "timeout" in error_str.lower():
        return "请求超时，请检查网络连接或稍后重试"
    if "rate" in error_str.lower():
        return "API 调用频率超限，请稍后重试"
    return "操作失败，请稍后重试或查看日志获取详情"


def _get_db_settings():
    """从数据库 app_settings 表读取配置"""
    try:
        from services.database import Database
        db = Database()
        model = db.get_setting("MODEL", "deepseek-chat")
        api_key = db.get_setting("API_KEY", "")
        db.close()
        return model, api_key
    except Exception as e:
        logger.warning("从数据库读取配置失败: %s", e)
        return None, None


def init_orchestrator():
    """延迟初始化编排器"""
    if st.session_state.orchestrator is not None:
        return True

    try:
        from services.orchestrator import Orchestrator

        model = st.secrets.get("MODEL", "deepseek-chat")
        api_key = st.secrets.get("API_KEY", None)

        if not api_key:
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")

        if not api_key:
            db_model, db_api_key = _get_db_settings()
            if db_api_key:
                model = db_model or model
                api_key = db_api_key
                logger.info("从数据库恢复配置: model=%s", model)

        if not api_key:
            st.session_state.initialized = False
            return False

        st.session_state.orchestrator = Orchestrator(model=model, api_key=api_key)
        st.session_state.initialized = True
        logger.info("Orchestrator 初始化成功: model=%s", model)
        return True
    except Exception as e:
        logger.error("初始化 Orchestrator 失败: %s", e, exc_info=True)
        st.session_state.initialized = False
        return False


def main():
    """主入口"""

    # ============ 侧边栏（最先渲染，确保不被后续代码影响） ============
    with st.sidebar:
        st.markdown("## Content2Revenue AI")
        st.markdown("---")

        # 导航菜单
        page = st.radio(
            "导航菜单",
            ["📊 仪表盘", "📝 内容分析", "👤 线索分析",
             "🎯 匹配中心", "💡 策略建议", "💰 成本分析", "⚙️ 系统设置"],
            label_visibility="collapsed",
            index=0,
        )

        st.markdown("---")

        # 系统状态
        if st.session_state.initialized:
            st.success("✅ 系统已连接")
        else:
            st.warning("⚠️ 系统未连接")
            st.info("请在「系统设置」中配置 API Key")

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
        logger.error("页面渲染异常: %s", e, exc_info=True)
        st.error(f"页面加载出错: {_safe_error_message(e)}")


if __name__ == "__main__":
    main()
