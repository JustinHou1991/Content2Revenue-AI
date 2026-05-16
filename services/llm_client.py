"""
LLM Client - 统一的大语言模型调用接口
支持 DeepSeek / 通义千问 / 商汤日日新 / 其他OpenAI兼容模型
"""

import os
import json
import re
import logging
import threading
import time
import random
from typing import Optional, Dict, Any, List, Iterator, Callable, Tuple
import httpx
from openai import OpenAI

from services.llm_cache import LLMCache

logger = logging.getLogger(__name__)


# 全局自定义模型注册表（线程安全保护）
_custom_model_configs: Dict[str, Dict[str, Any]] = {}
_custom_model_lock = threading.Lock()


def register_custom_model(
    model_name: str,
    base_url: str,
    api_key: str,
    supports_json_mode: bool = True,
    max_tokens_default: int = 4096,
    cost_per_1k_input: float = 0.001,
    cost_per_1k_output: float = 0.002,
) -> None:
    """
    注册自定义模型配置（支持任意 OpenAI 兼容 API）

    Args:
        model_name:       模型名称，如 "my-gpt-4"
        base_url:        API base URL，如 "https://api.openai.com/v1"
        api_key:         API 密钥
        supports_json_mode: 是否支持 response_format=json_object
        max_tokens_default: 默认最大输出 token 数
        cost_per_1k_input:  每千输入 token 成本（美元）
        cost_per_1k_output: 每千输出 token 成本（美元）
    """
    with _custom_model_lock:
        _custom_model_configs[model_name] = {
        "base_url": base_url.rstrip("/"),
        "api_key": api_key,
        "max_tokens_default": max_tokens_default,
        "supports_json_mode": supports_json_mode,
        "cost_per_1k_input": cost_per_1k_input,
        "cost_per_1k_output": cost_per_1k_output,
        "_is_custom": True,
    }
    logger.info("已注册自定义模型: %s (base_url=%s)", model_name, base_url)


def remove_custom_model(model_name: str) -> None:
    """移除自定义模型配置"""
    with _custom_model_lock:
        if model_name in _custom_model_configs:
            del _custom_model_configs[model_name]
            logger.info("已移除自定义模型: %s", model_name)


