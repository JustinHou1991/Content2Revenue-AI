# Content2Revenue AI - 核心模块文档

## 概述

本文档描述了 Content2Revenue AI 平台的核心架构模块，这些模块提供了可扩展、可靠的企业级基础设施。

## 核心模块清单

### 1. BackupManager - 备份管理器

**文件**: `core/backup_manager.py`

**功能**:
- 数据库在线备份（SQLite backup API）
- 配置文件备份
- 完整性校验（SHA-256）
- 版本回滚支持
- 自动清理旧备份

**使用示例**:
```python
from core.backup_manager import BackupManager

# 创建备份
bm = BackupManager("data/backups")
backup_id = bm.create_backup(
    "data/app.db",
    config_paths=["config.yaml"],
    name="pre_update_backup"
)

# 回滚到上一个版本
bm.rollback(steps=1)
```

### 2. EventBus - 事件总线

**文件**: `core/event_bus.py`

**功能**:
- 发布-订阅模式事件通信
- 5级优先级系统（CRITICAL, HIGH, NORMAL, LOW, BACKGROUND）
- 同步/异步事件处理
- 事件过滤和持久化

**使用示例**:
```python
from core.event_bus import EventBus, EventPriority

bus = EventBus()

@bus.on("order.created", priority=EventPriority.HIGH)
def handle_order(event):
    print(f"收到订单: {event.data}")

bus.emit("order.created", {"order_id": "123", "amount": 1000})
```

### 3. ConfigCenter - 配置中心

**文件**: `core/config_center.py`

**功能**:
- 多环境配置管理（dev/test/prod）
- 嵌套配置键支持（如 `database.url`）
- 动态配置刷新
- 配置加密（Fernet）
- 环境变量加载

**使用示例**:
```python
from core.config_center import ConfigCenter

config = ConfigCenter("config")
config.load_from_file("config.yaml", profile="dev")

# 获取配置
db_url = config.get("database.url")
port = config.get("server.port", 8080)  # 带默认值

# 设置加密
config.set_encryption_key("secret-key")
config.set_secure("api.key", "sensitive-value")
```

### 4. MigrationManager - 迁移管理器

**文件**: `core/migration_manager.py`

**功能**:
- 数据库版本控制
- 自动迁移执行
- 迁移回滚
- 校验和验证
- 迁移历史记录

**使用示例**:
```python
from core.migration_manager import MigrationManager

mm = MigrationManager("data/app.db", "migrations")

# 创建迁移
mm.create_migration(
    name="add_users_table",
    up_sql="CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
    down_sql="DROP TABLE users"
)

# 执行迁移
mm.migrate()

# 回滚
mm.rollback(steps=1)
```

### 5. WorkflowEngine - 工作流引擎

**文件**: `core/workflow_engine.py`

**功能**:
- DAG（有向无环图）任务编排
- 并行任务执行
- 依赖管理（`>>` 操作符）
- 失败重试机制
- 超时控制

**使用示例**:
```python
from core.workflow_engine import WorkflowEngine, Task, Workflow

class DataTask(Task):
    async def execute(self, context):
        return {"processed": True}

# 创建工作流
wf = Workflow("data_pipeline")
task_a = DataTask("extract")
task_b = DataTask("transform")
task_c = DataTask("load")

# 设置依赖: A -> B -> C
task_a >> task_b >> task_c

wf.add_task(task_a).add_task(task_b).add_task(task_c)

# 执行
engine = WorkflowEngine()
results = await engine.execute_workflow(wf)
```

### 6. RuleEngine - 规则引擎

**文件**: `core/rule_engine.py`

**功能**:
- DSL规则定义（JSON格式）
- 复杂条件组合（AND/OR/NOT）
- 热更新支持
- 规则优先级
- 回调函数注册

