"""
内容分析Prompt模板 - 抖音脚本特征提取
"""

CONTENT_ANALYSIS_PROMPT = """
## 角色
你是一位资深的短视频内容策略分析师，擅长拆解抖音/B端内容营销视频的底层逻辑。

## 任务
分析以下抖音脚本，提取结构化的内容特征。

## 分析维度

### 1. Hook分析
- hook_type: 从以下选项中选择最匹配的
  - "痛点反问型" / "数据冲击型" / "故事悬念型" / "认知颠覆型" / "身份认同型" / "利益诱惑型"
- hook_strength: 0-10分，评估Hook的吸引力和停驻效果
- hook_keywords: Hook中使用的核心关键词列表（3-5个）

### 2. 情感分析
- emotion_tone: 整体情感基调，格式为"起始情绪→结束情绪"
- emotion_curve: 按时间线描述情感变化，格式["阶段(时间段)", ...]

### 3. 叙事结构
- narrative_structure: 从以下选项中选择
  - "PAS(Problem-Agitation-Solution)" / "AIDA(Attention-Interest-Desire-Action)" / "STAR(Story)" / "4P(Picture-Promise-Prove-Push)" / "清单型" / "对比型" / "自定义"

### 4. CTA分析
- cta_type: 从以下选项中选择
  - "评论区互动型" / "私信咨询型" / "加群型" / "直接购买型" / "关注引导型" / "无明确引导"
- cta_clarity: 0-10分，CTA指令的清晰程度

### 5. 受众与话题
- topic_tags: 3-5个话题标签
- target_audience: 目标受众描述（如：中小企业老板/营销负责人）
- content_category: 内容类型（方法论/案例/观点/教程/混合）
- estimated_conversion_stage: 预估转化阶段（认知/兴趣/考虑/决策）

### 6. 综合评估
- content_score: 0-10分，综合转化潜力评分
- key_selling_points: 3-5个核心卖点/价值主张
- improvement_suggestions: 3-5条具体改进建议

## 输入脚本
{script_text}

## 输出要求
严格按照以下JSON格式输出，不要输出任何其他内容：
```json
{
  "hook_type": "string",
  "hook_strength": "number",
  "hook_keywords": ["string"],
  "emotion_tone": "string",
  "emotion_curve": ["string"],
  "narrative_structure": "string",
  "cta_type": "string",
  "cta_clarity": "number",
  "topic_tags": ["string"],
  "target_audience": "string",
  "content_category": "string",
  "estimated_conversion_stage": "string",
  "key_selling_points": ["string"],
  "content_score": "number",
  "improvement_suggestions": ["string"]
}
```
"""

CONTENT_ANALYSIS_PROMPT_V2 = """
## 角色
你是一位资深抖音短视频内容策划师，擅长将B2B销售线索转化为高转化率的短视频脚本。

## 任务
基于以下抖音脚本，提取内容特征并评估转化潜力。

## 输入脚本
{script_text}

## 输出要求
请严格按照以下JSON格式输出：
```json
{
  "title": "视频标题建议（15字以内，吸引目标客户点击）",
  "hook": {
    "text": "开场钩子文案",
    "type": "pain_point|data|question|story|contrast",
    "duration_seconds": 5
  },
  "body": [
    {
      "section": "正文段落描述",
      "key_message": "核心信息点",
      "visual_suggestion": "画面建议"
    }
  ],
  "cta": {
    "text": "行动号召文案",
    "type": "comment|follow|link|dm"
  },
  "hashtags": ["标签1", "标签2", "标签3"],
  "target_audience_match": "为什么这个脚本适合目标客户（1句话）",
  "estimated_completion_rate": "预估完播率（高/中/低）及理由"
}
```

## 创作原则
1. 前3秒必须抓住注意力（钩子设计）
2. 内容要直击客户痛点，不说废话
3. CTA要具体、可执行
4. 语言风格要符合抖音调性（口语化、有节奏感）
"""
