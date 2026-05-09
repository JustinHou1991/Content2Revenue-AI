# Changelog

所有项目的显著变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [2.1.0] - 2026-05-09

### 核心架构 (core/)

#### 新增 8 个企业级核心模块
- **BackupManager** - 数据库在线备份、SHA-256 完整性校验、版本回滚
- **EventBus** - 发布-订阅事件总线、5 级优先级、同步/异步处理
- **ConfigCenter** - 多环境配置管理、嵌套键支持、Fernet 加密存储
- **MigrationManager** - 数据库版本控制、自动迁移、回滚支持
- **WorkflowEngine** - DAG 任务编排、并行执行、失败重试、超时控制
- **RuleEngine** - DSL 规则定义、复杂条件组合（AND/OR/NOT）、热更新
- **DataValidator** - 声明式验证、多类型支持、嵌套对象验证、数据清洗
- **ReportEngine** - 多维度分析、聚合函数、JSON/CSV/HTML/Markdown 导出

### 代码质量优化

#### 修复 5 个 Critical 级别问题
- 第三方依赖（yaml/cryptography）添加容错导入
- 修复裸 except 捕获 SystemExit/KeyboardInterrupt
- 修复数据库连接泄漏（嵌套 try/finally）
- 修复 workflow timeout=None 导致 TypeError
- 添加递归深度保护防止栈溢出

#### 修复 6 个 High 级别问题
- 备份恢复失败时自动从临时备份还原
- EventBus 读取 handlers 时添加线程锁
- 迁移 ID 比较改为精确匹配
- 插件系统初始化添加循环依赖检测
- 规则链添加循环检测防止无限递归

#### 修复 11 个 Medium 级别问题
- 清理所有未使用的导入
- 移除模块级 logging.basicConfig() 避免干扰应用日志
- HTML 导出添加 XSS 转义
- 工作流拓扑排序添加环检测
- fnmatch/hashlib 导入移至文件顶部

### 测试

#### 新增 21 个核心模块集成测试
- BackupManager: 备份创建、回滚、完整性验证
- EventBus: 发布订阅、优先级排序、取消订阅
- ConfigCenter: 配置管理
- MigrationManager: 迁移执行与回滚
- WorkflowEngine: 顺序执行、并行执行、循环依赖检测
- RuleEngine: 规则执行、复杂条件、循环链检测
- DataValidator: 基本验证、嵌套验证、空值边界
- ReportEngine: 报表生成、导出、空数据处理
- 完整业务流程集成测试

### 依赖更新
- 新增 `pyyaml>=6.0`（配置中心 YAML 支持）
- 新增 `cryptography>=41.0`（配置加密）
- 新增 `pytest>=7.0.0`（测试框架）

### 文档
- 新增 `docs/CORE_MODULES.md` - 核心模块 API 文档
- 更新 `docs/ROADMAP_v2.md` - Phase 2 全部标记完成

---

## [2.0.0] - 2024-01-15

### 架构重构

#### 新增抽象基类 `BaseAnalyzer`
- 引入模板方法模式，统一所有分析器的标准流程
- 定义抽象方法：`_get_system_prompt`、`_build_prompt`、`_parse_response`
- 提供默认实现：输入验证、输出验证、历史记录
- 支持批量分析，带进度回调和取消机制
- 集成缓存装饰器，自动缓存分析结果
- 集成 `InputValidator`，内置安全防护

#### 新增缓存管理器 `CacheManager`
- 统一的内存缓存管理，支持TTL过期
- LRU淘汰策略，超出容量自动清理
- 线程安全实现，支持并发访问
- 提供 `@cached` 装饰器，简化缓存使用
- 命中率统计，便于性能优化

### 安全加固

#### 新增输入验证器 `InputValidator`
- **XSS防护**：检测并过滤 `<script>`、事件处理器等危险标签
- **SQL注入防护**：检测 `SELECT`、`DROP` 等SQL关键字
- **Prompt注入防护**：检测"忽略指令"等攻击模式
- 内容长度限制，防止资源耗尽攻击
- 支持文本、JSON、CSV多种数据类型的验证

#### 新增审计日志 `AuditLogger`
- 结构化记录所有敏感操作
- SQLite持久化存储，支持高效查询
- 多维度索引：时间、事件类型、用户ID
- 内置API调用和数据访问便捷方法
- 支持操作耗时统计和错误追踪

