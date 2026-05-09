"""
Content2Revenue AI - 全局CSS样式系统
设计语言参考: Linear (暗色主题、精致灰度、流畅动画)
             Databox (KPI卡片、简洁图表)
             Anthropic (温暖品牌色、友好调性)
"""

import streamlit as st


# ============================================================
# CSS 变量系统
# ============================================================
CSS_VARIABLES = """
:root {
    /* === 品牌色 === */
    --brand-primary: #6366F1;
    --brand-primary-hover: #818CF8;
    --brand-primary-muted: rgba(99, 102, 241, 0.15);
    --brand-primary-subtle: rgba(99, 102, 241, 0.08);

    /* === 语义色 === */
    --color-success: #10B981;
    --color-success-muted: rgba(16, 185, 129, 0.15);
    --color-warning: #F59E0B;
    --color-warning-muted: rgba(245, 158, 11, 0.15);
    --color-error: #EF4444;
    --color-error-muted: rgba(239, 68, 68, 0.15);
    --color-info: #3B82F6;
    --color-info-muted: rgba(59, 130, 246, 0.15);

    /* === 背景层次 (Linear 风格灰度) === */
    --bg-base: #0F0F11;
    --bg-elevated: #16161A;
    --bg-surface: #1A1A2E;
    --bg-surface-hover: #1E1E35;
    --bg-overlay: #222240;
    --bg-muted: #2A2A45;

    /* === 边框 === */
    --border-default: rgba(255, 255, 255, 0.06);
    --border-subtle: rgba(255, 255, 255, 0.04);
    --border-strong: rgba(255, 255, 255, 0.12);
    --border-brand: rgba(99, 102, 241, 0.4);

    /* === 文字 === */
    --text-primary: #E2E8F0;
    --text-secondary: #94A3B8;
    --text-tertiary: #64748B;
    --text-muted: #475569;
    --text-brand: #818CF8;
    --text-inverse: #0F0F11;

    /* === 圆角 === */
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;
    --radius-full: 9999px;

    /* === 阴影 === */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
    --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.15);
    --shadow-glow-strong: 0 0 40px rgba(99, 102, 241, 0.25);

    /* === 间距 === */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 12px;
    --space-lg: 16px;
    --space-xl: 24px;
    --space-2xl: 32px;
    --space-3xl: 48px;

    /* === 动画 === */
    --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
    --ease-in-out: cubic-bezier(0.45, 0, 0.55, 1);
    --duration-fast: 150ms;
    --duration-normal: 250ms;
    --duration-slow: 400ms;
}
"""


# ============================================================
# 基础重置与全局样式
# ============================================================
BASE_STYLES = """
/* === 全局重置 === */
.stApp {
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
}

/* 隐藏 Streamlit 默认元素 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* === 字体 === */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.stApp, .stApp p, .stApp span, .stApp div, .stApp li {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}

/* === 滚动条 === */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: var(--bg-muted);
    border-radius: var(--radius-full);
}
::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
}

/* === 选中文字 === */
::selection {
    background: var(--brand-primary-muted);
    color: var(--text-brand);
}
"""


# ============================================================
# 卡片样式系统
# ============================================================
CARD_STYLES = """
/* === 基础卡片 === */
.c2r-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: var(--space-xl);
    transition: all var(--duration-normal) var(--ease-out);
    position: relative;
    overflow: hidden;
}

.c2r-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.06),
        transparent
    );
}

.c2r-card:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
}

/* === 指标卡片 (Databox 风格) === */
.c2r-metric-card {
    background: linear-gradient(
        135deg,
        var(--bg-surface) 0%,
        var(--bg-elevated) 100%
    );
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: var(--space-xl);
    position: relative;
    overflow: hidden;
    transition: all var(--duration-normal) var(--ease-out);
}

.c2r-metric-card::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -50%;
    width: 100%;
    height: 100%;
    background: radial-gradient(
        circle,
        var(--brand-primary-subtle) 0%,
        transparent 70%
    );
    pointer-events: none;
    opacity: 0;
    transition: opacity var(--duration-slow) var(--ease-out);
}

.c2r-metric-card:hover::after {
    opacity: 1;
}

.c2r-metric-card:hover {
    border-color: var(--border-brand);
    box-shadow: var(--shadow-glow);
    transform: translateY(-2px);
}

.c2r-metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    margin: var(--space-sm) 0;
}

.c2r-metric-title {
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.c2r-metric-delta {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.8125rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: var(--radius-full);
}

.c2r-metric-delta--up {
    color: var(--color-success);
    background: var(--color-success-muted);
}

.c2r-metric-delta--down {
    color: var(--color-error);
    background: var(--color-error-muted);
}

/* === 数据卡片 (Linear 风格) === */
.c2r-data-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    overflow: hidden;
    transition: all var(--duration-normal) var(--ease-out);
}

.c2r-data-card:hover {
    border-color: var(--border-strong);
}

.c2r-data-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-lg) var(--space-xl);
    border-bottom: 1px solid var(--border-subtle);
}

.c2r-data-card-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: var(--space-sm);
}

.c2r-data-card-body {
    padding: var(--space-xl);
}

.c2r-data-card-footer {
    padding: var(--space-md) var(--space-xl);
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-elevated);
}
"""


