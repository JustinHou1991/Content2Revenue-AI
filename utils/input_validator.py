"""输入验证器 - 防止注入攻击和恶意输入"""
import re
import html
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """输入验证器"""

    # 危险模式（仅保留XSS相关，移除SQL关键字检查）
    # 注意：SQLite使用参数化查询，本身就防SQL注入
    # SQL关键字检查会误伤正常中文输入如"选择一个方案"、"删除旧数据"
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',  # JS 协议
        r'on\w+\s*=',  # 事件处理器
    ]

    # 最大长度限制
    MAX_TEXT_LENGTH = 10000
    MAX_LIST_LENGTH = 100
    MAX_DICT_DEPTH = 5

    @classmethod
    def sanitize_text(cls, text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
        """清洗文本输入"""
        if not isinstance(text, str):
            text = str(text)

        # 检查长度
        if len(text) > max_length:
            logger.warning(f"输入文本过长 ({len(text)} > {max_length})，已截断")
            text = text[:max_length]

        # 检查危险模式
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                logger.warning(f"检测到危险模式: {pattern}")
                text = re.sub(pattern, '[REMOVED]', text, flags=re.IGNORECASE | re.DOTALL)

        # HTML 转义（不转义引号，避免破坏数据库存储内容）
        text = html.escape(text, quote=False)

        return text

    @classmethod
    def validate_json(cls, data: Dict, max_depth: int = MAX_DICT_DEPTH) -> Dict:
        """验证 JSON 数据"""
        def check_depth(obj, current_depth: int) -> bool:
            if current_depth > max_depth:
                return False
            if isinstance(obj, dict):
                return all(check_depth(v, current_depth + 1) for v in obj.values())
            if isinstance(obj, list):
                return all(check_depth(item, current_depth + 1) for item in obj)
            return True

        if not check_depth(data, 0):
            raise ValueError(f"JSON 嵌套深度超过 {max_depth} 层")

        return data

    @classmethod
    def validate_csv_data(cls, df: Any, max_rows: int = 10000) -> Any:
        """验证 CSV 数据"""
        import pandas as pd

        if not isinstance(df, pd.DataFrame):
            raise ValueError("输入必须是 DataFrame")

        if len(df) > max_rows:
            logger.warning(f"CSV 行数过多 ({len(df)} > {max_rows})，已截断")
            df = df.head(max_rows)

        # 清洗字符串列
        for col in df.select_dtypes(include=['object', 'string']).columns:
            df[col] = df[col].apply(lambda x: cls.sanitize_text(str(x)) if pd.notna(x) else x)

        return df

    @classmethod
    def check_prompt_injection(cls, text: str) -> tuple[bool, str]:
        """检查 Prompt 注入攻击"""
        injection_patterns = [
            r'忽略.*指令',
            r'忽略.*提示',
            r'ignore.*instruction',
            r'ignore.*prompt',
            r'你.*现在.*是',
            r'you are now',
            r'系统.*提示',
            r'system.*prompt',
        ]

        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True, f"检测到可能的 Prompt 注入: {pattern}"

        return False, ""


# 便捷函数
def sanitize_input(data: Any) -> Any:
    """通用输入清洗"""
    if isinstance(data, str):
        return InputValidator.sanitize_text(data)
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize_input(item) for item in data]
    return data
