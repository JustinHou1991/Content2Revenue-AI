"""
ScoringModel 集成测试 - 验证内容长度评分逻辑和完整评分流程
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.scoring_model import (
    ContentScoringModel,
    ContentFeatures,
    ScoreResult,
    score_content_quick,
    get_content_grade,
)


class TestShortContentLengthBonus:
    """测试短内容（< 2000 字符）获得 length_bonus"""

    def test_short_content_in_optimal_range(self, db):
        """内容长度在最优范围（300-800）内应获得 +0.10 加分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=500,  # 在最优范围内
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        # 验证结构分数包含长度加分
        structure_factors = [f for f in result.factors if "结构" in f and "长度" in f]
        assert len(structure_factors) >= 1
        assert any("加分" in f for f in structure_factors)

        # 结构分数应高于基础分
        base_structure_score = 0.88  # "问题-方案-行动" 的基准分
        assert result.structure_score > base_structure_score * 10

    def test_short_content_below_min(self, db):
        """内容长度低于最小值（100）应获得减分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=50,  # 低于 LENGTH_MIN=100
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        # 验证结构分数包含长度减分
        structure_factors = [f for f in result.factors if "结构" in f and "过短" in f]
        assert len(structure_factors) >= 1
        assert any("减分" in f for f in structure_factors)

    def test_short_content_acceptable_range(self, db):
        """内容长度在可接受范围（100-300 或 800-2000）应获得 +0.05 加分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=200,  # 在可接受范围内（100-300）
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        # 验证结构分数包含长度加分
        structure_factors = [f for f in result.factors if "结构" in f and "长度" in f]
        assert len(structure_factors) >= 1
        assert any("加分" in f for f in structure_factors)

    def test_content_length_1500(self, db):
        """内容长度 1500（在可接受范围 800-2000）应获得 +0.05 加分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=1500,
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        structure_factors = [f for f in result.factors if "结构" in f and "长度" in f]
        assert len(structure_factors) >= 1
        assert any("可接受" in f and "加分" in f for f in structure_factors)


class TestLongContentLengthPenalty:
    """测试长内容（> 2000 字符）获得 length_penalty"""

    def test_long_content_penalty(self, db):
        """内容长度超过 2000 应获得减分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=3000,  # 超过 LENGTH_MAX=2000
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        # 验证结构分数包含长度减分
        structure_factors = [f for f in result.factors if "结构" in f and "过长" in f]
        assert len(structure_factors) >= 1
        assert any("减分" in f for f in structure_factors)

    def test_very_long_content_penalty(self, db):
        """非常长的内容（5000字符）应获得减分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=5000,
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        structure_factors = [f for f in result.factors if "结构" in f and "过长" in f]
        assert len(structure_factors) >= 1

        # 长内容应产生改进建议
        length_recs = [r for r in result.recommendations if "较长" in r or "精简" in r]
        assert len(length_recs) >= 1


class TestBoundaryContentLength:
    """测试边界值（恰好 2000 字符）"""

    def test_exactly_2000_characters(self, db):
        """恰好 2000 字符不应获得减分（2000 是 LENGTH_MAX，不包含等于）"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=2000,  # 恰好等于 LENGTH_MAX
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        # 2000 不大于 2000，不应触发过长减分
        structure_factors = [f for f in result.factors if "结构" in f and "长度" in f]
        assert len(structure_factors) >= 1
        # 不应有 "过长" 相关的减分
        assert not any("过长" in f and "减分" in f for f in structure_factors)

    def test_just_above_2000_characters(self, db):
        """2001 字符应获得减分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=2001,  # 刚超过 LENGTH_MAX
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        structure_factors = [f for f in result.factors if "结构" in f and "过长" in f]
        assert len(structure_factors) >= 1
        assert any("减分" in f for f in structure_factors)

    def test_exactly_100_characters(self, db):
        """恰好 100 字符（LENGTH_MIN 边界）"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=100,  # 恰好等于 LENGTH_MIN
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        # 100 不小于 100，不应触发过短减分
        structure_factors = [f for f in result.factors if "结构" in f]
        assert not any("过短" in f for f in structure_factors)

    def test_exactly_300_characters(self, db):
        """恰好 300 字符（最优范围下界）"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=300,  # 恰好等于 LENGTH_OPTIMAL_RANGE[0]
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        structure_factors = [f for f in result.factors if "结构" in f and "最佳范围" in f]
        assert len(structure_factors) >= 1

    def test_exactly_800_characters(self, db):
        """恰好 800 字符（最优范围上界）"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=800,  # 恰好等于 LENGTH_OPTIMAL_RANGE[1]
            structure_type="问题-方案-行动",
        )
        result = model.score_content(features)

        structure_factors = [f for f in result.factors if "结构" in f and "最佳范围" in f]
        assert len(structure_factors) >= 1