# ============================================================
# 按钮样式系统
# ============================================================
BUTTON_STYLES = """
/* === 主要按钮 === */
.c2r-btn-primary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
    padding: 10px 20px;
    background: var(--brand-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all var(--duration-fast) var(--ease-out);
    position: relative;
    overflow: hidden;
}

.c2r-btn-primary:hover {
    background: var(--brand-primary-hover);
    box-shadow: var(--shadow-glow);
    transform: translateY(-1px);
}

.c2r-btn-primary:active {
    transform: translateY(0);
    box-shadow: none;
}

/* === 次要按钮 === */
.c2r-btn-secondary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
    padding: 10px 20px;
    background: var(--bg-overlay);
    color: var(--text-primary);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all var(--duration-fast) var(--ease-out);
}

.c2r-btn-secondary:hover {
    background: var(--bg-muted);
    border-color: rgba(255, 255, 255, 0.2);
    transform: translateY(-1px);
}

/* === 幽灵按钮 === */
.c2r-btn-ghost {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
    padding: 10px 20px;
    background: transparent;
    color: var(--text-secondary);
    border: none;
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all var(--duration-fast) var(--ease-out);
}

.c2r-btn-ghost:hover {
    background: var(--bg-surface);
    color: var(--text-primary);
}

/* === 图标按钮 === */
.c2r-btn-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--duration-fast) var(--ease-out);
}

.c2r-btn-icon:hover {
    background: var(--bg-surface);
    color: var(--text-primary);
    border-color: var(--border-strong);
}

/* === 危险按钮 === */
.c2r-btn-danger {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
    padding: 10px 20px;
    background: var(--color-error-muted);
    color: var(--color-error);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all var(--duration-fast) var(--ease-out);
}

.c2r-btn-danger:hover {
    background: rgba(239, 68, 68, 0.25);
    border-color: rgba(239, 68, 68, 0.4);
}

/* === Streamlit 原生按钮覆盖 === */
.stButton > button {
    background: var(--brand-primary) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-weight: 500 !important;
    transition: all var(--duration-fast) var(--ease-out) !important;
    padding: 10px 24px !important;
}

.stButton > button:hover {
    background: var(--brand-primary-hover) !important;
    box-shadow: var(--shadow-glow) !important;
    transform: translateY(-1px) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

.stDownloadButton > button {
    background: var(--bg-overlay) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: var(--radius-md) !important;
}
"""


# ============================================================
# 状态徽章样式
# ============================================================
BADGE_STYLES = """
.c2r-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: var(--radius-full);
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    white-space: nowrap;
    transition: all var(--duration-fast) var(--ease-out);
}

.c2r-badge--blue {
    background: var(--color-info-muted);
    color: var(--color-info);
}

.c2r-badge--green {
    background: var(--color-success-muted);
    color: var(--color-success);
}

.c2r-badge--yellow {
    background: var(--color-warning-muted);
    color: var(--color-warning);
}

.c2r-badge--red {
    background: var(--color-error-muted);
    color: var(--color-error);
}

.c2r-badge--purple {
    background: var(--brand-primary-muted);
    color: var(--brand-primary-hover);
}

.c2r-badge--gray {
    background: rgba(100, 116, 139, 0.15);
    color: var(--text-secondary);
}

.c2r-badge--lg {
    padding: 6px 16px;
    font-size: 0.8125rem;
}

.c2r-badge--sm {
    padding: 2px 8px;
    font-size: 0.6875rem;
}

.c2r-badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    flex-shrink: 0;
}

.c2r-badge--pulse .c2r-badge-dot {
    animation: pulse-dot 2s ease-in-out infinite;
}
"""


