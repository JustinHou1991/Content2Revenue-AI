#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心模块集成测试

测试范围:
1. BackupManager - 备份与回滚功能
2. PluginSystem - 插件加载与管理
3. EventBus - 事件发布订阅
4. ConfigCenter - 配置管理
5. MigrationManager - 数据库迁移
6. WorkflowEngine - 工作流执行
7. RuleEngine - 规则引擎
8. DataValidator - 数据验证
9. ReportEngine - 报表生成

作者: AI Assistant
创建日期: 2026-05-09
"""

import sys
import os
import json
import tempfile
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.backup_manager import BackupManager, BackupMetadata
from core.event_bus import EventBus, EventPriority
from core.config_center import ConfigCenter
from core.migration_manager import MigrationManager
from core.workflow_engine import WorkflowEngine, Task, Workflow
from core.rule_engine import RuleEngine, Rule, RuleCondition, RuleAction, RuleContext
from core.data_validator import DataValidator, ValidationRule, FieldType
from core.report_engine import ReportEngine, ReportConfig, ReportDimension, ReportMetric, AggregationType


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name: str):
        """测试装饰器"""
        def decorator(func):
            self.tests.append((name, func))
            return func
        return decorator
    
    def run(self):
        """运行所有测试"""
        print("=" * 60)
        print("核心模块集成测试")
        print("=" * 60)
        print()
        
        for name, func in self.tests:
            try:
                func()
                print(f"✓ {name}")
                self.passed += 1
            except AssertionError as e:
                print(f"✗ {name}")
                print(f"  错误: {e}")
                self.failed += 1
            except Exception as e:
                print(f"✗ {name}")
                print(f"  异常: {type(e).__name__}: {e}")
                self.failed += 1
        
        print()
        print("=" * 60)
        print(f"测试结果: {self.passed} 通过, {self.failed} 失败")
        print("=" * 60)
        
        return self.failed == 0


runner = TestRunner()


# ==================== BackupManager 测试 ====================

@runner.test("BackupManager - 创建备份")
def test_backup_create():
    """测试备份创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试数据库
        db_path = os.path.join(tmpdir, "test.db")
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'test')")
        conn.commit()
        conn.close()
        
        # 创建备份
        manager = BackupManager(backup_dir=tmpdir)
        backup_path = manager.create_backup(db_path, name="test_backup")
        
        assert os.path.exists(backup_path), "备份文件应存在"
        
        # 验证备份元数据
        backups = manager.list_backups()
        assert len(backups) == 1, "应有一个备份"
        assert backups[0]["id"] == "test_backup", "备份名称应匹配"


@runner.test("BackupManager - 回滚功能")
def test_backup_rollback():
    """测试备份回滚"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # 创建初始数据
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'original')")
        conn.commit()
        conn.close()
        
        # 创建备份
        manager = BackupManager(backup_dir=tmpdir)
        manager.create_backup(db_path, name="before_change")
        
        # 修改数据
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE test SET name = 'modified' WHERE id = 1")
        conn.commit()
        conn.close()
        
        # 再创建一个备份（用于回滚）
        manager.create_backup(db_path, name="after_change")
        
        # 回滚
        assert manager.rollback(steps=1), "回滚应成功"
        
        # 验证数据恢复
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM test WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        
        assert result[0] == "original", "数据应恢复到原始值"


# ==================== EventBus 测试 ====================

@runner.test("EventBus - 事件发布订阅")
def test_event_bus():
    """测试事件总线"""
    bus = EventBus()
    events_received = []
    
    @bus.on("test.event")
    def handler(event):
        events_received.append(event.data)
    
    bus.emit("test.event", {"message": "hello"})
    
    assert len(events_received) == 1, "应接收到一个事件"
    assert events_received[0]["message"] == "hello", "事件数据应匹配"


@runner.test("EventBus - 优先级排序")
def test_event_priority():
    """测试事件优先级"""
    bus = EventBus()
    order = []
    
    @bus.on("priority.test", priority=EventPriority.LOW.value)
    def low_handler(event):
        order.append("low")
    
    @bus.on("priority.test", priority=EventPriority.HIGH.value)
    def high_handler(event):
        order.append("high")
    
    @bus.on("priority.test", priority=EventPriority.NORMAL.value)
    def normal_handler(event):
        order.append("normal")
    
    bus.emit("priority.test", {})
    
    assert order == ["high", "normal", "low"], "应按优先级顺序执行"


# ==================== ConfigCenter 测试 ====================

@runner.test("ConfigCenter - 配置管理")
def test_config_center():
    """测试配置中心"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, "app_config.json")
        
        # 创建初始配置
        with open(config_file, 'w') as f:
            json.dump({"database": {"host": "localhost", "port": 3306}}, f)
        
        center = ConfigCenter(config_dir=tmpdir)
        center.load_from_file(config_file)
        
        # 测试读取
        assert center.get("database.host") == "localhost", "应能读取嵌套配置"
        assert center.get("database.port") == 3306, "应能读取数字配置"
        
        # 测试设置
        center.set("database.host", "127.0.0.1")
        assert center.get("database.host") == "127.0.0.1", "设置后应更新"
        
        # 测试默认值
        assert center.get("unknown.key", "default") == "default", "应返回默认值"


