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
from typing import Optional, Dict, Any, List, Iterator, Callable, Tuple
import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """统一的LLM调用客户端"""

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
    }

    def __init__(self, model: str = "deepseek-chat", api_key: Optional[str] = None):
        """
        初始化LLM客户端

        Args:
            model: 模型名称，如 "deepseek-chat", "qwen-plus"
            api_key: API密钥，如果不传则从环境变量读取
        """
        if model not in self.MODEL_CONFIGS:
            raise ValueError(
                f"不支持的模型: {model}。"
                f"支持的模型: {list(self.MODEL_CONFIGS.keys())}"
            )

        self.model: str = model
        self.config: Dict[str, Any] = self.MODEL_CONFIGS[model]

        # Token 计数与成本追踪
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._total_calls: int = 0
        self._lock = threading.Lock()

        # API Key：优先使用传入的，否则从环境变量读取
        key = api_key or os.environ.get(self.config["env_key"])
        if not key:
            raise ValueError(
                f"请设置环境变量 {self.config['env_key']} " f"或传入api_key参数"
            )

        self.client = OpenAI(
            api_key=key,
            base_url=self.config["base_url"],
            timeout=httpx.Timeout(60.0, connect=10.0),
            max_retries=2,
        )

        logger.info(
            "LLMClient 初始化完成: model=%s, base_url=%s",
            self.model,
            self.config["base_url"],
        )

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
        """累计成本（人民币）"""
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
    ) -> str:
        """
        普通对话调用

        Args:
            messages: OpenAI格式的消息列表
            temperature: 温度参数
            max_tokens: 最大输出token数

        Returns:
            模型生成的文本
        """
        try:
            start_time = time.monotonic()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or self.config["max_tokens_default"],
            )
            self._record_usage(response)
            elapsed = time.monotonic() - start_time
            content = response.choices[0].message.content or ""
            logger.info(
                "chat() 完成: model=%s, tokens=%d, 耗时=%.2fs",
                self.model,
                response.usage.completion_tokens if response.usage else -1,
                elapsed,
            )
            return content
        except Exception as e:
            logger.error("chat() 调用失败: %s", e)
            raise RuntimeError(f"LLM调用失败: {str(e)}")

    def chat_json(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        JSON模式调用 - 确保输出合法JSON

        Args:
            system_prompt: 系统提示词
            user_content: 用户输入内容
            temperature: 温度参数（默认0.1，保证稳定性）
            max_tokens: 最大输出token数
            max_retries: 最大重试次数

        Returns:
            解析后的JSON字典
        """
        # 在方法开头初始化，确保 except 块中始终可用
        raw: Optional[str] = None
        content: Optional[str] = None

        for attempt in range(max_retries + 1):
            try:
                if not self.config["supports_json_mode"]:
                    # 不支持json mode的模型，用prompt引导
                    messages = [
                        {
                            "role": "system",
                            "content": system_prompt
                            + "\n\n重要：请只输出JSON，不要输出任何其他内容。",
                        },
                        {"role": "user", "content": user_content},
                    ]
                    raw = self.chat(
                        messages, temperature=temperature, max_tokens=max_tokens
                    )
                    # 尝试提取JSON
                    json_str = self._extract_json(raw)
                    return json.loads(json_str)

                # 支持json mode的模型
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or self.config["max_tokens_default"],
                    response_format={"type": "json_object"},
                )
                self._record_usage(response)
                content = response.choices[0].message.content
                if not content:
                    raise RuntimeError("模型返回了空内容，请重试或调整prompt")
                return json.loads(content)

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
                    return self._repair_json(repair_text)
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
                if attempt == max_retries:
                    raise
                logger.debug(
                    "chat_json() 第 %d 次尝试异常，将重试: %s",
                    attempt + 1,
                    e,
                )
                continue

        raise RuntimeError("JSON解析失败，已用尽所有重试次数")

    def chat_stream(
        self, messages: List[Dict[str, str]], temperature: float = 0.3
    ) -> Iterator[str]:
        """
        流式输出（用于UI展示）

        Args:
            messages: OpenAI格式的消息列表
            temperature: 温度参数

        Yields:
            每个chunk的文本内容
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            logger.error("chat_stream() 流式调用失败: %s", e)
            raise RuntimeError(f"流式调用失败: {str(e)}")

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
            return match.group(1).strip()

        # 尝试提取第一个 { ... } 块
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]

        raise ValueError(f"无法从模型输出中提取JSON: {text[:200]}...")

    def _repair_json(self, broken_json: str) -> Dict[str, Any]:
        """让LLM修复损坏的JSON"""
        try:
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