# ============================================================
# 表格样式
# ============================================================
TABLE_STYLES = """
/* === 数据表格 === */
.c2r-table-wrapper {
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    overflow: hidden;
    background: var(--bg-surface);
}

.c2r-table {
    width: 100%;
    border-collapse: collapse;
}

.c2r-table thead th {
    background: var(--bg-elevated);
    padding: var(--space-md) var(--space-lg);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    text-align: left;
    border-bottom: 1px solid var(--border-default);
    white-space: nowrap;
}

.c2r-table tbody td {
    padding: var(--space-md) var(--space-lg);
    font-size: 0.875rem;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-subtle);
    transition: background var(--duration-fast) var(--ease-out);
}

.c2r-table tbody tr:last-child td {
    border-bottom: none;
}

.c2r-table tbody tr:hover td {
    background: var(--bg-surface-hover);
}

/* === Streamlit DataFrame 覆盖 === */
.stDataFrame {
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
}

.stDataFrame thead th {
    background: var(--bg-elevated) !important;
    color: var(--text-tertiary) !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    border-bottom: 1px solid var(--border-default) !important;
}

.stDataFrame tbody td {
    background: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border-bottom: 1px solid var(--border-subtle) !important;
}
"""


# ============================================================
# 侧边栏样式
# ============================================================
SIDEBAR_STYLES = """
/* === 侧边栏容器 === */
section[data-testid="stSidebar"] {
    background: var(--bg-elevated) !important;
    border-right: 1px solid var(--border-default) !important;
    width: 280px !important;
    min-width: 280px !important;
}

section[data-testid="stSidebar"]::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 1px;
    height: 100%;
    background: linear-gradient(
        180deg,
        transparent,
        var(--border-default),
        transparent
    );
}

/* === 侧边栏标题 === */
.c2r-sidebar-section {
    margin-bottom: var(--space-xl);
}

.c2r-sidebar-title {
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: var(--space-sm);
    padding: 0 var(--space-lg);
}

/* === 侧边栏导航项 === */
.c2r-nav-item {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-sm) var(--space-lg);
    margin: 2px var(--space-sm);
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--duration-fast) var(--ease-out);
    text-decoration: none;
}

.c2r-nav-item:hover {
    background: var(--bg-surface);
    color: var(--text-primary);
}

.c2r-nav-item--active {
    background: var(--brand-primary-muted);
    color: var(--text-brand);
    font-weight: 500;
}

.c2r-nav-item--active:hover {
    background: var(--brand-primary-muted);
    color: var(--text-brand);
}

/* === 侧边栏分隔线 === */
.c2r-sidebar-divider {
    height: 1px;
    background: var(--border-default);
    margin: var(--space-lg) var(--space-lg);
}

/* === 侧边栏 Logo === */
.c2r-sidebar-logo {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-lg);
    margin-bottom: var(--space-md);
}

.c2r-sidebar-logo-text {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.01em;
}

.c2r-sidebar-logo-sub {
    font-size: 0.6875rem;
    color: var(--text-tertiary);
    font-weight: 400;
}
"""


# ============================================================
# 图表容器样式
# ============================================================
CHART_STYLES = """
/* === 图表容器 === */
.c2r-chart-container {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: var(--space-xl);
    position: relative;
    overflow: hidden;
}

.c2r-chart-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.06),
        transparent
    );
}

.c2r-chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-lg);
}

.c2r-chart-title {
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
}

.c2r-chart-subtitle {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    margin-top: 2px;
}

/* === Plotly 图表覆盖 === */
.js-plotly-plot .plotly .modebar {
    background: transparent !important;
    right: 8px !important;
    top: 8px !important;
}

.js-plotly-plot .plotly .modebar-btn {
    background: var(--bg-overlay) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-sm) !important;
}

.js-plotly-plot .plotly .modebar-btn:hover {
    background: var(--bg-muted) !important;
}

/* === 图表网格布局 === */
.c2r-chart-grid {
    display: grid;
    gap: var(--space-lg);
}

.c2r-chart-grid--2 {
    grid-template-columns: repeat(2, 1fr);
}

.c2r-chart-grid--3 {
    grid-template-columns: repeat(3, 1fr);
}

.c2r-chart-grid--2-1 {
    grid-template-columns: 2fr 1fr;
}

.c2r-chart-grid--1-2 {
    grid-template-columns: 1fr 2fr;
}
"""


