#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则引擎 RuleEngine - 业务规则管理系统

设计灵感:
- Drools: 规则定义与工作内存模式
- AWS EventBridge: 事件模式匹配
- JSON Logic: 声明式规则DSL

核心特性:
1. DSL规则定义 - 声明式JSON规则，支持复杂条件组合
2. 热更新机制 - 规则动态加载，无需重启服务
3. 规则优先级 - 支持优先级排序与冲突解决
4. 规则组合 - 规则链与嵌套规则支持
5. 条件评估 - 支持多种操作符与自定义函数
6. 动作执行 - 支持多种动作类型与回调函数

作者: AI Assistant
创建日期: 2026-05-09
版本: 1.0.0
"""

import json
import re
import operator
import asyncio
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union, Set
from dataclasses import dataclass, field as dataclass_field, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OperatorType(Enum):
    """规则操作符类型"""
    # 比较操作符
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    
    # 字符串操作符
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"  # 正则匹配
    
    # 集合操作符
    IN = "in"
    NOT_IN = "not_in"
    
    # 逻辑操作符
    AND = "and"
    OR = "or"
    NOT = "not"
    
    # 存在性操作符
    EXISTS = "exists"
    IS_EMPTY = "is_empty"
    
    # 范围操作符
    BETWEEN = "between"


class ActionType(Enum):
    """规则动作类型"""
    CALLBACK = "callback"           # 执行回调函数
    SET_VALUE = "set_value"         # 设置值
    EMIT_EVENT = "emit_event"       # 触发事件
    LOG = "log"                     # 记录日志
    RETURN = "return"               # 返回结果
    CHAIN = "chain"                 # 链式调用其他规则


@dataclass
class RuleCondition:
    """
    规则条件定义
    
    支持的条件格式:
    - 简单条件: {"field": "age", "op": ">=", "value": 18}
    - 逻辑组合: {"and": [condition1, condition2]}
    - 嵌套字段: {"field": "user.profile.age", "op": "==", "value": 25}
    """
    field: Optional[str] = None
    op: Optional[str] = None
    value: Any = None
    conditions: List['RuleCondition'] = dataclass_field(default_factory=list)
    logic_op: Optional[str] = None  # "and" 或 "or"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleCondition':
        """从字典创建条件对象"""
        if not data:
            return cls()
            
        # 处理逻辑组合条件
        if "and" in data:
            return cls(
                logic_op="and",
                conditions=[cls.from_dict(c) for c in data["and"]]
            )
        if "or" in data:
            return cls(
                logic_op="or",
                conditions=[cls.from_dict(c) for c in data["or"]]
            )
        if "not" in data:
            return cls(
                logic_op="not",
                conditions=[cls.from_dict(data["not"])]
            )
            
        # 处理简单条件
        return cls(
            field=data.get("field"),
            op=data.get("op"),
            value=data.get("value")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        if self.logic_op:
            if self.logic_op == "not":
                return {"not": self.conditions[0].to_dict() if self.conditions else {}}
            return {self.logic_op: [c.to_dict() for c in self.conditions]}
        
        result = {}
        if self.field is not None:
            result["field"] = self.field
        if self.op is not None:
            result["op"] = self.op
        if self.value is not None:
            result["value"] = self.value
        return result


@dataclass
class RuleAction:
    """
    规则动作定义
    
    支持的动作格式:
    - 回调: {"type": "callback", "handler": "function_name", "params": {...}}
    - 设值: {"type": "set_value", "target": "field_name", "value": ...}
    - 事件: {"type": "emit_event", "event": "event_name", "data": {...}}
    """
    type: str
    params: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleAction':
        """从字典创建动作对象"""
        return cls(
            type=data.get("type", "callback"),
            params={k: v for k, v in data.items() if k != "type"}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {"type": self.type}
        result.update(self.params)
        return result


@dataclass
class Rule:
    """
    规则定义
    
    属性:
        id: 规则唯一标识
        name: 规则名称
        description: 规则描述
        priority: 优先级（数字越小优先级越高）
        condition: 规则条件
        actions: 规则动作列表
        enabled: 是否启用
        tags: 规则标签
        metadata: 元数据
        created_at: 创建时间
        updated_at: 更新时间
        version: 规则版本
    """
    id: str
    name: str
    description: str = ""
    priority: int = 100
    condition: RuleCondition = dataclass_field(default_factory=RuleCondition)
    actions: List[RuleAction] = dataclass_field(default_factory=list)
    enabled: bool = True
    tags: List[str] = dataclass_field(default_factory=list)
    metadata: Dict[str, Any] = dataclass_field(default_factory=dict)
    created_at: str = dataclass_field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = dataclass_field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0.0"
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.condition, dict):
            self.condition = RuleCondition.from_dict(self.condition)
        if self.actions and isinstance(self.actions[0], dict):
            self.actions = [RuleAction.from_dict(a) for a in self.actions]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Rule':
        """从字典创建规则对象"""
        rule_data = data.copy()
        if "condition" in rule_data:
            rule_data["condition"] = RuleCondition.from_dict(rule_data["condition"])
        if "actions" in rule_data:
            rule_data["actions"] = [
                RuleAction.from_dict(a) if isinstance(a, dict) else a
                for a in rule_data["actions"]
            ]
        return cls(**{k: v for k, v in rule_data.items() if k in cls.__dataclass_fields__})
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "condition": self.condition.to_dict(),
            "actions": [a.to_dict() for a in self.actions],
            "enabled": self.enabled,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version
        }
    
    def compute_hash(self) -> str:
        """计算规则哈希（用于检测变更）"""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class RuleContext:
    """
    规则执行上下文
    
    管理规则执行过程中的状态和数据，支持:
    - 事实数据存储
    - 中间结果缓存
    - 执行历史记录
    - 变量传递
    """
    
    def __init__(self, facts: Optional[Dict[str, Any]] = None):
        self.facts = facts or {}
        self.results: List[Dict[str, Any]] = []
        self.variables: Dict[str, Any] = {}
        self.execution_log: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.modified_fields: Set[str] = set()
    
    def get_fact(self, path: str, default: Any = None) -> Any:
        """
        获取事实数据，支持嵌套路径
        
        Args:
            path: 字段路径，如 "user.profile.age"
            default: 默认值
            
        Returns:
            字段值或默认值
        """
        keys = path.split(".")
        value = self.facts
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set_fact(self, path: str, value: Any) -> None:
        """
        设置事实数据
        
        Args:
            path: 字段路径
            value: 字段值
        """
        keys = path.split(".")
        target = self.facts
        
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        target[keys[-1]] = value
        self.modified_fields.add(path)
        
        self.execution_log.append({
            "type": "fact_modified",
            "path": path,
            "value": value,
            "timestamp": datetime.now().isoformat()
        })
    
    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)
    
    def add_result(self, rule_id: str, actions_executed: List[str]) -> None:
        """添加执行结果"""
        self.results.append({
            "rule_id": rule_id,
            "actions": actions_executed,
            "timestamp": datetime.now().isoformat()
        })
    
    def log(self, message: str, level: str = "info") -> None:
        """记录执行日志"""
        self.execution_log.append({
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            "duration_seconds": duration,
            "rules_triggered": len(self.results),
            "actions_executed": sum(len(r["actions"]) for r in self.results),
            "facts_modified": len(self.modified_fields),
            "variables_set": len(self.variables)
        }


class RuleEngine:
    """
    规则引擎核心类
    
    功能特性:
    1. 规则管理 - 增删改查规则
    2. 规则评估 - 评估条件并执行动作
    3. 热更新 - 动态加载规则文件
    4. 回调注册 - 注册自定义函数
    5. 规则链 - 支持规则链式调用
    
    使用示例:
        engine = RuleEngine()
        
        # 注册回调
        engine.register_callback("send_email", send_email_func)
        
        # 加载规则
        engine.load_rules_from_file("rules.json")
        
        # 执行规则
        context = RuleContext(facts={"user": {"age": 25}})
        engine.execute(context)
    """
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.callbacks: Dict[str, Callable] = {}
        self.custom_operators: Dict[str, Callable] = {}
        self.rule_files: Dict[str, str] = {}  # path -> hash
        
        # 注册内置操作符
        self._register_builtin_operators()
    
    def _register_builtin_operators(self) -> None:
        """注册内置操作符"""
        self.custom_operators = {
            "==": operator.eq,
            "!=": operator.ne,
            ">": operator.gt,
            "<": operator.lt,
            ">=": operator.ge,
            "<=": operator.le,
            "contains": lambda a, b: b in a if a else False,
            "starts_with": lambda a, b: str(a).startswith(str(b)) if a else False,
            "ends_with": lambda a, b: str(a).endswith(str(b)) if a else False,
            "matches": lambda a, b: bool(re.match(b, str(a))) if a else False,
            "in": lambda a, b: a in b,
            "not_in": lambda a, b: a not in b,
            "exists": lambda a, b: a is not None,
            "is_empty": lambda a, b: not bool(a),
            "between": lambda a, b: b[0] <= a <= b[1] if isinstance(b, (list, tuple)) and len(b) == 2 else False
        }
    
    # ==================== 规则管理 ====================
    
    def add_rule(self, rule: Rule) -> None:
        """
        添加规则
        
        Args:
            rule: 规则对象
        """
        self.rules[rule.id] = rule
        logger.info(f"规则已添加: {rule.id} (优先级: {rule.priority})")
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        删除规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            是否成功删除
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"规则已删除: {rule_id}")
            return True
        return False
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新规则
        
        Args:
            rule_id: 规则ID
            updates: 更新内容
            
        Returns:
            是否成功更新
        """
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        
        for key, value in updates.items():
            if key == "condition" and isinstance(value, dict):
                value = RuleCondition.from_dict(value)
            elif key == "actions" and isinstance(value, list):
                value = [RuleAction.from_dict(a) if isinstance(a, dict) else a for a in value]
            
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.now().isoformat()
        logger.info(f"规则已更新: {rule_id}")
        return True
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """获取规则"""
        return self.rules.get(rule_id)
    
    def get_all_rules(self) -> List[Rule]:
        """获取所有规则"""
        return list(self.rules.values())
    
    def get_enabled_rules(self) -> List[Rule]:
        """获取启用的规则，按优先级排序"""
        enabled = [r for r in self.rules.values() if r.enabled]
        return sorted(enabled, key=lambda r: r.priority)
    
    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False
    
    # ==================== 规则加载 ====================
    
    def load_rules_from_file(self, file_path: str) -> int:
        """
        从文件加载规则
        
        Args:
            file_path: 规则文件路径
            
        Returns:
            加载的规则数量
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"规则文件不存在: {file_path}")
            return 0
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 计算文件哈希用于热更新检测
            content = json.dumps(data, sort_keys=True)
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            # 检查是否有变更
            if file_path in self.rule_files and self.rule_files[file_path] == file_hash:
                logger.debug(f"规则文件未变更: {file_path}")
                return 0
            
            self.rule_files[file_path] = file_hash
            
            # 解析规则
            rules_data = data.get("rules", []) if isinstance(data, dict) else data
            count = 0
            
            for rule_data in rules_data:
                rule = Rule.from_dict(rule_data)
                self.add_rule(rule)
                count += 1
            
            logger.info(f"从 {file_path} 加载了 {count} 条规则")
            return count
            
        except Exception as e:
            logger.error(f"加载规则文件失败: {e}")
            return 0
    
    def load_rules_from_directory(self, directory: str) -> int:
        """
        从目录加载所有规则文件
        
        Args:
            directory: 规则目录路径
            
        Returns:
            加载的规则数量
        """
        path = Path(directory)
        if not path.exists():
            logger.error(f"规则目录不存在: {directory}")
            return 0
        
        count = 0
        for rule_file in path.glob("*.json"):
            count += self.load_rules_from_file(str(rule_file))
        
        return count
    
    def reload_rules(self) -> int:
        """
        重新加载所有规则文件（热更新）
        
        Returns:
            更新的规则数量
        """
        updated = 0
        for file_path in list(self.rule_files.keys()):
            prev_rules = {k: v for k, v in self.rules.items()}
            loaded = self.load_rules_from_file(file_path)
            if loaded > 0:
                updated += loaded
        
        if updated > 0:
            logger.info(f"热更新完成，共更新 {updated} 条规则")
        
        return updated
    
    def save_rules_to_file(self, file_path: str) -> bool:
        """
        保存规则到文件
        
        Args:
            file_path: 保存路径
            
        Returns:
            是否成功保存
        """
        try:
            data = {
                "rules": [r.to_dict() for r in self.rules.values()],
                "exported_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"规则已保存到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存规则失败: {e}")
            return False
    
    # ==================== 回调注册 ====================
    
    def register_callback(self, name: str, callback: Callable) -> None:
        """
        注册回调函数
        
        Args:
            name: 回调名称
            callback: 回调函数
        """
        self.callbacks[name] = callback
        logger.debug(f"回调已注册: {name}")
    
    def register_operator(self, name: str, operator_func: Callable) -> None:
        """
        注册自定义操作符
        
        Args:
            name: 操作符名称
            operator_func: 操作符函数
        """
        self.custom_operators[name] = operator_func
        logger.debug(f"操作符已注册: {name}")
    
    # ==================== 规则评估 ====================
    
    def evaluate_condition(self, condition: RuleCondition, context: RuleContext) -> bool:
        """
        评估条件
        
        Args:
            condition: 条件对象
            context: 执行上下文
            
        Returns:
            条件是否满足
        """
        # 处理逻辑组合
        if condition.logic_op:
            if condition.logic_op == "and":
                return all(
                    self.evaluate_condition(c, context)
                    for c in condition.conditions
                )
            elif condition.logic_op == "or":
                return any(
                    self.evaluate_condition(c, context)
                    for c in condition.conditions
                )
            elif condition.logic_op == "not":
                return not self.evaluate_condition(condition.conditions[0], context)
        
        # 处理简单条件
        if not condition.field or not condition.op:
            return True
        
        # 获取字段值
        field_value = context.get_fact(condition.field)
        
        # 获取操作符函数
        op_func = self.custom_operators.get(condition.op)
        if not op_func:
            logger.warning(f"未知操作符: {condition.op}")
            return False
        
        try:
            return op_func(field_value, condition.value)
        except Exception as e:
            logger.error(f"条件评估失败: {e}")
            return False
    
    def execute_action(self, action: RuleAction, context: RuleContext, rule: Rule) -> Any:
        """
        执行动作
        
        Args:
            action: 动作对象
            context: 执行上下文
            rule: 所属规则
            
        Returns:
            动作执行结果
        """
        action_type = action.type
        params = action.params
        
        try:
            if action_type == ActionType.CALLBACK.value:
                handler_name = params.get("handler")
                if handler_name and handler_name in self.callbacks:
                    callback = self.callbacks[handler_name]
                    callback_params = params.get("params", {})
                    # 支持变量替换
                    callback_params = self._resolve_params(callback_params, context)
                    return callback(context, **callback_params)
                else:
                    logger.warning(f"回调未找到: {handler_name}")
                    
            elif action_type == ActionType.SET_VALUE.value:
                target = params.get("target")
                value = params.get("value")
                if target:
                    context.set_fact(target, value)
                    return value
                    
            elif action_type == ActionType.EMIT_EVENT.value:
                event_name = params.get("event")
                event_data = params.get("data", {})
                context.log(f"事件触发: {event_name}")
                return {"event": event_name, "data": event_data}
                
            elif action_type == ActionType.LOG.value:
                level = params.get("level", "info")
                message = params.get("message", "")
                context.log(message, level)
                logger.log(getattr(logging, level.upper(), logging.INFO), message)
                
            elif action_type == ActionType.RETURN.value:
                return params.get("value")
                
            elif action_type == ActionType.CHAIN.value:
                rule_id = params.get("rule_id")
                if rule_id and rule_id in self.rules:
                    chained_rule = self.rules[rule_id]
                    return self._execute_rule(chained_rule, context)
                    
        except Exception as e:
            logger.error(f"动作执行失败: {e}")
            raise
    
    def _resolve_params(self, params: Dict[str, Any], context: RuleContext) -> Dict[str, Any]:
        """解析参数中的变量引用"""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                # 变量引用: $fact.path 或 $var.name
                ref = value[1:]
                if "." in ref:
                    resolved[key] = context.get_fact(ref)
                else:
                    resolved[key] = context.get_variable(ref)
            else:
                resolved[key] = value
        return resolved
    
    def _execute_rule(self, rule: Rule, context: RuleContext) -> bool:
        """
        执行单条规则

        Args:
            rule: 规则对象
            context: 执行上下文

        Returns:
            是否触发规则
        """
        if not rule.enabled:
            return False

        # 检测递归循环
        active_rules = context.get_variable("_active_rules", set())
        if rule.id in active_rules:
            logger.warning(f"检测到规则链循环: {rule.id}")
            return False
        active_rules = active_rules | {rule.id}
        context.set_variable("_active_rules", active_rules)

        try:
            # 评估条件
            if not self.evaluate_condition(rule.condition, context):
                return False

            context.log(f"规则触发: {rule.name} (ID: {rule.id})")

            # 执行动作
            executed_actions = []
            for action in rule.actions:
                try:
                    self.execute_action(action, context, rule)
                    executed_actions.append(action.type)
                except Exception as e:
                    context.log(f"动作执行失败: {action.type} - {e}", "error")
                    raise

            context.add_result(rule.id, executed_actions)
            return True
        finally:
            context.set_variable("_active_rules", active_rules - {rule.id})
    
    def execute(self, context: RuleContext, stop_on_first: bool = False) -> RuleContext:
        """
        执行所有匹配的规则
        
        Args:
            context: 执行上下文
            stop_on_first: 是否在第一条规则触发后停止
            
        Returns:
            执行后的上下文
        """
        rules = self.get_enabled_rules()
        
        for rule in rules:
            try:
                triggered = self._execute_rule(rule, context)
                if triggered and stop_on_first:
                    break
            except Exception as e:
                context.log(f"规则执行异常: {rule.id} - {e}", "error")
                logger.error(f"规则执行异常: {rule.id} - {e}")
        
        return context
    
    async def execute_async(self, context: RuleContext) -> RuleContext:
        """异步执行规则"""
        # 目前同步执行，可扩展为真正的异步
        return self.execute(context)
    
    # ==================== 规则验证 ====================
    
    def validate_rule(self, rule_data: Dict[str, Any]) -> List[str]:
        """
        验证规则定义
        
        Args:
            rule_data: 规则数据
            
        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []
        
        # 检查必填字段
        if "id" not in rule_data:
            errors.append("缺少规则ID")
        if "name" not in rule_data:
            errors.append("缺少规则名称")
        if "condition" not in rule_data:
            errors.append("缺少规则条件")
        if "actions" not in rule_data:
            errors.append("缺少规则动作")
        
        # 检查条件格式
        if "condition" in rule_data:
            condition = rule_data["condition"]
            if not isinstance(condition, dict):
                errors.append("条件必须是对象")
        
        # 检查动作格式
        if "actions" in rule_data:
            actions = rule_data["actions"]
            if not isinstance(actions, list):
                errors.append("动作必须是数组")
            for i, action in enumerate(actions):
                if not isinstance(action, dict):
                    errors.append(f"动作[{i}]必须是对象")
                elif "type" not in action:
                    errors.append(f"动作[{i}]缺少类型")
        
        return errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取规则统计信息"""
        total = len(self.rules)
        enabled = sum(1 for r in self.rules.values() if r.enabled)
        
        # 按标签统计
        tag_counts = {}
        for rule in self.rules.values():
            for tag in rule.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "total_rules": total,
            "enabled_rules": enabled,
            "disabled_rules": total - enabled,
            "tag_distribution": tag_counts,
            "registered_callbacks": len(self.callbacks),
            "registered_operators": len(self.custom_operators),
            "rule_files": len(self.rule_files)
        }


# ==================== 便捷函数 ====================

def create_simple_rule(
    rule_id: str,
    name: str,
    field: str,
    op: str,
    value: Any,
    action_type: str = "log",
    action_params: Optional[Dict] = None,
    priority: int = 100
) -> Rule:
    """
    创建简单规则
    
    Args:
        rule_id: 规则ID
        name: 规则名称
        field: 字段名
        op: 操作符
        value: 比较值
        action_type: 动作类型
        action_params: 动作参数
        priority: 优先级
        
    Returns:
        规则对象
    """
    return Rule(
        id=rule_id,
        name=name,
        priority=priority,
        condition=RuleCondition(field=field, op=op, value=value),
        actions=[RuleAction(type=action_type, params=action_params or {})]
    )


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建规则引擎
    engine = RuleEngine()
    
    # 注册回调函数
    def notify_admin(context: RuleContext, message: str):
        print(f"[通知] {message}")
        return {"notified": True}
    
    engine.register_callback("notify_admin", notify_admin)
    
    # 创建规则
    rule = Rule(
        id="high_value_order",
        name="高价值订单检测",
        description="检测订单金额超过1000的订单",
        priority=10,
        condition=RuleCondition(
            field="order.amount",
            op=">=",
            value=1000
        ),
        actions=[
            RuleAction(type="callback", params={
                "handler": "notify_admin",
                "params": {"message": "检测到高价值订单"}
            }),
            RuleAction(type="log", params={
                "level": "info",
                "message": "高价值订单已处理"
            })
        ],
        tags=["order", "high_value"]
    )
    
    engine.add_rule(rule)
    
    # 执行规则
    facts = {
        "order": {
            "id": "ORD-001",
            "amount": 1500,
            "customer": "张三"
        }
    }
    
    context = RuleContext(facts=facts)
    engine.execute(context)
    
    print("\n执行结果:")
    print(json.dumps(context.get_execution_summary(), indent=2))