**使用示例**:
```python
from core.rule_engine import RuleEngine, Rule, RuleCondition, RuleAction, RuleContext

engine = RuleEngine()

# 注册回调
def notify_admin(context, message):
    print(f"通知: {message}")

engine.register_callback("notify", notify_admin)

# 创建规则
rule = Rule(
    id="high_value_order",
    name="高价值订单",
    condition=RuleCondition(field="amount", op=">=", value=1000),
    actions=[
        RuleAction(type="callback", params={
            "handler": "notify",
            "params": {"message": "高价值订单!"}
        })
    ],
    priority=10
)

engine.add_rule(rule)

# 执行
context = RuleContext(facts={"amount": 1500})
engine.execute(context)
```

### 7. DataValidator - 数据验证器

**文件**: `core/data_validator.py`

**功能**:
- 声明式验证规则
- 多种数据类型支持（string, integer, email, url等）
- 嵌套对象验证
- 自定义验证函数
- 数据清洗

**使用示例**:
```python
from core.data_validator import DataValidator, ValidationRule, FieldType

schema = {
    "email": ValidationRule(type=FieldType.EMAIL, required=True),
    "age": ValidationRule(
        type=FieldType.INTEGER,
        min_value=0,
        max_value=150
    ),
    "tags": ValidationRule(
        type=FieldType.ARRAY,
        item_schema=ValidationRule(type=FieldType.STRING)
    )
}

validator = DataValidator(schema)
is_valid, errors, cleaned = validator.validate({
    "email": "user@example.com",
    "age": "25",
    "tags": ["premium", "active"]
})
```

### 8. ReportEngine - 报表引擎

**文件**: `core/report_engine.py`

**功能**:
- 多维度数据分析
- 聚合函数（SUM, AVG, COUNT, MIN, MAX等）
- 数据透视表
- 多种导出格式（JSON, CSV, HTML, Markdown）
- 报表模板管理

**使用示例**:
```python
from core.report_engine import ReportEngine, ReportConfig, ReportDimension, ReportMetric, AggregationType

engine = ReportEngine()

# 配置报表
config = ReportConfig(
    name="销售报表",
    dimensions=[ReportDimension("category"), ReportDimension("region")],
    metrics=[
        ReportMetric("amount", AggregationType.SUM, display_name="销售额"),
        ReportMetric("quantity", AggregationType.SUM, display_name="销量")
    ]
)

# 生成报表
data = [
    {"category": "A", "region": "北", "amount": 1000, "quantity": 10},
    {"category": "A", "region": "南", "amount": 2000, "quantity": 20},
]

result = engine.generate(data, config)

# 导出
html = engine.export_to_html(result)
csv = engine.export_to_csv(result)
```

## 架构设计原则

### 1. 单一职责
每个模块专注于一个明确的职责领域，通过清晰的接口与其他模块交互。

### 2. 可扩展性
- 插件系统支持自定义扩展
- 回调机制允许业务逻辑注入
- 配置驱动，无需修改代码

### 3. 可靠性
- 完整的错误处理和日志记录
- 事务支持（数据库操作）
- 备份和回滚机制

### 4. 性能
- 异步执行支持
- 并行处理
- 缓存机制

## 集成测试

所有核心模块都包含完整的集成测试：

```bash
python tests/test_core_modules.py
```

测试覆盖：
- BackupManager: 备份创建和回滚
- EventBus: 事件发布订阅和优先级
- ConfigCenter: 配置管理和加密
- MigrationManager: 数据库迁移和回滚
- WorkflowEngine: 工作流执行和并行处理
- RuleEngine: 规则执行和复杂条件
- DataValidator: 数据验证和清洗
- ReportEngine: 报表生成和导出
- 完整集成流程测试

## 最佳实践

1. **错误处理**: 始终检查返回值和异常
2. **日志记录**: 使用模块提供的日志功能
3. **配置管理**: 敏感信息使用加密存储
4. **测试**: 新功能必须包含单元测试
5. **文档**: 更新本文档以反映API变更

## 版本历史

- v1.0.0 (2026-05-09): 初始版本，包含8个核心模块