# ============================================================
# 页面头部样式
# ============================================================
PAGE_HEADER_STYLES = """
.c2r-page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: var(--space-2xl);
    padding-bottom: var(--space-xl);
    border-bottom: 1px solid var(--border-subtle);
}

.c2r-page-header-info {
    flex: 1;
}

.c2r-page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    line-height: 1.2;
    margin: 0;
}

.c2r-page-subtitle {
    font-size: 0.9375rem;
    color: var(--text-secondary);
    margin-top: var(--space-sm);
    line-height: 1.5;
}

.c2r-page-actions {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    flex-shrink: 0;
    margin-left: var(--space-xl);
}
"""


# ============================================================
# 空状态样式
# ============================================================
EMPTY_STATE_STYLES = """
.c2r-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-3xl) var(--space-xl);
    text-align: center;
}

.c2r-empty-state-icon {
    font-size: 3rem;
    margin-bottom: var(--space-lg);
    opacity: 0.4;
    filter: grayscale(0.5);
}

.c2r-empty-state-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-sm);
}

.c2r-empty-state-desc {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    max-width: 400px;
    line-height: 1.6;
    margin-bottom: var(--space-xl);
}
"""


# ============================================================
# 进度指示器样式
# ============================================================
PROGRESS_STYLES = """
.c2r-progress-wrapper {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
}

.c2r-progress-label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.8125rem;
}

.c2r-progress-label-text {
    color: var(--text-secondary);
    font-weight: 500;
}

.c2r-progress-label-value {
    color: var(--text-primary);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.c2r-progress-track {
    width: 100%;
    height: 6px;
    background: var(--bg-muted);
    border-radius: var(--radius-full);
    overflow: hidden;
    position: relative;
}

.c2r-progress-fill {
    height: 100%;
    border-radius: var(--radius-full);
    transition: width var(--duration-slow) var(--ease-out);
    position: relative;
}

.c2r-progress-fill--blue {
    background: linear-gradient(90deg, #3B82F6, #6366F1);
}

.c2r-progress-fill--green {
    background: linear-gradient(90deg, #10B981, #34D399);
}

.c2r-progress-fill--yellow {
    background: linear-gradient(90deg, #F59E0B, #FBBF24);
}

.c2r-progress-fill--red {
    background: linear-gradient(90deg, #EF4444, #F87171);
}

.c2r-progress-fill--purple {
    background: linear-gradient(90deg, #6366F1, #8B5CF6);
}

.c2r-progress-fill::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(255, 255, 255, 0.15) 50%,
        transparent 100%
    );
    animation: shimmer 2s ease-in-out infinite;
}
"""


# ============================================================
# 标签页样式
# ============================================================
TABS_STYLES = """
.c2r-tabs {
    display: flex;
    gap: 2px;
    border-bottom: 1px solid var(--border-default);
    padding: 0 var(--space-sm);
    position: relative;
}

.c2r-tab {
    padding: var(--space-md) var(--space-lg);
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-tertiary);
    cursor: pointer;
    border: none;
    background: none;
    position: relative;
    transition: color var(--duration-fast) var(--ease-out);
    white-space: nowrap;
}

.c2r-tab:hover {
    color: var(--text-secondary);
}

.c2r-tab--active {
    color: var(--text-primary);
}

.c2r-tab--active::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--brand-primary);
    border-radius: 2px 2px 0 0;
    animation: tab-indicator var(--duration-normal) var(--ease-out);
}

/* === Streamlit Tabs 覆盖 === */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: transparent !important;
    border-bottom: 1px solid var(--border-default) !important;
}

.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-md) var(--radius-md) 0 0 !important;
    color: var(--text-tertiary) !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    padding: var(--space-md) var(--space-lg) !important;
    transition: all var(--duration-fast) var(--ease-out) !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-secondary) !important;
    background: var(--bg-surface) !important;
}

.stTabs [aria-selected="true"] {
    color: var(--text-primary) !important;
    background: var(--bg-surface) !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--brand-primary) !important;
    height: 2px !important;
}

.stTabs [data-baseweb="tab-content"] {
    border: none !important;
    padding-top: var(--space-xl) !important;
}
"""


