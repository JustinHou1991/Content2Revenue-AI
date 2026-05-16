"""行业报告页面 - 自动生成行业内容营销趋势报告"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List

from ui.base_page import BasePage


class IndustryReportPage(BasePage):
    """行业报告页面"""

    def __init__(self):
        super().__init__(
            title="📊 行业报告",
            icon="📊",
            description="生成行业内容营销趋势分析报告",
        )

    def _render_content(self):
        """渲染页面内容"""
        if not self._check_initialization():
            return

        st.markdown("""
        ### 生成行业内容营销趋势报告
        
        基于您的历史数据分析，生成专业的行业报告。
        可用于内容营销、客户展示或销售支持。
        """)

        # 报告类型选择
        report_type = st.selectbox(
            "报告类型",
            options=[
                "内容营销趋势分析",
                "线索画像分布报告",
                "内容-线索匹配分析",
                "综合分析报告",
            ],
            help="选择要生成的报告类型"
        )

        # 时间范围
        col1, col2 = st.columns(2)
        with col1:
            days_range = st.selectbox(
                "分析时间范围",
                options=[7, 14, 30, 60, 90],
                format_func=lambda x: f"近{x}天",
                index=2,
                help="分析最近多少天的数据"
            )

        with col2:
            industry = st.selectbox(
                "行业筛选",
                options=["全部行业", "教育培训", "餐饮", "SaaS/软件", "装修", "零售", "医疗", "金融"],
                help="筛选特定行业的数据"
            )

        # 生成选项
        with st.expander("报告选项"):
            col1, col2 = st.columns(2)
            with col1:
                include_charts = st.checkbox("包含可视化图表", value=True)
                include_recommendations = st.checkbox("包含优化建议", value=True)
            with col2:
                include_competitors = st.checkbox("包含竞品分析", value=False)
                watermark = st.checkbox("添加水印", value=False)

        # 生成报告
        if st.button("📄 生成报告", type="primary", use_container_width=True):
            self._generate_report(
                report_type,
                days_range,
                industry,
                include_charts,
                include_recommendations,
                include_competitors,
                watermark
            )

    def _generate_report(
        self,
        report_type: str,
        days_range: int,
        industry: str,
        include_charts: bool,
        include_recommendations: bool,
        include_competitors: bool,
        watermark: bool
    ):
        """生成报告"""
        orchestrator = self._get_orchestrator()
        
        # 获取数据
        contents = orchestrator.db.get_all_content_analyses(limit=500)
        leads = orchestrator.db.get_all_lead_analyses(limit=500)
        matches = orchestrator.db.get_all_match_results(limit=500)

        # 筛选时间范围
        cutoff_date = (datetime.now() - timedelta(days=days_range)).isoformat()
        
        filtered_contents = [
            c for c in contents
            if c.get("created_at", "") >= cutoff_date
        ]
        filtered_leads = [
            l for l in leads
            if l.get("created_at", "") >= cutoff_date
        ]
        filtered_matches = [
            m for m in matches
            if m.get("created_at", "") >= cutoff_date
        ]

        if report_type == "内容营销趋势分析":
            report = self._generate_content_trend_report(
                filtered_contents, days_range, industry, include_charts, include_recommendations
            )
        elif report_type == "线索画像分布报告":
            report = self._generate_lead_distribution_report(
                filtered_leads, days_range, industry, include_charts
            )
        elif report_type == "内容-线索匹配分析":
            report = self._generate_match_analysis_report(
                filtered_contents, filtered_leads, filtered_matches, days_range, industry, include_recommendations
            )
        else:
            report = self._generate_comprehensive_report(
                filtered_contents, filtered_leads, filtered_matches, days_range, industry,
                include_charts, include_recommendations
            )

        # 添加水印
        if watermark:
            report += f"\n\n---\n*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Content2Revenue*\n"

        # 展示报告
        st.divider()
        st.subheader("📋 报告预览")
        st.markdown(report)

        # 下载按钮
        filename = f"行业报告_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        st.download_button(
            label="📥 下载报告",
            data=report,
            file_name=filename,
            mime="text/markdown",
            use_container_width=True
        )

    def _generate_content_trend_report(
        self,
        contents: List[Dict],
        days_range: int,
        industry: str,
        include_charts: bool,
        include_recommendations: bool
    ) -> str:
        """生成内容营销趋势报告"""
        import json
        import statistics
        
        # 分析内容数据
        hook_strengths = []
        cta_clarities = []
        content_scores = []
        categories = []
        hook_types = []
        
        for content in contents:
            json_data = content.get("analysis_json", {})
            if isinstance(json_data, str):
                try:
                    json_data = json.loads(json_data)
                except:
                    continue
            
            hook_strengths.append(float(json_data.get("hook_strength", 0) or 0))
            cta_clarities.append(float(json_data.get("cta_clarity", 0) or 0))
            content_scores.append(float(json_data.get("content_score", 0) or 0))
            if json_data.get("content_category"):
                categories.append(json_data["content_category"])
            if json_data.get("hook_type"):
                hook_types.append(json_data["hook_type"])
        
        # 计算统计数据
        avg_hook = statistics.mean(hook_strengths) if hook_strengths else 0
        avg_cta = statistics.mean(cta_clarities) if cta_clarities else 0
        avg_score = statistics.mean(content_scores) if content_scores else 0
        
        # 生成报告
        report = f"""# 内容营销趋势分析报告

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**分析时间范围**: 近{days_range}天  
**行业筛选**: {industry}

