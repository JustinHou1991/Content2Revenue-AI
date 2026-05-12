#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
十轮全面审查测试

覆盖范围：
1. 语法检查 - 所有模块无语法错误
2. 核心模块单元测试 - 14个core模块
3. 服务层测试 - 关键服务模块
4. 新增模块测试 - 竞品分析后新增/优化的模块
5. 集成测试 - 完整业务流程
6. 并发压力测试 - 多线程安全性
7. 代码质量检查 - 导入完整性

作者: AI Assistant
创建日期: 2026-05-10
"""

import sys
import os
import time
import tempfile
import threading
import random
import asyncio
import sqlite3
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
from core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from core.middleware_manager import MiddlewareManager, MiddlewareContext
from core.di_container import DIContainer, Lifecycle
from core.saga_orchestrator import SagaOrchestrator, SagaDefinition, SagaContext
from core.connection_pool import ConnectionPool, PoolConfig, DatabaseConnectionFactory
from core.plugin_system import PluginManager, PluginInterface


class ComprehensiveTestRunner:
    """全面审查测试运行器"""

    def __init__(self, total_rounds: int = 10):
        self.total_rounds = total_rounds
        self.current_round = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.round_results = []
        self.start_time = time.time()

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    # ==================== 1. 语法检查 ====================

    def run_syntax_check(self) -> bool:
        """语法检查 - 所有模块"""
        modules = [
            'core.backup_manager', 'core.event_bus', 'core.config_center',
            'core.migration_manager', 'core.workflow_engine', 'core.rule_engine',
            'core.data_validator', 'core.report_engine', 'core.circuit_breaker',
            'core.middleware_manager', 'core.di_container', 'core.saga_orchestrator',
            'core.connection_pool', 'core.plugin_system',
            'services.content_attribution',
        ]
        for module in modules:
            try:
                __import__(module)
            except Exception as e:
                self.log(f"语法/导入错误: {module} - {e}", "ERROR")
                return False
        return True

    # ==================== 2. 核心模块单元测试 ====================

    def run_core_unit_tests(self) -> bool:
        """核心模块单元测试"""
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
            self.test_plugin_system,
        ]
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log(f"核心模块测试失败: {test.__name__} - {e}", "ERROR")
                return False
        return True

    def test_backup_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            conn.commit()
            conn.close()
            bm = BackupManager(backup_dir=tmpdir)
            backup_path = bm.create_backup(db_path, name="test")
            assert os.path.exists(backup_path)
            assert len(bm.list_backups()) == 1

    def test_event_bus(self):
        bus = EventBus()
        received = []
        bus.subscribe("test", lambda e: received.append(e.data))
        bus.emit("test", {"v": 1})
        assert len(received) == 1

    def test_config_center(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, "config.json")
            import json
            with open(config_file, 'w') as f:
                json.dump({"key": "value"}, f)
            cc = ConfigCenter(config_dir=tmpdir)
            cc.load_from_file(config_file)
            assert cc.get("key") == "value"

    def test_migration_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            migrations_dir = os.path.join(tmpdir, "migrations")
            mm = MigrationManager(db_path, migrations_dir)
            mm.create_migration("test", "CREATE TABLE t (id INTEGER)", "DROP TABLE t")
            applied = mm.migrate()
            assert len(applied) == 1

    def test_workflow_engine(self):
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
        engine = RuleEngine()
        triggered = []
        engine.register_callback("test", lambda ctx, **kw: triggered.append(True))
        engine.add_rule(Rule(
            id="test", name="Test",
            condition=RuleCondition(field="x", op="==", value=1),
            actions=[RuleAction(type="callback", params={"handler": "test"})]
        ))
        ctx = RuleContext(facts={"x": 1})
        engine.execute(ctx)
        assert len(triggered) == 1

    def test_data_validator(self):
        schema = {
            "name": ValidationRule(type=FieldType.STRING, required=True),
            "age": ValidationRule(type=FieldType.INTEGER, min_value=0)
        }
        validator = DataValidator(schema)
        is_valid, errors, cleaned = validator.validate({"name": "test", "age": "25"})
        assert is_valid
        assert cleaned["age"] == 25

    def test_report_engine(self):
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
        breaker = CircuitBreaker(name="test", failure_threshold=3, timeout=1.0)
        result = breaker.call(lambda: "success")
        assert result == "success"
        for _ in range(3):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except:
                pass
        assert breaker.state.value == "open"

    def test_middleware_manager(self):
        async def async_test():
            manager = MiddlewareManager()
            async def test_mw(ctx):
                ctx.set('test', True)
                return ctx
            manager.use(test_mw)
            assert len(manager.get_middlewares()) == 1
            result = await manager.execute(metadata={'path': '/test'})
            assert result is not None
        asyncio.run(async_test())

    def test_di_container(self):
        container = DIContainer()
        class DBService:
            def query(self): return "data"
        class UserService:
            def __init__(self, db: DBService):
                self.db = db
        container.register(DBService, lifecycle=Lifecycle.SINGLETON)
        container.register(UserService, lifecycle=Lifecycle.TRANSIENT)
        db1 = container.resolve(DBService)
        db2 = container.resolve(DBService)
        assert db1 is db2
        user_svc = container.resolve(UserService)
        assert user_svc.db is db1

    def test_plugin_system(self):
        pm = PluginManager()
        # PluginManager 使用 load_plugin 方法而非 register
        assert hasattr(pm, 'load_plugin')
        assert hasattr(pm, 'initialize_all')
        assert len(pm._plugins) == 0

    # ==================== 3. 新增/优化模块测试 ====================

    def run_new_module_tests(self) -> bool:
        """新增模块测试"""
        tests = [
            self.test_content_attribution,
            self.test_unified_cache,
            self.test_ab_test_engine,
            self.test_scoring_model_feedback,
        ]
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log(f"新增模块测试失败: {test.__name__} - {e}", "ERROR")
                import traceback
                self.log(traceback.format_exc(), "ERROR")
                return False
        return True

    def test_content_attribution(self):
        """测试内容归因模块"""
        from services.content_attribution import (
            AttributionEngine, AttributionModel, Touchpoint, TouchpointType, CustomerJourney
        )
        engine = AttributionEngine()

        # 创建客户旅程
        journey = CustomerJourney(customer_id="c1", converted=True, conversion_value=10000)

        journey.add_touchpoint(Touchpoint(
            touchpoint_type=TouchpointType.CONTENT_VIEW, channel="抖音", content_title="视频A",
            timestamp=datetime(2026, 1, 1, 10, 0)
        ))
        journey.add_touchpoint(Touchpoint(
            touchpoint_type=TouchpointType.LEAD_CONVERSION, channel="微信", content_title="表单",
            timestamp=datetime(2026, 1, 5, 14, 0)
        ))
        journey.add_touchpoint(Touchpoint(
            touchpoint_type=TouchpointType.CONTENT_VIEW, channel="抖音", content_title="视频B",
            timestamp=datetime(2026, 1, 3, 9, 0)
        ))

        # 添加旅程到引擎
        engine.add_journey(journey)

        # 测试首次触点归因
        report = engine.analyze(model=AttributionModel.FIRST_TOUCH)
        assert report is not None
        assert len(report.channel_scores) > 0

        # 测试最后触点归因
        report_last = engine.analyze(model=AttributionModel.LAST_TOUCH)
        assert report_last is not None

        # 测试线性归因
        report_linear = engine.analyze(model=AttributionModel.LINEAR)
        assert report_linear is not None

        # 测试模型对比
        comparison = engine.compare_models()
        assert isinstance(comparison, dict)
        assert "model_reports" in comparison

    def test_unified_cache(self):
        """测试统一缓存"""
        from utils.cache import UnifiedCache
        cache = UnifiedCache(max_size=100, default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.exists("key1")
        cache.delete("key1")
        assert not cache.exists("key1")
        # 批量设置（逐个set）
        for k, v in {"a": 1, "b": 2, "c": 3}.items():
            cache.set(k, v)
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        # 统计
        stats = cache.get_stats()
        assert stats["hits"] >= 0
        assert "hit_rate" in stats

    def test_ab_test_engine(self):
        """测试AB测试引擎"""
        from services.ab_test_engine import ABTestEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            from services.database import Database
            db = Database(db_path)
            engine = ABTestEngine(db)
            # 测试样本量计算
            result = engine.calculate_sample_size(
                baseline_conversion=0.05, minimum_detectable_effect=0.02
            )
            assert result is not None
            assert "sample_size_per_variant" in result
            assert result["sample_size_per_variant"] > 0
            # 测试统计显著性
            sig = engine.calculate_statistical_significance(
                variant_a_conversions=50, variant_a_visitors=1000,
                variant_b_conversions=70, variant_b_visitors=1000
            )
            assert sig is not None
            assert "is_significant" in sig

    def test_scoring_model_feedback(self):
        """测试评分模型反馈学习"""
        from services.scoring_model import ContentScoringModel, ContentFeatures
        model = ContentScoringModel()
        # 使用正确的 ContentFeatures 对象
        features = ContentFeatures(
            hook_type="question", cta_type="direct",
            content_length=500, emotion_tone="positive", structure_type="problem_solution"
        )
        scores = model.score_content(features)
        assert scores is not None
        assert hasattr(scores, 'overall_score')
        # 测试反馈学习
        history = model.get_adjustment_history()
        assert isinstance(history, list)
        # 测试重置
        model.reset_scores_to_defaults()
        history_after = model.get_adjustment_history()
        assert len(history_after) == 0

    # ==================== 4. 集成测试 ====================

    def run_integration_test(self) -> bool:
        """集成测试 - 完整业务流程"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 配置中心
                config = ConfigCenter(config_dir=tmpdir)
                config.set("database.path", os.path.join(tmpdir, "app.db"))

                # 数据库迁移
                mm = MigrationManager(config.get("database.path"), os.path.join(tmpdir, "migrations"))
                mm.create_migration("init", "CREATE TABLE orders (id INTEGER PRIMARY KEY)", "DROP TABLE orders")
                mm.migrate()

                # 备份
                bm = BackupManager(backup_dir=tmpdir)
                bm.create_backup(config.get("database.path"), name="init")

                # 事件
                bus = EventBus()
                events = []
                bus.subscribe("order.created", lambda e: events.append(e.data))

                # 规则引擎
                engine = RuleEngine()
                engine.add_rule(Rule(
                    id="test", name="Test",
                    condition=RuleCondition(field="amount", op=">", value=100),
                    actions=[]
                ))

                # 数据验证
                validator = DataValidator({
                    "amount": ValidationRule(type=FieldType.NUMBER, required=True)
                })
                is_valid, _, cleaned = validator.validate({"amount": 200})
                assert is_valid, "数据验证失败"

                bus.emit("order.created", cleaned)
                assert len(events) == 1, f"期望1个事件，实际{len(events)}个"

                # DI容器集成
                container = DIContainer()
                container.register_instance(ConfigCenter, config)
                resolved_config = container.resolve(ConfigCenter)
                assert resolved_config is config

                return True
        except Exception as e:
            self.log(f"集成测试失败: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False

    # ==================== 5. 并发压力测试 ====================

    def run_stress_test(self) -> bool:
        """并发压力测试"""
        try:
            import concurrent.futures

            # EventBus 并发
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
            time.sleep(0.5)
            assert counter[0] == 1000, f"EventBus: 期望1000，实际{counter[0]}"

            # DI容器并发
            container = DIContainer()
            class Svc:
                pass
            container.register(Svc, lifecycle=Lifecycle.SINGLETON)
            instances = []
            def resolve_svc():
                instances.append(container.resolve(Svc))
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(resolve_svc) for _ in range(100)]
                concurrent.futures.wait(futures)
            assert all(i is instances[0] for i in instances), "DI单例并发失败"

            # 熔断器并发
            breaker = CircuitBreaker(name="stress_test", failure_threshold=100)
            results = []
            def call_breaker(success):
                if success:
                    return breaker.call(lambda: "ok")
                else:
                    try:
                        breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
                    except:
                        return "error"
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(200):
                    futures.append(executor.submit(call_breaker, i < 150))
                concurrent.futures.wait(futures)
                results = [f.result() for f in futures]

            return True
        except Exception as e:
            self.log(f"压力测试失败: {e}", "ERROR")
            return False

    # ==================== 6. 代码质量检查 ====================

    def run_quality_check(self) -> bool:
        """代码质量检查"""
        try:
            # 检查所有core模块可导入
            core_dir = os.path.join(os.path.dirname(__file__), '..', 'core')
            py_files = [f[:-3] for f in os.listdir(core_dir) if f.endswith('.py') and f != '__init__.py']
            for module_name in py_files:
                __import__(f"core.{module_name}")

            # 检查services关键模块（跳过需要httpx的模块）
            service_modules = ['services.database', 'services.base_analyzer',
                               'services.content_attribution', 'services.ab_test_engine',
                               'services.scoring_model']
            for module in service_modules:
                try:
                    __import__(module)
                except ImportError as e:
                    # 跳过缺少第三方依赖的模块
                    if 'httpx' in str(e).lower() or 'openai' in str(e).lower():
                        continue
                    raise

            # 检查utils模块
            util_modules = ['utils.cache', 'utils.cache_manager', 'utils.logger']
            for module in util_modules:
                __import__(module)

            return True
        except Exception as e:
            self.log(f"代码质量检查失败: {e}", "ERROR")
            return False

    # ==================== 执行轮次 ====================

    def run_round(self, round_num: int) -> dict:
        self.current_round = round_num
        self.log(f"{'=' * 60}")
        self.log(f"开始第 {round_num}/{self.total_rounds} 轮全面审查测试")
        self.log(f"{'=' * 60}")

        round_start = time.time()
        results = {"round": round_num, "tests": {}, "passed": 0, "failed": 0, "duration": 0}

        tests = [
            ("语法检查", self.run_syntax_check),
            ("核心模块测试", self.run_core_unit_tests),
            ("新增模块测试", self.run_new_module_tests),
            ("集成测试", self.run_integration_test),
            ("并发压力测试", self.run_stress_test),
            ("代码质量检查", self.run_quality_check),
        ]

        for test_name, test_func in tests:
            try:
                start = time.time()
                passed = test_func()
                duration = time.time() - start
                results["tests"][test_name] = {"passed": passed, "duration": round(duration, 3)}
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

        if results["failed"] == 0:
            self.log(f"第 {round_num} 轮全部通过 ✓", "SUCCESS")
        else:
            self.log(f"第 {round_num} 轮: {results['passed']}通过, {results['failed']}失败", "WARNING")

        self.round_results.append(results)
        return results

    def run_all(self) -> dict:
        """执行所有轮次"""
        self.log(f"{'=' * 60}")
        self.log(f"开始 {self.total_rounds} 轮全面审查测试")
        self.log(f"{'=' * 60}")

        for i in range(1, self.total_rounds + 1):
            self.run_round(i)
            print()

        # 汇总
        total_passed = sum(r["passed"] for r in self.round_results)
        total_failed = sum(r["failed"] for r in self.round_results)
        total_tests = total_passed + total_failed
        total_time = time.time() - self.start_time

        self.log(f"{'=' * 60}")
        self.log(f"{self.total_rounds} 轮全面审查测试完成")
        self.log(f"{'=' * 60}")
        self.log(f"总测试数: {total_tests}")
        self.log(f"通过: {total_passed}")
        self.log(f"失败: {total_failed}")
        self.log(f"通过率: {total_passed / total_tests * 100:.1f}%")
        self.log(f"总耗时: {total_time:.2f}s")
        self.log(f"平均每轮: {total_time / self.total_rounds:.2f}s")

        if total_failed == 0:
            self.log("所有轮次全部通过！", "SUCCESS")
        else:
            self.log(f"存在 {total_failed} 项失败", "ERROR")

        return {
            "total_rounds": self.total_rounds,
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": total_passed / total_tests * 100 if total_tests > 0 else 0,
            "total_time": round(total_time, 2),
            "rounds": self.round_results
        }


if __name__ == "__main__":
    runner = ComprehensiveTestRunner(total_rounds=10)
    result = runner.run_all()
