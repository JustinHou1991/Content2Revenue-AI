# Content2Revenue AI

> AI驱动的内容-商业转化智能平台 — 弥合内容团队与销售团队之间的数据断层

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-BSL%201.1-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-221%20|%2095%25%20Coverage-brightgreen.svg)](#测试)
[![Code Style](https://img.shields.io/badge/Code%20Style-flake8-blue.svg)](#代码规范)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](DEPLOYMENT.md)

---

## 🎯 项目背景

**问题**：内容团队不知道自己做的视频带来了什么质量的线索，销售团队也不知道哪些内容特征在驱动高价值客户。

**解决方案**：用AI分别分析抖音脚本（内容特征）和销售线索（客户画像），在语义空间中进行匹配，生成数据驱动的内容策略建议。

**核心叙事**：不是传统的归因分析（需要数据有关联），而是**智能推荐** — 基于语义理解，告诉内容团队"应该做什么样的内容来吸引高价值线索"。

---

## ✨ 核心功能

| 模块 | 功能 | 技术亮点 |
|------|------|---------|
| 📝 **内容智能分析** | 从抖音脚本提取Hook类型、情感基调、叙事结构、CTA等15+个特征 | Prompt Engineering + 结构化JSON输出 |
| 👤 **线索智能分析** | 构建客户画像：行业、痛点、购买阶段、意向度、决策因素 | 多维度画像 + 自动评分分级 |
| 🎯 **语义匹配引擎** | 5维度评估内容与线索的适配度 | 受众匹配/痛点相关/阶段对齐/CTA适当/情感共鸣 |
| 💡 **AI策略顾问** | 生成内容策略、分发策略、转化预测、A/B测试建议 | 多步推理 + 业务知识融合 |
| 💾 **智能缓存管理** | 基于内容Hash的缓存系统，TTL过期机制 | 降低API调用成本，提升响应速度 |
| 🛡️ **安全输入验证** | Prompt注入检测、XSS防护、SQL注入防护 | 多层安全防护机制 |
| 📊 **审计日志系统** | 记录用户操作和系统事件 | 支持合规审计和问题追溯 |
| 🏥 **健康检查监控** | 数据库、磁盘、内存状态监控 | 实时系统健康状态 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                  展示层 (Streamlit UI)                       │
│  仪表盘 | 内容分析 | 线索分析 | 匹配中心 | 策略建议 | 💰 成本分析  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  服务层 (Orchestrator)                       │
│  ContentAnalyzer → LeadAnalyzer → MatchEngine → StrategyAdvisor │
│  ScoringModel | ABTestEngine | DataCleaner                     │
│  BaseAnalyzer (抽象基类) | HealthChecker                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  基础设施层 (config.py + utils/)              │
│  配置管理 | 日志系统 | 缓存系统 | 性能监控 | 数据导出 | 智能字段映射 │
│  CacheManager | InputValidator | AuditLogger                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  能力层 (LLM + Prompt)                       │
│  DeepSeek / 通义千问 (OpenAI兼容协议)                         │
│  JSON Mode + 自动重试 + 结构化输出 + 内容Hash缓存              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  数据层 (SQLite + CSV)                       │
│  content_analysis | lead_analysis | match_results             │
│  strategy_advice | app_settings | analysis_cache              │
│  api_usage | strategy_feedback | ab_tests | audit_logs        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 方式一：Docker部署（推荐，3分钟启动）

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/content2revenue.git
cd content2revenue

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的API Key

# 3. 启动服务
docker-compose up -d

# 4. 访问应用
# 打开浏览器访问 http://localhost:8501
```

详细部署指南请查看 [DEPLOYMENT.md](DEPLOYMENT.md)

### 方式二：本地开发环境

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API Key
export DEEPSEEK_API_KEY="sk-your-key"
# 或
export DASHSCOPE_API_KEY="sk-your-key"

# 3. 启动应用
streamlit run app.py
```

打开浏览器访问 `http://localhost:8501`

### 4. 加载示例数据

首次使用时，可通过应用内「系统设置」页面一键加载示例数据（包含3条抖音脚本和5条销售线索），快速体验完整功能流程。

### 5. 运行测试

```bash
python -m pytest tests/ -v
```

当前包含 **221个单元测试**，覆盖核心业务逻辑、配置管理、数据处理等模块，**代码覆盖率达到95%**。

---

## 📁 项目结构

```
content2revenue/
├── app.py                      # Streamlit主入口
├── config.py                   # 统一配置管理（三级优先级）
├── requirements.txt            # 依赖清单
├── .cursorrules                # Cursor AI配置
├── .streamlit/
│   └── config.toml             # 主题配置
│
├── services/                   # 核心业务逻辑
│   ├── llm_client.py           # 统一LLM接口（DeepSeek/通义千问）
│   ├── base_analyzer.py        # 分析器抽象基类
│   ├── content_analyzer.py     # 内容特征提取
│   ├── lead_analyzer.py        # 线索画像构建
│   ├── match_engine.py         # 语义匹配引擎
│   ├── strategy_advisor.py     # AI策略顾问
│   ├── database.py             # SQLite数据持久化
│   ├── data_cleaner.py         # 数据清洗Pipeline
│   ├── orchestrator.py         # 端到端流程编排
│   ├── ab_test_engine.py       # A/B测试引擎
│   ├── scoring_model.py        # 内容评分模型
│   ├── health_check.py         # 健康检查器
│   └── request_batcher.py      # 请求批处理器
│
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── logger.py               # 日志系统（RotatingFileHandler）
│   ├── cache.py                # 基于内容hash的缓存系统
│   ├── cache_manager.py        # 统一缓存管理器（内存+TTL）
│   ├── input_validator.py      # 输入验证器（安全防护）
│   ├── audit_logger.py         # 审计日志记录器
│   ├── performance.py          # 性能监控（执行时间追踪）
│   ├── export.py               # 数据导出（Excel/PDF）
│   └── field_mapping.py        # 智能字段映射（CSV自动识别）
│
├── prompts/                    # Prompt模板
│   └── content_analysis.py     # 内容分析Prompt
│
├── ui/                         # Streamlit界面
│   ├── components/             # UI组件
│   │   ├── charts.py           # 图表组件
│   │   ├── data_display.py     # 数据展示组件
│   │   ├── design_system.py    # 设计系统
│   │   └── forms.py            # 表单组件
│   ├── pages/                  # 页面模块
│   │   ├── dashboard.py        # 仪表盘
│   │   ├── content_analysis.py # 内容分析
│   │   ├── lead_analysis.py    # 线索分析
│   │   ├── match_center.py     # 匹配中心
│   │   ├── strategy.py         # 策略建议
│   │   ├── cost_analytics.py   # 成本分析（Plotly图表）
│   │   └── settings.py         # 系统设置
│   ├── base_page.py            # 页面基类
│   └── styles.py               # 样式定义
│
├── tests/                      # 单元测试
│   ├── __init__.py
│   ├── test_analyzers.py       # 分析器测试
│   ├── test_base_analyzer.py   # 基类分析器测试
│   ├── test_cache_manager.py   # 缓存管理器测试
│   ├── test_input_validator.py # 输入验证器测试
│   ├── test_audit_logger.py    # 审计日志测试
│   ├── test_health_check.py    # 健康检查测试
│   ├── test_data_cleaner.py    # 数据清洗测试
│   ├── test_database.py        # 数据库测试
│   ├── test_database_integration.py  # 数据库集成测试
│   ├── test_data_cleaner_integration.py  # 数据清洗集成测试
│   ├── test_scoring_model_integration.py # 评分模型集成测试
│   ├── test_llm_client_threading.py      # LLM客户端线程测试
│   ├── test_e2e_pipeline.py    # 端到端流程测试
│   └── conftest.py             # pytest配置
│
├── docs/                       # 文档目录
│   ├── API.md                  # API使用文档
│   └── ARCHITECTURE.md         # 架构文档
│
├── .github/workflows/          # CI/CD配置
│   └── ci.yml                  # GitHub Actions工作流
│
└── data/
    ├── sample_data.py          # 示例数据
    └── logs/
        └── c2r.log             # 应用日志文件
```

---

## 🔧 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 前端 | Streamlit | Python全栈，快速构建数据应用界面，支持热重载和组件化开发 |
| 后端 | Streamlit (单体) | 前后端一体化架构，简化部署和开发流程 |
| 数据库 | SQLite | 轻量、零依赖、单文件 |
| AI | OpenAI兼容SDK | DeepSeek/通义千问均支持 |
| 数据处理 | Pandas | 数据清洗和标准化 |
| 可视化 | Plotly | 交互式图表 |
| 日志系统 | logging + RotatingFileHandler | 自动轮转、模块级别控制 |
| 缓存系统 | utils/cache.py + CacheManager | 基于内容hash的SQLite缓存 + 内存缓存，TTL过期机制 |
| 性能监控 | utils/performance.py | 函数执行时间追踪、慢操作警告、基准测试 |
| 数据导出 | openpyxl + reportlab | Excel/PDF报告生成，支持批量导出 |
| 智能字段映射 | utils/field_mapping.py | CSV导入自动识别字段，支持同义词匹配 |
| 安全防护 | utils/input_validator.py | Prompt注入检测、XSS防护、SQL注入防护 |
| 审计日志 | utils/audit_logger.py | 用户操作和系统事件记录 |
| 健康检查 | services/health_check.py | 数据库、磁盘、内存状态监控 |

---

## ⚙️ 配置管理

项目采用**三级配置优先级**机制，确保灵活性与安全性的平衡：

| 优先级 | 配置来源 | 说明 |
|--------|---------|------|
| 1（最高） | 环境变量 | `DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY` 等 |
| 2 | `secrets.toml` | Streamlit Secrets，适合部署环境 |
| 3（最低） | 数据库设置表 | 应用内「系统设置」页面配置，支持持久化 |

配置逻辑统一由 `config.py` 管理，所有模块通过 `get_config()` 获取配置项。

---

## 📝 日志系统

项目内置结构化日志系统，便于问题排查和运行监控：

- **日志文件位置**: `data/logs/c2r.log`
- **轮转策略**: 单文件最大 5MB，保留 3 个备份
- **级别控制**: 按模块设置不同日志级别（DEBUG/INFO/WARNING/ERROR）
- **格式**: `[时间] [级别] [模块] 消息内容`

日志系统由 `utils/logger.py` 统一管理，各模块通过 `get_logger(__name__)` 获取实例。

---

## 🛡️ 安全特性

项目内置多层安全防护机制：

| 安全层 | 实现 | 功能 |
|--------|------|------|
| 输入验证 | `InputValidator` | XSS检测、SQL注入防护、危险模式过滤 |
| Prompt注入防护 | 正则表达式匹配 | 检测"忽略指令"等注入模式 |
| 内容清洗 | HTML转义 | 防止恶意脚本执行 |
| 审计日志 | `AuditLogger` | 记录所有敏感操作，支持追溯 |
| 访问控制 | 操作日志关联用户ID | 支持用户行为分析 |

---

## ⚡ 性能优化

项目采用多种性能优化策略：

| 优化点 | 实现 | 效果 |
|--------|------|------|
| 智能缓存 | `CacheManager` + `@cached` 装饰器 | 减少重复API调用，命中率可达80%+ |
| 批量处理 | `batch_analyze` 方法 | 支持批量分析，减少IO开销 |
| 连接池 | SQLite连接复用 | 减少数据库连接开销 |
| 异步处理 | 线程安全的LLM客户端 | 支持并发API调用 |
| 性能监控 | `performance.py` | 实时追踪慢操作，支持优化决策 |

---

## 📊 数据格式

### 销售线索CSV

| 字段 | 说明 | 示例 |
|------|------|------|
| 公司名称 | 客户公司 | 启航教育科技 |
| 行业 | 所属行业 | 教育培训 |
| 联系人姓名 | 姓名 | 张总 |
| 职位 | 角色 | 创始人 |
| 需求描述 | 客户需求 | 获客成本太高 |
| 来源 | 线索来源 | 抖音私信 |
| 意向级别 | A/B/C/D | A |

### 抖音脚本CSV

| 字段 | 说明 | 示例 |
|------|------|------|
| 完整脚本 | 脚本全文 | 你是不是还在用传统方式... |
| 标题 | 视频标题 | 3步获客法 |
| 播放量 | 播放数据 | 10000 |
| 点赞数 | 互动数据 | 500 |

---

## 🗺️ Roadmap

### Phase 2 — 智能优化（已完成）
- [x] 批量导出: 支持导出分析报告为PDF/Excel
- [x] 数据看板增强: 成本分析页面（Plotly图表）
- [x] CI/CD流水线: GitHub Actions配置
- [x] 缓存系统: 基于内容hash的缓存
- [x] 性能监控: 执行时间追踪
- [x] 智能字段映射: CSV导入自动识别字段
- [x] 批量操作取消: 支持中断批量分析
- [x] A/B测试框架：同一线索生成多个策略版本
- [x] 效果追踪：将策略建议的采纳率和实际转化率回传
- [x] 内容评分模型：基于历史数据训练轻量级评分模型
- [x] **架构重构**: BaseAnalyzer抽象基类，统一分析器接口
- [x] **缓存管理器**: CacheManager统一内存缓存管理
- [x] **输入验证器**: InputValidator安全防护层
- [x] **审计日志**: AuditLogger操作审计系统
- [x] **健康检查**: HealthChecker系统状态监控

### Phase 3 — 工作流自动化（探索中）
- [ ] 多平台适配：抖音/快手/视频号不同风格
- [ ] 团队协作：脚本审核工作流、版本管理
- [ ] 数据飞轮：视频发布后真实数据回传，持续优化

### Phase 4 — 企业级能力（长期愿景）
- [ ] RAG知识库：行业知识增强策略建议
- [ ] 私有化部署方案
- [ ] API开放平台

---

## 🤔 设计决策

> 详见 [DECISIONS.md](DECISIONS.md)

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端框架 | Streamlit | Python开发者友好，快速迭代，内置数据可视化组件丰富 |
| 后端架构 | 单体应用 | 降低系统复杂度，便于本地部署和快速迭代 |
| 数据库 | SQLite | 零依赖，单文件存储，备份简单，适合中小规模数据 |
| LLM接口 | OpenAI兼容SDK | 国内主流模型（DeepSeek/通义千问）原生支持，无需额外适配层 |
| JSON保障 | 三重机制 | API层+Prompt层+后处理层，确保结构化输出稳定性 |
| 缓存策略 | 内容Hash+SQLite | 零额外依赖，自动过期，统计方便，有效降低API调用成本 |
| A/B测试 | 独立引擎 | 与核心业务解耦，支持统计显著性检验，数据持久化便于长期追踪 |
| 成本追踪 | LLMClient集成 | 实时计算每次调用成本，支持多维度分析和优化建议 |
| 架构模式 | 模板方法模式 | BaseAnalyzer定义标准流程，子类实现特定逻辑，确保一致性 |
| 安全防护 | 多层验证 | 输入层+处理层双重防护，防止Prompt注入和XSS攻击 |

---

## 📄 License

Business Source License 1.1 (BSL 1.1)

本项目采用 BSL 1.1 许可证，允许个人学习、内部使用和学术研究，商业使用需获得授权。

- **允许**: 个人学习、内部使用、学术研究、贡献代码
- **限制**: 不得将本项目作为SaaS服务提供给第三方、不得嵌入竞争产品转售
- **4年后**: 自动转为 Apache 2.0 许可证

详见 [LICENSE](LICENSE) 文件。

---

## 💼 商业化与部署

### 企业级特性

| 特性 | 状态 | 说明 |
|------|------|------|
| Docker部署 | ✅ 已支持 | 一键启动，含生产/开发环境 |
| 用户认证 | ✅ 已支持 | JWT认证，RBAC权限控制 |
| 多租户 | 🚧 规划中 | 数据隔离，支持SaaS模式 |
| PostgreSQL | 🚧 规划中 | 高性能数据库支持 |
| API开放平台 | 🚧 规划中 | RESTful API，Webhook支持 |
| 前端重构 | 🚧 规划中 | Next.js + React |

### 部署文档

- [DEPLOYMENT.md](DEPLOYMENT.md) - Docker部署指南
- [docs/DATABASE_MIGRATION_PLAN.md](docs/DATABASE_MIGRATION_PLAN.md) - 数据库迁移方案
- [docs/FRONTEND_REFACTOR_PLAN.md](docs/FRONTEND_REFACTOR_PLAN.md) - 前端重构计划
- [docs/COMMERCIAL_FEASIBILITY_REPORT.md](docs/COMMERCIAL_FEASIBILITY_REPORT.md) - 商业化可行性分析

### 商业授权

如需商业授权、定制开发或技术支持，请联系：
- Email: justinhou@example.com

---

## 👤 作者

**JustinHou**

PM + 抖音运营背景，转型AI Generalist。

> "我不只是会写代码的PM，我是能用AI解决真实商业问题的工程师。"