---

## 一、数据概览

| 指标 | 数值 |
|------|------|
| 分析内容数量 | {len(contents)} 条 |
| 平均Hook强度 | {avg_hook:.1f}/10 |
| 平均CTA清晰度 | {avg_cta:.1f}/10 |
| 平均内容评分 | {avg_score:.1f}/10 |

---

## 二、内容类型分布

"""
        
        # 内容类型统计
        if categories:
            from collections import Counter
            cat_counts = Counter(categories)
            for cat, count in cat_counts.most_common(5):
                pct = count / len(categories) * 100
                report += f"- **{cat}**: {count}条 ({pct:.1f}%)\n"
        
        report += "\n## 三、Hook类型分布\n\n"
        
        if hook_types:
            hook_counts = Counter(hook_types)
            for hook_type, count in hook_counts.most_common():
                pct = count / len(hook_types) * 100
                report += f"- **{hook_type}**: {count}条 ({pct:.1f}%)\n"
        
        if include_recommendations:
            report += "\n## 四、优化建议\n\n"
            
            if avg_hook < 6:
                report += "### Hook吸引力优化\n"
                report += "- 当前Hook平均强度偏低，建议：\n"
                report += "  1. 使用数据冲击型Hook（如'90%的老板都在犯这个错'）\n"
                report += "  2. 前3秒使用强对比或悬念\n"
                report += "  3. 避免平淡的开场白\n\n"
            
            if avg_cta < 6:
                report += "### CTA清晰度优化\n"
                report += "- 当前CTA不够清晰，建议：\n"
                report += "  1. 明确告诉用户下一步行动\n"
                report += "  2. 使用行动导向语言\n"
                report += "  3. 匹配线索购买阶段\n\n"
            
            if avg_score < 6:
                report += "### 综合内容质量\n"
                report += "- 内容评分有较大提升空间\n"
                report += "- 建议系统学习高评分内容的特征\n"
        
        return report

    def _generate_lead_distribution_report(
        self,
        leads: List[Dict],
        days_range: int,
        industry: str,
        include_charts: bool
    ) -> str:
        """生成线索画像分布报告"""
        import json
        import statistics
        
        # 分析线索数据
        intent_levels = []
        industries = []
        buying_stages = []
        lead_scores = []
        
        for lead in leads:
            profile = lead.get("profile_json", {})
            if isinstance(profile, str):
                try:
                    profile = json.loads(profile)
                except:
                    continue
            
            intent_levels.append(float(profile.get("intent_level", 5) or 5))
            industries.append(profile.get("industry", "未知"))
            buying_stages.append(profile.get("buying_stage", "未知"))
            lead_scores.append(float(profile.get("lead_score", 0) or 0))
        
        # 计算统计
        avg_intent = statistics.mean(intent_levels) if intent_levels else 0
        avg_score = statistics.mean(lead_scores) if lead_scores else 0
        
        # 生成报告
        report = f"""# 线索画像分布报告

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**分析时间范围**: 近{days_range}天  
**行业筛选**: {industry}

