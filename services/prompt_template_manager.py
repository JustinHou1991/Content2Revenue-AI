"""
LLM提示词模板管理系统

基于学习的最佳实践：
- 自适应提示词优化（Adaptive Prompts）
- 评估闭环（LLM-as-a-Judge）
- 版本控制和A/B测试支持

功能：
- 集中管理提示词模板
- 支持版本控制和回滚
- 收集使用反馈
- 分析提示词效果
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """提示词类型枚举"""
    CONTENT_ANALYSIS = "content_analysis"
    LEAD_ANALYSIS = "lead_analysis"
    MATCH = "match"
    STRATEGY = "strategy"


class FeedbackType(Enum):
    """反馈类型枚举"""
    POSITIVE = "positive"  # 用户满意
    NEUTRAL = "neutral"    # 中立
    NEGATIVE = "negative"  # 不满意


@dataclass
class PromptTemplate:
    """提示词模板"""
    name: str
    type: str
    version: str
    template: str
    description: str = ""
    variables: List[str] = None
    created_at: str = None
    updated_at: str = None
    is_active: bool = True
    usage_count: int = 0
    success_count: int = 0
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """从字典创建"""
        return cls(**data)
    
    def get_success_rate(self) -> float:
        """计算成功率"""
        if self.usage_count == 0:
            return 0.0
        return (self.success_count / self.usage_count) * 100


@dataclass
class PromptFeedback:
    """提示词反馈"""
    template_name: str
    template_version: str
    feedback_type: str
    rating: int  # 1-5 星
    comment: str = ""
    context: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class PromptTemplateManager:
    """提示词模板管理器（基于学习的最佳实践）"""
    
    # 默认提示词模板
    DEFAULT_TEMPLATES = {
        PromptType.CONTENT_ANALYSIS.value: PromptTemplate(
            name="content_analysis_v1",
            type=PromptType.CONTENT_ANALYSIS.value,
            version="1.0",
            template="""你是一位专业的抖音内容分析师。请分析以下抖音脚本，提取关键特征：

脚本内容：
{content}

请从以下维度进行分析：
1. Hook类型（痛点型、好奇型、冲突型等）
2. 情感基调（正面/负面/中性）
3. 叙事结构（起承转合）
4. CTA类型（引流型、转化型等）
5. 内容评分（1-10分）

以JSON格式输出分析结果。""",
            description="抖音脚本分析默认模板 v1.0",
            variables=["content"]
        ),
        PromptType.LEAD_ANALYSIS.value: PromptTemplate(
            name="lead_analysis_v1",
            type=PromptType.LEAD_ANALYSIS.value,
            version="1.0",
            template="""你是一位专业的B2B销售分析师。请分析以下销售线索，构建客户画像：

线索信息：
公司名称：{company}
行业：{industry}
痛点：{pain_points}
购买阶段：{stage}
对话记录：{conversation}

请从以下维度进行分析：
1. 客户画像（公司规模、决策链等）
2. 需求分析
3. 购买意向评分（1-10）
4. 线索等级（A/B/C/D）
5. 跟进建议

