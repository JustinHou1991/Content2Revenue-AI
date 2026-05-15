"""
导出模块 - 支持 Excel 和 PDF 报告生成

TODO: 以下字段名需要与各分析器的实际输出对齐（当前使用 .get() 已做容错，不会报错但可能取不到值）:
  - _write_matches_sheet: needs_match_score / budget_match_score / timing_match_score
    (match_engine 实际输出维度为 audience_fit / pain_point_relevance / stage_alignment /
     cta_appropriateness / emotion_resonance，通过 dimension_scores 子字典访问)
  - _write_strategies_sheet: strategy_type / priority / expected_conversion_rate /
    recommended_script / follow_up_timing / key_talking_points
    (strategy_advisor 实际输出为 content_strategy / distribution_strategy /
     conversion_prediction / a_b_test_suggestion 等子字典)
  - _write_content_sheet: hook_type / content_score / conversion_potential /
    target_audience / key_selling_points
    (content_analyzer 实际输出字段名基本一致，但 conversion_potential 可能不存在)
  - _write_leads_sheet: 各 profile_json 字段名需与 lead_analyzer 输出对齐
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# PDF 相关导入
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

logger = logging.getLogger(__name__)


# ===== Excel 导出功能 =====


def export_to_excel(
    data: Dict[str, Any],
    filename: str,
    include_content: bool = True,
    include_leads: bool = True,
    include_matches: bool = True,
    include_strategies: bool = True,
) -> str:
    """
    导出分析结果为 Excel 文件

    Args:
        data: 包含各类分析数据的字典
        filename: 输出文件名（不含扩展名）
        include_content: 是否包含内容分析 sheet
        include_leads: 是否包含线索分析 sheet
        include_matches: 是否包含匹配结果 sheet
        include_strategies: 是否包含策略建议 sheet

    Returns:
        生成的文件路径
    """
    output_path = f"{filename}.xlsx"

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # 内容分析 Sheet
        if include_content and "content_analyses" in data:
            _write_content_sheet(writer, data["content_analyses"])

        # 线索分析 Sheet
        if include_leads and "lead_analyses" in data:
            _write_leads_sheet(writer, data["lead_analyses"])

        # 匹配结果 Sheet
        if include_matches and "match_results" in data:
            _write_matches_sheet(writer, data["match_results"])

        # 策略建议 Sheet
        if include_strategies and "strategies" in data:
            _write_strategies_sheet(writer, data["strategies"])

        # 汇总信息 Sheet
        _write_summary_sheet(writer, data)

    logger.info(f"Excel 导出完成: {output_path}")
    return output_path


def _write_content_sheet(writer: pd.ExcelWriter, contents: List[Dict]) -> None:
    """写入内容分析数据"""
    rows = []
    for item in contents:
        analysis = item.get("analysis_json", {})
        row = {
            "内容ID": item.get("id", ""),
            "创建时间": item.get("created_at", ""),
            "模型": item.get("model", ""),
            "钩子类型": analysis.get("hook_type", ""),
            "内容评分": analysis.get("content_score", ""),
            "转化潜力": analysis.get("conversion_potential", ""),
            "目标受众": ", ".join(analysis.get("target_audience", [])),
            "关键卖点": ", ".join(analysis.get("key_selling_points", [])),
            "内容摘要": (
                str(item.get("raw_text", ""))[:200] + "..."
                if len(str(item.get("raw_text", ""))) > 200
                else str(item.get("raw_text", ""))
            ),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name="内容分析", index=False)
    _format_worksheet(writer.sheets["内容分析"], df)


def _write_leads_sheet(writer: pd.ExcelWriter, leads: List[Dict]) -> None:
    """写入线索分析数据"""
    rows = []
    for item in leads:
        profile = item.get("profile_json", {})
        raw_data = item.get("raw_data_json", {})
        row = {
            "线索ID": item.get("id", ""),
            "创建时间": item.get("created_at", ""),
            "模型": item.get("model", ""),
            "公司名称": profile.get("company_name", ""),
            "行业": profile.get("industry", ""),
            "公司规模": profile.get("company_size", ""),
            "业务阶段": profile.get("business_stage", ""),
            "决策权": profile.get("decision_authority", ""),
            "预算范围": profile.get("budget_range", ""),
            "紧急程度": profile.get("urgency_level", ""),
            "匹配优先级": profile.get("match_priority", ""),
            "联系人": raw_data.get("contact_name", ""),
            "联系方式": raw_data.get("contact_info", ""),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name="线索分析", index=False)
    _format_worksheet(writer.sheets["线索分析"], df)


def _write_matches_sheet(writer: pd.ExcelWriter, matches: List[Dict]) -> None:
    """写入匹配结果数据"""
    rows = []
    for item in matches:
        match_result = item.get("match_result_json", {})
        content_snapshot = item.get("content_snapshot_json", {})
        lead_snapshot = item.get("lead_snapshot_json", {})
        dim_scores = match_result.get("dimension_scores", {})

        row = {
            "匹配ID": item.get("id", ""),
            "内容ID": item.get("content_id", ""),
            "线索ID": item.get("lead_id", ""),
            "创建时间": item.get("created_at", ""),
            "模型": item.get("model", ""),
            "匹配度评分": match_result.get("overall_score", ""),
            "匹配等级": match_result.get("match_level", ""),
            "内容标题": (
                content_snapshot.get("title", "")[:50] if content_snapshot else ""
            ),
            "公司名称": lead_snapshot.get("company_name", "") if lead_snapshot else "",
            "受众匹配": dim_scores.get("audience_fit", ""),
            "痛点相关": dim_scores.get("pain_point_relevance", ""),
            "阶段对齐": dim_scores.get("stage_alignment", ""),
            "CTA适当": dim_scores.get("cta_appropriateness", ""),
            "情感共鸣": dim_scores.get("emotion_resonance", ""),
            "匹配理由": str(match_result.get("match_reason", ""))[:200],
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name="匹配结果", index=False)
    _format_worksheet(writer.sheets["匹配结果"], df)


def _write_strategies_sheet(writer: pd.ExcelWriter, strategies: List[Dict]) -> None:
    """写入策略建议数据"""
    rows = []
    for item in strategies:
        strategy = item.get("strategy_json", {})
        cs = strategy.get("content_strategy", {})
        ds = strategy.get("distribution_strategy", {})
        cp = strategy.get("conversion_prediction", {})
        ab = strategy.get("a_b_test_suggestion", {})
        row = {
            "策略ID": item.get("id", ""),
            "匹配ID": item.get("match_id", ""),
            "内容ID": item.get("content_id", ""),
            "线索ID": item.get("lead_id", ""),
            "创建时间": item.get("created_at", ""),
            "模型": item.get("model", ""),
            "推荐Hook": cs.get("recommended_hook", ""),
            "推荐结构": cs.get("recommended_structure", ""),
            "语气指导": cs.get("tone_guidance", ""),
            "最佳发布时间": ds.get("best_timing", ""),
            "渠道建议": ds.get("channel_suggestion", ""),
            "预估转化率": cp.get("estimated_conversion_rate", ""),
            "置信度": cp.get("confidence_level", ""),
            "A/B方案A": ab.get("variant_a", ""),
            "A/B方案B": ab.get("variant_b", ""),
            "预估影响": strategy.get("estimated_impact", ""),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_excel(writer, sheet_name="策略建议", index=False)
    _format_worksheet(writer.sheets["策略建议"], df)


def _write_summary_sheet(writer: pd.ExcelWriter, data: Dict[str, Any]) -> None:
    """写入汇总信息"""
    summary_data = {
        "指标": [
            "导出时间",
            "内容分析数量",
            "线索分析数量",
            "匹配结果数量",
            "策略建议数量",
        ],
        "数值": [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            len(data.get("content_analyses", [])),
            len(data.get("lead_analyses", [])),
            len(data.get("match_results", [])),
            len(data.get("strategies", [])),
        ],
    }
    df = pd.DataFrame(summary_data)
    df.to_excel(writer, sheet_name="数据汇总", index=False)
    _format_worksheet(writer.sheets["数据汇总"], df)


def _format_worksheet(worksheet, df: pd.DataFrame) -> None:
    """格式化工作表样式"""
    # 定义样式
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_alignment = Alignment(vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # 设置表头样式
    for cell in worksheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # 设置数据行样式和列宽
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter

        for cell in column:
            cell.alignment = cell_alignment
            cell.border = thin_border
            try:
                if cell.value:
                    cell_length = len(str(cell.value))
                    if cell_length > max_length:
                        max_length = cell_length
            except Exception:
                pass

        # 自动调整列宽（限制最大宽度）
        adjusted_width = min(max_length + 2, 50)
        worksheet.column_dimensions[column_letter].width = adjusted_width

    # 冻结首行
    worksheet.freeze_panes = "A2"


# ===== PDF 报告功能 =====


class PDFReportGenerator:
    """PDF 报告生成器"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._register_fonts()
        self._setup_custom_styles()

    def _register_fonts(self):
        """注册中文字体"""
        # 尝试注册常见中文字体
        font_paths = [
            # Linux 系统字体
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # macOS 字体
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            # Windows 字体
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ]

        self.font_name = "Helvetica"
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_name = "ChineseFont"
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    self.font_name = font_name
                    logger.info(f"成功注册字体: {font_path}")
                    break
                except Exception as e:
                    logger.warning(f"字体注册失败 {font_path}: {e}")
                    continue

    def _setup_custom_styles(self):
        """设置自定义样式"""
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Heading1"],
            fontName=self.font_name,
            fontSize=24,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=30,
            alignment=TA_CENTER,
        )

        self.heading_style = ParagraphStyle(
            "CustomHeading",
            parent=self.styles["Heading2"],
            fontName=self.font_name,
            fontSize=16,
            textColor=colors.HexColor("#16213e"),
            spaceAfter=12,
            spaceBefore=12,
        )

        self.subheading_style = ParagraphStyle(
            "CustomSubHeading",
            parent=self.styles["Heading3"],
            fontName=self.font_name,
            fontSize=13,
            textColor=colors.HexColor("#0f3460"),
            spaceAfter=8,
            spaceBefore=8,
        )

        self.normal_style = ParagraphStyle(
            "CustomNormal",
            parent=self.styles["Normal"],
            fontName=self.font_name,
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
        )

        self.info_style = ParagraphStyle(
            "InfoStyle",
            parent=self.styles["Normal"],
            fontName=self.font_name,
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER,
        )

    def generate_report(
        self,
        match_result: Dict[str, Any],
        strategy: Dict[str, Any],
        output_path: Optional[str] = None,
    ) -> str:
        """
        生成匹配策略 PDF 报告

        Args:
            match_result: 匹配结果数据
            strategy: 策略建议数据
            output_path: 输出文件路径，默认自动生成

        Returns:
            生成的文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"match_strategy_report_{timestamp}.pdf"

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        story = []

        # 封面
        self._add_cover_page(story, match_result)

        # 匹配分析详情
        self._add_match_analysis(story, match_result)

        # 策略建议
        self._add_strategy_section(story, strategy)

        # 执行计划
        self._add_action_plan(story, strategy)

        # 页脚信息
        self._add_footer(story)

        doc.build(story)
        logger.info(f"PDF 报告生成完成: {output_path}")
        return output_path

    def _add_cover_page(self, story: List, match_result: Dict[str, Any]):
        """添加封面"""
        # 标题
        story.append(Spacer(1, 3 * cm))
        story.append(Paragraph("Content2Revenue AI", self.title_style))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("内容-线索匹配策略报告", self.title_style))
        story.append(Spacer(1, 2 * cm))

        # 匹配概览
        match_data = match_result.get("match_result", {})
        overall_score = match_data.get("overall_score", 0)

        # 评分展示
        score_color = self._get_score_color(overall_score)
        score_style = ParagraphStyle(
            "ScoreStyle",
            fontName=self.font_name,
            fontSize=48,
            textColor=score_color,
            alignment=TA_CENTER,
        )
        story.append(Paragraph(f"{overall_score}", score_style))
        story.append(Spacer(1, 0.3 * cm))

        level_style = ParagraphStyle(
            "LevelStyle",
            fontName=self.font_name,
            fontSize=14,
            textColor=colors.grey,
            alignment=TA_CENTER,
        )
        match_level = match_data.get("match_level", "未知")
        story.append(Paragraph(f"匹配等级: {match_level}", level_style))
        story.append(Spacer(1, 2 * cm))

        # 基本信息
        content_snapshot = match_result.get("content_snapshot") or {}
        lead_snapshot = match_result.get("lead_snapshot") or {}

        info_data = [
            ["内容标题", str(content_snapshot.get("title", "N/A"))[:50]],
            ["目标公司", str(lead_snapshot.get("company_name", "N/A"))],
            ["生成时间", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ]

        info_table = Table(info_data, colWidths=[4 * cm, 10 * cm])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(info_table)
        story.append(PageBreak())

    def _add_match_analysis(self, story: List, match_result: Dict[str, Any]):
        """添加匹配分析详情"""
        story.append(Paragraph("匹配度分析", self.heading_style))
        story.append(Spacer(1, 0.3 * cm))

        match_data = match_result.get("match_result", {})

        dim_scores = match_data.get("dimension_scores", {})
        dimensions = [
            ("受众匹配度", dim_scores.get("audience_fit", 0)),
            ("痛点相关性", dim_scores.get("pain_point_relevance", 0)),
            ("阶段对齐度", dim_scores.get("stage_alignment", 0)),
            ("CTA适当性", dim_scores.get("cta_appropriateness", 0)),
            ("情感共鸣度", dim_scores.get("emotion_resonance", 0)),
        ]

        dim_data = [["维度", "评分", "评级"]]
        for name, score in dimensions:
            rating = self._get_rating_label(score)
            dim_data.append([name, f"{score}", rating])

        dim_table = Table(dim_data, colWidths=[5 * cm, 3 * cm, 4 * cm])
        dim_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(dim_table)
        story.append(Spacer(1, 0.5 * cm))

        # 匹配理由
        story.append(Paragraph("匹配分析", self.subheading_style))
        reasoning = match_data.get("match_reason", "暂无分析")
        story.append(Paragraph(str(reasoning), self.normal_style))
        story.append(Spacer(1, 0.5 * cm))

        # 风险提示
        risks = match_data.get("risk_factors", [])
        if risks:
            story.append(Paragraph("风险提示", self.subheading_style))
            for risk in risks:
                story.append(Paragraph(f"• {risk}", self.normal_style))
            story.append(Spacer(1, 0.3 * cm))

        story.append(PageBreak())

    def _add_strategy_section(self, story: List, strategy: Dict[str, Any]):
        """添加策略建议部分"""
        story.append(Paragraph("转化策略建议", self.heading_style))
        story.append(Spacer(1, 0.3 * cm))

        strategy_data = strategy.get("strategy", {})

        # 策略概览
        overview_data = [
            ["策略类型", str(strategy_data.get("strategy_type", "N/A"))],
            ["优先级", str(strategy_data.get("priority", "N/A"))],
            ["预期转化率", f"{strategy_data.get('expected_conversion_rate', 0)}%"],
            ["建议跟进时机", str(strategy_data.get("follow_up_timing", "N/A"))],
        ]

        overview_table = Table(overview_data, colWidths=[4 * cm, 10 * cm])
        overview_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f4f8")),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(overview_table)
        story.append(Spacer(1, 0.5 * cm))

        # 关键切入点
        story.append(Paragraph("关键切入点", self.subheading_style))
        talking_points = strategy_data.get("key_talking_points", [])
        for point in talking_points:
            story.append(Paragraph(f"• {point}", self.normal_style))
        story.append(Spacer(1, 0.5 * cm))

        # 推荐话术
        story.append(Paragraph("推荐话术", self.subheading_style))
        script = strategy_data.get("recommended_script", "暂无推荐话术")
        script_style = ParagraphStyle(
            "ScriptStyle",
            parent=self.normal_style,
            backColor=colors.HexColor("#f5f5f5"),
            borderPadding=10,
            leftIndent=10,
            rightIndent=10,
        )
        story.append(Paragraph(str(script), script_style))
        story.append(Spacer(1, 0.5 * cm))

        # 异议处理
        objections = strategy_data.get("objection_handling", [])
        if objections:
            story.append(Paragraph("异议处理建议", self.subheading_style))
            for obj in objections:
                concern = obj.get("concern", "")
                response = obj.get("response", "")
                story.append(
                    Paragraph(f"<b>客户疑虑:</b> {concern}", self.normal_style)
                )
                story.append(
                    Paragraph(f"<b>应对策略:</b> {response}", self.normal_style)
                )
                story.append(Spacer(1, 0.2 * cm))

        story.append(PageBreak())

    def _add_action_plan(self, story: List, strategy: Dict[str, Any]):
        """添加执行计划"""
        story.append(Paragraph("执行计划", self.heading_style))
        story.append(Spacer(1, 0.3 * cm))

        strategy_data = strategy.get("strategy", {})

        # 行动步骤
        steps = strategy_data.get("action_steps", [])
        if steps:
            step_data = [["步骤", "行动内容", "建议时间"]]
            for i, step in enumerate(steps, 1):
                action = step.get("action", "")
                timing = step.get("timing", "")
                step_data.append([str(i), action, timing])

            step_table = Table(step_data, colWidths=[2 * cm, 9 * cm, 3 * cm])
            step_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (0, -1), "CENTER"),
                        ("ALIGN", (1, 0), (1, -1), "LEFT"),
                        ("ALIGN", (2, 0), (2, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(step_table)
        else:
            story.append(Paragraph("暂无具体行动步骤", self.normal_style))

        story.append(Spacer(1, 0.5 * cm))

        # 成功指标
        story.append(Paragraph("成功指标", self.subheading_style))
        success_metrics = strategy_data.get("success_metrics", [])
        for metric in success_metrics:
            story.append(Paragraph(f"• {metric}", self.normal_style))

    def _add_footer(self, story: List):
        """添加页脚信息"""
        story.append(Spacer(1, 2 * cm))
        story.append(
            Paragraph(
                f"本报告由 Content2Revenue AI 生成于 {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
                self.info_style,
            )
        )
        story.append(
            Paragraph("报告内容仅供参考，具体执行请结合实际情况调整", self.info_style)
        )

    def _get_score_color(self, score: float) -> colors.Color:
        """根据分数返回颜色"""
        if score >= 80:
            return colors.HexColor("#28a745")
        elif score >= 60:
            return colors.HexColor("#ffc107")
        else:
            return colors.HexColor("#dc3545")

    def _get_rating_label(self, score: float) -> str:
        """根据分数返回评级标签"""
        if score >= 80:
            return "优秀"
        elif score >= 60:
            return "良好"
        elif score >= 40:
            return "一般"
        else:
            return "需改进"


def generate_pdf_report(
    match_result: Dict[str, Any],
    strategy: Dict[str, Any],
    output_path: Optional[str] = None,
) -> str:
    """
    生成匹配策略 PDF 报告的便捷函数

    Args:
        match_result: 匹配结果数据
        strategy: 策略建议数据
        output_path: 输出文件路径

    Returns:
        生成的文件路径
    """
    generator = PDFReportGenerator()
    return generator.generate_report(match_result, strategy, output_path)


# ===== 便捷导出函数 =====


def export_match_strategy_to_pdf(
    match_result: Dict[str, Any],
    strategy: Dict[str, Any],
    filename: Optional[str] = None,
) -> str:
    """
    导出匹配策略为 PDF

    Args:
        match_result: 匹配结果
        strategy: 策略建议
        filename: 文件名（不含扩展名）

    Returns:
        生成的文件路径
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"strategy_report_{timestamp}"

    output_path = f"{filename}.pdf"
    return generate_pdf_report(match_result, strategy, output_path)


