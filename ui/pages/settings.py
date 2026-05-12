"""
系统设置页面
"""

import streamlit as st


# 内置模型列表
BUILTIN_MODELS = [
    "deepseek-chat",
    "deepseek-reasoner",
    "qwen-turbo",
    "qwen-plus",
    "qwen-max",
    "sensechat-5",
    "sensechat-turbo",
    "sensenova-v6-pro",
    "sensenova-v6-turbo",
    "LongCat-Flash-Chat",
]

MODEL_DISPLAY_NAMES = {
    "deepseek-chat": "DeepSeek Chat（推荐）",
    "deepseek-reasoner": "DeepSeek Reasoner",
    "qwen-turbo": "通义千问 Turbo",
    "qwen-plus": "通义千问 Plus",
    "qwen-max": "通义千问 Max",
    "sensechat-5": "商汤 SenseChat-5",
    "sensechat-turbo": "商汤 SenseChat-Turbo",
    "sensenova-v6-pro": "商汤 SenseNova V6 Pro",
    "sensenova-v6-turbo": "商汤 SenseNova V6 Turbo",
    "LongCat-Flash-Chat": "LongCat Flash Chat",
}


def _get_db():
    """获取数据库连接"""
    try:
        if st.session_state.get("initialized") and st.session_state.get("orchestrator"):
            return st.session_state.orchestrator.db
        from services.database import Database
        db = Database()
        return db
    except Exception:
        return None


def _get_saved_config():
    """从数据库读取已保存的配置"""
    saved_model = "deepseek-chat"
    saved_api_key = ""
    try:
        db = _get_db()
        if db:
            saved_model = db.get_setting("MODEL", "deepseek-chat")
            saved_api_key = db.get_setting("API_KEY", "")
    except Exception:
        pass
    return saved_model, saved_api_key


def _get_all_model_options():
    """获取所有可用模型（内置 + 自定义）"""
    custom_models = []
    try:
        from services.llm_client import LLMClient
        custom_models = LLMClient.get_custom_models()
    except Exception:
        pass
    return BUILTIN_MODELS + custom_models


def _model_display_name(model: str) -> str:
    """获取模型显示名称"""
    if model in MODEL_DISPLAY_NAMES:
        return MODEL_DISPLAY_NAMES[model]
    # 自定义模型：去掉 custom_ 前缀，加上标记
    if model.startswith("custom_"):
        return f"🔧 {model[7:]}"
    return model


def render_settings():
    """渲染系统设置页面"""
    st.title("系统设置")
    st.markdown("配置API密钥、管理数据")

    tab1, tab2 = st.tabs(["快速配置", "🔧 自定义模型"])

    # ==================== 快速配置 ====================
    with tab1:
        saved_model, saved_api_key = _get_saved_config()
        all_models = _get_all_model_options()

        # 确保当前保存的模型在列表中
        if saved_model and saved_model not in all_models:
            all_models.insert(0, saved_model)

        try:
            default_idx = all_models.index(saved_model) if saved_model in all_models else 0
        except ValueError:
            default_idx = 0

        model = st.selectbox(
            "模型",
            all_models,
            index=default_idx,
            format_func=_model_display_name,
        )

        # 自定义模型不需要手动输入 API Key
        is_custom = model.startswith("custom_")
        if is_custom:
            st.info("自定义模型的 API Key 已随模型配置保存，无需重复输入。")
            api_key = "__custom__"
        else:
            api_key = st.text_input(
                "API Key",
                type="password",
                value=saved_api_key if saved_api_key else "",
                placeholder="sk-...",
            )

        if st.button("保存并连接", type="primary", use_container_width=True):
            if not is_custom and not api_key:
                st.error("请输入 API Key")
                return

            with st.spinner("正在测试连接..."):
                try:
                    from services.orchestrator import Orchestrator

                    if st.session_state.get("orchestrator"):
                        st.session_state.orchestrator.close()

                    # 自定义模型使用注册时存储的 API Key（传 None）
                    connect_key = None if is_custom else api_key
                    st.session_state.orchestrator = Orchestrator(
                        model=model, api_key=connect_key
                    )
                    st.session_state.initialized = True

                    st.session_state.orchestrator.db.set_setting("MODEL", model)
                    if not is_custom and api_key:
                        st.session_state.orchestrator.db.set_setting("API_KEY", api_key)

                    st.success(f"连接成功！当前模型: {_model_display_name(model)}")

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

    # ==================== 自定义模型 ====================
    with tab2:
        st.markdown(
            "添加自定义 OpenAI 兼容模型。配置后可在「快速配置」中选择使用。"
        )

        with st.form("add_custom_model"):
            st.markdown("**添加新模型**")
            custom_name = st.text_input(
                "模型名称",
                placeholder="例如: my-gpt-4o",
                help="自定义标识符，用于在模型列表中显示",
            )
            custom_base_url = st.text_input(
                "API Base URL",
                placeholder="https://api.openai.com/v1",
                help="OpenAI 兼容 API 地址（通常以 /v1 结尾）",
            )
            custom_api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="sk-...",
            )

            submitted = st.form_submit_button(
                "添加模型", type="primary", use_container_width=True
            )

            if submitted:
                if not custom_name or not custom_base_url or not custom_api_key:
                    st.error("请填写所有字段")
                else:
                    try:
                        from services.llm_client import register_custom_model

                        model_key = f"custom_{custom_name}"
                        register_custom_model(
                            model_name=model_key,
                            base_url=custom_base_url.rstrip("/"),
                            api_key=custom_api_key,
                        )

                        # 持久化到数据库
                        db = _get_db()
                        if db:
                            db.set_setting(f"CUSTOM_MODEL_{custom_name}_BASE_URL", custom_base_url.rstrip("/"))
                            db.set_setting(f"CUSTOM_MODEL_{custom_name}_API_KEY", custom_api_key)

                        st.success(f"模型「{custom_name}」添加成功！请在「快速配置」中选择使用。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"添加失败: {str(e)}")

        st.markdown("---")

        # 已添加的自定义模型列表
        st.markdown("**已添加的自定义模型**")
        try:
            from services.llm_client import LLMClient
            custom_models = LLMClient.get_custom_models()
            if custom_models:
                for model_key in custom_models:
                    display_name = model_key.replace("custom_", "")
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"- **{display_name}**")
                    with col2:
                        if st.button("删除", key=f"del_{model_key}"):
                            LLMClient.remove_custom_model(model_key)
                            # 清理数据库
                            db = _get_db()
                            if db:
                                for suffix in ["BASE_URL", "API_KEY"]:
                                    db.delete_setting(f"CUSTOM_MODEL_{display_name}_{suffix}")
                            st.rerun()
            else:
                st.info("暂无自定义模型，请使用上方表单添加。")
        except Exception as e:
            st.warning(f"加载自定义模型列表失败: {e}")


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
