"""
系统设置页面
"""

import streamlit as st

from ui.components.design_system import (
    page_header,
    metric_row,
    divider,
    callout,
    empty_state,
    status_badge,
)


def _get_all_model_options():
    """获取所有可用模型选项"""
    try:
        from services.llm_client import LLMClient
        return LLMClient.get_all_models()
    except Exception:
        return []


def _get_model_display_name(model: str) -> str:
    """获取模型的友好显示名称"""
    display_names = {
        "deepseek-chat": "DeepSeek Chat（推荐，性价比最高）",
        "deepseek-reasoner": "DeepSeek Reasoner（深度推理）",
        "qwen-turbo": "通义千问 Turbo（最快）",
        "qwen-plus": "通义千问 Plus（推荐，中文强）",
        "qwen-max": "通义千问 Max（最强）",
        "sensechat-5": "商汤 SenseChat-5（128K上下文）",
        "sensechat-turbo": "商汤 SenseChat-Turbo（超低价）",
        "sensenova-v6-pro": "商汤 SenseNova V6 Pro（多模态）",
        "sensenova-v6-turbo": "商汤 SenseNova V6 Turbo（多模态）",
        "LongCat-Flash-Thinking-2601": "LongCat Flash Thinking（深度推理）",
    }
    return display_names.get(model, model)