# ==================== MigrationManager 测试 ====================

@runner.test("MigrationManager - 迁移执行")
def test_migration():
    """测试数据库迁移"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        migrations_dir = os.path.join(tmpdir, "migrations")
        
        manager = MigrationManager(db_path, migrations_dir)
        
        # 创建迁移
        migration_id = manager.create_migration(
            name="create_users",
            up_sql="CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
            down_sql="DROP TABLE users"
        )
        
        # 执行迁移
        applied = manager.migrate()
        assert len(applied) == 1, "应应用一个迁移"
        
        # 验证表创建
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None, "users表应存在"
        conn.close()
        
        # 测试回滚
        rolled_back = manager.rollback(steps=1)
        assert len(rolled_back) == 1, "应回滚一个迁移"


# ==================== WorkflowEngine 测试 ====================

@runner.test("WorkflowEngine - 工作流执行")
def test_workflow():
    """测试工作流引擎"""
    engine = WorkflowEngine()
    execution_order = []
    
    class SimpleTask(Task):
        def __init__(self, name):
            self._name = name
            super().__init__(task_id=name, name=name)
        
        async def execute(self, context):
            execution_order.append(self._name)
            return {"task": self._name}
    
    # 创建任务
    task_a = SimpleTask("A")
    task_b = SimpleTask("B")
    task_c = SimpleTask("C")
    
    # 设置依赖: A -> B -> C
    task_a >> task_b
    task_b >> task_c
    
    workflow = Workflow("test_workflow")
    for task in [task_a, task_b, task_c]:
        workflow.add_task(task)
    
    # 执行
    asyncio.run(engine.execute_workflow(workflow))
    
    assert execution_order == ["A", "B", "C"], "应按依赖顺序执行"


@runner.test("WorkflowEngine - 并行执行")
def test_parallel_workflow():
    """测试并行工作流"""
    engine = WorkflowEngine()
    execution_times = {}
    
    class TimedTask(Task):
        def __init__(self, name, delay):
            self._name = name
            self.delay = delay
            super().__init__(task_id=name, name=name)
        
        async def execute(self, context):
            await asyncio.sleep(self.delay)
            execution_times[self._name] = datetime.now()
            return {"task": self._name}
    
    # 创建并行任务（无依赖）
    task_a = TimedTask("A", 0.1)
    task_b = TimedTask("B", 0.1)
    task_c = TimedTask("C", 0.1)
    
    workflow = Workflow("parallel_test")
    for task in [task_a, task_b, task_c]:
        workflow.add_task(task)
    
    start_time = datetime.now()
    asyncio.run(engine.execute_workflow(workflow))
    end_time = datetime.now()
    
    # 并行执行应在约0.1秒内完成，而不是0.3秒
    duration = (end_time - start_time).total_seconds()
    assert duration < 0.25, f"并行执行应更快，实际耗时 {duration} 秒"


# ==================== RuleEngine 测试 ====================

@runner.test("RuleEngine - 规则执行")
def test_rule_engine():
    """测试规则引擎"""
    engine = RuleEngine()
    
    # 注册回调
    results = []
    def callback(context, message):
        results.append(message)
    
    engine.register_callback("test_callback", callback)
    
    # 创建规则
    rule = Rule(
        id="test_rule",
        name="测试规则",
        condition=RuleCondition(field="age", op=">=", value=18),
        actions=[
            RuleAction(type="callback", params={"handler": "test_callback", "params": {"message": "成年人"}})
        ]
    )
    
    engine.add_rule(rule)
    
    # 测试触发
    context = RuleContext(facts={"age": 25})
    engine.execute(context)
    
    assert len(results) == 1, "规则应被触发"
    assert results[0] == "成年人", "回调应被执行"
    
    # 测试不触发
    results.clear()
    context = RuleContext(facts={"age": 15})
    engine.execute(context)
    
    assert len(results) == 0, "规则不应被触发"


@runner.test("RuleEngine - 复杂条件")
def test_complex_rules():
    """测试复杂规则条件"""
    engine = RuleEngine()
    triggered = []
    
    def callback(context, **kwargs):
        triggered.append(True)
    
    engine.register_callback("complex_callback", callback)
    
    # 创建AND条件规则
    rule = Rule(
        id="complex_rule",
        name="复杂条件规则",
        condition=RuleCondition(
            logic_op="and",
            conditions=[
                RuleCondition(field="age", op=">=", value=18),
                RuleCondition(field="country", op="==", value="CN")
            ]
        ),
        actions=[RuleAction(type="callback", params={"handler": "complex_callback"})]
    )
    
    engine.add_rule(rule)
    
    # 满足所有条件
    context = RuleContext(facts={"age": 25, "country": "CN"})
    engine.execute(context)
    assert len(triggered) == 1, "应触发规则"
    
    # 不满足条件
    triggered.clear()
    context = RuleContext(facts={"age": 25, "country": "US"})
    engine.execute(context)
    assert len(triggered) == 0, "不应触发规则"


# ==================== DataValidator 测试 ====================

@runner.test("DataValidator - 基本验证")
def test_data_validator():
    """测试数据验证器"""
    schema = {
        "name": ValidationRule(
            type=FieldType.STRING,
            required=True,
            min_length=2,
            max_length=50
        ),
        "age": ValidationRule(
            type=FieldType.INTEGER,
            min_value=0,
            max_value=150
        ),
        "email": ValidationRule(
            type=FieldType.EMAIL,
            required=True
        )
    }
    
    validator = DataValidator(schema)
    
    # 有效数据
    is_valid, errors, cleaned = validator.validate({
        "name": "张三",
        "age": "25",
        "email": "zhangsan@example.com"
    })
    
    assert is_valid, f"数据应有效，错误: {errors}"
    assert cleaned["age"] == 25, "年龄应转换为整数"
    
    # 无效数据
    is_valid, errors, _ = validator.validate({
        "name": "",
        "age": 200,
        "email": "invalid-email"
    })
    
    assert not is_valid, "数据应无效"
    assert len(errors) > 0, "应有错误信息"


@runner.test("DataValidator - 嵌套验证")
def test_nested_validation():
    """测试嵌套对象验证"""
    schema = {
        "user": ValidationRule(
            type=FieldType.OBJECT,
            required=True,
            nested_schema={
                "name": ValidationRule(type=FieldType.STRING, required=True),
                "age": ValidationRule(type=FieldType.INTEGER, required=True)
            }
        )
    }
    
    validator = DataValidator(schema)
    
    # 有效嵌套数据
    is_valid, errors, cleaned = validator.validate({
        "user": {"name": "张三", "age": 25}
    })
    
    assert is_valid, f"嵌套数据应有效，错误: {errors}"
    
    # 无效嵌套数据
    is_valid, errors, _ = validator.validate({
        "user": {"name": "", "age": "invalid"}
    })
    
    assert not is_valid, "嵌套数据应无效"


# ==================== ReportEngine 测试 ====================

@runner.test("ReportEngine - 报表生成")
def test_report_engine():
    """测试报表引擎"""
    engine = ReportEngine()
    
    # 测试数据
    data = [
        {"category": "A", "region": "北", "amount": 100},
        {"category": "A", "region": "南", "amount": 200},
        {"category": "B", "region": "北", "amount": 150},
        {"category": "B", "region": "南", "amount": 250},
    ]
    
    # 配置报表
    config = ReportConfig(
        name="销售报表",
        dimensions=[ReportDimension("category")],
        metrics=[ReportMetric("amount", AggregationType.SUM, display_name="总金额")]
    )
    
    # 生成报表
    result = engine.generate(data, config)
    
    assert len(result.data) == 2, "应按类别分为2组"
    assert result.total_rows == 4, "总行数应为4"
    
    # 验证聚合结果
    category_a = next((r for r in result.data if r.get("category") == "A"), None)
    assert category_a is not None, "应包含类别A"
    assert category_a.get("总金额") == 300, "类别A总金额应为300"


@runner.test("ReportEngine - 导出功能")
def test_report_export():
    """测试报表导出"""
    engine = ReportEngine()
    
    data = [{"name": "张三", "score": 90}, {"name": "李四", "score": 85}]
    config = ReportConfig(
        name="成绩报表",
        dimensions=[ReportDimension("name")],
        metrics=[ReportMetric("score", AggregationType.SUM)]
    )
    
    result = engine.generate(data, config)
    
    # 测试JSON导出
    json_output = engine.export_to_json(result)
    assert "张三" in json_output, "JSON应包含数据"
    
    # 测试CSV导出
    csv_output = engine.export_to_csv(result)
    assert "name" in csv_output, "CSV应包含表头"
    assert "张三" in csv_output, "CSV应包含数据"
    
    # 测试HTML导出
    html_output = engine.export_to_html(result)
    assert "<table>" in html_output, "HTML应包含表格"
    assert "成绩报表" in html_output, "HTML应包含标题"


# ==================== 集成测试 ====================

@runner.test("集成测试 - 完整流程")
def test_integration():
    """测试完整集成流程"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 配置中心初始化
        config_file = os.path.join(tmpdir, "app_config.json")
        with open(config_file, 'w') as f:
            json.dump({
                "database": {"path": os.path.join(tmpdir, "app.db")},
                "features": {"validation": True, "reporting": True}
            }, f)
        
        config_center = ConfigCenter(config_dir=tmpdir)
        config_center.load_from_file(config_file)
        db_path = config_center.get("database.path")
        
        # 2. 数据库迁移
        migrations_dir = os.path.join(tmpdir, "migrations")
        migration_manager = MigrationManager(db_path, migrations_dir)
        migration_manager.create_migration(
            name="init_tables",
            up_sql="CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL, status TEXT)",
            down_sql="DROP TABLE orders"
        )
        migration_manager.migrate()
        
        # 3. 创建备份
        backup_manager = BackupManager(backup_dir=tmpdir)
        backup_manager.create_backup(db_path, name="after_init")
        
        # 4. 事件总线
        event_bus = EventBus()
        events_log = []
        
        @event_bus.on("order.created")
        def on_order_created(event):
            events_log.append(event.data)
        
        # 5. 规则引擎
        rule_engine = RuleEngine()
        high_value_orders = []
        
        def notify_high_value(context, order_id):
            high_value_orders.append(order_id)
        
        rule_engine.register_callback("notify_high_value", notify_high_value)
        rule_engine.add_rule(Rule(
            id="high_value_rule",
            name="高价值订单",
            condition=RuleCondition(field="amount", op=">=", value=1000),
            actions=[RuleAction(type="callback", params={"handler": "notify_high_value", "params": {"order_id": "$order_id"}})]
        ))
        
        # 6. 数据验证
        validator = DataValidator({
            "order_id": ValidationRule(type=FieldType.STRING, required=True),
            "amount": ValidationRule(type=FieldType.NUMBER, required=True, min_value=0),
            "status": ValidationRule(type=FieldType.STRING, required=True)
        })
        
        # 7. 模拟订单处理
        test_orders = [
            {"order_id": "ORD-001", "amount": 500, "status": "pending"},
            {"order_id": "ORD-002", "amount": 1500, "status": "pending"},
            {"order_id": "ORD-003", "amount": 2000, "status": "confirmed"},
        ]
        
        for order in test_orders:
            # 验证数据
            is_valid, errors, cleaned = validator.validate(order)
            assert is_valid, f"订单数据应有效: {errors}"
            
            # 触发事件
            event_bus.emit("order.created", cleaned)
            
            # 执行规则
            context = RuleContext(facts=cleaned)
            rule_engine.execute(context)
        
        # 验证结果
        assert len(events_log) == 3, "应记录3个订单事件"
        assert len(high_value_orders) == 2, "应识别2个高价值订单"
        
        # 8. 报表生成
        report_engine = ReportEngine()
        report_config = ReportConfig(
            name="订单统计",
            dimensions=[ReportDimension("status")],
            metrics=[
                ReportMetric("amount", AggregationType.SUM, display_name="总金额"),
                ReportMetric("order_id", AggregationType.COUNT, display_name="订单数")
            ]
        )
        
        report_result = report_engine.generate(test_orders, report_config)
        assert len(report_result.data) == 2, "应按状态分为2组"
        
        # 9. 导出报表
        html_report = report_engine.export_to_html(report_result)
        assert "订单统计" in html_report, "报表应包含标题"
        
        print(f"  集成测试完成: {len(events_log)} 个事件, {len(high_value_orders)} 个高价值订单")


