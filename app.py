"""
Content2Revenue AI - 主入口
AI驱动的内容-商业转化智能平台
"""

import streamlit as st
import os
import sys
import traceback
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 页面配置 — 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="Content2Revenue AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Content2Revenue AI — AI驱动的内容-商业转化智能平台",
    },
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
# 固化模型配置（免费API Key，仅用于展示测试）
# ============================================================
DEFAULT_MODEL = os.environ.get("C2R_DEFAULT_MODEL", "LongCat-2.0-Preview")
DEFAULT_API_KEY = os.environ.get("C2R_API_KEY", "")

# 初始化session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "initialized" not in st.session_state:
    st.session_state.initialized = False


def _safe_error_message(error: Exception) -> str:
    """将内部错误转换为用户友好的消息"""
    error_str = str(error) if error else ""
    logger.warning("用户可见错误: %s", error_str[:200])
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
        err_trace = traceback.format_exc()
        logger.error("初始化失败: %s", e, exc_info=True)
        st.session_state.initialized = False
        st.error(f"⚠️ 系统初始化失败: {str(e)}")
        with st.expander("查看技术详情（供调试用）"):
            st.code(err_trace)
        return False


def main():
    """主入口"""

    # 自动初始化编排器
    _auto_init_orchestrator()

    # 确定当前页面
    page_options = ["📊 仪表盘", "📝 内容分析", "👤 线索分析",
                    "🎯 匹配中心", "💡 策略建议", "💰 成本分析", "⚙️ 系统设置"]

    # 初始化 session_state（仅首次）
    if "current_page" not in st.session_state:
        st.session_state.current_page = "📊 仪表盘"

    # 处理按钮跳转（必须在 radio 渲染之前，通过修改 current_page 来影响 index）
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

    # ============ 侧边栏 ============
    with st.sidebar:
        st.markdown("## Content2Revenue AI")
        st.caption("AI驱动的内容-商业转化智能平台")
        st.markdown("---")

        # 使用 on_change 回调同步页面状态
        def _on_page_change():
            st.session_state.current_page = st.session_state._page_radio

        # 计算初始 index（基于 current_page，按钮跳转后自动指向正确选项）
        try:
            init_index = page_options.index(st.session_state.current_page)
        except ValueError:
            init_index = 0

        st.radio(
            "导航菜单",
            page_options,
            index=init_index,
            label_visibility="collapsed",
            key="_page_radio",
            on_change=_on_page_change,
        )

        current_page = st.session_state.current_page

        st.markdown("---")

        # 系统状态
        if st.session_state.initialized:
            st.success("✅ 系统已连接")
        else:
            st.warning("⚠️ 系统未连接")

        st.markdown("---")

        # 联系方式 / 商务合作
        st.markdown("#### 🤝 联系我们")
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                padding: 16px;
                border-radius: 12px;
                border: 1px solid #2d2d44;
                text-align: center;
            ">
                <div style="font-size: 13px; color: #a0a0b0; margin-bottom: 8px;">
                    商务合作 & 技术咨询
                </div>
                <div style="font-size: 18px; font-weight: bold; color: #6366F1; margin-bottom: 4px;">
                    📱 微信: JustinHou3199
                </div>
                <div style="font-size: 12px; color: #666;">
                    欢迎交流产品需求与技术合作
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 隐藏 Streamlit 默认元素
        hide_streamlit_default = """
        <style>
            /* 隐藏右上角菜单按钮 */
            [data-testid="stMainMenu"] {
                visibility: hidden;
            }
            /* 隐藏底部 Made with Streamlit */
            footer {
                visibility: hidden;
            }
            footer:after {
                content: "Content2Revenue AI © 2025";
                visibility: visible;
                display: block;
                text-align: center;
                color: #666;
                font-size: 12px;
                padding: 10px;
            }
        </style>
        """
        st.markdown(hide_streamlit_default, unsafe_allow_html=True)

    

    # ============ 页面路由 ============
    try:
        if current_page == "📊 仪表盘":
            from ui.pages.dashboard import render_dashboard
            render_dashboard()
        elif current_page == "📝 内容分析":
            from ui.pages.content_analysis import render_content_analysis
            render_content_analysis()
        elif current_page == "👤 线索分析":
            from ui.pages.lead_analysis import render_lead_analysis
            render_lead_analysis()
        elif current_page == "🎯 匹配中心":
            from ui.pages.match_center import render_match_center
            render_match_center()
        elif current_page == "💡 策略建议":
            from ui.pages.strategy import render_strategy
            render_strategy()
        elif current_page == "💰 成本分析":
            from ui.pages.cost_analytics import render_cost_analytics
            render_cost_analytics()
        elif current_page == "⚙️ 系统设置":
            from ui.pages.settings import render_settings
            render_settings()
    except Exception as e:
        logger.error("页面渲染异常: %s", e, exc_info=True)
        st.error(f"页面加载出错: {_safe_error_message(e)}")
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
