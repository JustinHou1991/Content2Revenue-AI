"""ROI计算器页面 - 帮助用户计算使用C2R后的投资回报"""
import streamlit as st
from datetime import datetime
from typing import Dict, Any

from ui.base_page import BasePage
from ui.components import callout


class ROICalculatorPage(BasePage):
    """ROI计算器页面"""

    def __init__(self):
        super().__init__(
            title="💰 ROI计算器",
            icon="💰",
            description="计算使用Content2Revenue后的投资回报",
        )

    def _render_content(self):
        """渲染页面内容"""
        st.markdown("""
        ### 使用Content2Revenue能帮你多赚多少钱？
        
        输入你的业务数据，计算优化后的预期收益。
        """)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 当前业务数据")
            
            monthly_leads = st.number_input(
                "月均线索量（条）",
                min_value=1,
                max_value=10000,
                value=50,
                help="每月获取的线索数量"
            )
            
            current_conversion = st.slider(
                "当前转化率（%）",
                min_value=0.1,
                max_value=50.0,
                value=8.0,
                step=0.1,
                help="线索到成交的转化率"
            )
            
            avg_deal_value = st.number_input(
                "客单价（元）",
                min_value=100,
                max_value=1000000,
                value=5000,
                step=100,
                help="平均每单成交金额"
            )
            
            c2r_monthly_cost = st.number_input(
                "C2R月费（元）",
                min_value=0,
                max_value=100000,
                value=1500,
                step=100,
                help="使用Content2Revenue的月度成本"
            )

        with col2:
            st.subheader("🎯 优化预期")
            
            # 根据匹配度预测转化率提升
            st.markdown("**匹配度与转化率提升关系**")
            st.caption("基于历史数据分析，匹配度每提升1分，转化率约提升0.5%")
            
            current_match_score = st.slider(
                "当前平均匹配度",
                min_value=1.0,
                max_value=10.0,
                value=5.0,
                step=0.1,
                help="使用C2R前的内容-线索匹配度"
            )
            
            expected_match_score = st.slider(
                "预期匹配度（使用C2R后）",
                min_value=1.0,
                max_value=10.0,
                value=7.5,
                step=0.1,
                help="使用C2R优化后的预期匹配度"
            )

        # 计算ROI
        if st.button("🚀 计算投资回报", type="primary", use_container_width=True):
            self._calculate_roi(
                monthly_leads,
                current_conversion,
                avg_deal_value,
                c2r_monthly_cost,
                current_match_score,
                expected_match_score
            )

    def _calculate_roi(
        self,
        monthly_leads: int,
        current_conversion: float,
        avg_deal_value: float,
        c2r_cost: float,
        current_score: float,
        expected_score: float
    ):
        """计算并展示ROI"""
        
        # 计算转化率提升
        match_improvement = expected_score - current_score
        conversion_lift = match_improvement * 0.5  # 每提升1分匹配度，转化率提升0.5%
        new_conversion = min(current_conversion + conversion_lift, 50.0)
        
        # 计算收入
        current_monthly_revenue = monthly_leads * (current_conversion / 100) * avg_deal_value
        new_monthly_revenue = monthly_leads * (new_conversion / 100) * avg_deal_value
        monthly_gain = new_monthly_revenue - current_monthly_revenue
        
        # 年度数据
        yearly_gain = monthly_gain * 12
        yearly_cost = c2r_cost * 12
        net_yearly_gain = yearly_gain - yearly_cost
        
        # ROI计算
        roi_percentage = (yearly_gain / yearly_cost) * 100 if yearly_cost > 0 else 0
        payback_months = c2r_cost / monthly_gain if monthly_gain > 0 else float('inf')
        
        # 展示结果
        st.divider()
        st.subheader("📈 计算结果")
        
        # 关键指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "当前月收入",
                f"¥{current_monthly_revenue:,.0f}",
                help="基于当前转化率和客单价"
            )
        
        with col2:
            st.metric(
                "优化后月收入",
                f"¥{new_monthly_revenue:,.0f}",
                f"+¥{monthly_gain:,.0f}",
                help="使用C2R优化后的预期收入"
            )
        
        with col3:
            st.metric(
                "年增收",
                f"¥{yearly_gain:,.0f}",
                help="12个月的累计增收"
            )
        
        with col4:
            st.metric(
                "投资回报率",
                f"{roi_percentage:.0f}%",
                help="年增收 / C2R年费"
            )
        
        # 详细分析
        st.divider()
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 💡 关键洞察")
            
            insights = []
            
            if match_improvement >= 2:
                insights.append(f"✅ 匹配度从{current_score:.1f}提升到{expected_score:.1f}，是显著改进")
            
            if conversion_lift >= 1:
                insights.append(f"✅ 转化率预计提升{conversion_lift:.1f}个百分点")
            
            if roi_percentage >= 300:
                insights.append(f"🚀 ROI高达{roi_percentage:.0f}%，每投入1元回报{roi_percentage/100:.1f}元")
            elif roi_percentage >= 100:
                insights.append(f"📈 ROI为{roi_percentage:.0f}%，投资回报良好")
            else:
                insights.append(f"⚠️ ROI为{roi_percentage:.0f}%，建议优化使用策略")
            
            if payback_months <= 3:
                insights.append(f"💰 回本周期仅{payback_months:.1f}个月，风险极低")
            elif payback_months <= 6:
                insights.append(f"💰 回本周期{payback_months:.1f}个月，风险可控")
            
            for insight in insights:
                st.write(insight)
        
        with col_right:
            st.markdown("#### 📋 建议行动")
            
            if roi_percentage >= 300:
                st.success("""
                **强烈推荐立即使用**
                
                1. 开通C2R完整版
                2. 导入历史内容和线索数据
                3. 运行批量匹配分析
                4. 根据策略建议优化内容
                
                预期3个月内看到明显效果
                """)
            elif roi_percentage >= 100:
                st.info("""
                **建议试用**
                
                1. 先使用免费版体验
                2. 分析5-10条核心内容
                3. 验证匹配度提升效果
                4. 效果满意后升级完整版
                """)
            else:
                st.warning("""
                **建议先优化业务基础**
                
                当前数据可能不适合立即使用C2R：
                - 检查线索质量是否达标
                - 优化现有转化流程
                - 提升客单价或线索量
                - 业务稳定后再考虑使用
                """)
        
        # 导出报告
        st.divider()
        report_data = f"""
# Content2Revenue ROI分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 输入数据
- 月均线索量: {monthly_leads} 条
- 当前转化率: {current_conversion}%
- 客单价: ¥{avg_deal_value:,.0f}
- C2R月费: ¥{c2r_cost:,.0f}
- 当前匹配度: {current_score:.1f}/10
- 预期匹配度: {expected_score:.1f}/10

## 计算结果
- 转化率提升: {conversion_lift:.1f}%
- 当前月收入: ¥{current_monthly_revenue:,.0f}
- 优化后月收入: ¥{new_monthly_revenue:,.0f}
- 月增收: ¥{monthly_gain:,.0f}
- 年增收: ¥{yearly_gain:,.0f}
- 投资回报率: {roi_percentage:.0f}%
- 回本周期: {payback_months:.1f} 个月

## 结论
{"强烈推荐使用" if roi_percentage >= 300 else "建议试用" if roi_percentage >= 100 else "建议先优化业务基础"}
"""
        
        st.download_button(
            label="📥 下载ROI分析报告",
            data=report_data,
            file_name=f"C2R_ROI_Report_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )


def render_roi_calculator():
    """便捷函数"""
    page = ROICalculatorPage()
    page.render()
