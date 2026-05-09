"""表单组件 - 统一的表单元素"""
import streamlit as st
import pandas as pd
import threading
from typing import Optional, Callable, Any, List, Dict, Tuple


def render_file_uploader(
    label: str,
    file_type: str = "csv",
    max_size_mb: int = 10,
    help_text: str = None,
    on_upload: Optional[Callable[[pd.DataFrame], None]] = None
) -> Optional[pd.DataFrame]:
    """渲染文件上传组件

    Args:
        label: 上传组件标签
        file_type: 文件类型
        max_size_mb: 最大文件大小(MB)
        help_text: 帮助文本
        on_upload: 上传成功后的回调函数

    Returns:
        上传的DataFrame或None
    """
    uploaded = st.file_uploader(
        label,
        type=[file_type],
        help=help_text
    )

    if uploaded is None:
        return None

    if uploaded.size > max_size_mb * 1024 * 1024:
        st.error(f"文件大小超过 {max_size_mb}MB 限制")
        return None

    try:
        df = pd.read_csv(uploaded)
        if on_upload:
            on_upload(df)
        return df
    except Exception as e:
        st.error(f"文件读取失败: {e}")
        return None


def render_text_area(
    label: str,
    placeholder: str = "",
    height: int = 200,
    max_chars: Optional[int] = None,
    help_text: str = None,
    key: Optional[str] = None
) -> str:
    """渲染大文本输入区

    Args:
        label: 标签
        placeholder: 占位符文本
        height: 高度(像素)
        max_chars: 最大字符数
        help_text: 帮助文本
        key: 组件key

    Returns:
        输入的文本
    """
    text = st.text_area(
        label,
        placeholder=placeholder,
        height=height,
        max_chars=max_chars,
        help=help_text,
        key=key
    )

    if max_chars:
        char_count = len(text)
        st.caption(f"{char_count}/{max_chars} 字符")

    return text


def render_action_buttons(
    primary_label: str,
    secondary_label: Optional[str] = None,
    primary_disabled: bool = False,
    secondary_disabled: bool = False,
    primary_key: Optional[str] = None,
    secondary_key: Optional[str] = None
) -> Tuple[bool, Optional[bool]]:
    """渲染操作按钮组

    Args:
        primary_label: 主按钮标签
        secondary_label: 次按钮标签(可选)
        primary_disabled: 主按钮是否禁用
        secondary_disabled: 次按钮是否禁用
        primary_key: 主按钮key
        secondary_key: 次按钮key

    Returns:
        (主按钮是否点击, 次按钮是否点击)
    """
    if secondary_label:
        col1, col2 = st.columns([1, 1])
        with col1:
            primary = st.button(
                primary_label,
                type="primary",
                disabled=primary_disabled,
                use_container_width=True,
                key=primary_key
            )
        with col2:
            secondary = st.button(
                secondary_label,
                disabled=secondary_disabled,
                use_container_width=True,
                key=secondary_key
            )
        return primary, secondary
    else:
        primary = st.button(
            primary_label,
            type="primary",
            disabled=primary_disabled,
            use_container_width=True,
            key=primary_key
        )
        return primary, None


def render_lead_form() -> Dict[str, Any]:
    """渲染线索录入表单

    Returns:
        表单数据字典
    """
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("联系人姓名", placeholder="张总")
        company = st.text_input("公司名称", placeholder="XX教育科技")
        industry = st.text_input("所属行业", placeholder="教育培训")
        title = st.text_input("职位/角色", placeholder="创始人/总监")

    with col2:
        source = st.selectbox(
            "线索来源",
            ["抖音私信", "抖音评论", "官网", "转介绍", "展会", "其他"]
        )
        company_size = st.selectbox(
            "公司规模",
            ["1-10人", "10-50人", "50-200人", "200-500人", "500+人"]
        )
        intent_level = st.selectbox("初步意向", ["高", "中", "低", "未知"])

    conversation = st.text_area(
        "对话记录 / 需求描述",
        height=120,
        placeholder="例：看了你们的视频，我们公司目前获客成本太高了，想了解一下你们的方案...",
    )
    remark = st.text_area("备注", height=60, placeholder="其他补充信息...")

    return {
        "name": name,
        "company": company,
        "industry": industry,
        "title": title,
        "source": source,
        "company_size": company_size,
        "intent_level": intent_level,
        "conversation": conversation,
        "remark": remark,
    }


def render_batch_progress(
    total: int,
    current: int,
    prefix: str = "正在处理",
    show_cancel: bool = True
) -> Tuple[Optional[Any], bool]:
    """渲染批量处理进度条和取消按钮

    Args:
        total: 总数
        current: 当前进度
        prefix: 进度文本前缀
        show_cancel: 是否显示取消按钮

    Returns:
        (进度条对象, 是否取消)
    """
    progress_container = st.container()
    cancel_event = threading.Event()

    with progress_container:
        if show_cancel:
            col1, col2 = st.columns([4, 1])
            with col1:
                progress_bar = st.progress(
                    current / total if total > 0 else 0,
                    text=f"{prefix}... ({current}/{total})"
                )
            with col2:
                cancel_btn = st.button(
                    "取消分析",
                    type="secondary",
                    use_container_width=True
                )
                if cancel_btn:
                    cancel_event.set()
            return progress_bar, cancel_event.is_set()
        else:
            progress_bar = st.progress(
                current / total if total > 0 else 0,
                text=f"{prefix}... ({current}/{total})"
            )
            return progress_bar, False


def render_form_row(
    fields: List[Dict[str, Any]],
    columns: int = 2
) -> Dict[str, Any]:
    """渲染表单行

    Args:
        fields: 字段配置列表，每个字段包含type, label, options等
        columns: 列数

    Returns:
        字段值字典
    """
    cols = st.columns(columns)
    values = {}

    for idx, field in enumerate(fields):
        with cols[idx % columns]:
            field_type = field.get("type", "text")
            label = field.get("label", "")
            key = field.get("key", f"field_{idx}")

            if field_type == "text":
                values[key] = st.text_input(
                    label,
                    value=field.get("default", ""),
                    placeholder=field.get("placeholder", "")
                )
            elif field_type == "select":
                values[key] = st.selectbox(
                    label,
                    options=field.get("options", []),
                    index=field.get("default_index", 0)
                )
            elif field_type == "textarea":
                values[key] = st.text_area(
                    label,
                    value=field.get("default", ""),
                    height=field.get("height", 100)
                )
            elif field_type == "number":
                values[key] = st.number_input(
                    label,
                    min_value=field.get("min", 0),
                    max_value=field.get("max", 100),
                    value=field.get("default", 0)
                )

    return values


def render_search_filter(
    placeholder: str = "搜索...",
    on_search: Optional[Callable[[str], None]] = None
) -> str:
    """渲染搜索过滤器

    Args:
        placeholder: 占位符文本
        on_search: 搜索回调

    Returns:
        搜索关键词
    """
    search = st.text_input(
        "",
        placeholder=placeholder,
        label_visibility="collapsed"
    )

    if search and on_search:
        on_search(search)

    return search


def render_select_with_label(
    label: str,
    options: List[str],
    default_index: int = 0,
    help_text: str = None,
    key: Optional[str] = None
) -> str:
    """渲染带标签的选择框

    Args:
        label: 标签
        options: 选项列表
        default_index: 默认选中索引
        help_text: 帮助文本
        key: 组件key

    Returns:
        选中的值
    """
    return st.selectbox(
        label,
        options=options,
        index=default_index,
        help=help_text,
        key=key
    )