# ============================================================
# 动画效果
# ============================================================
ANIMATION_STYLES = """
/* === 淡入动画 === */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* === 从上方滑入 === */
@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* === 从下方滑入 === */
@keyframes slideInDown {
    from {
        opacity: 0;
        transform: translateY(-12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* === 从左侧滑入 === */
@keyframes slideInLeft {
    from {
        opacity: 0;
        transform: translateX(-12px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* === 缩放淡入 === */
@keyframes scaleIn {
    from {
        opacity: 0;
        transform: scale(0.95);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}

/* === 脉冲点 === */
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* === 微光效果 === */
@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* === 标签页指示器 === */
@keyframes tab-indicator {
    from {
        opacity: 0;
        transform: scaleX(0.8);
    }
    to {
        opacity: 1;
        transform: scaleX(1);
    }
}

/* === 加载旋转 === */
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* === 动画工具类 === */
.c2r-animate-fade-in {
    animation: fadeIn var(--duration-normal) var(--ease-out);
}

.c2r-animate-slide-up {
    animation: slideInUp var(--duration-normal) var(--ease-out);
}

.c2r-animate-slide-down {
    animation: slideInDown var(--duration-normal) var(--ease-out);
}

.c2r-animate-slide-left {
    animation: slideInLeft var(--duration-normal) var(--ease-out);
}

.c2r-animate-scale-in {
    animation: scaleIn var(--duration-normal) var(--ease-out);
}

/* === 交错动画延迟 === */
.c2r-delay-1 { animation-delay: 50ms; animation-fill-mode: both; }
.c2r-delay-2 { animation-delay: 100ms; animation-fill-mode: both; }
.c2r-delay-3 { animation-delay: 150ms; animation-fill-mode: both; }
.c2r-delay-4 { animation-delay: 200ms; animation-fill-mode: both; }
.c2r-delay-5 { animation-delay: 250ms; animation-fill-mode: both; }
.c2r-delay-6 { animation-delay: 300ms; animation-fill-mode: both; }
"""


# ============================================================
# 输入框与表单样式
# ============================================================
FORM_STYLES = """
/* === 文本输入框 === */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-size: 0.875rem !important;
    padding: 10px 14px !important;
    transition: all var(--duration-fast) var(--ease-out) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--brand-primary) !important;
    box-shadow: 0 0 0 3px var(--brand-primary-muted) !important;
    outline: none !important;
}

.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: var(--text-muted) !important;
}

/* === 选择框 === */
.stSelectbox > div > div {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}

.stSelectbox > div > div:hover {
    border-color: var(--border-strong) !important;
}

/* === 滑块 === */
.stSlider > div > div > div > div {
    background: var(--bg-muted) !important;
}

/* === 复选框 === */
.stCheckbox {
    color: var(--text-secondary) !important;
}

/* === 标签 === */
.stSelectbox label, .stTextInput label, .stTextArea label {
    color: var(--text-secondary) !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
}
"""


# ============================================================
# 工具提示与弹出层
# ============================================================
TOOLTIP_STYLES = """
/* === 工具提示 === */
.c2r-tooltip {
    position: relative;
    display: inline-flex;
}

.c2r-tooltip::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%) translateY(4px);
    padding: 6px 12px;
    background: var(--bg-overlay);
    color: var(--text-primary);
    font-size: 0.75rem;
    font-weight: 500;
    border-radius: var(--radius-sm);
    white-space: nowrap;
    pointer-events: none;
    opacity: 0;
    transition: all var(--duration-fast) var(--ease-out);
    border: 1px solid var(--border-default);
    box-shadow: var(--shadow-md);
    z-index: 100;
}

.c2r-tooltip:hover::after {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}

/* === Streamlit 工具提示覆盖 === */
.stTooltip {
    background: var(--bg-overlay) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.75rem !important;
    box-shadow: var(--shadow-md) !important;
}
"""