---

## 一、数据概览

| 指标 | 数值 |
|------|------|
| 线索总数 | {len(leads)} 条 |
| 平均意向度 | {avg_intent:.1f}/10 |
| 平均线索评分 | {avg_score:.1f}/100 |

---

## 二、行业分布

"""
        
        from collections import Counter
        if industries:
            ind_counts = Counter(industries)
            for ind, count in ind_counts.most_common(10):
                pct = count / len(industries) * 100
                report += f"- **{ind}**: {count}条 ({pct:.1f}%)\n"
        
        report += "\n## 三、购买阶段分布\n\n"
        
        if buying_stages:
            stage_counts = Counter(buying_stages)
            for stage, count in stage_counts.most_common():
                pct = count / len(buying_stages) * 100
                report += f"- **{stage}**: {count}条 ({pct:.1f}%)\n"
        
        report += "\n## 四、线索质量分布\n\n"
        
        high_quality = sum(1 for s in lead_scores if s >= 70)
        medium_quality = sum(1 for s in lead_scores if 40 <= s < 70)
        low_quality = sum(1 for s in lead_scores if s < 40)
        
        if leads:
            report += f"- **高质量线索**（≥70分）: {high_quality}条 ({high_quality/len(leads)*100:.1f}%)\n"
            report += f"- **中等质量线索**（40-69分）: {medium_quality}条 ({medium_quality/len(leads)*100:.1f}%)\n"
            report += f"- **低质量线索**（<40分）: {low_quality}条 ({low_quality/len(leads)*100:.1f}%)\n"
        
        return report

    def _generate_match_analysis_report(
        self,
        contents: List[Dict],
        leads: List[Dict],
        matches: List[Dict],
        days_range: int,
        industry: str,
        include_recommendations: bool
    ) -> str:
        """生成内容-线索匹配分析报告"""
        import json
        import statistics
        
        # 分析匹配数据
        match_scores = []
        dimension_scores = []
        
        for match in matches:
            json_data = match.get("match_result_json", {})
            if isinstance(json_data, str):
                try:
                    json_data = json.loads(json_data)
                except:
                    continue
            
            score = float(json_data.get("overall_score", 0) or 0)
            if score > 0:
                match_scores.append(score)
            
            dims = json_data.get("dimension_scores", {})
            if dims:
                dimension_scores.append(dims)
        
        # 计算统计
        avg_match = statistics.mean(match_scores) if match_scores else 0
        
        # 各维度平均
        dim_avgs = {}
        if dimension_scores:
            for dim in ["audience_fit", "pain_point_relevance", "stage_alignment", 
                       "cta_appropriateness", "emotion_resonance"]:
                vals = [d.get(dim, 0) for d in dimension_scores if d.get(dim)]
                if vals:
                    dim_avgs[dim] = statistics.mean(vals)
        
        # 生成报告
        report = f"""# 内容-线索匹配分析报告

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**分析时间范围**: 近{days_range}天  
**行业筛选**: {industry}

---

## 一、数据概览

| 指标 | 数值 |
|------|------|
| 匹配记录数 | {len(matches)} 条 |
| 平均匹配度 | {avg_match:.1f}/10 |
| 内容数量 | {len(contents)} 条 |
| 线索数量 | {len(leads)} 条 |

---

## 二、匹配度分布