# ==================== 边界与异常测试 ====================

@runner.test("RuleEngine - 规则链循环检测")
def test_rule_chain_cycle():
    """测试规则链循环检测"""
    engine = RuleEngine()
    triggered = []
    engine.register_callback("cycle_callback", lambda context, **kw: triggered.append(True))
    
    # 规则A链式调用规则B，规则B链式调用规则A
    engine.add_rule(Rule(
        id="rule_a", name="规则A",
        condition=RuleCondition(field="x", op="==", value=1),
        actions=[
            RuleAction(type="chain", params={"rule_id": "rule_b"}),
            RuleAction(type="callback", params={"handler": "cycle_callback"})
        ]
    ))
    engine.add_rule(Rule(
        id="rule_b", name="规则B",
        condition=RuleCondition(field="y", op="==", value=1),
        actions=[
            RuleAction(type="chain", params={"rule_id": "rule_a"}),
            RuleAction(type="callback", params={"handler": "cycle_callback"})
        ]
    ))
    
    context = RuleContext(facts={"x": 1, "y": 1})
    engine.execute(context)
    # 规则A触发: callback执行1次 + chain到B(被循环阻止)
    # 规则B触发: callback执行1次 + chain到A(被循环阻止)
    # 每个规则2个action，callback各执行1次 = 2次
    # 关键是不应无限递归（无循环检测时会栈溢出）
    assert len(triggered) >= 2, f"至少应触发2次，实际触发 {len(triggered)} 次"
    assert len(triggered) < 100, f"不应无限递归，实际触发 {len(triggered)} 次"


