"""
分析器抽象基类模块 - 为所有分析器提供公共基础
"""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .llm_client import LLMClient
from utils.cache_manager import cached
from utils.input_validator import InputValidator, sanitize_input

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """分析器抽象基类

    为所有分析器提供统一的基础架构，包括：
    - LLM客户端初始化
    - 提示词构建（抽象方法）
    - 响应解析（抽象方法）
    - 输出验证（公共实现）
    - 分析历史记录

    子类必须实现：
    - _build_prompt: 构建特定领域的提示词
    - _parse_response: 解析LLM响应为结构化数据
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """初始化分析器

        Args:
            llm_client: LLM客户端实例
        """
        self.llm: LLMClient = llm_client
        self.system_prompt: str = self._get_system_prompt()
        self._analysis_history: List[Dict[str, Any]] = []

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """获取系统提示词

        Returns:
            系统提示词字符串
        """
        pass

    @abstractmethod
    def _build_prompt(self, **kwargs) -> str:
        """构建用户提示词（抽象方法）

        Args:
            **kwargs: 构建提示词所需的参数

        Returns:
            用户提示词字符串
        """
        pass

    @abstractmethod
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析LLM响应（抽象方法）

        Args:
            response: LLM返回的原始JSON数据

        Returns:
            解析后的结构化数据
        """
        pass

    def _validate_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """验证并补全输出字段（公共实现）

        子类可以重写此方法以添加特定验证逻辑，
        但应先调用 super()._validate_output()。

        Args:
            output: 待验证的输出数据

        Returns:
            验证后的输出数据
        """
        # 基础验证：确保输出不为空
        if not output or not isinstance(output, dict):
            logger.warning("输出为空或格式错误，返回空字典")
            return {}
        return output

    def analyze(self, input_data: Any) -> Dict[str, Any]:
        """主分析流程（模板方法模式）

        定义分析的标准流程：
        1. 验证输入数据
        2. 构建提示词
        3. 调用LLM
        4. 解析响应
        5. 验证输出
        6. 记录分析历史

        Args:
            input_data: 输入数据

        Returns:
            分析结果字典

        Raises:
            ValueError: 输入数据无效时
            RuntimeError: LLM调用失败时
        """
        # 验证并清洗输入（防御性检查：确保子类重写返回了有效数据）
        input_data = self._validate_input(input_data)
        if input_data is None:
            raise ValueError("输入验证返回了空值，请检查数据格式")

        # 构建提示词
        user_prompt = self._build_prompt_from_input(input_data)

        # 调用LLM
        try:
            response = self.llm.chat_json(
                system_prompt=self.system_prompt,
                user_content=user_prompt,
                temperature=self._get_temperature(),
            )
        except Exception as e:
            logger.error("LLM调用失败: %s", e)
            raise RuntimeError(f"分析失败: {str(e)}") from e

        # 解析响应
        parsed = self._parse_response(response)

        # 验证输出
        validated = self._validate_output(parsed)

        # 构建结果
        result = self._build_result(validated, input_data)

        # 记录历史
        self._record_analysis(result)

        return result

    def _validate_input(self, input_data: Any) -> Any:
        """验证并清洗输入数据

        子类可以重写此方法以添加特定验证逻辑。

        Args:
            input_data: 输入数据

        Returns:
            验证并清洗后的输入数据

        Raises:
            ValueError: 输入数据无效时
        """
        if input_data is None:
            raise ValueError("输入数据不能为空")

        # 检查 Prompt 注入攻击
        if isinstance(input_data, str):
            is_injection, msg = InputValidator.check_prompt_injection(input_data)
            if is_injection:
                logger.warning(f"Prompt 注入检测: {msg}")
                raise ValueError("输入包含可疑内容，请检查后重试")
            # 清洗输入数据
            return InputValidator.sanitize_text(input_data)
        elif isinstance(input_data, dict):
            # sanitize_input 返回新字典
            return sanitize_input(input_data)
        else:
            return input_data

    def _build_prompt_from_input(self, input_data: Any) -> str:
        """根据输入数据构建提示词

        默认实现直接调用 _build_prompt，子类可以重写。

        Args:
            input_data: 输入数据

        Returns:
            用户提示词字符串
        """
        return self._build_prompt(data=input_data)

    def _get_temperature(self) -> float:
        """获取LLM温度参数

        子类可以重写此方法以调整创造性程度。

        Returns:
            温度参数值（0.0-1.0）
        """
        return 0.3

    def _build_result(
        self, validated_output: Dict[str, Any], input_data: Any
    ) -> Dict[str, Any]:
        """构建最终结果

        子类应该重写此方法以构建特定格式的结果。

        Args:
            validated_output: 验证后的输出数据
            input_data: 原始输入数据

        Returns:
            最终结果字典
        """
        return {
            "output": validated_output,
            "created_at": datetime.now().isoformat(),
            "model": self.llm.model,
        }

    def _record_analysis(self, result: Dict[str, Any]) -> None:
        """记录分析历史

        Args:
            result: 分析结果
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }
        self._analysis_history.append(record)

        # 限制历史记录大小
        if len(self._analysis_history) > 1000:
            self._analysis_history = self._analysis_history[-1000:]

    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """获取分析历史

        Returns:
            分析历史列表
        """
        return self._analysis_history.copy()

    def clear_history(self) -> None:
        """清空分析历史"""
        self._analysis_history.clear()

    def batch_analyze(
        self,
        items: List[Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        cancel_event: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """批量分析

        Args:
            items: 待分析的项目列表
            progress_callback: 进度回调函数，接收 (current_index, total_count) 参数
            cancel_event: 取消事件对象（需有 is_set() 方法）

        Returns:
            分析结果列表
        """
        total = len(items)
        logger.info("开始批量分析，共 %d 条", total)
        results: List[Dict[str, Any]] = []

        for i, item in enumerate(items):
            # 检查取消事件
            if cancel_event is not None and hasattr(cancel_event, "is_set"):
                if cancel_event.is_set():
                    logger.info("批量分析被取消，已完成 %d/%d 条", i, total)
                    break

            try:
                result = self.analyze(item)
                results.append(
                    {
                        "success": True,
                        "data": result,
                        "index": i,
                    }
                )
            except Exception as e:
                logger.warning("批量分析第 %d 条失败: %s", i, e)
                results.append(
                    {
                        "success": False,
                        "error": str(e),
                        "index": i,
                    }
                )

            if progress_callback is not None:
                progress_callback(i + 1, total)

        success_count = sum(1 for r in results if r.get("success"))
        logger.info("批量分析完成，成功 %d/%d", success_count, total)
        return results

    def _wrap_user_content(self, content: str, max_length: int = 5000) -> str:
        """包装用户内容以减少Prompt注入风险

        Args:
            content: 原始内容
            max_length: 最大长度限制

        Returns:
            包装后的内容
        """
        truncated = content[:max_length] if len(content) > max_length else content
        return f"<user_content>\n{truncated}\n</user_content>"

    def _ensure_list_field(
        self, data: Dict[str, Any], field_name: str, default: Optional[List] = None
    ) -> None:
        """确保字段为列表类型

        Args:
            data: 数据字典
            field_name: 字段名
            default: 默认值
        """
        if default is None:
            default = []
        if field_name not in data or not isinstance(data[field_name], list):
            value = data.get(field_name)
            data[field_name] = [str(value)] if value else default

    def _ensure_numeric_range(
        self,
        data: Dict[str, Any],
        field_name: str,
        min_val: float,
        max_val: float,
        default: float,
    ) -> None:
        """确保数值字段在有效范围内

        Args:
            data: 数据字典
            field_name: 字段名
            min_val: 最小值
            max_val: 最大值
            default: 默认值
        """
        try:
            value = float(data.get(field_name, default))
            data[field_name] = max(min_val, min(max_val, value))
        except (ValueError, TypeError):
            logger.warning("字段 '%s' 数值无效，使用默认值 %s", field_name, default)
            data[field_name] = default

    def _ensure_string_field(
        self, data: Dict[str, Any], field_name: str, default: str = ""
    ) -> None:
        """确保字段为字符串类型

        Args:
            data: 数据字典
            field_name: 字段名
            default: 默认值
        """
        if field_name not in data or not isinstance(data[field_name], str):
            value = data.get(field_name)
            data[field_name] = str(value) if value is not None else default