def export_analyses_to_excel(
    db_instance, filename: Optional[str] = None, limit: int = 1000
) -> str:
    """
    从数据库导出所有分析数据为 Excel

    Args:
        db_instance: Database 实例
        filename: 输出文件名（不含扩展名）
        limit: 每种类型最大导出数量

    Returns:
        生成的文件路径
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"c2r_export_{timestamp}"

    data = {
        "content_analyses": db_instance.get_all_content_analyses(limit),
        "lead_analyses": db_instance.get_all_lead_analyses(limit),
        "match_results": db_instance.get_all_match_results(limit),
        "strategies": db_instance.get_all_strategy_advices(limit),
    }

    return export_to_excel(data, filename)


# ===== 使用示例 =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 测试数据
    test_match_result = {
        "match_id": "match-001",
        "match_result": {
            "overall_score": 85,
            "match_level": "高度匹配",
            "needs_match_score": 90,
            "budget_match_score": 80,
            "timing_match_score": 85,
            "match_reason": "该线索与内容高度匹配，客户明确表达了对CRM系统的需求...",
            "risk_factors": ["预算审批周期较长", "决策链条复杂"],
        },
        "content_snapshot": {
            "content_id": "content-001",
            "title": "CRM系统选型指南",
        },
        "lead_snapshot": {
            "lead_id": "lead-001",
            "company_name": "杭州某某科技有限公司",
        },
        "model": "deepseek-chat",
        "created_at": datetime.now().isoformat(),
    }

    test_strategy = {
        "strategy_id": "strategy-001",
        "match_id": "match-001",
        "strategy": {
            "strategy_type": "价值导向型",
            "priority": "高",
            "expected_conversion_rate": 35,
            "follow_up_timing": "24小时内",
            "key_talking_points": [
                "强调ROI提升数据",
                "展示同行业成功案例",
                "提供免费试用机会",
            ],
            "recommended_script": "您好，注意到贵公司正在寻找CRM解决方案...",
            "objection_handling": [
                {"concern": "价格太高", "response": "可以从长期ROI角度分析成本收益"},
            ],
            "action_steps": [
                {"action": "发送产品资料", "timing": "立即"},
                {"action": "安排产品演示", "timing": "本周内"},
            ],
            "success_metrics": ["获得试用申请", "安排决策人会议"],
        },
        "model": "deepseek-chat",
        "created_at": datetime.now().isoformat(),
    }

    # 测试 PDF 生成
    pdf_path = generate_pdf_report(test_match_result, test_strategy, "test_report.pdf")
    print(f"PDF 报告已生成: {pdf_path}")

    # 测试 Excel 导出
    test_data = {
        "content_analyses": [
            {
                "id": "content-001",
                "created_at": datetime.now().isoformat(),
                "model": "deepseek-chat",
                "analysis_json": {
                    "hook_type": "痛点反问型",
                    "content_score": 8.5,
                    "conversion_potential": "高",
                    "target_audience": ["中小企业主", "销售总监"],
                    "key_selling_points": ["效率提升", "成本降低"],
                },
                "raw_text": "这是一段测试内容...",
            }
        ],
        "lead_analyses": [
            {
                "id": "lead-001",
                "created_at": datetime.now().isoformat(),
                "model": "deepseek-chat",
                "profile_json": {
                    "company_name": "杭州某某科技",
                    "industry": "SaaS",
                    "company_size": "50-100人",
                    "business_stage": "成长期",
                    "decision_authority": "高",
                    "budget_range": "10-50万",
                    "urgency_level": "高",
                    "match_priority": "A级",
                },
                "raw_data_json": {
                    "contact_name": "张总",
                    "contact_info": "138****8888",
                },
            }
        ],
        "match_results": [test_match_result],
        "strategies": [test_strategy],
    }

    excel_path = export_to_excel(test_data, "test_export")
    print(f"Excel 文件已生成: {excel_path}")