@runner.test("WorkflowEngine - 循环依赖检测")
def test_workflow_cycle_detection():
    """测试工作流循环依赖检测"""
    engine = WorkflowEngine()
    
    class DummyTask(Task):
        def __init__(self, tid):
            super().__init__(task_id=tid, name=tid)
        async def execute(self, context):
            return True
    
    task_a = DummyTask("A")
    task_b = DummyTask("B")
    
    # 创建循环: A -> B -> A
    task_a >> task_b
    task_b >> task_a
    
    wf = Workflow("cycle_test")
    wf.add_task(task_a).add_task(task_b)
    
    try:
        wf.get_execution_order()
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "循环" in str(e) or "cycle" in str(e).lower()


@runner.test("DataValidator - 空值和边界验证")
def test_validator_edge_cases():
    """测试数据验证边界条件"""
    schema = {
        "name": ValidationRule(type=FieldType.STRING, required=True, allow_null=True),
        "score": ValidationRule(type=FieldType.INTEGER, required=False, min_value=0, max_value=100, default=50),
    }
    
    validator = DataValidator(schema)
    
    # allow_null=True 时 None 应该合法
    is_valid, errors, cleaned = validator.validate({"name": None, "score": None})
    assert is_valid, f"allow_null 应该允许 None，错误: {errors}"
    assert cleaned["score"] == 50, f"应使用默认值 50，实际: {cleaned.get('score')}"
    
    # 超出范围
    is_valid, errors, _ = validator.validate({"name": "test", "score": 200})
    assert not is_valid, "超出范围应失败"
    
    # 缺少可选字段应使用默认值
    is_valid, errors, cleaned = validator.validate({"name": "hello"})
    assert is_valid, f"缺少可选字段应合法，错误: {errors}"
    assert cleaned["score"] == 50