def render_settings():
    """渲染系统设置页面"""

    # ── 页面头部 ──
    page_header(
        title="系统设置",
        subtitle="配置API密钥、管理数据",
    )

    # ================================================================
    # API 配置区
    # ================================================================
    st.markdown(
        '<div class="c2r-card c2r-animate-fade-in">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        '<span style="font-size:1.125rem;font-weight:600;color:var(--text-primary);">'
        'API 配置</span>'
        '<span class="c2r-badge c2r-badge--purple c2r-badge--sm">必填</span>'
        '</div>'
        '<div style="font-size:0.8125rem;color:var(--text-tertiary);margin-bottom:20px;">'
        '选择 AI 模型服务商并配置密钥以启用全部功能</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["快速配置", "高级配置", "🔧 自定义模型"])

    with tab1:
        # 尝试从数据库加载已保存的配置作为默认值
        saved_model = "deepseek-chat"
        saved_api_key = ""
        try:
            if st.session_state.get("initialized") and st.session_state.get("orchestrator"):
                saved_model = st.session_state.orchestrator.db.get_setting(
                    "MODEL", "deepseek-chat"
                )
                saved_api_key = st.session_state.orchestrator.db.get_setting(
                    "API_KEY", ""
                )
            else:
                from services.database import Database
                db = Database()
                saved_model = db.get_setting("MODEL", "deepseek-chat")
                saved_api_key = db.get_setting("API_KEY", "")
                db.close()
        except Exception:
            pass

        # 动态获取所有模型选项
        all_models = _get_all_model_options()
        # 确保默认模型在列表中
        if saved_model and saved_model not in all_models:
            all_models.insert(0, saved_model)

        try:
            default_idx = all_models.index(saved_model) if saved_model in all_models else 0
        except ValueError:
            default_idx = 0

        model = st.selectbox(
            "模型服务商",
            all_models,
            index=default_idx,
            format_func=_get_model_display_name,
        )

        # 注意：自定义模型的 API Key 在添加时存储，这里不重复填写
        is_custom_model = model.startswith("custom_")
        api_key_placeholder = "（已随模型配置保存）" if is_custom_model else "sk-..."
        api_key_default = "" if is_custom_model else (saved_api_key if saved_api_key else "")

        api_key = st.text_input(
            "API Key",
            type="password",
            value=api_key_default,
            placeholder=api_key_placeholder,
            help=(
                "DeepSeek: https://platform.deepseek.com/api_keys\n"
                "通义千问: https://dashscope.console.aliyun.com/apiKey\n"
                "商汤日日新: https://console.sensecore.cn/aistudio/management/api-key"
            ),
        )

        if st.button("保存并连接", type="primary", use_container_width=True):
            # 自定义模型已包含 API Key，不需要额外输入
            if not is_custom_model and not api_key:
                callout("请输入 API Key", type="error")
                return

            with st.spinner("正在测试连接..."):
                try:
                    from services.llm_client import LLMClient

                    # 关闭旧连接
                    if st.session_state.get("orchestrator"):
                        st.session_state.orchestrator.close()

                    # 创建 LLM 客户端
                    if is_custom_model:
                        # 自定义模型：使用注册时存储的 API Key
                        llm_client = LLMClient(model=model)
                        connect_api_key = None  # 不在数据库存储 API Key
                    else:
                        # 内置模型：使用用户输入的 API Key
                        llm_client = LLMClient(model=model, api_key=api_key)
                        connect_api_key = api_key

                    st.session_state.initialized = True

                    # 测试调用
                    info = llm_client.get_model_info()
                    callout(f"连接成功！模型: {info['model']}", type="success")

                    # 持久化到数据库（API Key 单独加密存储）
                    from services.orchestrator import Orchestrator
                    st.session_state.orchestrator = Orchestrator(
                        model=model,
                        api_key=connect_api_key,
                    )
                    st.session_state.orchestrator.db.set_setting("MODEL", model)
                    if connect_api_key:
                        st.session_state.orchestrator.db.set_setting("API_KEY", connect_api_key)
                    callout("配置已保存，刷新页面后仍然有效。", type="info")

                except Exception as e:
                    callout(f"连接失败: {str(e)}", type="error")
                    st.session_state.initialized = False

    with tab2:
        st.markdown(
            '<div style="font-size:0.875rem;color:var(--text-secondary);margin-bottom:12px;">'
            "手动设置环境变量：</div>",
            unsafe_allow_html=True,
        )
        st.code(
            """
# DeepSeek
export DEEPSEEK_API_KEY="sk-your-key"

# 通义千问
export DASHSCOPE_API_KEY="sk-your-key"
""",
            language="bash",
        )

        st.markdown(
            '<div style="font-size:0.875rem;color:var(--text-secondary);margin:20px 0 12px;">'
            '或在 <code style="background:var(--bg-muted);padding:2px 8px;border-radius:4px;'
            'font-size:0.8125rem;color:var(--text-brand);">.streamlit/secrets.toml</code> '
            "中配置：</div>",
            unsafe_allow_html=True,
        )
        st.code(
            """
MODEL = "deepseek-chat"
API_KEY = "sk-your-key"
""",
            language="toml",
        )

        divider()

        st.markdown(
            '<div style="font-size:0.875rem;font-weight:600;color:var(--text-primary);'
            'margin-bottom:12px;">配置优先级</div>'
            '<div style="font-size:0.8125rem;color:var(--text-secondary);line-height:2.2;'
            'padding-left:4px;">'
            '<span style="color:var(--text-brand);font-weight:600;">1.</span> '
            '<code style="background:var(--bg-muted);padding:2px 8px;border-radius:4px;'
            'font-size:0.8125rem;">.streamlit/secrets.toml</code>'
            ' <span style="color:var(--text-tertiary);">— 部署环境推荐</span><br>'
            '<span style="color:var(--text-brand);font-weight:600;">2.</span> '
            "环境变量 "
            '<span style="color:var(--text-tertiary);">— Docker / 服务器部署推荐</span><br>'
            '<span style="color:var(--text-brand);font-weight:600;">3.</span> '
            "数据库 app_settings "
            '<span style="color:var(--text-tertiary);">— UI 设置页面保存的配置</span>'
            "</div>",
            unsafe_allow_html=True,
        )

    with tab3:
        st.markdown(
            '<div style="font-size:0.875rem;color:var(--text-secondary);margin-bottom:20px;">'
            "添加自定义 OpenAI 兼容模型。配置后可在「快速配置」中选择使用。</div>",
            unsafe_allow_html=True,
        )

        with st.form("add_custom_model"):
            st.markdown("**添加新模型**")
            custom_name = st.text_input(
                "模型名称",
                placeholder="例如: my-gpt-4、custom-llama",
                help="输入一个唯一标识符，如模型 ID 或自定义名称",
            )
            custom_base_url = st.text_input(
                "API Base URL",
                placeholder="https://api.openai.com/v1",
                help="OpenAI 兼容 API 的 base URL（通常以 /v1 结尾）",
            )
            custom_api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="sk-...",
            )
            custom_model_id = st.text_input(
                "模型 ID",
                placeholder="gpt-4o、claude-3-sonnet-20240229",
                help="在 API 中实际使用的模型标识符（如请求体中的 model 字段值）",
            )

            submitted = st.form_submit_button(
                "添加模型",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                if not custom_name or not custom_base_url or not custom_api_key or not custom_model_id:
                    callout("请填写所有字段", type="error")
                else:
                    try:
                        from services.llm_client import register_custom_model

                        # 注册自定义模型：模型名用 custom_ 前缀区分
                        model_key = f"custom_{custom_name}"
                        register_custom_model(
                            model_name=model_key,
                            base_url=custom_base_url.rstrip("/"),
                            api_key=custom_api_key,
                        )
                        # 持久化到数据库（含加密的 API Key）
                        from services.database import Database
                        db = Database()
                        db.set_setting(f"CUSTOM_MODEL_{custom_name}_BASE_URL", custom_base_url.rstrip("/"))
                        db.set_setting(f"CUSTOM_MODEL_{custom_name}_MODEL_ID", custom_model_id)
                        db.set_setting(f"CUSTOM_MODEL_{custom_name}_NAME", custom_name)
                        db.set_setting(f"CUSTOM_MODEL_{custom_name}_API_KEY", custom_api_key)
                        db.close()

                        callout(
                            f"✅ 自定义模型「{custom_name}」添加成功！请在「快速配置」中选择使用。",
                            type="success",
                        )
                        st.rerun()
                    except Exception as e:
                        callout(f"添加失败: {str(e)}", type="error")

        divider()

        # 已添加的自定义模型列表
        st.markdown("**已添加的自定义模型**")
        try:
            from services.llm_client import LLMClient
            custom_models = LLMClient.get_custom_models()
            if custom_models:
                for model_key in custom_models:
                    custom_name = model_key.replace("custom_", "")
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"- **{custom_name}**")
                    with col2:
                        if st.button("🗑️", key=f"del_{model_key}"):
                            try:
                                LLMClient.remove_custom_model(model_key)
                                # 同时清理数据库元数据
                                from services.database import Database
                                db = Database()
                                for key_suffix in ["BASE_URL", "MODEL_ID", "NAME"]:
                                    db.delete_setting(f"CUSTOM_MODEL_{custom_name}_{key_suffix}")
                                db.close()
                            except Exception:
                                pass
                            st.rerun()
            else:
                st.info("暂无自定义模型，请使用上方表单添加。")
        except Exception as e:
            st.warning(f"加载自定义模型列表失败: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    divider()

    # ================================================================
    # 数据管理区
    # ================================================================
    st.markdown(
        '<div class="c2r-card c2r-fade-in-delay-1">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        '<span style="font-size:1.125rem;font-weight:600;color:var(--text-primary);">'
        "数据管理</span>"
        "</div>"
        '<div style="font-size:0.8125rem;color:var(--text-tertiary);margin-bottom:20px;">'
        "查看系统数据统计，执行数据维护操作</div>",
        unsafe_allow_html=True,
    )

    try:
        if st.session_state.get("initialized") and st.session_state.get("orchestrator"):
            stats = st.session_state.orchestrator.db.get_stats()

            metric_row(
                [
                    {
                        "title": "内容分析",
                        "value": str(stats["content_count"]),
                        "icon": "📝",
                        "border_color": "var(--brand-primary)",
                    },
                    {
                        "title": "线索分析",
                        "value": str(stats["lead_count"]),
                        "icon": "👤",
                        "border_color": "var(--color-info)",
                    },
                    {
                        "title": "匹配结果",
                        "value": str(stats["match_count"]),
                        "icon": "🎯",
                        "border_color": "var(--color-success)",
                    },
                    {
                        "title": "策略建议",
                        "value": str(stats["strategy_count"]),
                        "icon": "💡",
                        "border_color": "var(--color-warning)",
                    },
                ]
            )

            st.markdown('<div style="margin-top:24px;">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("清空所有数据", type="secondary"):
                    st.session_state.confirm_clear = True

            with col2:
                if st.button("重新初始化系统", type="secondary"):
                    if st.session_state.get("orchestrator"):
                        st.session_state.orchestrator.close()
                    st.session_state.orchestrator = None
                    st.session_state.initialized = False
                    st.rerun()

            with col3:
                if st.button("加载示例数据", type="secondary"):
                    _load_sample_data()

            # 清空数据确认对话框
            if st.session_state.get("confirm_clear"):
                callout(
                    "确定要清空所有数据吗？此操作不可撤销！",
                    type="warning",
                )
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("确认清空", type="primary"):
                        try:
                            if st.session_state.get("orchestrator"):
                                st.session_state.orchestrator.db.clear_all_data()
                            callout("数据已清空", type="success")
                            st.session_state.confirm_clear = False
                            st.rerun()
                        except Exception as e:
                            callout(f"清空失败: {str(e)}", type="error")
                with col_cancel:
                    if st.button("取消"):
                        st.session_state.confirm_clear = False
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            empty_state(
                title="系统未连接",
                description="请先配置 API Key 以启用数据管理功能",
                icon="&#128274;",
            )
    except Exception as e:
        callout(f"数据管理加载失败: {str(e)}", type="error")

    st.markdown("</div>", unsafe_allow_html=True)

    divider()

    # ================================================================
    # 关于区
    # ================================================================
    st.markdown(
        '<div class="c2r-card c2r-fade-in-delay-2">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">'
        '<span style="font-size:1.125rem;font-weight:600;color:var(--text-primary);">'
        "关于</span>"
        "</div>"
        # 产品名称
        '<div style="margin-bottom:20px;">'
        '<div style="font-size:1rem;font-weight:600;color:var(--text-primary);'
        'margin-bottom:4px;">Content2Revenue AI</div>'
        '<div style="font-size:0.8125rem;color:var(--text-tertiary);">'
        "AI 驱动的内容-商业转化智能平台</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # 核心功能列表
    features = [
        ("内容智能分析", "从抖音脚本提取 Hook、情感、叙事结构、CTA 等特征", "📝"),
        ("线索智能分析", "构建客户画像，评估意向度和购买阶段", "👤"),
        ("语义匹配引擎", "5 维度评估内容与线索的适配度", "🎯"),
        ("AI 策略顾问", "生成内容策略、分发策略、转化预测和 A/B 测试建议", "💡"),
    ]

    features_html = ""
    for title, desc, icon in features:
        features_html += (
            '<div style="display:flex;align-items:flex-start;gap:12px;padding:12px 0;'
            'border-bottom:1px solid var(--border-subtle);">'
            f'<span style="font-size:1rem;width:24px;text-align:center;flex-shrink:0;">{icon}</span>'
            "<div>"
            f'<div style="font-size:0.875rem;font-weight:500;color:var(--text-primary);">{title}</div>'
            f'<div style="font-size:0.8125rem;color:var(--text-tertiary);margin-top:2px;">{desc}</div>'
            "</div></div>"
        )

    st.markdown(features_html, unsafe_allow_html=True)

    # 技术栈标签
    st.markdown(
        '<div style="margin-top:20px;display:flex;align-items:center;gap:8px;">'
        '<span style="font-size:0.75rem;font-weight:600;color:var(--text-tertiary);'
        'text-transform:uppercase;letter-spacing:0.05em;">技术栈</span>'
        '<span style="flex:1;height:1px;background:var(--border-subtle);"></span>'
        "</div>"
        '<div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;">'
        '<span class="c2r-badge c2r-badge--blue">Streamlit</span>'
        '<span class="c2r-badge c2r-badge--green">SQLite</span>'
        '<span class="c2r-badge c2r-badge--purple">DeepSeek</span>'
        '<span class="c2r-badge c2r-badge--yellow">Qwen</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


def _load_sample_data():
    """加载示例数据到数据库，方便新用户体验"""
    try:
        from data.sample_data import SAMPLE_SCRIPTS, SAMPLE_LEADS

        progress_bar = st.progress(0, text="正在加载示例数据...")

        # 加载示例脚本
        for i, sample in enumerate(SAMPLE_SCRIPTS):
            try:
                if st.session_state.get("orchestrator"):
                    st.session_state.orchestrator.analyze_content(sample["script_text"])
            except Exception as e:
                st.warning(f"示例脚本 {sample['script_id']} 分析失败: {e}")
            progress_bar.progress(
                (i + 1) / (len(SAMPLE_SCRIPTS) + len(SAMPLE_LEADS)),
                text=f"正在分析示例脚本... ({i + 1}/{len(SAMPLE_SCRIPTS)})",
            )

        # 加载示例线索
        for j, sample in enumerate(SAMPLE_LEADS):
            try:
                if st.session_state.get("orchestrator"):
                    st.session_state.orchestrator.analyze_lead(sample["lead_data"])
            except Exception as e:
                st.warning(f"示例线索 {sample['lead_id']} 分析失败: {e}")
            progress_bar.progress(
                (len(SAMPLE_SCRIPTS) + j + 1)
                / (len(SAMPLE_SCRIPTS) + len(SAMPLE_LEADS)),
                text=f"正在分析示例线索... ({j + 1}/{len(SAMPLE_LEADS)})",
            )

        progress_bar.empty()
        st.success(
            f"示例数据加载完成！已加载 {len(SAMPLE_SCRIPTS)} 条脚本 + {len(SAMPLE_LEADS)} 条线索"
        )
        st.info("你可以去「匹配中心」尝试批量匹配，或去「仪表盘」查看数据概览。")
        st.rerun()
    except Exception as e:
        st.error(f"加载示例数据失败: {str(e)}")
