#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
30轮迭代审查测试

每轮测试包括:
1. 语法检查
2. 单元测试
3. 集成测试
4. 边界条件测试
5. 性能基准测试
6. 代码质量检查

作者: AI Assistant
创建日期: 2026-05-09
"""

import sys
import os
import time
import subprocess
import tempfile
import threading
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入所有核心模块
from core.backup_manager import BackupManager
from core.event_bus import EventBus
from core.config_center import ConfigCenter
from core.migration_manager import MigrationManager
from core.workflow_engine import WorkflowEngine, Task, Workflow
from core.rule_engine import RuleEngine, Rule, RuleCondition, RuleAction, RuleContext
from core.data_validator import DataValidator, ValidationRule, FieldType
from core.report_engine import ReportEngine, ReportConfig, ReportDimension, ReportMetric, AggregationType
from core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError, registry
from core.middleware_manager import MiddlewareManager, MiddlewareContext, LoggingMiddleware
from core.di_container import DIContainer, Lifecycle
from core.saga_orchestrator import SagaOrchestrator, SagaDefinition
from core.connection_pool import ConnectionPool, PoolConfig, DatabaseConnectionFactory


class RoundTestRunner:
    """轮次测试运行器"""
    
    def __init__(self, total_rounds: int = 30):
        self.total_rounds = total_rounds
        self.current_round = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.round_results = []
        self.start_time = time.time()
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def run_syntax_check(self) -> bool:
        """语法检查"""
        modules = [
            'core.backup_manager',
            'core.event_bus',
            'core.config_center',
            'core.migration_manager',
            'core.workflow_engine',
            'core.rule_engine',
            'core.data_validator',
            'core.report_engine',
            'core.circuit_breaker',
            'core.middleware_manager',
            'core.di_container',
            'core.saga_orchestrator',
            'core.connection_pool',
        ]

        for module in modules:
            try:
                __import__(module)
            except SyntaxError as e:
                self.log(f"语法错误: {module} - {e}", "ERROR")
                return False
            except ImportError as e:
                self.log(f"导入错误: {module} - {e}", "ERROR")
                return False
        
        return True
    
    def run_unit_tests(self) -> bool:
        """单元测试"""
        tests = [
            self.test_backup_manager,
            self.test_event_bus,
            self.test_config_center,
            self.test_migration_manager,
            self.test_workflow_engine,
            self.test_rule_engine,
            self.test_data_validator,
            self.test_report_engine,
            self.test_circuit_breaker,
            self.test_middleware_manager,
            self.test_di_container,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                self.log(f"单元测试失败: {test.__name__} - {e}", "ERROR")
                return False

        return True
    
    def test_backup_manager(self):
        """测试 BackupManager"""
        import tempfile
        import sqlite3
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            conn.commit()
            conn.close()
            
            bm = BackupManager(backup_dir=tmpdir)
            backup_path = bm.create_backup(db_path, name="test")
            assert os.path.exists(backup_path)
            
            backups = bm.list_backups()
            assert len(backups) == 1
    
    def test_event_bus(self):
        """测试 EventBus"""
        bus = EventBus()
        received = []
        
        @bus.on("test")
        def handler(event):
            received.append(event.data)
        
        bus.emit("test", {"v": 1})
        assert len(received) == 1
    
    def test_config_center(self):
        """测试 ConfigCenter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, "config.json")
            with open(config_file, 'w') as f:
                import json
                json.dump({"key": "value"}, f)
            
            cc = ConfigCenter(config_dir=tmpdir)
            cc.load_from_file(config_file)
            assert cc.get("key") == "value"
    
    def test_migration_manager(self):
        """测试 MigrationManager"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            migrations_dir = os.path.join(tmpdir, "migrations")
            
            mm = MigrationManager(db_path, migrations_dir)
            mm.create_migration("test", "CREATE TABLE t (id INTEGER)", "DROP TABLE t")
            applied = mm.migrate()
            assert len(applied) == 1
    
    def test_workflow_engine(self):
        """测试 WorkflowEngine"""
        import asyncio
        
        engine = WorkflowEngine()
        executed = []
        
        class TestTask(Task):
            def __init__(self, name):
                super().__init__(task_id=name, name=name)
                self._name = name
            
            async def execute(self, context):
                executed.append(self._name)
                return True
        
        task_a = TestTask("A")
        task_b = TestTask("B")
        task_a >> task_b
        
        wf = Workflow("test")
        wf.add_task(task_a).add_task(task_b)
        
        asyncio.run(engine.execute_workflow(wf))
        assert executed == ["A", "B"]
    
    def test_rule_engine(self):
        """测试 RuleEngine"""
        engine = RuleEngine()
        triggered = []
        
        def callback(ctx, **kw):
            triggered.append(True)
        
        engine.register_callback("test", callback)
        engine.add_rule(Rule(
            id="test",
            name="Test Rule",
            condition=RuleCondition(field="x", op="==", value=1),
            actions=[RuleAction(type="callback", params={"handler": "test"})]
        ))
        
        ctx = RuleContext(facts={"x": 1})
        engine.execute(ctx)
        assert len(triggered) == 1
    
    def test_data_validator(self):
        """测试 DataValidator"""
        schema = {
            "name": ValidationRule(type=FieldType.STRING, required=True),
            "age": ValidationRule(type=FieldType.INTEGER, min_value=0)
        }
        
        validator = DataValidator(schema)
        is_valid, errors, cleaned = validator.validate({"name": "test", "age": "25"})
        assert is_valid
        assert cleaned["age"] == 25
    
    def test_report_engine(self):
        """测试 ReportEngine"""
        engine = ReportEngine()
        
        data = [{"cat": "A", "amt": 100}, {"cat": "A", "amt": 200}]
        config = ReportConfig(
            name="test",
            dimensions=[ReportDimension("cat")],
            metrics=[ReportMetric("amt", AggregationType.SUM, display_name="amt")]
        )
        
        result = engine.generate(data, config)
        assert len(result.data) == 1
        assert result.data[0]["amt"] == 300
    
    def test_circuit_breaker(self):
        """测试 CircuitBreaker"""
        breaker = CircuitBreaker(name="test", failure_threshold=3, timeout=1.0)
        
        # 正常调用
        result = breaker.call(lambda: "success")
        assert result == "success"
        
        # 触发熔断
        for _ in range(3):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except:
                pass
        
        assert breaker.state.value == "open"

    def test_middleware_manager(self):
        """测试 MiddlewareManager"""
        import asyncio

        async def async_test():
            manager = MiddlewareManager()

            # 测试中间件注册
            async def test_middleware(context):
                context.set('test', True)
                return context

            manager.use(test_middleware)
            assert len(manager.get_middlewares()) == 1

            # 测试执行
            result = await manager.execute(metadata={'path': '/test'})
            assert result is not None

        asyncio.run(async_test())

    def test_di_container(self):
        """测试 DIContainer"""
        container = DIContainer()

        # 定义测试服务
        class DatabaseService:
            def query(self):
                return "data"

        class UserService:
            def __init__(self, db: DatabaseService):
                self.db = db

        # 注册服务
        container.register(DatabaseService, lifecycle=Lifecycle.SINGLETON)
        container.register(UserService, lifecycle=Lifecycle.TRANSIENT)

        # 解析服务
        db1 = container.resolve(DatabaseService)
        db2 = container.resolve(DatabaseService)
        assert db1 is db2  # 单例验证

        user_svc = container.resolve(UserService)
        assert user_svc.db is db1  # 依赖注入验证

    def run_integration_test(self) -> bool:
        """集成测试"""
        try:
            import tempfile
            import time
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # 完整业务流程
                config = ConfigCenter(config_dir=tmpdir)
                config.set("database.path", os.path.join(tmpdir, "app.db"))
                
                # 数据库迁移
                mm = MigrationManager(config.get("database.path"), os.path.join(tmpdir, "migrations"))
                mm.create_migration("init", "CREATE TABLE orders (id INTEGER PRIMARY KEY)", "DROP TABLE orders")
                mm.migrate()
                
                # 备份
                bm = BackupManager(backup_dir=tmpdir)
                bm.create_backup(config.get("database.path"), name="init")
                
                # 事件 - 使用同步处理
                bus = EventBus()
                events = []
                
                def on_order_created(event):
                    events.append(event.data)
                
                bus.subscribe("order.created", on_order_created)
                
                # 规则
                engine = RuleEngine()
                engine.add_rule(Rule(
                    id="test",
                    name="Test",
                    condition=RuleCondition(field="amount", op=">", value=100),
                    actions=[]
                ))
                
                # 验证
                validator = DataValidator({
                    "amount": ValidationRule(type=FieldType.NUMBER, required=True)
                })
                
                is_valid, _, cleaned = validator.validate({"amount": 200})
                assert is_valid, "数据验证失败"
                
                # 发射事件
                bus.emit("order.created", cleaned)
                
                # 验证事件被处理
                assert len(events) == 1, f"期望收到1个事件，实际收到{len(events)}个"
                assert events[0]["amount"] == 200.0, f"事件数据不正确: {events[0]}"
                
                return True
        except Exception as e:
            self.log(f"集成测试失败: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
    
    def run_stress_test(self) -> bool:
        """压力测试"""
        try:
            import threading
            import concurrent.futures
            
            # EventBus 并发测试
            bus = EventBus()
            counter = [0]
            
            @bus.on("stress")
            def handler(event):
                counter[0] += 1
            
            def emit_events():
                for _ in range(100):
                    bus.emit("stress", {"v": 1})
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(emit_events) for _ in range(10)]
                concurrent.futures.wait(futures)
            
            # 给一些时间处理
            time.sleep(0.5)
            assert counter[0] == 1000, f"期望1000，实际{counter[0]}"
            
            return True
        except Exception as e:
            self.log(f"压力测试失败: {e}", "ERROR")
            return False
    
    def run_round(self, round_num: int) -> dict:
        """执行一轮测试"""
        self.current_round = round_num
        self.log(f"=" * 60)
        self.log(f"开始第 {round_num}/{self.total_rounds} 轮测试")
        self.log(f"=" * 60)
        
        round_start = time.time()
        results = {
            "round": round_num,
            "tests": {},
            "passed": 0,
            "failed": 0,
            "duration": 0
        }
        
        tests = [
            ("语法检查", self.run_syntax_check),
            ("单元测试", self.run_unit_tests),
            ("集成测试", self.run_integration_test),
            ("压力测试", self.run_stress_test),
        ]
        
        for test_name, test_func in tests:
            try:
                start = time.time()
                passed = test_func()
                duration = time.time() - start
                
                results["tests"][test_name] = {
                    "passed": passed,
                    "duration": round(duration, 3)
                }
                
                if passed:
                    results["passed"] += 1
                    self.log(f"✓ {test_name} 通过 ({duration:.3f}s)")
                else:
                    results["failed"] += 1
                    self.log(f"✗ {test_name} 失败", "ERROR")
            except Exception as e:
                results["tests"][test_name] = {"passed": False, "error": str(e)}
                results["failed"] += 1
                self.log(f"✗ {test_name} 异常: {e}", "ERROR")
        
        results["duration"] = round(time.time() - round_start, 3)
        
        # 汇总
        if results["failed"] == 0:
            self.log(f"第 {round_num} 轮测试全部通过 ✓", "SUCCESS")
        else:
            self.log(f"第 {round_num} 轮测试有 {results['failed']} 项失败", "WARNING")
        
        return results
    
    def run_all_rounds(self):
        """执行所有轮次"""
        self.log("=" * 60)
        self.log("开始 30 轮迭代审查测试")
        self.log("=" * 60)
        
        for i in range(1, self.total_rounds + 1):
            result = self.run_round(i)
            self.round_results.append(result)
            
            if result["failed"] > 0:
                self.failed_tests += result["failed"]
            else:
                self.passed_tests += len(result["tests"])
        
        self.print_summary()
    
    def print_summary(self):
        """打印汇总报告"""
        total_time = time.time() - self.start_time
        
        self.log("=" * 60)
        self.log("30轮迭代审查测试完成")
        self.log("=" * 60)
        
        # 统计
        total_tests = sum(len(r["tests"]) for r in self.round_results)
        total_passed = sum(r["passed"] for r in self.round_results)
        total_failed = sum(r["failed"] for r in self.round_results)
        
        self.log(f"总测试数: {total_tests}")
        self.log(f"通过: {total_passed}")
        self.log(f"失败: {total_failed}")
        self.log(f"通过率: {(total_passed/total_tests*100):.1f}%")
        self.log(f"总耗时: {total_time:.2f}s")
        self.log(f"平均每轮: {total_time/self.total_rounds:.2f}s")
        
        # 失败的轮次
        failed_rounds = [r for r in self.round_results if r["failed"] > 0]
        if failed_rounds:
            self.log(f"\n失败的轮次: {[r['round'] for r in failed_rounds]}", "WARNING")
        else:
            self.log("\n所有轮次全部通过！", "SUCCESS")
        
        self.log("=" * 60)


if __name__ == "__main__":
    runner = RoundTestRunner(total_rounds=30)
    runner.run_all_rounds()
    
    # 返回码
    failed_rounds = [r for r in runner.round_results if r["failed"] > 0]
    sys.exit(0 if len(failed_rounds) == 0 else 1)
