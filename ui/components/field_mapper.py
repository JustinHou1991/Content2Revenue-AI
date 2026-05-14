"""
字段映射 UI 组件 - Streamlit 交互式字段映射预览
"""

from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from utils.field_mapping import (
    FIELD_SYNONYMS,
    detect_columns,
    get_required_fields_for_analysis,
    validate_mapping_for_analysis,
)


def show_mapping_preview(
    mapping: Dict[str, str | None], df_columns: List[str]
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

    column_options = ["-- 未选择 --"] + list(df_columns)

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


def auto_map_and_preview(
    df: pd.DataFrame, analysis_type: str
) -> Dict[str, str | None]:
    """
    完整的字段映射流程：自动检测 -> 用户确认 -> 返回最终映射

    Args:
        df: 上传的CSV数据
        analysis_type: 分析类型（"content" 或 "lead"）

    Returns:
        用户确认后的映射字典，如果用户取消则返回None
    """
    auto_mapping = detect_columns(df.columns.tolist())

    st.markdown("---")
    final_mapping = show_mapping_preview(auto_mapping, df.columns.tolist())

    is_valid, missing_fields = validate_mapping_for_analysis(
        final_mapping, analysis_type
    )

    if not is_valid:
        st.error(f"❌ 缺少必需字段: {', '.join(missing_fields)}")
        st.info("💡 请在上方映射表中选择对应的CSV列")
        return None

    if st.button("✅ 确认映射并开始分析", type="primary", use_container_width=True):
        return final_mapping

    return None