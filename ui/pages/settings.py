"""
系统设置页面
"""

import streamlit as st


def render_settings():
    """渲染系统设置页面"""
    st.title("系统设置")
    st.markdown("配置API密钥、管理数据")

    st.markdown("---")

    # API 配置
    st.subheader("API 配置")

    # 尝试从数据库加载已保存的配置
    saved_model = "deepseek-chat"
    saved_api_key = ""
    try:
        if st.session_state.get("initialized") and st.session_state.get("orchestrator"):
            saved_model = st.session_state.orchestrator.db.get_setting("MODEL", "deepseek-chat")
            saved_api_key = st.session_state.orchestrator.db.get_setting("API_KEY", "")
        else:
            from services.database import Database
            db = Database()
            saved_model = db.get_setting("MODEL", "deepseek-chat")
            saved_api_key = db.get_setting("API_KEY", "")
            db.close()
    except Exception:
        pass

    # 模型选择
    model_options = [
        "deepseek-chat",
        "deepseek-reasoner",
        "qwen-turbo",
        "qwen-plus",
        "qwen-max",
        "sensechat-5",
        "sensechat-turbo",
        "sensenova-v6-pro",
        "sensenova-v6-turbo",
        "LongCat-Flash-Thinking-2601",
    ]

    try:
        default_idx = model_options.index(saved_model) if saved_model in model_options else 0
    except ValueError:
        default_idx = 0

    model = st.selectbox(
        "模型服务商",
        model_options,
        index=default_idx,
        format_func=lambda x: {
            "deepseek-chat": "DeepSeek Chat（推荐）",
            "deepseek-reasoner": "DeepSeek Reasoner",
            "qwen-turbo": "通义千问 Turbo",
            "qwen-plus": "通义千问 Plus",
            "qwen-max": "通义千问 Max",
            "sensechat-5": "商汤 SenseChat-5",
            "sensechat-turbo": "商汤 SenseChat-Turbo",
            "sensenova-v6-pro": "商汤 SenseNova V6 Pro",
            "sensenova-v6-turbo": "商汤 SenseNova V6 Turbo",
            "LongCat-Flash-Thinking-2601": "LongCat Flash Thinking",
        }.get(x, x),
    )

    api_key = st.text_input(
        "API Key",
        type="password",
        value=saved_api_key if saved_api_key else "",
        placeholder="sk-...",
    )

    if st.button("保存并连接", type="primary", use_container_width=True):
        if not api_key:
            st.error("请输入 API Key")
            return

        with st.spinner("正在测试连接..."):
            try:
                from services.orchestrator import Orchestrator

                if st.session_state.get("orchestrator"):
                    st.session_state.orchestrator.close()

                st.session_state.orchestrator = Orchestrator(model=model, api_key=api_key)
                st.session_state.initialized = True

                st.session_state.orchestrator.db.set_setting("MODEL", model)
                st.session_state.orchestrator.db.set_setting("API_KEY", api_key)
                st.success("连接成功！配置已保存。")

            except Exception as e:
                st.error(f"连接失败: {str(e)}")
                st.session_state.initialized = False

    st.markdown("---")

    # 数据管理
    st.subheader("数据管理")

    if st.session_state.get("initialized") and st.session_state.get("orchestrator"):
        try:
            stats = st.session_state.orchestrator.db.get_stats()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("内容分析", stats["content_count"])
            col2.metric("线索分析", stats["lead_count"])
            col3.metric("匹配结果", stats["match_count"])
            col4.metric("策略建议", stats["strategy_count"])

            if st.button("加载示例数据"):
                _load_sample_data()

        except Exception as e:
            st.error(f"数据管理加载失败: {str(e)}")
    else:
        st.info("请先配置 API Key 以启用数据管理功能")


def _load_sample_data():
    """加载示例数据"""
    try:
        from data.sample_data import SAMPLE_SCRIPTS, SAMPLE_LEADS

        progress_bar = st.progress(0, text="正在加载示例数据...")

        for i, sample in enumerate(SAMPLE_SCRIPTS):
            try:
                if st.session_state.get("orchestrator"):
                    st.session_state.orchestrator.analyze_content(sample["script_text"])
            except Exception as e:
                st.warning(f"示例脚本 {sample['script_id']} 分析失败: {e}")
            progress_bar.progress((i + 1) / (len(SAMPLE_SCRIPTS) + len(SAMPLE_LEADS)))

        for j, sample in enumerate(SAMPLE_LEADS):
            try:
                if st.session_state.get("orchestrator"):
                    st.session_state.orchestrator.analyze_lead(sample["lead_data"])
            except Exception as e:
                st.warning(f"示例线索 {sample['lead_id']} 分析失败: {e}")
            progress_bar.progress((len(SAMPLE_SCRIPTS) + j + 1) / (len(SAMPLE_SCRIPTS) + len(SAMPLE_LEADS)))

        progress_bar.empty()
        st.success("示例数据加载完成！")
        st.rerun()
    except Exception as e:
        st.error(f"加载示例数据失败: {str(e)}")