@runner.test("ReportEngine - 空数据处理")
def test_report_empty_data():
    """测试空数据报表"""
    engine = ReportEngine()
    config = ReportConfig(
        name="空报表",
        dimensions=[ReportDimension("category")],
        metrics=[ReportMetric("amount", AggregationType.SUM)]
    )
    
    result = engine.generate([], config)
    assert result.total_rows == 0
    assert result.data == []


@runner.test("BackupManager - 备份验证失败处理")
def test_backup_verification():
    """测试备份完整性验证"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        
        manager = BackupManager(backup_dir=tmpdir)
        manager.create_backup(db_path, name="good_backup")
        
        # 篡改备份文件
        backup_dir = Path(tmpdir) / "good_backup" / "database.db"
        with open(backup_dir, "ab") as f:
            f.write(b"tampered")
        
        # 验证应失败
        assert not manager._verify_backup("good_backup"), "被篡改的备份验证应失败"


@runner.test("EventBus - 取消订阅")
def test_event_unsubscribe():
    """测试事件取消订阅"""
    bus = EventBus()
    received = []
    
    def handler(event):
        received.append(event.data)
    
    bus.subscribe("test.event", handler)
    bus.emit("test.event", {"v": 1})
    assert len(received) == 1
    
    bus.unsubscribe("test.event", handler)
    bus.emit("test.event", {"v": 2})
    assert len(received) == 1, "取消订阅后不应再收到事件"


# ==================== 运行测试 ====================

if __name__ == "__main__":
    success = runner.run()
    sys.exit(0 if success else 1)