class LLMClient:
    """统一的LLM调用客户端"""

    # 全局限流信号量：防止多线程同时调用 API 触发 thundering herd
    _global_semaphore = threading.BoundedSemaphore(4)

    # 模型配置注册表
    MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
        "deepseek-chat": {
            "base_url": "https://api.deepseek.com",
            "env_key": "DEEPSEEK_API_KEY",
            "max_tokens_default": 4096,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.001,
            "cost_per_1k_output": 0.002,
        },
        "deepseek-reasoner": {
            "base_url": "https://api.deepseek.com",
            "env_key": "DEEPSEEK_API_KEY",
            "max_tokens_default": 8192,
            "supports_json_mode": False,
            "cost_per_1k_input": 0.004,
            "cost_per_1k_output": 0.016,
        },
        "qwen-turbo": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "env_key": "DASHSCOPE_API_KEY",
            "max_tokens_default": 8192,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.0008,
            "cost_per_1k_output": 0.002,
        },
        "qwen-plus": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "env_key": "DASHSCOPE_API_KEY",
            "max_tokens_default": 8192,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.004,
            "cost_per_1k_output": 0.008,
        },
        "qwen-max": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "env_key": "DASHSCOPE_API_KEY",
            "max_tokens_default": 8192,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.02,
            "cost_per_1k_output": 0.06,
        },
        # ===== 商汤日日新 SenseNova =====
        "sensechat-5": {
            "base_url": "https://api.sensenova.cn/compatible-mode/v2",
            "env_key": "SENSNOVA_API_KEY",
            "max_tokens_default": 4096,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.008,
            "cost_per_1k_output": 0.02,
        },
        "sensechat-turbo": {
            "base_url": "https://api.sensenova.cn/compatible-mode/v2",
            "env_key": "SENSNOVA_API_KEY",
            "max_tokens_default": 4096,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.0003,
            "cost_per_1k_output": 0.0006,
        },
        "sensenova-v6-pro": {
            "base_url": "https://api.sensenova.cn/compatible-mode/v2",
            "env_key": "SENSNOVA_API_KEY",
            "max_tokens_default": 4096,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.009,
        },
        "sensenova-v6-turbo": {
            "base_url": "https://api.sensenova.cn/compatible-mode/v2",
            "env_key": "SENSNOVA_API_KEY",
            "max_tokens_default": 4096,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.0015,
            "cost_per_1k_output": 0.0045,
        },
        # ===== LongCat =====
        "LongCat-2.0-Preview": {
            "base_url": "https://api.longcat.chat/openai",
            "env_key": "LONGCAT_API_KEY",
            "max_tokens_default": 8192,
            "supports_json_mode": True,
            "cost_per_1k_input": 0.001,
            "cost_per_1k_output": 0.002,
        },
    }

    def __init__(self, model: str = "deepseek-chat", api_key: Optional[str] = None):
        """
        初始化LLM客户端

        Args:
            model: 模型名称，支持内置模型或已注册的自定义模型
            api_key: API密钥；自定义模型会忽略此参数（使用注册时提供的密钥）
        """
        # 优先查找自定义模型，其次查找内置模型（加锁保护）
        with _custom_model_lock:
            if model in _custom_model_configs:
                self.config = _custom_model_configs[model]
                self._is_custom = True
            elif model in self.MODEL_CONFIGS:
                self.config = self.MODEL_CONFIGS[model]
                self._is_custom = False
            else:
                all_models = list(self.MODEL_CONFIGS.keys()) + list(_custom_model_configs.keys())
                raise ValueError(
                    f"不支持的模型: {model}。"
                    f"支持的模型: {all_models}"
                )

        self.model: str = model

        # Token 计数与成本追踪
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._total_calls: int = 0
        self._lock = threading.Lock()

        # API Key：自定义模型使用注册时存储的 key；内置模型从环境变量读取
        if self._is_custom:
            key = self.config["api_key"]
        else:
            key = api_key or self._resolve_api_key(self.config.get("env_key", ""))
        if not key:
            env_hint = self.config.get("env_key", "API_KEY")
            raise ValueError(f"请设置环境变量 {env_hint} 或传入api_key参数")

        self.client = OpenAI(
            api_key=key,
            base_url=self.config["base_url"],
            timeout=httpx.Timeout(60.0, connect=10.0),
            max_retries=0,  # 禁用内置重试，使用手动重试逻辑避免叠加
        )

        # 初始化 LLM 缓存
        self._llm_cache = LLMCache()

        logger.info(
            "LLMClient 初始化完成: model=%s, base_url=%s",
            self.model,
            self.config["base_url"],
        )

    # ===== 模型管理 =====

    @staticmethod
    def get_builtin_models() -> List[str]:
        """获取所有内置模型名称"""
        return list(LLMClient.MODEL_CONFIGS.keys())

    @staticmethod
    def get_custom_models() -> List[str]:
        """获取所有已注册的自定义模型名称"""
        with _custom_model_lock:
            return list(_custom_model_configs.keys())

    @staticmethod
    def get_all_models() -> List[str]:
        """获取所有可用模型名称（内置 + 自定义）"""
        return LLMClient.get_builtin_models() + LLMClient.get_custom_models()

    @staticmethod
    def remove_custom_model(model_name: str) -> bool:
        """移除已注册的自定义模型"""
        with _custom_model_lock:
            if model_name in _custom_model_configs:
                del _custom_model_configs[model_name]
                logger.info("已移除自定义模型: %s", model_name)
                return True
            return False

    @staticmethod
    def _resolve_api_key(env_key: str) -> Optional[str]:
        """多源解析 API Key：环境变量 → st.secrets（Streamlit Cloud 兼容）"""
        key = os.environ.get(env_key)
        if key:
            return key
        try:
            import streamlit as st
            if hasattr(st, "secrets") and env_key in st.secrets:
                return st.secrets[env_key]
        except Exception:
            pass
        return None

    # ===== Token 与成本追踪 =====

    def _record_usage(
        self,
        response: Any,
        operation_type: str = "",
        content_id: str = "",
        lead_id: str = "",
        db_instance=None,
    ) -> None:
        """
        从 OpenAI 响应中提取并记录 token 用量

        Args:
            response: OpenAI API 响应对象
            operation_type: 操作类型标识（如 'content_analysis', 'lead_analysis'）
            content_id: 关联的内容ID
            lead_id: 关联的线索ID
            db_instance: Database 实例，用于持久化记录
        """
        try:
            usage = response.usage
            if usage is not None:
                input_tokens = usage.prompt_tokens or 0
                output_tokens = usage.completion_tokens or 0
                with self._lock:
                    self._total_input_tokens += input_tokens
                    self._total_output_tokens += output_tokens
                    self._total_calls += 1

                # 计算本次调用成本
                call_cost = self.estimate_cost(input_tokens, output_tokens)

                logger.debug(
                    "Token 用量: input=%d, output=%d, 累计 input=%d, output=%d, calls=%d, cost=%.4f",
                    input_tokens,
                    output_tokens,
                    self._total_input_tokens,
                    self._total_output_tokens,
                    self._total_calls,
                    call_cost,
                )

                # 如果提供了数据库实例，保存使用记录
                if db_instance is not None:
                    try:
                        db_instance.save_api_usage(
                            {
                                "model": self.model,
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "cost": call_cost,
                                "operation_type": operation_type,
                                "content_id": content_id,
                                "lead_id": lead_id,
                            }
                        )
                    except Exception as db_exc:
                        logger.warning("保存API使用记录到数据库失败: %s", db_exc)
        except Exception as exc:
            logger.warning("无法从响应中提取 token 用量: %s", exc)

    @property
    def total_input_tokens(self) -> int:
        """累计输入 token 数"""
        return self._total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        """累计输出 token 数"""
        return self._total_output_tokens

    @property
    def total_tokens(self) -> int:
        """累计总 token 数"""
        return self._total_input_tokens + self._total_output_tokens

    @property
    def total_calls(self) -> int:
        """累计调用次数"""
        return self._total_calls

    @property
    def total_cost(self) -> float:
        """累计成本（美元，基于官方定价）"""
        return self.estimate_cost(self._total_input_tokens, self._total_output_tokens)

    def reset_usage_stats(self) -> None:
        """重置 token 用量统计"""
        with self._lock:
            self._total_input_tokens = 0
            self._total_output_tokens = 0
            self._total_calls = 0
        logger.info("Token 用量统计已重置")

    # ===== 核心调用方法 =====

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
    ) -> str:
        """
        普通对话调用（内置 429 退避重试）

        Args:
            messages: OpenAI格式的消息列表
            temperature: 温度参数
            max_tokens: 最大输出token数
            max_retries: 429/5xx 最大重试次数

        Returns:
            模型生成的文本
        """
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                start_time = time.monotonic()
                with self._global_semaphore:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens or self.config["max_tokens_default"],
                    )
                try:
                    self._record_usage(response)
                except Exception:
                    pass
                elapsed = time.monotonic() - start_time
                content = (response.choices[0].message.content or "") if response.choices else ""
                logger.info(
                    "chat() 完成: model=%s, tokens=%d, 耗时=%.2fs",
                    self.model,
                    response.usage.completion_tokens if response.usage else -1,
                    elapsed,
                )
                return content
            except Exception as e:
                last_error = e
                error_str = str(e)
                # 429 速率限制或 5xx 服务端错误 → 指数退避重试
                is_rate_limit = "429" in error_str or "rate_limit" in error_str.lower()
                is_server_error = any(code in error_str for code in ["500", "502", "503", "504"])
                if (is_rate_limit or is_server_error) and attempt < max_retries:
                    wait_time = min(2 ** attempt * 2, 30)
                    time.sleep(wait_time + random.uniform(0, 1))
                    logger.warning(
                        "chat() 第 %d 次调用遇到 %s，等待 %.1fs 后重试: %s",
                        attempt + 1,
                        "速率限制" if is_rate_limit else "服务端错误",
                        wait_time,
                        error_str[:200],
                    )
                    continue
                logger.error("chat() 调用失败（已重试 %d 次）: %s", attempt + 1, e)
                break

        raise RuntimeError(f"LLM调用失败: {str(last_error)}")

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """
        流式对话调用 - 返回增量文本

        Args:
            messages: OpenAI格式的消息列表
            temperature: 温度参数
            max_tokens: 最大输出token数

        Yields:
            增量文本片段

        Note:
            不支持缓存，每次都是实时调用
        """
        try:
            with self._global_semaphore:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or self.config["max_tokens_default"],
                    stream=True,
                )
            full_content_parts: List[str] = []
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta_content = chunk.choices[0].delta.content
                    full_content_parts.append(delta_content)
                    yield delta_content
            full_content = "".join(full_content_parts)
            input_tokens = self._estimate_tokens(messages)
            output_tokens = self._estimate_tokens_from_text(full_content)
            with self._lock:
                self._total_input_tokens += input_tokens
                self._total_output_tokens += output_tokens
                self._total_calls += 1
            logger.debug(
                "chat_stream() token用量: input=%d, output=%d",
                input_tokens,
                output_tokens,
            )
        except Exception as e:
            logger.error("chat_stream() 流式调用失败: %s", e)
            raise RuntimeError(f"流式调用失败: {str(e)}")

    def chat_json(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        JSON模式调用 - 确保输出合法JSON

        Args:
            system_prompt: 系统提示词
            user_content: 用户输入内容
            temperature: 温度参数（默认0.1，保证稳定性）
            max_tokens: 最大输出token数
            max_retries: 最大重试次数
            use_cache: 是否使用缓存（默认True）

        Returns:
            解析后的JSON字典
        """
        # 构建消息列表（原始版本，用于缓存键计算）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        # 检查缓存（使用原始 messages 作为缓存键）
        if use_cache:
            cached_response = self._llm_cache.get(messages, self.model, temperature=temperature, max_tokens=max_tokens)
            if cached_response is not None:
                logger.debug("LLM 缓存命中")
                return cached_response

        # 在方法开头初始化，确保 except 块中始终可用
        raw: Optional[str] = None
        content: Optional[str] = None
        response: Optional[Dict[str, Any]] = None

        for attempt in range(max_retries + 1):
            try:
                # 为每次尝试重新构建 messages（非 json_mode 时添加额外指令）
                if not self.config["supports_json_mode"]:
                    # 不支持json mode的模型，用prompt引导
                    attempt_messages = [
                        {
                            "role": "system",
                            "content": system_prompt
                            + "\n\n重要：请只输出JSON，不要输出任何其他内容。",
                        },
                        {"role": "user", "content": user_content},
                    ]
                    raw = self.chat(
                        attempt_messages, temperature=temperature, max_tokens=max_tokens
                    )
                    # 尝试提取JSON
                    json_str = self._extract_json(raw)
                    response = json.loads(json_str)
                else:
                    # 支持json mode的模型
                    attempt_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ]
                    with self._global_semaphore:
                        api_response = self.client.chat.completions.create(
                            model=self.model,
                            messages=attempt_messages,
                            temperature=temperature,
                            max_tokens=max_tokens or self.config["max_tokens_default"],
                            response_format={"type": "json_object"},
                        )
                    try:
                        self._record_usage(api_response)
                    except Exception:
                        pass
                    content = (api_response.choices[0].message.content if api_response.choices else "")
                    if not content:
                        raise RuntimeError("模型返回了空内容，请重试或调整prompt")
                    response = json.loads(content)

                # 缓存结果（使用原始 messages 作为缓存键，保证命中率）
                if use_cache and response is not None:
                    self._llm_cache.set(messages, self.model, response, temperature=temperature, max_tokens=max_tokens)

                return response

            except json.JSONDecodeError as e:
                # 安全地获取可用于修复的文本
                repair_text: Optional[str] = raw or content
                if not repair_text:
                    logger.warning(
                        "chat_json() 第 %d 次尝试 JSONDecodeError，但无可用文本进行修复",
                        attempt + 1,
                    )
                    if attempt == max_retries:
                        raise RuntimeError(
                            f"JSON解析失败（已重试 {max_retries + 1} 次），"
                            f"且无可用文本进行修复: {e}"
                        )
                    continue

                if attempt == max_retries:
                    # 最后一次尝试：让LLM修复JSON
                    logger.warning(
                        "chat_json() 最后一次尝试仍失败，尝试自动修复JSON: %s",
                        e,
                    )
                    response = self._repair_json(repair_text)
                    # 缓存修复后的结果
                    if use_cache:
                        self._llm_cache.set(messages, self.model, response, temperature=temperature, max_tokens=max_tokens)
                    return response
                logger.debug(
                    "chat_json() 第 %d 次尝试 JSONDecodeError，将重试: %s",
                    attempt + 1,
                    e,
                )
                continue
            except RuntimeError:
                # RuntimeError 由我们自己抛出（如空内容），直接向上传播
                if attempt == max_retries:
                    raise
                continue
            except Exception as e:
                # 429 速率限制 → 指数退避后重试
                error_str = str(e)
                is_rate_limit = "429" in error_str or "rate_limit" in error_str.lower()
                is_server_error = any(code in error_str for code in ["500", "502", "503", "504"])
                if (is_rate_limit or is_server_error) and attempt < max_retries:
                    wait_time = min(2 ** attempt * 2, 30)
                    time.sleep(wait_time + random.uniform(0, 1))
                    logger.warning(
                        "chat_json() 第 %d 次调用遇到 %s，等待 %.1fs 后重试",
                        attempt + 1,
                        "速率限制" if is_rate_limit else "服务端错误",
                        wait_time,
                    )
                    continue
                if attempt == max_retries:
                    raise
                logger.debug(
                    "chat_json() 第 %d 次尝试异常，将重试: %s",
                    attempt + 1,
                    e,
                )
                continue

        raise RuntimeError("JSON解析失败，已用尽所有重试次数")

    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """估算消息列表的 token 数（简单估算：1 token ≈ 4 字符）"""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    def _estimate_tokens_from_text(self, text: str) -> int:
        """估算文本的 token 数"""
        return len(text) // 4

    # ===== 内部辅助方法 =====

    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON（当模型不支持json mode时使用）"""
        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # 尝试提取```json ... ```块
        pattern = r"```(?:json)?\s*([\s\S]*?)```"
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        # 尝试匹配第一个完整的 JSON 对象 { ... }
        # 使用栈来确保 { 和 } 正确配对
        start = text.find("{")
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        try:
                            json.loads(candidate)
                            return candidate
                        except json.JSONDecodeError:
                            break

        raise ValueError(f"无法从模型输出中提取JSON: {text[:200]}...")

    def _repair_json(self, broken_json: str) -> Dict[str, Any]:
        """让LLM修复损坏的JSON"""
        try:
            with self._global_semaphore:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个JSON修复专家。请修复以下JSON，只输出修复后的JSON，不要有任何其他内容。",
                        },
                        {"role": "user", "content": broken_json},
                    ],
                    temperature=0.1,
                    response_format=(
                        {"type": "json_object"}
                        if self.config["supports_json_mode"]
                        else None
                    ),
                )
                self._record_usage(response)
                content = response.choices[0].message.content
            if not content:
                raise RuntimeError("JSON修复调用返回了空内容")

            # 对不支持 json_mode 的模型，返回的内容可能不是纯 JSON，
            # 需要先提取再解析
            if not self.config["supports_json_mode"]:
                json_str = self._extract_json(content)
                return json.loads(json_str)

            return json.loads(content)
        except Exception as e:
            logger.error("_repair_json() JSON修复失败: %s", e)
            raise RuntimeError(f"JSON修复失败: {str(e)}")

    # ===== 批量处理 =====

    def batch_process(
        self,
        items: List[Any],
        prompt_builder: Callable[[Any], Tuple[str, str]],
        concurrency: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        批量处理（带并发控制）

        Args:
            items: 待处理的数据列表
            prompt_builder: 接收item，返回(system_prompt, user_content)的函数
            concurrency: 并发数（建议不超过5，避免触发限流）

        Returns:
            处理结果列表，每项包含 success, data/error, item
        """
        import concurrent.futures

        logger.info(
            "batch_process() 开始: 共 %d 项, 并发数=%d, model=%s",
            len(items),
            concurrency,
            self.model,
        )

        def process_one(item: Any) -> Dict[str, Any]:
            system_prompt, user_content = prompt_builder(item)
            try:
                result = self.chat_json(system_prompt, user_content)
                return {"success": True, "data": result, "item": item}
            except Exception as e:
                logger.warning("batch_process() 单项处理失败: %s", e)
                return {"success": False, "error": str(e), "item": item}

        results: List[Dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(process_one, item) for item in items]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        success_count = sum(1 for r in results if r["success"])
        logger.info(
            "batch_process() 完成: 成功=%d/%d, 累计成本=%.4f元",
            success_count,
            len(items),
            self.total_cost,
        )
        return results

    # ===== 工具方法 =====

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """估算调用成本（人民币）"""
        input_cost = (input_tokens / 1000) * self.config["cost_per_1k_input"]
        output_cost = (output_tokens / 1000) * self.config["cost_per_1k_output"]
        return input_cost + output_cost

    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        return {
            "model": self.model,
            "base_url": self.config["base_url"],
            "max_tokens": self.config["max_tokens_default"],
            "supports_json_mode": self.config["supports_json_mode"],
        }

    def get_usage_summary(self) -> Dict[str, Any]:
        """获取 token 用量与成本汇总"""
        return {
            "model": self.model,
            "total_calls": self._total_calls,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }

    def get_cost_summary(self, db_instance=None) -> Dict[str, Any]:
        """
        获取成本汇总（包含内存统计和数据库统计）

        Args:
            db_instance: Database 实例，用于获取持久化的成本数据

        Returns:
            成本汇总字典
        """
        summary = {
            "current_session": {
                "model": self.model,
                "calls": self._total_calls,
                "input_tokens": self._total_input_tokens,
                "output_tokens": self._total_output_tokens,
                "total_tokens": self.total_tokens,
                "cost": round(self.total_cost, 4),
            },
            "model_config": {
                "name": self.model,
                "cost_per_1k_input": self.config.get("cost_per_1k_input", 0),
                "cost_per_1k_output": self.config.get("cost_per_1k_output", 0),
            },
            "cache_stats": self._llm_cache.get_stats(),
        }

        # 如果提供了数据库实例，获取历史统计
        if db_instance is not None:
            try:
                summary["database_stats"] = {
                    "total_cost": db_instance.get_total_cost(),
                    "today": db_instance.get_today_api_stats(),
                    "this_week": db_instance.get_week_api_stats(),
                    "this_month": db_instance.get_month_api_stats(),
                }
            except Exception as e:
                logger.warning("获取数据库成本统计失败: %s", e)
                summary["database_stats"] = {"error": str(e)}

        return summary

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取 LLM 缓存统计"""
        return self._llm_cache.get_stats()

    def clear_cache(self) -> None:
        """清空 LLM 缓存"""
        self._llm_cache.clear()
        logger.info("LLM 缓存已清空")


# ===== 使用示例 =====
if __name__ == "__main__":
    # 配置日志以便在示例中看到输出
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    # 测试代码
    try:
        # 使用DeepSeek
        llm = LLMClient(model="deepseek-chat")

        # 普通调用
        result = llm.chat([{"role": "user", "content": "用一句话解释什么是CRM"}])
        print("普通调用结果:", result)

        # JSON模式调用
        result = llm.chat_json(
            system_prompt="分析公司信息，输出JSON格式",
            user_content="公司：杭州某某科技有限公司，行业：SaaS软件",
        )
        print("JSON调用结果:", json.dumps(result, ensure_ascii=False, indent=2))

        # 用量汇总
        print(
            "用量汇总:",
            json.dumps(llm.get_usage_summary(), ensure_ascii=False, indent=2),
        )

    except Exception as e:
        print(f"错误: {e}")
