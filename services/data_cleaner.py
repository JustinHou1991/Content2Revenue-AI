"""
数据清洗模块 - 处理销售线索和抖音脚本数据
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CleaningStep:
    """单次清洗步骤记录"""

    step: str
    detail: str
    removed_count: int = 0


@dataclass
class CleaningRecord:
    """单次清洗的完整记录"""

    timestamp: str
    initial_count: int
    final_count: int
    removed: int
    steps: List[CleaningStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "initial_count": self.initial_count,
            "final_count": self.final_count,
            "removed": self.removed,
            "steps": [
                {"step": s.step, "detail": s.detail, "removed_count": s.removed_count}
                for s in self.steps
            ],
        }


class LeadDataCleaner:
    """销售线索数据清洗器"""

    # 行业映射表（可根据实际数据扩展）
    INDUSTRY_MAPPING: Dict[str, str] = {
        # 餐饮/食品
        "餐饮": "餐饮/食品",
        "食品": "餐饮/食品",
        "奶茶": "餐饮/食品",
        "咖啡": "餐饮/食品",
        "烘焙": "餐饮/食品",
        "餐饮加盟": "餐饮/食品",
        # 制造业
        "制造": "制造业",
        "工厂": "制造业",
        "加工": "制造业",
        "生产": "制造业",
        "工业": "制造业",
        "智能制造": "制造业",
        # 教育/培训
        "教育": "教育/培训",
        "培训": "教育/培训",
        "学校": "教育/培训",
        "教培": "教育/培训",
        "K12": "教育/培训",
        "职业教育": "教育/培训",
        # 电商/零售
        "电商": "电商/零售",
        "零售": "电商/零售",
        "淘宝": "电商/零售",
        "天猫": "电商/零售",
        "京东": "电商/零售",
        "拼多多": "电商/零售",
        "跨境电商": "电商/零售",
        "直播带货": "电商/零售",
        # 美业
        "美容": "美业",
        "美发": "美业",
        "美甲": "美业",
        "美业": "美业",
        "医美": "美业",
        "皮肤管理": "美业",
        # 健身/运动
        "健身": "健身/运动",
        "瑜伽": "健身/运动",
        "健身房": "健身/运动",
        "运动": "健身/运动",
        # 医疗/健康
        "医疗": "医疗/健康",
        "诊所": "医疗/健康",
        "健康": "医疗/健康",
        "养生": "医疗/健康",
        "体检": "医疗/健康",
        # 企业服务/SaaS
        "SaaS": "企业服务",
        "软件": "企业服务",
        "企业服务": "企业服务",
        "B2B": "企业服务",
        "数字化": "企业服务",
        # 房地产/装修
        "房地产": "房地产/装修",
        "房产": "房地产/装修",
        "装修": "房地产/装修",
        "家装": "房地产/装修",
        "建材": "房地产/装修",
        # 汽车/出行
        "汽车": "汽车/出行",
        "4S店": "汽车/出行",
        "汽修": "汽车/出行",
        "二手车": "汽车/出行",
        # 金融/保险
        "金融": "金融/保险",
        "保险": "金融/保险",
        "理财": "金融/保险",
        "贷款": "金融/保险",
        "投资": "金融/保险",
    }

    # 意向级别映射
    LEVEL_MAPPING: Dict[str, str] = {
        "A": "高", "高": "高", "HOT": "高", "H": "高", "强": "高",
        "B": "中", "中": "中", "WARM": "中", "M": "中", "一般": "中",
        "C": "低", "低": "低", "COLD": "低", "L": "低", "弱": "低",
    }

    def __init__(self) -> None:
        self.cleaning_log: List[CleaningRecord] = []
        self._current_steps: List[CleaningStep] = []

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗销售线索数据

        Args:
            df: 原始线索数据DataFrame

        Returns:
            清洗后的DataFrame
        """
        df = df.copy()
        initial_count: int = len(df)
        self._current_steps = []

        logger.info("开始清洗销售线索数据，共 %d 条记录", initial_count)

        # 1. 基础清洗
        df = self._remove_duplicates(df)
        df = self._handle_missing_values(df)

        # 2. 字段标准化
        df = self._standardize_company_name(df)
        df = self._standardize_industry(df)
        df = self._standardize_intent_level(df)
        df = self._parse_datetime(df)

        # 3. 特征提取
        df = self._extract_text_features(df)

        final_count: int = len(df)
        record = CleaningRecord(
            timestamp=datetime.now().isoformat(),
            initial_count=initial_count,
            final_count=final_count,
            removed=initial_count - final_count,
            steps=list(self._current_steps),
        )
        self.cleaning_log.append(record)

        logger.info(
            "销售线索数据清洗完成：原始 %d 条，最终 %d 条，移除 %d 条",
            initial_count,
            final_count,
            initial_count - final_count,
        )
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """去重处理"""
        # 根据手机号或公司名去重（优先手机号）
        if "手机号" in df.columns:
            before: int = len(df)
            df = df.drop_duplicates(subset=["手机号"], keep="first")
            after: int = len(df)
            if before != after:
                removed = before - after
                logger.info("去重：移除了 %d 条重复手机号记录", removed)
                self._current_steps.append(
                    CleaningStep(
                        step="去重", detail="重复手机号", removed_count=removed
                    )
                )

        # 如果没有手机号，根据公司名去重
        elif "公司名称" in df.columns:
            before = len(df)
            df = df.drop_duplicates(subset=["公司名称"], keep="first")
            after = len(df)
            if before != after:
                removed = before - after
                logger.info("去重：移除了 %d 条重复公司记录", removed)
                self._current_steps.append(
                    CleaningStep(
                        step="去重", detail="重复公司名称", removed_count=removed
                    )
                )

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 公司名是核心字段，不能为空
        if "公司名称" in df.columns:
            before: int = len(df)
            df = df.dropna(subset=["公司名称"])
            df = df[df["公司名称"].str.strip() != ""]
            after: int = len(df)
            if before != after:
                removed = before - after
                logger.info("缺失值处理：移除了 %d 条公司名为空的记录", removed)
                self._current_steps.append(
                    CleaningStep(
                        step="缺失值处理", detail="公司名为空", removed_count=removed
                    )
                )

        # 填充其他字段的缺失值
        text_columns: List[str] = ["需求描述", "跟进记录", "备注"]
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)

        categorical_columns: List[str] = ["行业", "来源", "渠道", "意向级别"]
        for col in categorical_columns:
            if col in df.columns:
                df[col] = df[col].fillna("未知")

        return df

    def _standardize_company_name(self, df: pd.DataFrame) -> pd.DataFrame:
        """公司名称标准化"""
        if "公司名称" not in df.columns:
            return df

        def clean_name(name: Any) -> Any:
            if pd.isna(name):
                return name
            name = str(name).strip()
            # 去除空格
            name = re.sub(r"\s+", "", name)
            # 去除常见后缀
            suffixes = [
                "有限公司",
                "有限责任公司",
                "股份有限公司",
                "集团公司",
                "公司",
                "集团",
            ]
            for suffix in suffixes:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
                    break
            return name

        df["公司名称_标准化"] = df["公司名称"].apply(clean_name)
        return df

    def _standardize_industry(self, df: pd.DataFrame) -> pd.DataFrame:
        """行业标准化"""
        if "行业" not in df.columns:
            return df

        def map_industry(industry: Any) -> str:
            if pd.isna(industry):
                return "未知"
            industry = str(industry).strip()
            # 直接匹配
            if industry in self.INDUSTRY_MAPPING:
                return self.INDUSTRY_MAPPING[industry]
            # 模糊匹配
            for key, value in self.INDUSTRY_MAPPING.items():
                if key in industry or industry in key:
                    return value
            return industry  # 无法匹配则保留原值

        df["行业_标准化"] = df["行业"].apply(map_industry)
        return df

    def _standardize_intent_level(self, df: pd.DataFrame) -> pd.DataFrame:
        """意向级别标准化"""
        if "意向级别" not in df.columns:
            return df

        def map_level(level: Any) -> str:
            if pd.isna(level):
                return "未知"
            level = str(level).strip().upper()
            return self.LEVEL_MAPPING.get(level, level)

        df["意向级别_标准化"] = df["意向级别"].apply(map_level)
        return df

    def _parse_datetime(self, df: pd.DataFrame) -> pd.DataFrame:
        """时间字段解析"""
        datetime_columns: List[str] = ["获客时间", "创建时间", "跟进时间"]
        for col in datetime_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                    # 提取时间特征
                    df[f"{col}_月份"] = df[col].dt.to_period("M").astype(str)
                    df[f"{col}_星期"] = df[col].dt.day_name()
                except Exception:
                    logger.warning("时间字段 '%s' 解析失败，跳过", col)
        return df

    def _extract_text_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取文本特征"""
        # 需求描述长度
        if "需求描述" in df.columns:
            df["需求描述_长度"] = df["需求描述"].str.len()
            df["需求描述_有内容"] = df["需求描述_长度"] > 10

        # 跟进记录条数（如果有多个跟进记录合并在一起）
        if "跟进记录" in df.columns:
            df["跟进记录_长度"] = df["跟进记录"].str.len()

        return df

    def get_cleaning_summary(self) -> Dict[str, Any]:
        """获取清洗摘要"""
        if not self.cleaning_log:
            return {}
        latest: CleaningRecord = self.cleaning_log[-1]
        return {
            "原始记录数": latest.initial_count,
            "清洗后记录数": latest.final_count,
            "移除记录数": latest.removed,
            "保留率": f"{(latest.final_count / latest.initial_count * 100):.1f}%",
            "清洗步骤": latest.to_dict()["steps"],
        }


class ScriptDataCleaner:
    """抖音脚本数据清洗器"""

    def __init__(self) -> None:
        self.cleaning_log: List[CleaningRecord] = []
        self._current_steps: List[CleaningStep] = []

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗抖音脚本数据

        Args:
            df: 原始脚本数据DataFrame

        Returns:
            清洗后的DataFrame
        """
        df = df.copy()
        initial_count: int = len(df)
        self._current_steps = []

        logger.info("开始清洗抖音脚本数据，共 %d 条记录", initial_count)

        # 1. 基础清洗
        df = self._remove_duplicates(df)
        df = self._handle_missing_values(df)

        # 2. 内容标准化
        df = self._standardize_script_text(df)
        df = self._parse_datetime(df)

        # 3. 数值字段处理
        df = self._process_numeric_columns(df)

        final_count: int = len(df)
        record = CleaningRecord(
            timestamp=datetime.now().isoformat(),
            initial_count=initial_count,
            final_count=final_count,
            removed=initial_count - final_count,
            steps=list(self._current_steps),
        )
        self.cleaning_log.append(record)

        logger.info(
            "抖音脚本数据清洗完成：原始 %d 条，最终 %d 条，移除 %d 条",
            initial_count,
            final_count,
            initial_count - final_count,
        )
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """去重处理"""
        # 根据脚本内容去重
        if "完整脚本" in df.columns:
            before: int = len(df)
            df = df.drop_duplicates(subset=["完整脚本"], keep="first")
            after: int = len(df)
            if before != after:
                removed = before - after
                logger.info("去重：移除了 %d 条重复脚本", removed)
                self._current_steps.append(
                    CleaningStep(
                        step="去重", detail="重复脚本内容", removed_count=removed
                    )
                )
        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 脚本内容是核心字段
        if "完整脚本" in df.columns:
            before: int = len(df)
            df = df.dropna(subset=["完整脚本"])
            df = df[df["完整脚本"].str.strip() != ""]
            after: int = len(df)
            if before != after:
                removed = before - after
                logger.info("缺失值处理：移除了 %d 条脚本为空的记录", removed)
                self._current_steps.append(
                    CleaningStep(
                        step="缺失值处理", detail="脚本内容为空", removed_count=removed
                    )
                )

        # 填充其他字段
        text_columns: List[str] = ["标题", "话题标签", "开头钩子", "结尾引导"]
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)

        return df

    def _standardize_script_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """脚本文本标准化"""
        if "完整脚本" not in df.columns:
            return df

        def clean_text(text: Any) -> Any:
            if pd.isna(text):
                return text
            text = str(text)
            # 去除多余空格
            text = re.sub(r"\s+", " ", text)
            # 去除特殊字符（保留中文、英文、数字、常用标点）
            text = re.sub(
                r"[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?，。！？、：:\"\"''（）()]", "", text
            )
            return text.strip()

        df["完整脚本_清洗"] = df["完整脚本"].apply(clean_text)
        df["脚本字数"] = df["完整脚本_清洗"].str.len()

        return df

    def _parse_datetime(self, df: pd.DataFrame) -> pd.DataFrame:
        """时间字段解析"""
        if "发布日期" in df.columns:
            try:
                df["发布日期"] = pd.to_datetime(df["发布日期"], errors="coerce")
                df["发布月份"] = df["发布日期"].dt.to_period("M").astype(str)
                df["发布星期"] = df["发布日期"].dt.day_name()
            except Exception:
                logger.warning("发布日期字段解析失败，跳过")
        return df

    def _process_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理数值字段"""
        numeric_columns: List[str] = [
            "播放量",
            "点赞数",
            "评论数",
            "转发数",
            "收藏数",
            "视频时长",
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # 计算互动率
        if all(col in df.columns for col in ["点赞数", "评论数", "转发数", "播放量"]):
            df["互动数"] = df["点赞数"] + df["评论数"] + df["转发数"]
            df["互动率"] = (df["互动数"] / df["播放量"] * 100).round(2)

        return df

    def get_cleaning_summary(self) -> Dict[str, Any]:
        """获取清洗摘要"""
        if not self.cleaning_log:
            return {}
        latest: CleaningRecord = self.cleaning_log[-1]
        return {
            "原始记录数": latest.initial_count,
            "清洗后记录数": latest.final_count,
            "移除记录数": latest.removed,
            "保留率": f"{(latest.final_count / latest.initial_count * 100):.1f}%",
            "清洗步骤": latest.to_dict()["steps"],
        }


# ===== 使用示例 =====
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 测试线索数据清洗
    print("=" * 50)
    print("测试线索数据清洗")
    print("=" * 50)

    sample_leads = pd.DataFrame(
        {
            "公司名称": [
                "  杭州某某科技有限公司  ",
                "北京某某教育咨询有限公司",
                "杭州某某科技有限公司",
            ],
            "行业": ["SaaS软件", "教育培训", "软件"],
            "手机号": ["13800138000", "13900139000", "13800138000"],  # 重复手机号
            "需求描述": ["需要获客系统", "", "需要获客系统"],
            "意向级别": ["A", "高", "hot"],
        }
    )

    print("原始数据:")
    print(sample_leads)
    print()

    cleaner = LeadDataCleaner()
    cleaned_leads = cleaner.clean(sample_leads)

    print("清洗后数据:")
    print(
        cleaned_leads[
            ["公司名称", "公司名称_标准化", "行业", "行业_标准化", "意向级别_标准化"]
        ]
    )
    print()
    print("清洗摘要:", cleaner.get_cleaning_summary())

    # 测试脚本数据清洗
    print("\n" + "=" * 50)
    print("测试脚本数据清洗")
    print("=" * 50)

    sample_scripts = pd.DataFrame(
        {
            "标题": ["获客秘籍", "销售技巧"],
            "完整脚本": [
                "你是不是还在用传统方式获客？每天花500块投流...",
                "你是不是还在用传统方式获客？每天花500块投流...",  # 重复
            ],
            "播放量": [10000, 5000],
            "点赞数": [500, 300],
        }
    )

    print("原始数据:")
    print(sample_scripts)
    print()

    script_cleaner = ScriptDataCleaner()
    cleaned_scripts = script_cleaner.clean(sample_scripts)

    print("清洗后数据:")
    print(cleaned_scripts)
    print()
    print("清洗摘要:", script_cleaner.get_cleaning_summary())
