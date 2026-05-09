"""
智能字段映射模块 - 自动检测和映射CSV列名到标准字段
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st

# 字段映射字典：标准字段名 -> 可能的同义词列表
FIELD_SYNONYMS: Dict[str, List[str]] = {
    "脚本内容": [
        "完整脚本",
        "脚本",
        "内容",
        "文案",
        "正文",
        "text",
        "content",
        "script",
        "body",
    ],
    "标题": ["标题", "题目", "主题", "title", "heading", "headline"],
    "播放量": [
        "播放量",
        "播放",
        "views",
        "play_count",
        "view_count",
        "plays",
        "video_views",
    ],
    "点赞数": ["点赞数", "点赞", "likes", "like_count", "likes_count", "赞"],
    "公司名称": [
        "公司名称",
        "公司",
        "企业",
        "company",
        "company_name",
        "enterprise",
        "corp",
    ],
    "行业": ["行业", "领域", "industry", "sector", "field", "category"],
    "联系人": [
        "联系人",
        "姓名",
        "name",
        "contact",
        "contact_name",
        "person",
        "客户姓名",
    ],
    "需求描述": [
        "需求描述",
        "需求",
        "描述",
        "requirement",
        "description",
        "needs",
        "conversation",
        "对话记录",
    ],
}


# 反向映射：同义词 -> 标准字段名（用于快速查找）
def _build_reverse_mapping() -> Dict[str, str]:
    """构建反向映射字典"""
    reverse_map: Dict[str, str] = {}
    for standard_field, synonyms in FIELD_SYNONYMS.items():
        for synonym in synonyms:
            reverse_map[synonym.lower()] = standard_field
    return reverse_map


REVERSE_MAPPING = _build_reverse_mapping()


def detect_columns(df_columns: List[str]) -> Dict[str, Optional[str]]:
    """
    自动检测CSV列名对应的标准字段

    Args:
        df_columns: DataFrame的列名列表

    Returns:
        映射字典，键为标准字段名，值为匹配的原始列名（未匹配则为None）
    """
    mapping: Dict[str, Optional[str]] = {field: None for field in FIELD_SYNONYMS.keys()}
    matched_columns: set = set()

    for col in df_columns:
        col_lower = str(col).lower().strip()

        # 直接匹配
        if col_lower in REVERSE_MAPPING:
            standard_field = REVERSE_MAPPING[col_lower]
            if mapping[standard_field] is None:  # 优先保留第一个匹配
                mapping[standard_field] = col
                matched_columns.add(col)
            continue

        # 模糊匹配：检查是否包含关键词
        for synonym, standard_field in REVERSE_MAPPING.items():
            if synonym in col_lower or col_lower in synonym:
                if mapping[standard_field] is None:
                    mapping[standard_field] = col
                    matched_columns.add(col)
                break

    return mapping


def normalize_columns(
    df: pd.DataFrame, mapping: Optional[Dict[str, Optional[str]]] = None
) -> pd.DataFrame:
    """
    根据映射关系标准化DataFrame列名

    Args:
        df: 原始DataFrame
        mapping: 字段映射字典（如果为None则自动检测）

    Returns:
        标准化后的DataFrame（复制）
    """
    if mapping is None:
        mapping = detect_columns(df.columns.tolist())

    # 创建列名重命名映射
    rename_map: Dict[str, str] = {}
    for standard_field, original_col in mapping.items():
        if original_col is not None and original_col in df.columns:
            rename_map[original_col] = standard_field

    # 重命名列
    df_normalized = df.rename(columns=rename_map)

    return df_normalized


def show_mapping_preview(
    mapping: Dict[str, Optional[str]], df_columns: List[str]
) -> Dict[str, str]:
    """
    在Streamlit中显示字段映射预览，允许用户确认或手动调整

    Args:
        mapping: 自动检测的字段映射
        df_columns: 原始DataFrame的所有列名

    Returns:
        用户确认/调整后的映射字典（只包含已匹配的字段）
    """
    st.subheader("📋 字段映射预览")
    st.caption("系统已自动识别CSV列名与标准字段的对应关系，请确认或手动调整")

    # 准备选项列表（包含空选项表示未选择）
    column_options = ["-- 未选择 --"] + list(df_columns)

    # 创建两列布局
    col1, col2 = st.columns([1, 1])

    user_mapping: Dict[str, str] = {}

    with col1:
        st.markdown("**标准字段**")
        for standard_field in FIELD_SYNONYMS.keys():
            st.markdown(f"• {standard_field}")

    with col2:
        st.markdown("**对应CSV列**")
        for standard_field in FIELD_SYNONYMS.keys():
            current_value = mapping.get(standard_field)
            # 确定默认索引
            if current_value is not None and current_value in df_columns:
                default_index = df_columns.index(current_value) + 1
            else:
                default_index = 0

            selected = st.selectbox(
                label=f"映射_{standard_field}",
                options=column_options,
                index=default_index,
                label_visibility="collapsed",
                key=f"mapping_{standard_field}",
            )

            if selected != "-- 未选择 --":
                user_mapping[standard_field] = selected

    # 显示映射统计
    st.markdown("---")
    matched_count = len(user_mapping)
    total_count = len(FIELD_SYNONYMS)

    if matched_count == 0:
        st.warning(f"⚠️ 尚未匹配任何字段（共 {total_count} 个标准字段）")
    elif matched_count < total_count:
        st.info(f"ℹ️ 已匹配 {matched_count}/{total_count} 个字段")
    else:
        st.success(f"✅ 已匹配全部 {total_count} 个字段")

    return user_mapping


def get_required_fields_for_analysis(analysis_type: str) -> List[str]:
    """
    获取指定分析类型所需的必需字段

    Args:
        analysis_type: 分析类型，可选 "content"（内容分析）或 "lead"（线索分析）

    Returns:
        必需字段列表
    """
    if analysis_type == "content":
        return ["脚本内容"]
    elif analysis_type == "lead":
        return ["需求描述"]  # 线索分析至少需要一个描述字段
    else:
        return []


def validate_mapping_for_analysis(
    mapping: Dict[str, str], analysis_type: str
) -> Tuple[bool, List[str]]:
    """
    验证字段映射是否满足分析要求

    Args:
        mapping: 用户确认后的字段映射
        analysis_type: 分析类型

    Returns:
        (是否有效, 缺失的必需字段列表)
    """
    required_fields = get_required_fields_for_analysis(analysis_type)
    missing_fields = [field for field in required_fields if field not in mapping]
    return len(missing_fields) == 0, missing_fields


def get_field_suggestions(field_name: str) -> List[str]:
    """
    获取指定标准字段的建议同义词

    Args:
        field_name: 标准字段名

    Returns:
        同义词列表
    """
    return FIELD_SYNONYMS.get(field_name, [])


def auto_map_and_preview(
    df: pd.DataFrame, analysis_type: str
) -> Optional[Dict[str, str]]:
    """
    完整的字段映射流程：自动检测 -> 用户确认 -> 返回最终映射

    Args:
        df: 上传的CSV数据
        analysis_type: 分析类型（"content" 或 "lead"）

    Returns:
        用户确认后的映射字典，如果用户取消则返回None
    """
    # 自动检测映射
    auto_mapping = detect_columns(df.columns.tolist())

    # 显示映射预览并让用户调整
    st.markdown("---")
    final_mapping = show_mapping_preview(auto_mapping, df.columns.tolist())

    # 验证映射
    is_valid, missing_fields = validate_mapping_for_analysis(
        final_mapping, analysis_type
    )

    if not is_valid:
        st.error(f"❌ 缺少必需字段: {', '.join(missing_fields)}")
        st.info("💡 请在上方映射表中选择对应的CSV列")
        return None

    # 用户确认按钮
    if st.button("✅ 确认映射并开始分析", type="primary", use_container_width=True):
        return final_mapping

    return None


# ===== 使用示例 =====
if __name__ == "__main__":
    # 测试字段检测
    test_columns = ["title", "content", "views", "likes", "company_name"]
    result = detect_columns(test_columns)
    print("测试列名:", test_columns)
    print("检测结果:")
    for field, mapped in result.items():
        print(f"  {field}: {mapped}")

    # 测试DataFrame标准化
    test_data = {
        "title": ["标题1", "标题2"],
        "content": ["内容1", "内容2"],
        "views": [1000, 2000],
    }
    df = pd.DataFrame(test_data)
    df_normalized = normalize_columns(df)
    print("\n原始列名:", df.columns.tolist())
    print("标准化后列名:", df_normalized.columns.tolist())