class TestFullScoringPipeline:
    """测试完整的评分流程"""

    def test_full_features_scoring(self, db):
        """所有特征完整的评分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=600,
            emotion_tone="紧迫感,信任感",
            structure_type="问题-方案-行动",
            industry="教育培训",
        )
        result = model.score_content(features)

        # 验证返回类型
        assert isinstance(result, ScoreResult)
        assert isinstance(result.overall_score, float)
        assert isinstance(result.factors, list)
        assert isinstance(result.recommendations, list)

        # 验证分数范围
        assert 0 <= result.overall_score <= 10
        assert 0 <= result.hook_score <= 10
        assert 0 <= result.cta_score <= 10
        assert 0 <= result.structure_score <= 10
        assert 0 <= result.confidence <= 1.0

        # 高质量内容应获得较高分数
        assert result.overall_score >= 7.0

        # 验证置信度（4个特征都提供，置信度应较高）
        assert result.confidence >= 0.8

    def test_minimal_features_scoring(self, db):
        """最小特征评分（只提供 hook_type）"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(hook_type="痛点反问型")
        result = model.score_content(features)

        assert isinstance(result, ScoreResult)
        assert 0 <= result.overall_score <= 10

        # 最小特征的置信度应较低
        assert result.confidence < 0.8

    def test_no_features_scoring(self, db):
        """无特征评分"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures()
        result = model.score_content(features)

        assert isinstance(result, ScoreResult)
        assert 0 <= result.overall_score <= 10

        # 应有改进建议
        assert len(result.recommendations) >= 1

    def test_batch_scoring(self, db):
        """批量评分"""
        model = ContentScoringModel(db=db)
        contents = [
            {"hook_type": "痛点反问型", "content_length": 500},
            {"hook_type": "故事引入型", "content_length": 1500},
            {"hook_type": "直接陈述型", "content_length": 3000},
        ]
        results = model.batch_score(contents)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, ScoreResult)
            assert 0 <= result.overall_score <= 10

        # 高质量内容分数应高于低质量内容
        assert results[0].overall_score > results[2].overall_score

    def test_predict_conversion_rate(self, db):
        """转化率预测"""
        model = ContentScoringModel(db=db)
        features = ContentFeatures(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=600,
            structure_type="问题-方案-行动",
        )
        prediction = model.predict_conversion_rate(features, industry="教育培训")

        assert "predicted_conversion_rate" in prediction
        assert "confidence_interval" in prediction
        assert "confidence" in prediction
        assert "score_breakdown" in prediction
        assert 0 <= prediction["predicted_conversion_rate"] <= 100

    def test_score_content_quick_function(self):
        """快速评分便捷函数"""
        result = score_content_quick(
            hook_type="痛点反问型",
            cta_type="立即行动型",
            content_length=600,
        )

        assert "overall_score" in result
        assert "hook_score" in result
        assert "cta_score" in result
        assert "structure_score" in result
        assert "confidence" in result
        assert "factors" in result
        assert "recommendations" in result
        assert "predicted_conversion" in result
        assert "confidence_interval" in result
        assert 0 <= result["overall_score"] <= 10

    def test_get_content_grade(self):
        """等级划分函数"""
        assert get_content_grade(9.5) == "S级 (卓越)"
        assert get_content_grade(8.0) == "A级 (优秀)"
        assert get_content_grade(7.0) == "B级 (良好)"
        assert get_content_grade(6.0) == "C级 (合格)"
        assert get_content_grade(5.0) == "D级 (需改进)"
        assert get_content_grade(3.0) == "E级 (不合格)"

    def test_feature_importance(self, db):
        """特征重要性"""
        model = ContentScoringModel(db=db)
        importance = model.get_feature_importance()

        assert importance["hook_type"] == 0.30
        assert importance["cta_type"] == 0.25
        assert importance["structure_type"] == 0.25
        assert importance["emotion_tone"] == 0.20
        # 总和应为 1.0
        assert abs(sum(importance.values()) - 1.0) < 0.001


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
