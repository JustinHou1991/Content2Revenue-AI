"""
数据清洗模块单元测试
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.data_cleaner import LeadDataCleaner, ScriptDataCleaner


class TestLeadCleanerDedup:

    def test_lead_cleaner_dedup(self, sample_lead_df):
        """测试线索去重 - 根据手机号去重"""
        cleaner = LeadDataCleaner()
        cleaned = cleaner.clean(sample_lead_df)

        # 原始4条，重复手机号13800138000有2条，去重后应为3条
        assert len(cleaned) == 3
        # 确认保留的是第一条（keep='first'）
        phone_numbers = cleaned["手机号"].tolist()
        assert phone_numbers.count("13800138000") == 1

    def test_lead_cleaner_dedup_by_company(self):
        """测试线索去重 - 无手机号时按公司名去重"""
        import pandas as pd

        df = pd.DataFrame(
            {
                "公司名称": ["公司A", "公司B", "公司A"],
                "行业": ["SaaS", "教育", "SaaS"],
            }
        )
        cleaner = LeadDataCleaner()
        cleaned = cleaner.clean(df)
        assert len(cleaned) == 2


class TestLeadCleanerMissingValues:

    def test_lead_cleaner_missing_values(self, sample_lead_df):
        """测试缺失值处理"""
        cleaner = LeadDataCleaner()
        cleaned = cleaner.clean(sample_lead_df)

        # 需求描述中的 None 应被填充为空字符串
        assert cleaned["需求描述"].isna().sum() == 0
        # 来源中的 None 应被填充为 "未知"
        assert cleaned["来源"].isna().sum() == 0
        assert "未知" in cleaned["来源"].values

    def test_lead_cleaner_missing_company_name(self):
        """测试公司名为空时记录被移除"""
        import pandas as pd

        df = pd.DataFrame(
            {
                "公司名称": ["公司A", "", None, "  "],
                "行业": ["SaaS", "教育", "制造", "零售"],
            }
        )
        cleaner = LeadDataCleaner()
        cleaned = cleaner.clean(df)
        # 只保留 "公司A"
        assert len(cleaned) == 1
        assert cleaned.iloc[0]["公司名称"] == "公司A"


class TestLeadCleanerIndustryMapping:

    def test_lead_cleaner_industry_mapping(self, sample_lead_df):
        """测试行业映射"""
        cleaner = LeadDataCleaner()
        cleaned = cleaner.clean(sample_lead_df)

        # 检查行业标准化列存在
        assert "行业_标准化" in cleaned.columns

        # "SaaS软件" 应映射到 "企业服务"
        saas_rows = cleaned[cleaned["行业"].str.contains("SaaS", na=False)]
        for _, row in saas_rows.iterrows():
            assert row["行业_标准化"] == "企业服务"

        # "教育培训" 应映射到 "教育/培训"
        edu_rows = cleaned[cleaned["行业"].str.contains("教育", na=False)]
        for _, row in edu_rows.iterrows():
            assert row["行业_标准化"] == "教育/培训"

        # "奶茶" 应映射到 "餐饮/食品"
        tea_rows = cleaned[cleaned["行业"].str.contains("奶茶", na=False)]
        for _, row in tea_rows.iterrows():
            assert row["行业_标准化"] == "餐饮/食品"

    def test_lead_cleaner_industry_mapping_unknown(self):
        """测试未知行业保留原值"""
        import pandas as pd

        df = pd.DataFrame(
            {
                "公司名称": ["公司A"],
                "行业": ["航空航天"],
                "手机号": ["13800000000"],
            }
        )
        cleaner = LeadDataCleaner()
        cleaned = cleaner.clean(df)
        # 无法匹配的行业应保留原值
        assert cleaned.iloc[0]["行业_标准化"] == "航空航天"


class TestLeadCleanerIntentLevelMapping:

    def test_lead_cleaner_intent_level_mapping(self, sample_lead_df):
        """测试意向级别映射"""
        cleaner = LeadDataCleaner()
        cleaned = cleaner.clean(sample_lead_df)

        assert "意向级别_标准化" in cleaned.columns

        # "A" -> "高"
        a_rows = cleaned[cleaned["意向级别"] == "A"]
        for _, row in a_rows.iterrows():
            assert row["意向级别_标准化"] == "高"

        # "高" -> "高"
        high_rows = cleaned[cleaned["意向级别"] == "高"]
        for _, row in high_rows.iterrows():
            assert row["意向级别_标准化"] == "高"

        # "hot" -> "高" (代码中 .upper() 后变成 "HOT"，修复后映射中包含 "HOT" 键)
        hot_rows = cleaned[cleaned["意向级别"] == "hot"]
        for _, row in hot_rows.iterrows():
            assert row["意向级别_标准化"] == "高"

        # "B" -> "中"
        b_rows = cleaned[cleaned["意向级别"] == "B"]
        for _, row in b_rows.iterrows():
            assert row["意向级别_标准化"] == "中"


class TestScriptCleanerDedup:

    def test_script_cleaner_dedup(self, sample_script_df):
        """测试脚本去重 - 根据完整脚本内容去重"""
        cleaner = ScriptDataCleaner()
        cleaned = cleaner.clean(sample_script_df)

        # 原始3条，第一条和第二条脚本内容相同，去重后应为2条
        assert len(cleaned) == 2


class TestScriptCleanerTextStandardization:

    def test_script_cleaner_text_standardization(self, sample_script_df):
        """测试脚本文本标准化"""
        cleaner = ScriptDataCleaner()
        cleaned = cleaner.clean(sample_script_df)

        assert "完整脚本_清洗" in cleaned.columns
        assert "脚本字数" in cleaned.columns

        # 清洗后的脚本不应包含多余空格
        for text in cleaned["完整脚本_清洗"]:
            assert "  " not in text  # 不应有连续空格

        # 脚本字数应大于0
        assert (cleaned["脚本字数"] > 0).all()

    def test_script_cleaner_text_special_chars(self):
        """测试特殊字符去除"""
        import pandas as pd

        df = pd.DataFrame(
            {
                "标题": ["测试"],
                "完整脚本": ["Hello!!! 你好@@@ 世界###"],
            }
        )
        cleaner = ScriptDataCleaner()
        cleaned = cleaner.clean(df)
        cleaned_text = cleaned.iloc[0]["完整脚本_清洗"]
        # @ 和 # 应被去除，! 和中文标点应保留
        assert "@" not in cleaned_text
        assert "#" not in cleaned_text


class TestScriptCleanerNumericColumns:

    def test_script_cleaner_numeric_columns(self, sample_script_df):
        """测试数值字段处理"""
        cleaner = ScriptDataCleaner()
        cleaned = cleaner.clean(sample_script_df)

        # 播放量中的 "abc" 应被转为 0
        assert "播放量" in cleaned.columns
        assert cleaned["播放量"].dtype in ["float64", "int64"]

        # 所有数值列不应有 NaN
        for col in ["播放量", "点赞数", "评论数", "转发数"]:
            assert cleaned[col].isna().sum() == 0

        # 应计算互动数和互动率
        assert "互动数" in cleaned.columns
        assert "互动率" in cleaned.columns

        # 验证互动数计算正确
        import pandas as pd

        expected_interaction = cleaned["点赞数"] + cleaned["评论数"] + cleaned["转发数"]
        pd.testing.assert_series_equal(
            cleaned["互动数"], expected_interaction, check_names=False
        )