"""
        
        if match_scores:
            excellent = sum(1 for s in match_scores if s >= 8)
            good = sum(1 for s in match_scores if 6 <= s < 8)
            medium = sum(1 for s in match_scores if 4 <= s < 6)
            poor = sum(1 for s in match_scores if s < 4)
            total = len(match_scores)
            
            report += f"- **优秀（≥8分）**: {excellent}条 ({excellent/total*100:.1f}%)\n"
            report += f"- **良好（6-8分）**: {good}条 ({good/total*100:.1f}%)\n"
            report += f"- **一般（4-6分）**: {medium}条 ({medium/total*100:.1f}%)\n"
            report += f"- **较差（<4分）**: {poor}条 ({poor/total*100:.1f}%)\n"
        
        report += "\n## 三、各维度表现\n\n"
        
        dim_names = {
            "audience_fit": "目标受众匹配",
            "pain_point_relevance": "痛点相关性",
            "stage_alignment": "阶段对齐",
            "cta_appropriateness": "CTA适当性",
            "emotion_resonance": "情感共鸣",
        }
        
        if dim_avgs:
            for dim, avg in sorted(dim_avgs.items(), key=lambda x: x[1]):
                name = dim_names.get(dim, dim)
                bar = "█" * int(avg) + "░" * (10 - int(avg))
                report += f"- **{name}**: {bar} {avg:.1f}\n"
        
        if include_recommendations:
            report += "\n## 四、优化建议\n\n"
            
            if dim_avgs:
                weakest = min(dim_avgs.items(), key=lambda x: x[1])
                dim_name = dim_names.get(weakest[0], weakest[0])
                report += f"### 重点改进: {dim_name}\n"
                report += f"当前表现: {weakest[1]:.1f}/10\n\n"
                
                if weakest[0] == "audience_fit":
                    report += "建议：\n"
                    report += "1. 明确内容的目标受众画像\n"
                    report += "2. 使用受众熟悉的语言和场景\n"
                    report += "3. 匹配受众的认知水平\n\n"
                elif weakest[0] == "cta_appropriateness":
                    report += "建议：\n"
                    report += "1. 根据线索购买阶段选择CTA类型\n"
                    report += "2. 决策期使用'预约演示'而非'发资料'\n"
                    report += "3. CTA要具体、明确\n\n"
        
        return report

    def _generate_comprehensive_report(
        self,
        contents: List[Dict],
        leads: List[Dict],
        matches: List[Dict],
        days_range: int,
        industry: str,
        include_charts: bool,
        include_recommendations: bool
    ) -> str:
        """生成综合分析报告"""
        # 组合多个报告
        report = f"""# 综合分析报告

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**分析时间范围**: 近{days_range}天  
**行业筛选**: {industry}

---

## 一、数据总览

| 类型 | 数量 |
|------|------|
| 内容分析 | {len(contents)} 条 |
| 线索分析 | {len(leads)} 条 |
| 匹配记录 | {len(matches)} 条 |

---

"""
        
        # 添加内容趋势
        if contents:
            report += "## 二、内容分析摘要\n\n"
            report += "详见「内容营销趋势分析报告」\n\n"
        
        # 添加线索分布
        if leads:
            report += "## 三、线索分布摘要\n\n"
            report += "详见「线索画像分布报告」\n\n"
        
        # 添加匹配分析
        if matches:
            report += "## 四、匹配分析摘要\n\n"
            report += "详见「内容-线索匹配分析报告」\n\n"
        
        if include_recommendations:
            report += "## 五、综合优化建议\n\n"
            report += "### 短期行动（1-2周）\n"
            report += "1. 分析现有高匹配度内容的共同特征\n"
            report += "2. 优化低匹配度内容的CTA\n"
            report += "3. 针对高频行业制作定向内容\n\n"
            
            report += "### 中期优化（1个月）\n"
            report += "1. 建立内容模板库\n"
            report += "2. 完善线索画像收集流程\n"
            report += "3. 定期分析匹配度趋势\n\n"
            
            report += "### 长期策略（3个月）\n"
            report += "1. 形成标准化内容生产流程\n"
            report += "2. 建立行业基准数据库\n"
            report += "3. 持续优化匹配算法\n"
        
        return report


def render_industry_report():
    """便捷函数"""
    page = IndustryReportPage()
    page.render()
