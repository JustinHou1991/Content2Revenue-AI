"""统一错误处理模块

提供项目统一的错误类型定义和处理函数
"""
import logging
import streamlit as st
from typing import Optional, Callable

logger = logging.getLogger(__name__)


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


def safe_execute(func: Callable, context: str = "", default_return=None, show_ui: bool = True):
    """安全执行包装器
    
    自动捕获异常并统一处理
    
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
        handle_error(e, context, show_ui)
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