# ============================================================
# 分隔线与间距工具
# ============================================================
UTILITY_STYLES = """
/* === 分隔线 === */
.c2r-divider {
    height: 1px;
    background: var(--border-default);
    margin: var(--space-xl) 0;
}

.c2r-divider--thick {
    height: 2px;
    background: linear-gradient(
        90deg,
        transparent,
        var(--border-default),
        transparent
    );
}

/* === 文字截断 === */
.c2r-truncate {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* === 文字颜色工具类 === */
.c2r-text-primary { color: var(--text-primary); }
.c2r-text-secondary { color: var(--text-secondary); }
.c2r-text-tertiary { color: var(--text-tertiary); }
.c2r-text-brand { color: var(--text-brand); }
.c2r-text-success { color: var(--color-success); }
.c2r-text-warning { color: var(--color-warning); }
.c2r-text-error { color: var(--color-error); }

/* === Flex 工具类 === */
.c2r-flex { display: flex; }
.c2r-flex-col { flex-direction: column; }
.c2r-flex-center { align-items: center; justify-content: center; }
.c2r-flex-between { justify-content: space-between; }
.c2r-flex-gap-sm { gap: var(--space-sm); }
.c2r-flex-gap-md { gap: var(--space-md); }
.c2r-flex-gap-lg { gap: var(--space-lg); }
.c2r-flex-wrap { flex-wrap: wrap; }

/* === 网格布局 === */
.c2r-grid {
    display: grid;
    gap: var(--space-lg);
}

.c2r-grid--2 { grid-template-columns: repeat(2, 1fr); }
.c2r-grid--3 { grid-template-columns: repeat(3, 1fr); }
.c2r-grid--4 { grid-template-columns: repeat(4, 1fr); }

/* === 隐藏 === */
.c2r-hidden { display: none !important; }
.c2r-sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
}
"""


# ============================================================
# 响应式样式
# ============================================================
RESPONSIVE_STYLES = """
@media (max-width: 768px) {
    .c2r-chart-grid--2,
    .c2r-chart-grid--3,
    .c2r-chart-grid--2-1,
    .c2r-chart-grid--1-2 {
        grid-template-columns: 1fr;
    }

    .c2r-grid--2,
    .c2r-grid--3,
    .c2r-grid--4 {
        grid-template-columns: 1fr;
    }

    .c2r-page-header {
        flex-direction: column;
        gap: var(--space-lg);
    }

    .c2r-page-actions {
        margin-left: 0;
        width: 100%;
    }

    .c2r-metric-value {
        font-size: 2rem;
    }

    .c2r-page-title {
        font-size: 1.375rem;
    }
}
"""


# ============================================================
# 加载状态样式
# ============================================================
LOADING_STYLES = """
/* === 加载骨架屏 === */
.c2r-skeleton {
    background: linear-gradient(
        90deg,
        var(--bg-surface) 25%,
        var(--bg-surface-hover) 50%,
        var(--bg-surface) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s ease-in-out infinite;
    border-radius: var(--radius-md);
}

@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.c2r-skeleton--text {
    height: 1em;
    width: 100%;
    margin-bottom: var(--space-sm);
}

.c2r-skeleton--title {
    height: 1.5em;
    width: 60%;
    margin-bottom: var(--space-md);
}

.c2r-skeleton--card {
    height: 120px;
    width: 100%;
}

.c2r-skeleton--circle {
    width: 40px;
    height: 40px;
    border-radius: 50%;
}

/* === 加载旋转器 === */
.c2r-spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-default);
    border-top-color: var(--brand-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    display: inline-block;
}

.c2r-spinner--lg {
    width: 32px;
    height: 32px;
    border-width: 3px;
}
"""


# ============================================================
# 完整样式组合
# ============================================================
COMPLETE_STYLES = "\n".join([
    CSS_VARIABLES,
    BASE_STYLES,
    CARD_STYLES,
    BUTTON_STYLES,
    BADGE_STYLES,
    TABLE_STYLES,
    SIDEBAR_STYLES,
    CHART_STYLES,
    PAGE_HEADER_STYLES,
    EMPTY_STATE_STYLES,
    PROGRESS_STYLES,
    TABS_STYLES,
    ANIMATION_STYLES,
    FORM_STYLES,
    TOOLTIP_STYLES,
    UTILITY_STYLES,
    RESPONSIVE_STYLES,
    LOADING_STYLES,
])


def inject_styles():
    """将完整的CSS样式注入到Streamlit应用中"""
    st.markdown(
        f"<style>{COMPLETE_STYLES}</style>",
        unsafe_allow_html=True
    )


def inject_custom_css(css: str):
    """注入自定义CSS片段"""
    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True
    )


