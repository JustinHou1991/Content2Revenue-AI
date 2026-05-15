"""行业基准对比服务

基于历史分析数据计算行业基准，用于内容分析的对比评估
"""
import json
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class BenchmarkService:
    """行业基准服务"""
    
    def __init__(self, db):
        """
        Args:
            db: Database实例
        """
        self.db = db
    
    def get_content_benchmark(
        self, 
        content_category: Optional[str] = None,
        min_samples: int = 5
    ) -> Dict[str, Any]:
        """获取内容分析的行业基准
        
        Args:
            content_category: 内容类型筛选（如"方法论"/"案例"/"教程"）
            min_samples: 最小样本数，低于此数返回空基准
            
        Returns:
            基准数据字典
        """
        # 获取所有内容分析
        analyses = self.db.get_all_content_analyses(limit=1000)
        
        if not analyses or len(analyses) < min_samples:
            return self._empty_benchmark()
        
        # 按内容类型筛选
        if content_category:
            analyses = [
                a for a in analyses 
                if a.get("analysis_json", {}).get("content_category") == content_category
            ]
        
        if len(analyses) < min_samples:
            return self._empty_benchmark()
        
        # 提取关键指标
        hook_strengths = []
        cta_clarities = []
        content_scores = []
        
        for analysis in analyses:
            json_data = analysis.get("analysis_json", {})
            if isinstance(json_data, str):
                try:
                    json_data = json.loads(json_data)
                except (json.JSONDecodeError, TypeError):
                    continue
            
            hook_strengths.append(self._safe_float(json_data.get("hook_strength")))
            cta_clarities.append(self._safe_float(json_data.get("cta_clarity")))
            content_scores.append(self._safe_float(json_data.get("content_score")))
        
        # 过滤无效值
        hook_strengths = [v for v in hook_strengths if v > 0]
        cta_clarities = [v for v in cta_clarities if v > 0]
        content_scores = [v for v in content_scores if v > 0]
        
        if not content_scores:
            return self._empty_benchmark()
        
        # 计算统计数据
        benchmark = {
            "sample_size": len(analyses),
            "content_category": content_category or "全部",
            "avg_hook_strength": round(statistics.mean(hook_strengths), 1) if hook_strengths else 5.0,
            "avg_cta_clarity": round(statistics.mean(cta_clarities), 1) if cta_clarities else 5.0,
            "avg_content_score": round(statistics.mean(content_scores), 1) if content_scores else 5.0,
            "median_content_score": round(statistics.median(content_scores), 1) if content_scores else 5.0,
            "p75_content_score": round(self._percentile(content_scores, 75), 1) if len(content_scores) >= 4 else 7.0,
            "p25_content_score": round(self._percentile(content_scores, 25), 1) if len(content_scores) >= 4 else 3.0,
        }
        
        logger.info(
            "计算内容基准: 类别=%s, 样本=%d, 平均分=%.1f",
            benchmark["content_category"],
            benchmark["sample_size"],
            benchmark["avg_content_score"]
        )
        
        return benchmark
    
    def calculate_percentile(
        self, 
        content_score: float,
        content_category: Optional[str] = None
    ) -> int:
        """计算内容评分在同类中的百分位
        
        Args:
            content_score: 当前内容评分
            content_category: 内容类型
            
        Returns:
            百分位数（0-100）
        """
        analyses = self.db.get_all_content_analyses(limit=1000)
        
        if content_category:
            analyses = [
                a for a in analyses 
                if a.get("analysis_json", {}).get("content_category") == content_category
            ]
        
        scores = []
        for analysis in analyses:
            json_data = analysis.get("analysis_json", {})
            if isinstance(json_data, str):
                try:
                    json_data = json.loads(json_data)
                except (json.JSONDecodeError, TypeError):
                    continue
            score = self._safe_float(json_data.get("content_score"))
            if score > 0:
                scores.append(score)
        
        if not scores:
            return 50
        
        # 计算百分位
        below_count = sum(1 for s in scores if s < content_score)
        return int((below_count / len(scores)) * 100)
    
    def compare_to_benchmark(
        self, 
        analysis_result: Dict[str, Any],
        content_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """将分析结果与基准对比
        
        Args:
            analysis_result: 内容分析结果
            content_category: 内容类型
            
        Returns:
            对比结果
        """
        benchmark = self.get_content_benchmark(content_category)
        
        if benchmark.get("sample_size", 0) < 5:
            # 样本不足，使用全部数据
            benchmark = self.get_content_benchmark(None)
        
        content_score = self._safe_float(analysis_result.get("content_score"))
        hook_strength = self._safe_float(analysis_result.get("hook_strength"))
        cta_clarity = self._safe_float(analysis_result.get("cta_clarity"))
        
        percentile = self.calculate_percentile(content_score, content_category)
        
        # 确定优于/低于平均的维度
        outperforms = []
        underperforms = []
        
        if hook_strength > benchmark.get("avg_hook_strength", 5.0):
            outperforms.append("hook_strength")
        elif hook_strength < benchmark.get("avg_hook_strength", 5.0) - 1:
            underperforms.append("hook_strength")
        
        if cta_clarity > benchmark.get("avg_cta_clarity", 5.0):
            outperforms.append("cta_clarity")
        elif cta_clarity < benchmark.get("avg_cta_clarity", 5.0) - 1:
            underperforms.append("cta_clarity")
        
        return {
            "industry_benchmark": benchmark,
            "percentile": percentile,
            "outperforms": outperforms,
            "underperforms": underperforms,
            "comparison_summary": self._generate_summary(
                content_score, percentile, outperforms, underperforms
            )
        }
    
    def _generate_summary(
        self, 
        content_score: float, 
        percentile: int,
        outperforms: List[str],
        underperforms: List[str]
    ) -> str:
        """生成对比总结"""
        if percentile >= 75:
            level = "优秀"
        elif percentile >= 50:
            level = "良好"
        elif percentile >= 25:
            level = "一般"
        else:
            level = "待改进"
        
        parts = [f"内容质量{level}，超过{percentile}%的同类内容"]
        
        if outperforms:
            dims = ", ".join(self._dim_name(d) for d in outperforms)
            parts.append(f"在{dims}方面表现突出")
        
        if underperforms:
            dims = ", ".join(self._dim_name(d) for d in underperforms)
            parts.append(f"建议重点优化{dims}")
        
        return "。".join(parts)
    
    def _dim_name(self, dim: str) -> str:
        """维度中文名"""
        names = {
            "hook_strength": "Hook吸引力",
            "cta_clarity": "CTA清晰度",
            "content_score": "综合评分",
        }
        return names.get(dim, dim)
    
    def _empty_benchmark(self) -> Dict[str, Any]:
        """返回空基准"""
        return {
            "sample_size": 0,
            "content_category": "未知",
            "avg_hook_strength": 5.0,
            "avg_cta_clarity": 5.0,
            "avg_content_score": 5.0,
            "median_content_score": 5.0,
            "p75_content_score": 7.0,
            "p25_content_score": 3.0,
        }
    
    def _safe_float(self, value: Any) -> float:
        """安全转换为float"""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]