以JSON格式输出分析结果。""",
            description="销售线索分析默认模板 v1.0",
            variables=["company", "industry", "pain_points", "stage", "conversation"]
        ),
    }
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.feedback_history: List[PromptFeedback] = []
        self._load_default_templates()
    
    def _load_default_templates(self):
        """加载默认模板"""
        for template in self.DEFAULT_TEMPLATES.values():
            self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """获取指定模板"""
        return self.templates.get(name)
    
    def get_active_templates_by_type(self, prompt_type: PromptType) -> List[PromptTemplate]:
        """获取指定类型的所有活跃模板"""
        return [
            t for t in self.templates.values()
            if t.type == prompt_type.value and t.is_active
        ]
    
    def add_template(self, template: PromptTemplate) -> bool:
        """添加新模板"""
        try:
            self.templates[template.name] = template
            logger.info(f"添加提示词模板: {template.name}")
            return True
        except Exception as e:
            logger.error(f"添加模板失败: {e}")
            return False
    
    def update_template(self, name: str, **kwargs) -> bool:
        """更新模板"""
        if name not in self.templates:
            logger.warning(f"模板不存在: {name}")
            return False
        
        try:
            template = self.templates[name]
            for key, value in kwargs.items():
                if hasattr(template, key):
                    setattr(template, key, value)
            template.updated_at = datetime.now().isoformat()
            logger.info(f"更新提示词模板: {name}")
            return True
        except Exception as e:
            logger.error(f"更新模板失败: {e}")
            return False
    
    def increment_usage(self, name: str, success: bool = True):
        """增加使用计数"""
        if name in self.templates:
            self.templates[name].usage_count += 1
            if success:
                self.templates[name].success_count += 1
    
    def record_feedback(self, feedback: PromptFeedback):
        """记录反馈"""
        self.feedback_history.append(feedback)
        
        # 更新对应模板的统计
        template = self.get_template(feedback.template_name)
        if template:
            # 根据评分更新成功率
            if feedback.rating >= 4:
                template.success_count += 1
            template.usage_count += 1
    
    def get_feedback_stats(self, template_name: str) -> Dict[str, Any]:
        """获取模板的反馈统计"""
        feedbacks = [f for f in self.feedback_history if f.template_name == template_name]
        
        if not feedbacks:
            return {
                "total_feedbacks": 0,
                "avg_rating": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "recent_feedbacks": []
            }
        
        ratings = [f.rating for f in feedbacks]
        
        return {
            "total_feedbacks": len(feedbacks),
            "avg_rating": sum(ratings) / len(ratings),
            "positive_count": len([f for f in feedbacks if f.feedback_type == FeedbackType.POSITIVE.value]),
            "negative_count": len([f for f in feedbacks if f.feedback_type == FeedbackType.NEGATIVE.value]),
            "recent_feedbacks": feedbacks[-10:]  # 最近10条
        }
    
    def render_template(self, name: str, **kwargs) -> Optional[str]:
        """渲染提示词模板"""
        template = self.get_template(name)
        if not template:
            logger.warning(f"模板不存在: {name}")
            return None
        
        try:
            rendered = template.template.format(**kwargs)
            return rendered
        except KeyError as e:
            logger.error(f"模板变量缺失: {e}")
            return None
    
    def create_version(self, name: str, new_version: str) -> Optional[PromptTemplate]:
        """创建新版本的模板"""
        template = self.get_template(name)
        if not template:
            return None
        
        new_name = f"{template.name.rsplit('_v', 1)[0]}_v{new_version}"
        new_template = PromptTemplate(
            name=new_name,
            type=template.type,
            version=new_version,
            template=template.template,
            description=f"{template.description} (版本 {new_version})",
            variables=template.variables.copy()
        )
        
        self.add_template(new_template)
        return new_template
    
    def get_best_template(self, prompt_type: PromptType) -> Optional[PromptTemplate]:
        """获取成功率最高的模板"""
        templates = self.get_active_templates_by_type(prompt_type)
        if not templates:
            return None
        
        return max(templates, key=lambda t: t.get_success_rate())
    
    def export_templates(self) -> str:
        """导出所有模板为JSON"""
        return json.dumps([
            t.to_dict() for t in self.templates.values()
        ], ensure_ascii=False, indent=2)
    
    def import_templates(self, json_str: str) -> int:
        """从JSON导入模板"""
        try:
            data = json.loads(json_str)
            count = 0
            for item in data:
                template = PromptTemplate.from_dict(item)
                self.templates[template.name] = template
                count += 1
            return count
        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            return 0


# 全局单例实例
_prompt_manager = None

def get_prompt_manager() -> PromptTemplateManager:
    """获取全局提示词管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptTemplateManager()
    return _prompt_manager
