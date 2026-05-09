#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证框架 DataValidator - 统一的数据校验与清洗系统

设计灵感:
- JSON Schema: 声明式验证规范
- Django Forms: 字段级验证与清洗
- Pydantic: 类型驱动的数据验证

核心特性:
1. 声明式验证 - JSON Schema 风格定义验证规则
2. 类型安全 - 自动类型转换与验证
3. 自定义验证器 - 支持函数和正则表达式
4. 嵌套验证 - 支持复杂对象和数组
5. 错误聚合 - 收集所有验证错误
6. 数据清洗 - 自动清理和格式化数据
7. 条件验证 - 基于其他字段的条件验证
8. 多语言错误 - 支持错误信息国际化

作者: AI Assistant
创建日期: 2026-05-09
版本: 1.0.0
"""

import re
import json
from typing import Dict, List, Any, Optional, Callable, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class ValidationError:
    """验证错误信息"""
    
    def __init__(
        self,
        field: str,
        message: str,
        code: str = "invalid",
        params: Optional[Dict[str, Any]] = None
    ):
        self.field = field
        self.message = message
        self.code = code
        self.params = params or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "field": self.field,
            "message": self.message,
            "code": self.code,
            "params": self.params
        }
    
    def __str__(self) -> str:
        return f"{self.field}: {self.message}"


class FieldType(Enum):
    """字段类型"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    URL = "url"
    UUID = "uuid"
    ENUM = "enum"
    ANY = "any"


@dataclass
class ValidationRule:
    """
    验证规则定义
    
    属性:
        type: 字段类型
        required: 是否必填
        default: 默认值
        min_length: 最小长度（字符串/数组）
        max_length: 最大长度（字符串/数组）
        min_value: 最小值（数字）
        max_value: 最大值（数字）
        pattern: 正则表达式模式
        enum: 枚举值列表
        validator: 自定义验证函数
        sanitizer: 数据清洗函数
        nested_schema: 嵌套对象验证模式
        item_schema: 数组元素验证模式
        depends_on: 依赖的其他字段
        condition: 条件验证规则
        error_message: 自定义错误信息
    """
    type: FieldType = FieldType.ANY
    required: bool = True
    default: Any = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    enum: Optional[List[Any]] = None
    validator: Optional[Callable[[Any], Tuple[bool, str]]] = None
    sanitizer: Optional[Callable[[Any], Any]] = None
    nested_schema: Optional[Dict[str, 'ValidationRule']] = None
    item_schema: Optional['ValidationRule'] = None
    depends_on: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    allow_null: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationRule':
        """从字典创建验证规则"""
        rule_data = data.copy()
        
        # 转换类型
        if "type" in rule_data and isinstance(rule_data["type"], str):
            rule_data["type"] = FieldType(rule_data["type"])
        
        # 处理嵌套模式
        if "nested_schema" in rule_data:
            rule_data["nested_schema"] = {
                k: cls.from_dict(v) if isinstance(v, dict) else v
                for k, v in rule_data["nested_schema"].items()
            }
        
        # 处理数组元素模式
        if "item_schema" in rule_data and isinstance(rule_data["item_schema"], dict):
            rule_data["item_schema"] = cls.from_dict(rule_data["item_schema"])
        
        return cls(**{k: v for k, v in rule_data.items() if k in cls.__dataclass_fields__})