### 系统监控

#### 新增健康检查 `HealthChecker`
- 内置数据库连接检查，返回延迟指标
- 磁盘空间监控，支持使用率告警
- 内存使用监控（需安装 psutil）
- 支持注册自定义检查项
- 自动计算整体健康状态

### 性能优化

- **智能缓存策略**：分析结果自动缓存，命中率可达80%+
- **批量处理优化**：支持批量分析，减少IO开销
- **连接复用**：SQLite连接池优化
- **线程安全**：LLM客户端支持并发调用

### 测试提升

- 测试数量从 48 个提升至 **221 个**
- 代码覆盖率从 60% 提升至 **95%**
- 新增测试模块：
  - `test_base_analyzer.py` - 基类分析器测试
  - `test_cache_manager.py` - 缓存管理器测试
  - `test_input_validator.py` - 输入验证器测试
  - `test_audit_logger.py` - 审计日志测试
  - `test_health_check.py` - 健康检查测试
  - `test_database_integration.py` - 数据库集成测试
  - `test_data_cleaner_integration.py` - 数据清洗集成测试
  - `test_scoring_model_integration.py` - 评分模型集成测试
  - `test_llm_client_threading.py` - LLM客户端线程测试
  - `test_e2e_pipeline.py` - 端到端流程测试

### 代码规范

- 统一代码风格，通过 flake8 检查
- 最大行长度：120字符
- 完善类型注解
- 增强文档字符串

---

## [1.2.0] - 2024-01-01

### 新增功能

#### A/B测试引擎
- 同一线索生成多个策略版本
- 支持统计显著性检验
- 效果追踪和数据持久化

#### 内容评分模型
- 基于历史数据训练轻量级评分模型
- 自动评估内容质量
- 支持模型版本管理

#### 成本分析
- 实时计算每次API调用成本
- 多维度成本分析图表
- 成本优化建议

### 改进

- 优化CSV导入，支持智能字段映射
- 增强批量操作，支持取消功能
- 改进错误处理和用户提示

---

## [1.1.0] - 2023-12-01

### 新增功能

#### 数据导出
- 支持导出为Excel格式
- 支持导出为PDF报告
- 批量导出功能

#### 性能监控
- 函数执行时间追踪
- 慢操作警告
- 性能基准测试

#### 缓存系统
- 基于内容Hash的缓存
- TTL过期机制
- 缓存统计

### 改进

- 优化数据库查询性能
- 改进UI响应速度
- 增强错误日志

---

## [1.0.0] - 2023-11-01

### 初始版本

#### 核心功能
- 内容智能分析（抖音脚本）
- 线索智能分析（销售线索）
- 语义匹配引擎
- AI策略顾问

#### 基础设施
- SQLite数据持久化
- 统一配置管理
- 日志系统
- CI/CD流水线

#### UI界面
- Streamlit仪表盘
- 内容分析页面
- 线索分析页面
- 匹配中心
- 策略建议页面
- 系统设置

---

## 版本说明

### 版本号格式

版本号格式：主版本号.次版本号.修订号

- **主版本号**：重大架构变更或不兼容的API修改
- **次版本号**：向下兼容的功能新增
- **修订号**：向下兼容的问题修复

### 标签说明

- `[SECURITY]` - 安全相关更新
- `[PERFORMANCE]` - 性能优化
- `[BUGFIX]` - 问题修复
- `[FEATURE]` - 新功能
- `[DOCS]` - 文档更新
- `[REFACTOR]` - 代码重构

---

## 升级指南

### 从 1.x 升级到 2.0

1. **依赖更新**
   ```bash
   pip install -r requirements.txt
   ```

2. **数据库迁移**
   - 自动创建 `audit_logs` 表
   - 无需手动迁移数据

3. **代码适配**
   - 自定义分析器建议继承 `BaseAnalyzer`
   - 使用 `@cached` 装饰器替代手动缓存
   - 使用 `InputValidator` 进行输入验证

4. **配置更新**
   - 新增可选配置项（有默认值）
   - 原有配置完全兼容

---

## 未来计划

### 2.1.0 (计划中)
- [ ] 多平台适配（抖音/快手/视频号）
- [ ] 团队协作功能
- [ ] 数据飞轮机制

### 3.0.0 (长期)
- [ ] RAG知识库集成
- [ ] 私有化部署方案
- [ ] API开放平台
