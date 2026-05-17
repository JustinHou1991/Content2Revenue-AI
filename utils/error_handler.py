"""统一错误处理模块

提供项目统一的错误类型定义和处理函数
"""
import logging
import time
import streamlit as st
from typing import Optional, Callable, TypeVar, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class C2RError(Exception):
    """项目统一错误基类"""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN", detail: Optional[dict] = None):
        self.message = message
        self.error_code = error_code
        self.detail = detail or {}
        super().__init__(self.message)


class LLMError(C2RError):
    """LLM调用相关错误"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, detail: Optional[dict] = None):
        self.status_code = status_code
        error_code = self._map_status_code(status_code)
        super().__init__(message, error_code, detail)
    
    def _map_status_code(self, status_code: Optional[int]) -> str:
        """将HTTP状态码映射为错误码"""
        if status_code is None:
            return "LLM_UNKNOWN"
        if status_code == 401:
            return "LLM_AUTH_ERROR"
        if status_code == 429:
            return "LLM_RATE_LIMIT"
        if status_code >= 500:
            return "LLM_SERVER_ERROR"
        return "LLM_REQUEST_ERROR"


class DatabaseError(C2RError):
    """数据库操作相关错误"""
    pass


class ValidationError(C2RError):
    """数据验证相关错误"""
    pass


class ConfigError(C2RError):
    """配置相关错误"""
    pass


class APIError(C2RError):
    """API调用相关错误"""
    pass


def handle_error(error: Exception, context: str = "", show_ui: bool = True) -> str:
    """统一错误处理函数
    
    Args:
        error: 异常对象
        context: 错误发生的上下文描述
        show_ui: 是否在UI上显示错误信息
        
    Returns:
        处理后的错误消息
    """
    # 构建错误消息
    if isinstance(error, C2RError):
        # 已知错误类型
        message = _handle_known_error(error, context)
    elif "401" in str(error) or "Unauthorized" in str(error):
        message = "❌ API Key无效或已过期，请检查配置"
        error_code = "AUTH_ERROR"
    elif "429" in str(error) or "rate limit" in str(error).lower():
        message = "❌ 请求过于频繁，请稍后重试"
        error_code = "RATE_LIMIT"
    elif "timeout" in str(error).lower():
        message = "❌ 请求超时，请稍后重试"
        error_code = "TIMEOUT"
    elif "connection" in str(error).lower():
        message = "❌ 网络连接失败，请检查网络"
        error_code = "CONNECTION_ERROR"
    elif "json" in str(error).lower() and "decode" in str(error).lower():
        message = "❌ 数据解析失败，请检查输入格式"
        error_code = "PARSE_ERROR"
    else:
        # 未知错误
        message = f"❌ {context}失败，请稍后重试"
        error_code = "UNKNOWN"
    
    # 记录日志
    logger.error(f"[{error_code}] {context}: {error}", exc_info=True)
    
    # UI显示
    if show_ui:
        st.error(message)
    
    return message


def _handle_known_error(error: C2RError, context: str) -> str:
    """处理已知的C2RError类型"""
    
    error_messages = {
        "LLM_AUTH_ERROR": "❌ API Key无效或已过期，请在系统设置中配置正确的API Key",
        "LLM_RATE_LIMIT": "❌ API调用过于频繁，请等待1分钟后重试",
        "LLM_SERVER_ERROR": "❌ AI服务暂时不可用，请稍后重试",
        "LLM_REQUEST_ERROR": "❌ AI请求失败，请检查输入内容",
        "LLM_UNKNOWN": "❌ AI服务调用失败，请稍后重试",
    }
    
    if error.error_code in error_messages:
        return error_messages[error.error_code]
    
    return f"❌ {error.message}"


def get_error_recovery_suggestion(error: Exception) -> Optional[str]:
    """获取错误恢复建议（基于学习的最佳实践）
    
    根据错误类型提供具体的恢复步骤建议，
    帮助用户快速解决问题而不是感到困惑。
    
    Returns:
        恢复建议字符串，如果无法提供建议则返回None
    """
    error_str = str(error).lower()
    
    # 网络相关错误
    if any(keyword in error_str for keyword in ["connection", "network", "dns", "refused"]):
        return "请检查网络连接后重试。如果使用VPN，请尝试关闭后重试。"
    
    # 超时错误
    if "timeout" in error_str:
        return "请求超时可能是网络问题或服务器繁忙，请稍后重试。如果问题持续，请检查API服务状态。"
    
    # 认证错误
    if any(keyword in error_str for keyword in ["401", "unauthorized", "auth", "api key"]):
        return "请在「系统设置」中检查并更新您的API Key。确保Key有足够的调用额度。"
    
    # 频率限制
    if any(keyword in error_str for keyword in ["429", "rate limit", "quota", "limit"]):
        return "API调用频率超限，请等待1-2分钟后重试。您可以在「系统设置」中调整API配置。"
    
    # 解析错误
    if any(keyword in error_str for keyword in ["parse", "json", "decode", "invalid"]):
        return "数据格式有问题，请检查输入内容后重试。"
    
    # 服务器错误
    if any(keyword in error_str for keyword in ["500", "502", "503", "server error"]):
        return "AI服务暂时不可用，这通常是临时问题。请等待几分钟后重试。"
    
    # 默认建议
    return None


def format_user_friendly_error(error: Exception, context: str = "") -> dict:
    """格式化用户友好的错误信息（包含消息、建议和操作）
    
    返回结构化信息，便于UI组件展示。
    
    Returns:
        包含以下键的字典:
        - message: 用户友好的错误消息
        - suggestion: 恢复建议（可选）
        - can_retry: 是否可以重试
        - severity: 严重程度 (info/warning/error)
    """
    result = {
        "message": str(error),
        "suggestion": None,
        "can_retry": True,
        "severity": "error"
    }
    
    # 获取恢复建议
    suggestion = get_error_recovery_suggestion(error)
    if suggestion:
        result["suggestion"] = suggestion
    
    # 根据错误类型调整可重试性
    error_str = str(error).lower()
    if any(keyword in error_str for keyword in ["401", "unauthorized", "auth"]):
        result["can_retry"] = False
        result["severity"] = "warning"
    elif any(keyword in error_str for keyword in ["timeout", "connection"]):
        result["severity"] = "warning"
    
    # 格式化主消息
    if context:
        result["message"] = f"{context}失败：{result['message']}"
    
    return result


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """带指数退避的重试装饰器（基于学习的最佳实践）
    
    对于瞬时错误（如网络超时、服务器繁忙）自动重试，
    使用指数退避策略避免对服务造成压力。
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避系数（每次重试延迟翻倍）
    
    Usage:
        @retry_on_failure(max_retries=3, delay=1.0)
        def call_api():
            return api.request()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否是可重试的错误
                    error_str = str(e).lower()
                    is_retryable = any(keyword in error_str for keyword in [
                        "timeout", "connection", "server error", "service unavailable",
                        "429", "rate limit", "temporary"
                    ])
                    
                    if not is_retryable or attempt >= max_retries:
                        # 不可重试的错误或已达最大次数
                        logger.warning(
                            f"函数 {func.__name__} 执行失败（非重试错误或已达最大次数）: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"函数 {func.__name__} 执行失败（第{attempt + 1}次尝试）: {e}，"
                        f"{current_delay:.1f}秒后重试..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # 如果所有重试都失败，抛出最后一个异常
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def safe_execute(func: Callable, context: str = "", default_return=None, show_ui: bool = True):
    """安全执行包装器（增强版）
    
    自动捕获异常并统一处理，提供用户友好的错误提示和恢复建议。
    
    Args:
        func: 要执行的函数
        context: 上下文描述
        default_return: 出错时的默认返回值
        show_ui: 是否在UI显示错误
        
    Returns:
        函数执行结果或default_return
    """
    try:
        return func()
    except Exception as e:
        # 获取用户友好的错误信息
        error_info = format_user_friendly_error(e, context)
        
        # 记录日志
        logger.error(f"[{error_info['severity'].upper()}] {error_info['message']}", exc_info=True)
        
        # UI显示
        if show_ui:
            st.error(error_info['message'])
            
            # 如果有恢复建议，也显示出来
            if error_info['suggestion']:
                st.info(f"💡 {error_info['suggestion']}")
        
        return default_return


class ErrorBoundary:
    """错误边界上下文管理器
    
    用法：
        with ErrorBoundary("内容分析"):
            result = analyzer.analyze(content)
    """
    
    def __init__(self, context: str, show_ui: bool = True):
        self.context = context
        self.show_ui = show_ui
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error = exc_val
            handle_error(exc_val, self.context, self.show_ui)
            return True  # 吞掉异常
        return False


def show_success(message: str):
    """显示成功消息"""
    st.success(f"✅ {message}")


def show_info(message: str):
    """显示信息消息"""
    st.info(f"ℹ️ {message}")


def show_warning(message: str):
    """显示警告消息"""
    st.warning(f"⚠️ {message}")