# ============================================================
# 调色板 (Dark Theme) — 从 theme.py 合并
# ============================================================
COLORS = {
    # 背景层级
    "bg_primary": "#0A0A0F",
    "bg_secondary": "#12121A",
    "bg_card": "#1A1A25",
    "bg_card_hover": "#22222F",
    "bg_input": "#14141E",
    "bg_overlay": "rgba(0, 0, 0, 0.6)",
    # 边框
    "border": "#2A2A3A",
    "border_hover": "#3A3A4F",
    "border_focus": "#6C5CE7",
    # 文字
    "text_primary": "#F0F0F5",
    "text_secondary": "#9090A8",
    "text_muted": "#606078",
    "text_placeholder": "#50506A",
    # 品牌色 - 温暖紫蓝渐变
    "brand_primary": "#6C5CE7",
    "brand_secondary": "#A78BFA",
    "brand_gradient_start": "#6C5CE7",
    "brand_gradient_end": "#A78BFA",
    # 功能色
    "success": "#22C55E",
    "success_bg": "rgba(34, 197, 94, 0.1)",
    "warning": "#F59E0B",
    "warning_bg": "rgba(245, 158, 11, 0.1)",
    "danger": "#EF4444",
    "danger_bg": "rgba(239, 68, 68, 0.1)",
    "info": "#3B82F6",
    "info_bg": "rgba(59, 130, 246, 0.1)",
    # 标签色
    "tag_blue": "#3B82F6",
    "tag_green": "#22C55E",
    "tag_orange": "#F59E0B",
    "tag_purple": "#8B5CF6",
    "tag_pink": "#EC4899",
}


# ============================================================
# 全局基础 CSS 注入 — 从 theme.py 合并
# ============================================================

_BASE_CSS = f"""
/* ===== 全局重置 ===== */
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.stApp {{
    background-color: {COLORS["bg_primary"]};
    color: {COLORS["text_primary"]};
}}

/* 隐藏 Streamlit 默认元素 */
#MainMenu, footer, header {{
    visibility: hidden;
}}

.stApp > header {{
    background-color: transparent !important;
}}

/* ===== 滚动条美化 ===== */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
::-webkit-scrollbar-track {{
    background: {COLORS["bg_secondary"]};
}}
::-webkit-scrollbar-thumb {{
    background: {COLORS["border"]};
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {COLORS["border_hover"]};
}}

/* ===== 通用卡片 ===== */
.c2r-card {{
    background: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    padding: 24px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}
.c2r-card:hover {{
    background: {COLORS["bg_card_hover"]};
    border-color: {COLORS["border_hover"]};
    box-shadow: 0 8px 32px rgba(108, 92, 231, 0.08);
}}

/* ===== 页面标题 ===== */
.c2r-page-title {{
    font-size: 28px;
    font-weight: 700;
    color: {COLORS["text_primary"]};
    letter-spacing: -0.5px;
    margin-bottom: 4px;
}}
.c2r-page-subtitle {{
    font-size: 14px;
    color: {COLORS["text_secondary"]};
    margin-bottom: 32px;
}}

/* ===== 按钮 ===== */
.c2r-btn-primary {{
    background: linear-gradient(135deg, {COLORS["brand_gradient_start"]}, {COLORS["brand_gradient_end"]});
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 28px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: inline-flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 16px rgba(108, 92, 231, 0.3);
}}
.c2r-btn-primary:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(108, 92, 231, 0.4);
}}

.c2r-btn-secondary {{
    background: {COLORS["bg_card"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: inline-flex;
    align-items: center;
    gap: 8px;
}}
.c2r-btn-secondary:hover {{
    background: {COLORS["bg_card_hover"]};
    border-color: {COLORS["border_hover"]};
    transform: translateY(-1px);
}}

.c2r-btn-ghost {{
    background: transparent;
    color: {COLORS["text_secondary"]};
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}}
.c2r-btn-ghost:hover {{
    background: {COLORS["bg_card"]};
    color: {COLORS["text_primary"]};
}}

/* ===== Tab 样式 ===== */
.c2r-tabs {{
    display: flex;
    gap: 4px;
    padding: 4px;
    background: {COLORS["bg_secondary"]};
    border-radius: 12px;
    margin-bottom: 24px;
    border: 1px solid {COLORS["border"]};
}}
.c2r-tab {{
    flex: 1;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    color: {COLORS["text_secondary"]};
    cursor: pointer;
    transition: all 0.25s ease;
    text-align: center;
    border: none;
    background: transparent;
}}
.c2r-tab:hover {{
    color: {COLORS["text_primary"]};
    background: {COLORS["bg_card"]};
}}
.c2r-tab.active {{
    background: {COLORS["bg_card"]};
    color: {COLORS["brand_primary"]};
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}

/* ===== 进度条 ===== */
.c2r-progress-bar {{
    height: 8px;
    background: {COLORS["bg_secondary"]};
    border-radius: 4px;
    overflow: hidden;
    position: relative;
}}
.c2r-progress-fill {{
    height: 100%;
    border-radius: 4px;
    transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}}
.c2r-progress-fill.green {{
    background: linear-gradient(90deg, #22C55E, #4ADE80);
}}
.c2r-progress-fill.yellow {{
    background: linear-gradient(90deg, #F59E0B, #FBBF24);
}}
.c2r-progress-fill.red {{
    background: linear-gradient(90deg, #EF4444, #F87171);
}}

/* ===== 标签 ===== */
.c2r-tag {{
    display: inline-flex;
    align-items: center;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    gap: 4px;
}}

/* ===== 淡入动画 ===== */
@keyframes c2rFadeIn {{
    from {{
        opacity: 0;
        transform: translateY(12px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0);
    }}
}}
.c2r-fade-in {{
    animation: c2rFadeIn 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}}
.c2r-fade-in-delay-1 {{
    animation: c2rFadeIn 0.5s cubic-bezier(0.4, 0, 0.2, 1) 0.1s forwards;
    opacity: 0;
}}
.c2r-fade-in-delay-2 {{
    animation: c2rFadeIn 0.5s cubic-bezier(0.4, 0, 0.2, 1) 0.2s forwards;
    opacity: 0;
}}
.c2r-fade-in-delay-3 {{
    animation: c2rFadeIn 0.5s cubic-bezier(0.4, 0, 0.2, 1) 0.3s forwards;
    opacity: 0;
}}

/* ===== 分隔线 ===== */
.c2r-divider {{
    display: flex;
    align-items: center;
    gap: 16px;
    color: {COLORS["text_muted"]};
    font-size: 13px;
    margin: 20px 0;
}}
.c2r-divider::before,
.c2r-divider::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: {COLORS["border"]};
}}

/* ===== 选择器样式覆盖 ===== */
div[data-testid="stSelectbox"] > div > div {{
    background-color: {COLORS["bg_input"]} !important;
    border: 1px solid {COLORS["border"]} !important;
    border-radius: 10px !important;
    color: {COLORS["text_primary"]} !important;
}}
div[data-testid="stSelectbox"] label {{
    color: {COLORS["text_secondary"]} !important;
    font-size: 13px !important;
}}

/* ===== 输入框样式覆盖 ===== */
div[data-testid="stTextInput"] > div > div > input {{
    background-color: {COLORS["bg_input"]} !important;
    border: 1px solid {COLORS["border"]} !important;
    border-radius: 10px !important;
    color: {COLORS["text_primary"]} !important;
    padding: 12px 16px !important;
}}
div[data-testid="stTextInput"] label {{
    color: {COLORS["text_secondary"]} !important;
    font-size: 13px !important;
}}

/* ===== Plotly 图表容器 ===== */
.js-plotly-plot .plotly .modebar {{
    display: none !important;
}}
</style>
"""


