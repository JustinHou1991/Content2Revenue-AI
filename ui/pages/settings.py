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

    tab1, tab2 = st.tabs(["快速配置", "高级配置"])

    with tab1:
        # 尝试从数据库加载已保存的配置作为默认值
        # 注意：即使没有初始化，也要尝试读取数据库配置
        saved_model = "deepseek-chat"
        saved_api_key = ""
        try:
            # 优先从已初始化的orchestrator读取
            if st.session_state.get("initialized") and st.session_state.get("orchestrator"):
                saved_model = st.session_state.orchestrator.db.get_setting(
                    "MODEL", "deepseek-chat"
                )
                saved_api_key = st.session_state.orchestrator.db.get_setting(
                    "API_KEY", ""
                )
            else:
                # 未初始化时，直接读取数据库
                from services.database import Database
                db = Database()
                saved_model = db.get_setting("MODEL", "deepseek-chat")
                saved_api_key = db.get_setting("API_KEY", "")
                db.close()
        except Exception as e:
            # 静默处理错误，使用默认值
            pass

        model = st.selectbox(
            "模型服务商",
            [
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
            ],
            index=(
                [
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
                ].index(saved_model)
                if saved_model
                in [
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
                else 0
            ),
            format_func=lambda x: {
                "deepseek-chat": "DeepSeek Chat（推荐，性价比最高）",
                "deepseek-reasoner": "DeepSeek Reasoner（深度推理）",
                "qwen-turbo": "通义千问 Turbo（最快）",
                "qwen-plus": "通义千问 Plus（推荐，中文强）",
                "qwen-max": "通义千问 Max（最强）",
                "sensechat-5": "商汤 SenseChat-5（128K上下文，对标GPT-4 Turbo）",
                "sensechat-turbo": "商汤 SenseChat-Turbo（超低价，适合批量）",
                "sensenova-v6-pro": "商汤 SenseNova V6 Pro（多模态，双冠军）",
                "sensenova-v6-turbo": "商汤 SenseNova V6 Turbo（多模态，性价比）",
                "LongCat-Flash-Thinking-2601": "LongCat Flash Thinking（深度推理）",
            }.get(x, x),
        )

        api_key = st.text_input(
            "API Key",
            type="password",
            value=saved_api_key if saved_api_key else "",
            placeholder="sk-...",
            help=(
                "DeepSeek: https://platform.deepseek.com/api_keys\n"
                "通义千问: https://dashscope.console.aliyun.com/apiKey\n"
                "商汤日日新: https://console.sensecore.cn/aistudio/management/api-key"
            ),
        )

        if st.button("保存并连接", type="primary", use_container_width=True):
            if not api_key:
                callout("请输入API Key", type="error")
                return

            # 尝试连接
            with st.spinner("正在测试连接..."):
                try:
                    from services.orchestrator import Orchestrator

                    # 关闭旧连接
                    if st.session_state.get("orchestrator"):
                        st.session_state.orchestrator.close()

                    st.session_state.orchestrator = Orchestrator(
                        model=model,
                        api_key=api_key,
                    )
                    st.session_state.initialized = True

                    # 测试调用
                    info = st.session_state.orchestrator.llm.get_model_info()
                    callout(f"连接成功！模型: {info['model']}", type="success")

                    # 持久化配置到数据库
                    st.session_state.orchestrator.db.set_setting("MODEL", model)
                    st.session_state.orchestrator.db.set_setting("API_KEY", api_key)
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
