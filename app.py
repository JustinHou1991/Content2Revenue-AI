"""
Content2Revenue AI - 主入口
AI驱动的内容-商业转化智能平台
"""

import streamlit as st
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 初始化统一日志系统（尽早执行，确保所有后续模块都能使用）
from utils.logger import setup_logging, get_logger
from config import get_config
from services.health_check import HealthChecker

# 初始化健康检查器
health_checker = HealthChecker()

try:
    # 尝试从 config 获取日志配置；如果 Streamlit secrets 尚不可用则使用默认值
    _cfg_log_level = os.environ.get("C2R_LOG_LEVEL", "INFO")
    _cfg_log_dir = os.environ.get("C2R_LOG_DIR", "data/logs")
    setup_logging(level=_cfg_log_level, log_dir=_cfg_log_dir)
except Exception:
    setup_logging()  # 回退到默认配置

logger = get_logger(__name__)


def _safe_error_message(error: Exception) -> str:
    """将内部错误转换为用户友好的消息"""
    error_str = str(error)
    # 常见错误类型的友好消息
    if "401" in error_str or "Authentication" in error_str:
        return "API Key 无效或已过期，请在设置页面重新配置"
    if "timeout" in error_str.lower():
        return "请求超时，请检查网络连接或稍后重试"
    if "rate" in error_str.lower():
        return "API 调用频率超限，请稍后重试"
    # 默认消息，不暴露内部细节
    return "操作失败，请稍后重试或查看日志获取详情"

# 页面配置
st.set_page_config(
    page_title="Content2Revenue AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 注入新设计系统样式
from ui.styles import inject_styles
inject_styles()

# 初始化session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "initialized" not in st.session_state:
    st.session_state.initialized = False


def _get_db_settings():
    """从数据库 app_settings 表读取配置（持久化）"""
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
    """延迟初始化编排器（避免每次交互都初始化）

    配置读取优先级：
    1. st.secrets（.streamlit/secrets.toml，部署环境）
    2. 环境变量（DEEPSEEK_API_KEY / DASHSCOPE_API_KEY）
    3. 数据库 app_settings 表（UI设置页面保存的配置）
    """
    if st.session_state.orchestrator is not None:
        return True

    try:
        from services.orchestrator import Orchestrator

        model = st.secrets.get("MODEL", "deepseek-chat")
        api_key = st.secrets.get("API_KEY", None)

        # 如果 secrets 没有配置，尝试环境变量
        if not api_key:
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")

        # 如果环境变量也没有，尝试从数据库读取（UI设置页面持久化的配置）
        if not api_key:
            db_model, db_api_key = _get_db_settings()
            if db_api_key:
                model = db_model or model
                api_key = db_api_key
                logger.info("从数据库恢复配置: model=%s", model)

        if not api_key:
            st.session_state.initialized = False
            logger.info("未找到API Key配置，等待用户在设置页面配置")
            return False

        st.session_state.orchestrator = Orchestrator(
            model=model,
            api_key=api_key,
        )
        st.session_state.initialized = True
        logger.info("Orchestrator 初始化成功: model=%s", model)
        return True
    except Exception as e:
        logger.error("初始化 Orchestrator 失败: %s", e, exc_info=True)
        st.error(f"初始化失败: {_safe_error_message(e)}")
        st.session_state.initialized = False
        return False


def main():
    """主入口"""
    # 检查初始化
    if not st.session_state.initialized:
        init_orchestrator()

    # 侧边栏导航 - 使用新设计系统组件
    from ui.components.design_system import sidebar_logo, sidebar_nav

    with st.sidebar:
        sidebar_logo(name="Content2Revenue", subtitle="AI")

        st.markdown('<div class="c2r-sidebar-divider"></div>', unsafe_allow_html=True)

        nav_items = [
            {"label": "仪表盘", "icon": "📊", "key": "dashboard"},
            {"label": "内容分析", "icon": "📝", "key": "content"},
            {"label": "线索分析", "icon": "👤", "key": "lead"},
            {"label": "匹配中心", "icon": "🎯", "key": "match"},
            {"label": "策略建议", "icon": "💡", "key": "strategy"},
            {"label": "成本分析", "icon": "💰", "key": "cost"},
            {"label": "系统设置", "icon": "⚙️", "key": "settings"},
        ]

        # 映射导航 key 到页面名称
        nav_key_to_page = {
            "dashboard": "📊 仪表盘",
            "content": "📝 内容分析",
            "lead": "👤 线索分析",
            "match": "🎯 匹配中心",
            "strategy": "💡 策略建议",
            "cost": "💰 成本分析",
            "settings": "⚙️ 系统设置",
        }

        # 确定当前激活的导航项
        current_page_map = {
            "📊 仪表盘": "dashboard",
            "📝 内容分析": "content",
            "👤 线索分析": "lead",
            "🎯 匹配中心": "match",
            "💡 策略建议": "strategy",
            "💰 成本分析": "cost",
            "⚙️ 系统设置": "settings",
        }

        # 检查是否有导航目标（从其他页面跳转过来）
        nav_target = st.session_state.get("nav_target")
        default_index = 0
        if nav_target and nav_target in nav_key_to_page:
            default_index = list(nav_key_to_page.keys()).index(nav_target)
            # 清空导航目标，避免重复跳转
            st.session_state.nav_target = None

        # 使用默认的 st.radio 作为导航（保持原有行为）
        page = st.radio(
            "导航",
            list(nav_key_to_page.values()),
            label_visibility="collapsed",
            format_func=lambda x: x,
            index=default_index,
            key="sidebar_nav",
        )

        st.markdown('<div class="c2r-sidebar-divider"></div>', unsafe_allow_html=True)

        # 系统状态
        if st.session_state.initialized:
            st.success("系统已连接")
            try:
                stats = st.session_state.orchestrator.get_dashboard_data()["stats"]
                st.metric("已分析内容", stats["content_count"])
                st.metric("已分析线索", stats["lead_count"])
                st.metric("匹配次数", stats["match_count"])
            except Exception as e:
                st.warning("数据库读取中...")
                logger.warning("侧边栏统计数据加载失败: %s", e)
        else:
            st.error("系统未连接")
            st.info("请在「系统设置」中配置API Key")

        # 健康状态指示
        st.markdown('<div class="c2r-sidebar-divider"></div>', unsafe_allow_html=True)
        try:
            health = health_checker.run_all_checks()
            status_color = {"healthy": "green", "warning": "orange", "unhealthy": "red"}
            color = status_color.get(health["overall_status"], "gray")
            st.markdown(f"**系统健康**: :{color}[{health['overall_status'].upper()}]")

            # 展开显示详细状态
            with st.expander("查看详情"):
                for check_name, check_result in health["checks"].items():
                    check_status = check_result.get("status", "unknown")
                    check_color = status_color.get(check_status, "gray")
                    st.markdown(f"- {check_name}: :{check_color}[{check_status}]")
        except Exception as e:
            st.markdown("**系统健康**: :gray[UNKNOWN]")
            logger.warning("健康检查失败: %s", e)

    # 路由到对应页面
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
        st.info("请尝试刷新页面，或前往「系统设置」检查配置。")


if __name__ == "__main__":
    main()