def inject_base_css():
    """注入全局基础样式（从 theme.py 合并）"""
    st.markdown(_BASE_CSS, unsafe_allow_html=True)


# ============================================================
# Plotly 统一主题 — 从 theme.py 合并
# ============================================================
PLOTLY_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {
        "family": "Inter, sans-serif",
        "color": "#9090A8",
        "size": 12,
    },
    "margin": {"l": 40, "r": 40, "t": 40, "b": 40},
    "xaxis": {
        "gridcolor": "#2A2A3A",
        "zerolinecolor": "#2A2A3A",
    },
    "yaxis": {
        "gridcolor": "#2A2A3A",
        "zerolinecolor": "#2A2A3A",
    },
}

PLOTLY_RADAR_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {
        "family": "Inter, sans-serif",
        "color": "#9090A8",
        "size": 11,
    },
    "margin": {"l": 60, "r": 60, "t": 40, "b": 40},
    "polar": {
        "radialaxis": {
            "visible": True,
            "range": [0, 10],
            "tickfont": {"size": 9, "color": "#606078"},
            "gridcolor": "#2A2A3A",
            "linecolor": "#2A2A3A",
        },
        "angularaxis": {
            "tickfont": {"size": 11, "color": "#9090A8"},
            "gridcolor": "#2A2A3A",
            "linecolor": "#2A2A3A",
            "rotation": 0,
        },
    },
    "showlegend": False,
}