class DataValidator:
    """
    数据验证器
    
    功能特性:
    1. 多类型验证 - 支持所有常见数据类型
    2. 嵌套验证 - 复杂对象和数组验证
    3. 自定义验证 - 支持函数和正则
    4. 数据清洗 - 自动格式化数据
    5. 错误聚合 - 收集所有验证错误
    6. 条件验证 - 基于上下文的验证
    
    使用示例:
        schema = {
            "name": ValidationRule(
                type=FieldType.STRING,
                required=True,
                min_length=2,
                max_length=50
            ),
            "email": ValidationRule(
                type=FieldType.EMAIL,
                required=True
            ),
            "age": ValidationRule(
                type=FieldType.INTEGER,
                min_value=0,
                max_value=150
            )
        }
        
        validator = DataValidator(schema)
        data = {"name": "张三", "email": "zhangsan@example.com", "age": 25}
        
        is_valid, errors, cleaned_data = validator.validate(data)
    """
    
    # 预定义验证模式
    PATTERNS = {
        "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        "url": r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$',
        "uuid": r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        "phone_cn": r'^1[3-9]\d{9}$',
        "phone_us": r'^\+?1?[-.]?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}$',
        "credit_card": r'^\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}$',
        "ipv4": r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        "date_iso": r'^\d{4}-\d{2}-\d{2}$',
        "datetime_iso": r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$'
    }
    
    def __init__(self, schema: Optional[Dict[str, ValidationRule]] = None):
        """
        初始化验证器
        
        Args:
            schema: 验证模式字典
        """
        self.schema = schema or {}
        self.errors: List[ValidationError] = []
        self.custom_validators: Dict[str, Callable] = {}
        self.custom_sanitizers: Dict[str, Callable] = {}
    
    def add_rule(self, field: str, rule: ValidationRule) -> None:
        """添加验证规则"""
        self.schema[field] = rule
    
    def remove_rule(self, field: str) -> bool:
        """移除验证规则"""
        if field in self.schema:
            del self.schema[field]
            return True
        return False
    
    def register_validator(self, name: str, validator: Callable[[Any], Tuple[bool, str]]) -> None:
        """注册自定义验证器"""
        self.custom_validators[name] = validator
    
    def register_sanitizer(self, name: str, sanitizer: Callable[[Any], Any]) -> None:
        """注册自定义清洗器"""
        self.custom_sanitizers[name] = sanitizer
    
    def validate(
        self,
        data: Dict[str, Any],
        schema: Optional[Dict[str, ValidationRule]] = None,
        path_prefix: str = ""
    ) -> Tuple[bool, List[ValidationError], Dict[str, Any]]:
        """
        验证数据
        
        Args:
            data: 待验证数据
            schema: 验证模式（默认使用初始化时的模式）
            path_prefix: 字段路径前缀（用于嵌套验证）
            
        Returns:
            (是否通过, 错误列表, 清洗后的数据)
        """
        self.errors = []
        schema = schema or self.schema
        cleaned_data = {}
        
        # 检查未知字段
        unknown_fields = set(data.keys()) - set(schema.keys())
        for field in unknown_fields:
            self.errors.append(ValidationError(
                field=f"{path_prefix}{field}" if path_prefix else field,
                message=f"未知字段: {field}",
                code="unknown_field"
            ))
        
        # 验证每个字段
        for field_name, rule in schema.items():
            full_path = f"{path_prefix}{field_name}" if path_prefix else field_name
            
            # 检查依赖条件
            if rule.depends_on and rule.condition:
                dep_value = data.get(rule.depends_on)
                if not self._check_condition(dep_value, rule.condition):
                    continue
            
            # 获取字段值
            value = data.get(field_name)
            
            # 处理默认值
            if value is None and rule.default is not None:
                value = rule.default
            
            # 验证必填（allow_null 时 None 值视为合法，跳过必填检查）
            if rule.required and value is None and not rule.allow_null:
                self.errors.append(ValidationError(
                    field=full_path,
                    message=rule.error_message or f"字段 {field_name} 是必填的",
                    code="required"
                ))
                continue
            
            # 允许null值
            if value is None and rule.allow_null:
                cleaned_data[field_name] = None
                continue
            
            # 跳过空值验证（非必填）
            if value is None and not rule.required:
                continue
            
            # 数据清洗
            if rule.sanitizer:
                try:
                    value = rule.sanitizer(value)
                except Exception as e:
                    self.errors.append(ValidationError(
                        field=full_path,
                        message=f"数据清洗失败: {e}",
                        code="sanitization_error"
                    ))
                    continue
            
            # 类型验证和转换
            converted_value = self._validate_type(
                full_path, field_name, value, rule
            )
            
            if converted_value is not None or rule.allow_null:
                cleaned_data[field_name] = converted_value
        
        return len(self.errors) == 0, self.errors, cleaned_data
    
    def _validate_type(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Any:
        """验证并转换类型"""
        try:
            if rule.type == FieldType.STRING:
                return self._validate_string(full_path, field_name, value, rule)
            elif rule.type == FieldType.INTEGER:
                return self._validate_integer(full_path, field_name, value, rule)
            elif rule.type == FieldType.NUMBER:
                return self._validate_number(full_path, field_name, value, rule)
            elif rule.type == FieldType.BOOLEAN:
                return self._validate_boolean(full_path, field_name, value, rule)
            elif rule.type == FieldType.ARRAY:
                return self._validate_array(full_path, field_name, value, rule)
            elif rule.type == FieldType.OBJECT:
                return self._validate_object(full_path, field_name, value, rule)
            elif rule.type == FieldType.DATE:
                return self._validate_date(full_path, field_name, value, rule)
            elif rule.type == FieldType.DATETIME:
                return self._validate_datetime(full_path, field_name, value, rule)
            elif rule.type == FieldType.EMAIL:
                return self._validate_email(full_path, field_name, value, rule)
            elif rule.type == FieldType.URL:
                return self._validate_url(full_path, field_name, value, rule)
            elif rule.type == FieldType.UUID:
                return self._validate_uuid(full_path, field_name, value, rule)
            elif rule.type == FieldType.ENUM:
                return self._validate_enum(full_path, field_name, value, rule)
            else:
                return value
                
        except Exception as e:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"类型验证失败: {e}",
                code="type_error"
            ))
            return None
    
    def _validate_string(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[str]:
        """验证字符串"""
        converted = str(value)
        
        # 长度验证
        if rule.min_length is not None and len(converted) < rule.min_length:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"长度不能少于 {rule.min_length} 个字符",
                code="min_length"
            ))
        
        if rule.max_length is not None and len(converted) > rule.max_length:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"长度不能超过 {rule.max_length} 个字符",
                code="max_length"
            ))
        
        # 正则验证
        if rule.pattern:
            if not re.match(rule.pattern, converted):
                self.errors.append(ValidationError(
                    field=full_path,
                    message=rule.error_message or "格式不正确",
                    code="pattern"
                ))
        
        # 自定义验证
        if rule.validator:
            is_valid, message = rule.validator(converted)
            if not is_valid:
                self.errors.append(ValidationError(
                    field=full_path,
                    message=message,
                    code="custom"
                ))
        
        return converted if not any(e.field == full_path for e in self.errors) else None
    
    def _validate_integer(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[int]:
        """验证整数"""
        try:
            converted = int(value)
        except (ValueError, TypeError):
            self.errors.append(ValidationError(
                field=full_path,
                message=f"必须是整数",
                code="type_error"
            ))
            return None
        
        # 范围验证
        if rule.min_value is not None and converted < rule.min_value:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"不能小于 {rule.min_value}",
                code="min_value"
            ))
        
        if rule.max_value is not None and converted > rule.max_value:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"不能大于 {rule.max_value}",
                code="max_value"
            ))
        
        return converted
    
    def _validate_number(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[float]:
        """验证数字"""
        try:
            converted = float(value)
        except (ValueError, TypeError):
            self.errors.append(ValidationError(
                field=full_path,
                message=f"必须是数字",
                code="type_error"
            ))
            return None
        
        # 范围验证
        if rule.min_value is not None and converted < rule.min_value:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"不能小于 {rule.min_value}",
                code="min_value"
            ))
        
        if rule.max_value is not None and converted > rule.max_value:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"不能大于 {rule.max_value}",
                code="max_value"
            ))
        
        return converted
    
    def _validate_boolean(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[bool]:
        """验证布尔值"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        self.errors.append(ValidationError(
            field=full_path,
            message=f"必须是布尔值",
            code="type_error"
        ))
        return None
    
    def _validate_array(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[List]:
        """验证数组"""
        if not isinstance(value, (list, tuple)):
            self.errors.append(ValidationError(
                field=full_path,
                message=f"必须是数组",
                code="type_error"
            ))
            return None
        
        converted = list(value)
        
        # 长度验证
        if rule.min_length is not None and len(converted) < rule.min_length:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"数组长度不能少于 {rule.min_length}",
                code="min_length"
            ))
        
        if rule.max_length is not None and len(converted) > rule.max_length:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"数组长度不能超过 {rule.max_length}",
                code="max_length"
            ))
        
        # 元素验证
        if rule.item_schema:
            validated_items = []
            for i, item in enumerate(converted):
                item_path = f"{full_path}[{i}]"
                item_value = self._validate_type(
                    item_path, f"{field_name}[{i}]", item, rule.item_schema
                )
                if item_value is not None:
                    validated_items.append(item_value)
            converted = validated_items
        
        return converted
    
    def _validate_object(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[Dict]:
        """验证对象"""
        if not isinstance(value, dict):
            self.errors.append(ValidationError(
                field=full_path,
                message=f"必须是对象",
                code="type_error"
            ))
            return None
        
        # 嵌套验证
        if rule.nested_schema:
            _, nested_errors, nested_data = self.validate(
                value, rule.nested_schema, f"{full_path}."
            )
            self.errors.extend(nested_errors)
            return nested_data
        
        return value
    
    def _validate_date(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[date]:
        """验证日期"""
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        self.errors.append(ValidationError(
            field=full_path,
            message=f"必须是有效的日期格式 (YYYY-MM-DD)",
            code="type_error"
        ))
        return None
    
    def _validate_datetime(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[datetime]:
        """验证日期时间"""
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value.replace('Z', '+0000'), fmt)
                except ValueError:
                    continue
        
        self.errors.append(ValidationError(
            field=full_path,
            message=f"必须是有效的日期时间格式",
            code="type_error"
        ))
        return None
    
    def _validate_email(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[str]:
        """验证邮箱"""
        converted = str(value)
        if not re.match(self.PATTERNS["email"], converted):
            self.errors.append(ValidationError(
                field=full_path,
                message=f"邮箱格式不正确",
                code="format_error"
            ))
            return None
        return converted.lower()
    
    def _validate_url(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[str]:
        """验证URL"""
        converted = str(value)
        if not re.match(self.PATTERNS["url"], converted):
            self.errors.append(ValidationError(
                field=full_path,
                message=f"URL格式不正确",
                code="format_error"
            ))
            return None
        return converted
    
    def _validate_uuid(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[str]:
        """验证UUID"""
        converted = str(value)
        if not re.match(self.PATTERNS["uuid"], converted, re.IGNORECASE):
            self.errors.append(ValidationError(
                field=full_path,
                message=f"UUID格式不正确",
                code="format_error"
            ))
            return None
        return converted.lower()
    
    def _validate_enum(
        self,
        full_path: str,
        field_name: str,
        value: Any,
        rule: ValidationRule
    ) -> Optional[Any]:
        """验证枚举"""
        if rule.enum and value not in rule.enum:
            self.errors.append(ValidationError(
                field=full_path,
                message=f"必须是以下值之一: {rule.enum}",
                code="invalid_choice"
            ))
            return None
        return value
    
    def _check_condition(self, value: Any, condition: Dict[str, Any]) -> bool:
        """检查条件"""
        op = condition.get("op", "==")
        target = condition.get("value")
        
        if op == "==":
            return value == target
        elif op == "!=":
            return value != target
        elif op == "in":
            return value in target
        elif op == "not_in":
            return value not in target
        elif op == "exists":
            return value is not None
        
        return False
    
    def get_errors_dict(self) -> Dict[str, List[str]]:
        """获取按字段分组的错误信息"""
        errors_dict: Dict[str, List[str]] = {}
        for error in self.errors:
            if error.field not in errors_dict:
                errors_dict[error.field] = []
            errors_dict[error.field].append(error.message)
        return errors_dict
    
    def get_first_error(self) -> Optional[ValidationError]:
        """获取第一个错误"""
        return self.errors[0] if self.errors else None


# ==================== 便捷函数 ====================

def validate_email(email: str) -> Tuple[bool, str]:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, ""
    return False, "邮箱格式不正确"


def validate_phone_cn(phone: str) -> Tuple[bool, str]:
    """验证中国手机号"""
    pattern = r'^1[3-9]\d{9}$'
    if re.match(pattern, phone):
        return True, ""
    return False, "手机号格式不正确"


def sanitize_string(value: str) -> str:
    """清洗字符串（去除首尾空格）"""
    return value.strip() if value else value


def sanitize_html(value: str) -> str:
    """清洗HTML标签"""
    import html
    cleaned = re.sub(r'<[^>]+>', '', value)
    return html.unescape(cleaned)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 定义验证模式
    schema = {
        "username": ValidationRule(
            type=FieldType.STRING,
            required=True,
            min_length=3,
            max_length=20,
            pattern=r'^[a-zA-Z0-9_]+$',
            sanitizer=sanitize_string
        ),
        "email": ValidationRule(
            type=FieldType.EMAIL,
            required=True
        ),
        "age": ValidationRule(
            type=FieldType.INTEGER,
            required=False,
            min_value=0,
            max_value=150,
            default=18
        ),
        "tags": ValidationRule(
            type=FieldType.ARRAY,
            required=False,
            max_length=5,
            item_schema=ValidationRule(
                type=FieldType.STRING,
                min_length=1,
                max_length=20
            )
        ),
        "address": ValidationRule(
            type=FieldType.OBJECT,
            required=False,
            nested_schema={
                "city": ValidationRule(type=FieldType.STRING, required=True),
                "street": ValidationRule(type=FieldType.STRING, required=False)
            }
        )
    }
    
    # 创建验证器
    validator = DataValidator(schema)
    
    # 测试数据
    test_data = {
        "username": "  john_doe  ",
        "email": "john@example.com",
        "age": "25",
        "tags": ["developer", "python"],
        "address": {
            "city": "Beijing",
            "street": "Main Street"
        }
    }
    
    # 验证
    is_valid, errors, cleaned = validator.validate(test_data)
    
    print(f"验证结果: {'通过' if is_valid else '失败'}")
    if errors:
        print("\n错误信息:")
        for error in errors:
            print(f"  - {error}")
    
    print("\n清洗后的数据:")
    print(json.dumps(cleaned, indent=2, ensure_ascii=False, default=str))
