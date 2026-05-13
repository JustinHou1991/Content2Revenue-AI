"""一键演示页面 - 预置案例快速展示效果"""
import streamlit as st
from typing import Dict, Any

from ui.base_page import BasePage
from ui.components import callout


class DemoPage(BasePage):
    """一键演示页面"""

    # 预置演示案例
    DEMO_CASES = {
        "教育培训 - 高匹配度案例": {
            "content": {
                "script_text": """你是不是还在用传统方式招生？
                每天发传单、打电话，一个月下来成本5000块，才招来3个学生。
                我有个客户，用了我们的抖音招生方案，一个月只花了800块，招了47个学生。
                他是怎么做到的？
                第一步，把课程内容做成15秒的痛点视频；
                第二步，用评论区引导家长私信；
                第三步，私信自动发送试听链接。
                这套方案我已经整理成文档了，想要的家长在评论区扣"方案"，我发给你。""",
                "analysis": {
                    "hook_type": "痛点反问型",
                    "hook_strength": 8.5,
                    "emotion_tone": "焦虑→希望",
                    "cta_type": "评论区互动型",
                    "cta_clarity": 7.0,
                    "target_audience": "教育培训机构负责人",
                    "content_category": "案例",
                    "estimated_conversion_stage": "考虑",
                    "key_selling_points": ["低成本", "高效率", "可复制"],
                    "content_score": 8.0,
                }
            },
            "lead": {
                "conversation": "【最新互动记录】在抖音私信输入了手机号 | 【需求描述】我们是做少儿编程培训的，现在招生成本太高了，想了解抖音招生方案",
                "profile": {
                    "industry": "教育培训",
                    "company_stage": "成长期",
                    "role": "决策者",
                    "pain_points": ["招生成本高", "传统方式效果差"],
                    "buying_stage": "考虑期",
                    "urgency": "中",
                    "intent_level": 7,
                    "recommended_content_type": "案例型",
                    "recommended_cta": "私信咨询型",
                }
            },
            "expected_match_score": 8.5,
        },
        "餐饮连锁 - 中等匹配度案例": {
            "content": {
                "script_text": """90%的餐饮老板都在犯这个错误！
                开业第一天就搞全场5折，结果吸引来的全是薅羊毛的，活动一结束人就没了。
                正确的做法是什么？
                开业前7天，每天发3条预热视频，展示你的招牌菜制作过程；
                开业当天，推出"充500送100"的会员活动，锁定长期客户；
                开业后7天，邀请老客户发抖音打卡，送小菜一份。
                这套打法，我帮300+餐饮店验证过，平均3个月回本。
                想要详细方案的，点击主页链接，加我微信详聊。""",
                "analysis": {
                    "hook_type": "数据冲击型",
                    "hook_strength": 8.0,
                    "emotion_tone": "恐惧→希望",
                    "cta_type": "私信咨询型",
                    "cta_clarity": 6.5,
                    "target_audience": "餐饮店老板",
                    "content_category": "方法论",
                    "estimated_conversion_stage": "认知",
                    "key_selling_points": ["避免常见错误", "系统化方案", "已验证"],
                    "content_score": 7.5,
                }
            },
            "lead": {
                "conversation": "【最新互动记录】在抖音企业主页发起了通话 | 【需求描述】我们是一家新开的火锅店，位置有点偏，想知道怎么用抖音引流",
                "profile": {
                    "industry": "餐饮",
                    "company_stage": "初创期",
                    "role": "决策者",
                    "pain_points": ["位置偏", "客流少"],
                    "buying_stage": "认知期",
                    "urgency": "高",
                    "intent_level": 6,
                    "recommended_content_type": "教程型",
                    "recommended_cta": "关注引导型",
                }
            },
            "expected_match_score": 6.5,
        },
        "SaaS软件 - 低匹配度+优化建议案例": {
            "content": {
                "script_text": """评论区扣1，我发你资料。
                今天给大家分享一个CRM系统的使用技巧。
                很多销售每天忙得要死，但就是不出业绩。
                原因是什么？不会管理客户。
                我们的CRM系统可以帮你：
                自动记录客户跟进记录；
                智能提醒下次跟进时间；
                自动生成销售报表。
                用了这套系统，销售效率提升50%。
                想要的扣1，我发你资料。""",
                "analysis": {
                    "hook_type": "利益诱惑型",
                    "hook_strength": 5.0,
                    "emotion_tone": "平淡",
                    "cta_type": "评论区互动型",
                    "cta_clarity": 5.0,
                    "target_audience": "销售团队管理者",
                    "content_category": "教程",
                    "estimated_conversion_stage": "认知",
                    "key_selling_points": ["效率提升", "自动化"],
                    "content_score": 5.5,
                }
            },
            "lead": {
                "conversation": "【最新互动记录】在抖音私信输入了手机号 | 【需求描述】我们公司有100个销售，现在用的是Excel管理客户，经常漏跟进，想了解CRM系统",
                "profile": {
                    "industry": "SaaS/软件",
                    "company_stage": "成熟期",
                    "role": "决策者",
                    "pain_points": ["客户管理混乱", "跟进不及时", "效率低"],
                    "buying_stage": "决策期",
                    "urgency": "高",
                    "intent_level": 8,
                    "recommended_content_type": "案例型",
                    "recommended_cta": "私信咨询型",
                }
            },
            "expected_match_score": 4.5,
            "improvement_suggestions": [
                "Hook太弱：'评论区扣1'是低质量Hook，建议改为数据冲击型'100个销售团队，90%都在犯这个错'",
                "CTA不匹配：线索处于决策期，需要'预约演示'而非'发资料'",
                "缺少案例：决策期客户需要看到同行成功案例",
            ]
        },
    }

    def __init__(self):
        super().__init__(
            title="🎬 效果演示",
            icon="🎬",
            description="一键体验Content2Revenue的核心功能",
        )

    def _render_content(self):
        """渲染页面内容"""
        st.markdown("""
        ### 不用上传数据，立即体验效果
        
        选择下方预置案例，快速了解Content2Revenue如何分析内容、评估线索、计算匹配度。
        """)

        # 案例选择
        case_name = st.selectbox(
            "选择演示案例",
            options=list(self.DEMO_CASES.keys()),
            help="每个案例展示了不同的匹配场景"
        )

        if case_name:
            case_data = self.DEMO_CASES[case_name]
            self._render_demo_case(case_name, case_data)

    def _render_demo_case(self, case_name: str, case_data: Dict[str, Any]):
        """渲染单个演示案例"""
        
        st.divider()
        
        # 步骤1：内容分析
        with st.expander("📹 步骤1：内容分析", expanded=True):
            st.markdown("**脚本文案：**")
            st.text(case_data["content"]["script_text"])
            
            st.markdown("**分析结果：**")
            analysis = case_data["content"]["analysis"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Hook类型", analysis["hook_type"])
                st.metric("Hook强度", f"{analysis['hook_strength']}/10")
            with col2:
                st.metric("情绪基调", analysis["emotion_tone"])
                st.metric("CTA类型", analysis["cta_type"])
            with col3:
                st.metric("内容评分", f"{analysis['content_score']}/10")
                st.metric("转化阶段", analysis["estimated_conversion_stage"])
        
        # 步骤2：线索分析
        with st.expander("👤 步骤2：线索分析", expanded=True):
            st.markdown("**线索信息：**")
            st.text(case_data["lead"]["conversation"])
            
            st.markdown("**画像分析：**")
            profile = case_data["lead"]["profile"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**行业：** {profile['industry']}")
                st.write(f"**公司阶段：** {profile['company_stage']}")
            with col2:
                st.write(f"**购买阶段：** {profile['buying_stage']}")
                st.write(f"**意向度：** {profile['intent_level']}/10")
            with col3:
                st.write(f"**紧迫程度：** {profile['urgency']}")
                st.write(f"**决策角色：** {profile['role']}")
            
            st.write(f"**核心痛点：** {', '.join(profile['pain_points'])}")
        
        # 步骤3：匹配分析
        with st.expander("🔗 步骤3：匹配分析", expanded=True):
            match_score = case_data["expected_match_score"]
            
            # 匹配度可视化
            st.progress(match_score / 10, text=f"匹配度：{match_score}/10")
            
            # 匹配度解读
            if match_score >= 7:
                st.success(f"✅ **高匹配度（{match_score}/10）**：内容与线索需求高度契合，推荐立即跟进")
            elif match_score >= 5:
                st.info(f"ℹ️ **中等匹配度（{match_score}/10）**：有一定匹配度，可以跟进但需优化")
            else:
                st.warning(f"⚠️ **低匹配度（{match_score}/10）**：匹配度较低，建议优化内容或更换线索")
            
            # 优化建议
            if "improvement_suggestions" in case_data:
                st.markdown("**📝 优化建议：**")
                for suggestion in case_data["improvement_suggestions"]:
                    st.write(f"- {suggestion}")
        
        # 总结
        st.divider()
        st.subheader("💡 案例总结")
        
        if case_name == "教育培训 - 高匹配度案例":
            st.success("""
            **高匹配度案例特点：**
            - 内容Hook直击痛点（招生成本高）
            - 案例数据具体可信（800块招47个学生）
            - 线索处于考虑期，有明确需求
            - CTA与线索阶段匹配（评论区互动适合考虑期）
            """)
        elif case_name == "餐饮连锁 - 中等匹配度案例":
            st.info("""
            **中等匹配度案例特点：**
            - 内容质量高，Hook吸引力强
            - 但线索处于认知期，CTA过于直接
            - 建议：认知期线索更适合"关注引导"而非"私信咨询"
            """)
        else:
            st.warning("""
            **低匹配度案例特点：**
            - 内容Hook太弱（评论区扣1）
            - 线索处于决策期，但CTA是"发资料"而非"预约演示"
            - 缺少决策期客户需要的案例证明
            - **优化后匹配度可提升至7分以上**
            """)


def render_demo():
    """便捷函数"""
    page = DemoPage()
    page.render()
