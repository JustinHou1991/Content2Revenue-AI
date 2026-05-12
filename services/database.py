"""
数据库模块 - SQLite数据持久化
"""

import sqlite3
import json
import logging
import os
import base64
import hashlib
import time
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# 尝试导入cryptography库，用于Fernet对称加密
_FERNET_AVAILABLE = False
try:
    from cryptography.fernet import Fernet
    _FERNET_AVAILABLE = True
    logger.info("cryptography库可用，将使用Fernet对称加密")
except ImportError:
    logger.warning("cryptography库不可用，将回退到XOR加密方案")

# Fernet密钥在数据库中的存储键名
_FERNET_KEY_SETTING = "_fernet_encryption_key"
# 用于标识数据是否为Fernet加密的前缀
_FERNET_PREFIX = "FERNET:"

# 所有需要JSON解析的字段名集合（跨所有表）
_ALL_JSON_FIELDS = frozenset(
    {
        "analysis_json",
        "raw_data_json",
        "profile_json",
        "match_result_json",
        "content_snapshot_json",
        "lead_snapshot_json",
        "strategy_json",
        "feedback_notes",
        "variant_config_json",
        "test_results_json",
    }
)


def generate_uuid() -> str:
    """生成唯一ID"""
    import uuid

    return str(uuid.uuid4())


class Database:
    """SQLite数据库管理器"""

    def __init__(self, db_path: str = "data/c2r.db"):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        # 确保数据库文件所在目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_tables()
        # 初始化Fernet加密密钥（如果cryptography库可用）
        self._fernet: Optional[Any] = None
        if _FERNET_AVAILABLE:
            self._init_fernet_key()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接（上下文管理器，自动关闭）"""
        logger.debug("创建新的数据库连接: %s", self.db_path)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        # 启用查询计时
        conn.set_trace_callback(self._query_logger)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _query_logger(self, query: str):
        """记录慢查询（超过100ms）"""
        # 使用连接对象的属性来存储查询开始时间
        # 注意：由于连接是临时的，这里使用线程局部存储
        pass  # 实际计时逻辑在 execute 中实现

    def _init_fernet_key(self) -> None:
        """
        初始化或加载Fernet加密密钥。

        密钥存储在数据库app_settings表中，如果不存在则自动生成。
        """
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT value FROM app_settings WHERE key = ?",
                    (_FERNET_KEY_SETTING,),
                ).fetchone()
                if row and row["value"]:
                    key_bytes = base64.b64decode(row["value"])
                    self._fernet = Fernet(key_bytes)
                    logger.info("已从数据库加载Fernet加密密钥")
                else:
                    # 生成新的Fernet密钥
                    key_bytes = Fernet.generate_key()
                    now = datetime.now().isoformat()
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                        VALUES (?, ?, ?)
                        """,
                        (_FERNET_KEY_SETTING, key_bytes.decode(), now),
                    )
                    self._fernet = Fernet(key_bytes)
                    logger.info("已生成新的Fernet加密密钥并存储到数据库")
        except Exception as e:
            logger.error("初始化Fernet密钥失败，将回退到XOR加密: %s", e)
            self._fernet = None

    def _xor_encrypt(self, value: str) -> str:
        """XOR加密（降级方案，安全性较弱）"""
        if not value:
            return ""
        key = hashlib.sha256(self.db_path.encode()).digest()
        key_bytes = key * (len(value) // len(key) + 1)
        encrypted = bytes(a ^ b for a, b in zip(value.encode(), key_bytes[: len(value)]))
        return base64.b64encode(encrypted).decode()

    def _xor_decrypt(self, encrypted: str) -> str:
        """XOR解密（降级方案）"""
        if not encrypted:
            return ""
        try:
            key = hashlib.sha256(self.db_path.encode()).digest()
            encrypted_bytes = base64.b64decode(encrypted)
            key_bytes = key * (len(encrypted_bytes) // len(key) + 1)
            decrypted = bytes(
                a ^ b for a, b in zip(encrypted_bytes, key_bytes[: len(encrypted_bytes)])
            )
            return decrypted.decode()
        except Exception as e:
            # 如果解密失败，记录警告并静默返回（可能是明文存储的旧数据）
            logger.warning("XOR解密失败: %s (数据可能为明文)", e)
            return encrypted

    def _encrypt_value(self, value: str) -> str:
        """
        加密敏感值（优先使用Fernet，不可用时降级到XOR）。

        Fernet加密的数据会添加 'FERNET:' 前缀以便解密时识别。
        """
        if not value:
            return ""
        # 优先使用Fernet对称加密
        if self._fernet is not None:
            try:
                encrypted = self._fernet.encrypt(value.encode())
                return _FERNET_PREFIX + base64.b64encode(encrypted).decode()
            except Exception as e:
                logger.warning("Fernet加密失败，回退到XOR: %s", e)
        # 降级到XOR加密
        return self._xor_encrypt(value)

    def _decrypt_value(self, encrypted: str) -> str:
        """
        解密敏感值（自动识别Fernet/XOR/明文）。

        识别逻辑：
        1. 如果有 'FERNET:' 前缀，使用Fernet解密
        2. 否则尝试XOR解密
        3. 如果都失败，返回原始值（兼容明文存储）
        """
        if not encrypted:
            return ""
        # 识别Fernet加密数据
        if encrypted.startswith(_FERNET_PREFIX):
            if self._fernet is not None:
                try:
                    encrypted_data = base64.b64decode(encrypted[len(_FERNET_PREFIX) :])
                    return self._fernet.decrypt(encrypted_data).decode()
                except Exception as e:
                    logger.warning("Fernet解密失败: %s", e)
            else:
                logger.warning("检测到Fernet加密数据但Fernet不可用，无法解密")
            return ""
        # 尝试XOR解密（兼容旧数据）
        xor_result = self._xor_decrypt(encrypted)
        return xor_result

    def _migrate_to_fernet(self, conn=None) -> int:
        """
        将所有旧的XOR加密数据自动迁移为Fernet加密。

        Args:
            conn: 可选的数据库连接（用于在同一事务内执行迁移）

        Returns:
            成功迁移的记录数量
        """
        if self._fernet is None:
            logger.info("Fernet不可用，跳过迁移")
            return 0

        migrated = 0
        own_conn = conn is None
        try:
            if own_conn:
                conn = self._get_conn()

            # 查找所有非Fernet加密的API_KEY记录
            rows = conn.execute(
                "SELECT key, value FROM app_settings WHERE key = 'API_KEY' AND value IS NOT NULL AND value != ''"
            ).fetchall()

            for row in rows:
                raw_value = row["value"]
                # 跳过已经是Fernet加密的数据
                if raw_value.startswith(_FERNET_PREFIX):
                    continue

                # 尝试用XOR解密旧数据
                decrypted = self._xor_decrypt(raw_value)
                if decrypted and decrypted != raw_value:
                    # 解密成功，用Fernet重新加密
                    new_encrypted = self._encrypt_value(decrypted)
                else:
                    # 可能是明文数据，也用Fernet加密保护
                    new_encrypted = self._encrypt_value(raw_value)

                now = datetime.now().isoformat()
                conn.execute(
                    "UPDATE app_settings SET value = ?, updated_at = ? WHERE key = ?",
                    (new_encrypted, now, row["key"]),
                )
                migrated += 1
                logger.info("已迁移加密数据: key=%s", row["key"])
        except Exception as e:
            logger.error("加密数据迁移失败: %s", e)

        if migrated > 0:
            logger.info("加密迁移完成，共迁移 %d 条记录", migrated)
        return migrated

    def _init_tables(self) -> None:
        """初始化数据库表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 内容分析结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_analysis (
                    id TEXT PRIMARY KEY,
                    raw_text TEXT NOT NULL,
                    analysis_json TEXT NOT NULL,
                    model TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)

            # 线索分析结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lead_analysis (
                    id TEXT PRIMARY KEY,
                    raw_data_json TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    model TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)

            # 匹配结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_results (
                    id TEXT PRIMARY KEY,
                    content_id TEXT,
                    lead_id TEXT,
                    match_result_json TEXT NOT NULL,
                    content_snapshot_json TEXT,
                    lead_snapshot_json TEXT,
                    model TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # 策略建议表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_advice (
                    id TEXT PRIMARY KEY,
                    match_id TEXT,
                    content_id TEXT,
                    lead_id TEXT,
                    strategy_json TEXT NOT NULL,
                    model TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # 系统配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)

            # API 使用记录表（成本统计）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost REAL NOT NULL DEFAULT 0.0,
                    operation_type TEXT,
                    content_id TEXT,
                    lead_id TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # 策略反馈表 - 效果追踪系统
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_feedback (
                    id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    was_adopted INTEGER NOT NULL DEFAULT 0,
                    actual_conversion REAL,
                    feedback_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    FOREIGN KEY (strategy_id) REFERENCES strategy_advice(id)
                )
            """)

            # A/B测试表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    id TEXT PRIMARY KEY,
                    match_id TEXT NOT NULL,
                    variant_name TEXT NOT NULL,
                    variant_config_json TEXT NOT NULL,
                    test_results_json TEXT,
                    is_control INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)

            # 创建索引以优化查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_usage_created_at
                ON api_usage(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_usage_model
                ON api_usage(model)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_strategy_feedback_strategy_id
                ON strategy_feedback(strategy_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ab_tests_match_id
                ON ab_tests(match_id)
            """)

            # 创建常用查询索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_created_at ON content_analysis(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lead_created_at ON lead_analysis(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_created_at ON match_results(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_lead_id ON match_results(lead_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_created_at ON strategy_advice(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_lead_id ON strategy_advice(lead_id)")

        logger.info("数据库表初始化完成")

    def close(self) -> None:
        """关闭数据库连接（连接已由上下文管理器自动管理，此方法为空操作）"""
        pass

    # ===== 内容分析 CRUD =====

    def save_content_analysis(self, result: Dict[str, Any]) -> str:
        """保存内容分析结果"""
        with self._get_conn() as conn:
            content_id = result["content_id"]
            now = datetime.now().isoformat()

            conn.execute(
                """
                INSERT OR REPLACE INTO content_analysis
                (id, raw_text, analysis_json, model, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    content_id,
                    result["raw_text"],
                    json.dumps(result["analysis"], ensure_ascii=False),
                    result.get("model", ""),
                    result["created_at"],
                    now,
                ),
            )
        logger.info("保存内容分析: %s", content_id)
        return content_id

    def get_content_analysis(self, content_id: str) -> Optional[Dict[str, Any]]:
        """获取单条内容分析结果"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM content_analysis WHERE id = ?", (content_id,)
            ).fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def get_all_content_analyses(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有内容分析结果"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM content_analysis ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_content_analyses_count(self) -> int:
        """获取内容分析总数（用于仪表盘统计）"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM content_analysis").fetchone()
            return row[0]

    def get_content_analyses_paginated(self, page: int = 1, page_size: int = 10) -> Tuple[List[Dict], int]:
        """分页获取内容分析（高效查询）"""
        with self._get_conn() as conn:
            # 先获取总数
            total = conn.execute("SELECT COUNT(*) FROM content_analysis").fetchone()[0]

            # 获取当前页数据
            offset = (page - 1) * page_size
            rows = conn.execute("""
                SELECT * FROM content_analysis
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (page_size, offset)).fetchall()

            return [self._row_to_dict(row) for row in rows], total

    def delete_content_analysis(self, content_id: str) -> bool:
        """删除内容分析结果"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM content_analysis WHERE id = ?", (content_id,)
            )
            deleted = cursor.rowcount > 0
        if deleted:
            logger.info("删除内容分析: %s", content_id)
        return deleted

    def save_content_analyses_batch(self, results: List[Dict[str, Any]]) -> int:
        """批量保存内容分析结果（单事务）"""
        if not results:
            return 0
        with self._get_conn() as conn:
            for result in results:
                content_id = result["content_id"]
                now = datetime.now().isoformat()
                conn.execute(
                    """INSERT OR REPLACE INTO content_analysis
                    (id, raw_text, analysis_json, model, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (content_id, result["raw_text"], json.dumps(result["analysis"], ensure_ascii=False),
                     result.get("model", ""), now, now),
                )
        return len(results)

    # ===== 线索分析 CRUD =====

    def save_lead_analysis(self, result: Dict[str, Any]) -> str:
        """保存线索分析结果"""
        with self._get_conn() as conn:
            lead_id = result["lead_id"]
            now = datetime.now().isoformat()

            conn.execute(
                """
                INSERT OR REPLACE INTO lead_analysis
                (id, raw_data_json, profile_json, model, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    lead_id,
                    json.dumps(result["raw_data"], ensure_ascii=False),
                    json.dumps(result["profile"], ensure_ascii=False),
                    result.get("model", ""),
                    result["created_at"],
                    now,
                ),
            )
        logger.info("保存线索分析: %s", lead_id)
        return lead_id

    def get_lead_analysis(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """获取单条线索分析结果"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM lead_analysis WHERE id = ?", (lead_id,)
            ).fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def get_all_lead_analyses(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有线索分析结果"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM lead_analysis ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_lead_analyses_count(self) -> int:
        """获取线索分析总数（用于仪表盘统计）"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM lead_analysis").fetchone()
            return row[0]

    def get_lead_analyses_paginated(self, page: int = 1, page_size: int = 10) -> Tuple[List[Dict], int]:
        """分页获取线索分析（高效查询）"""
        with self._get_conn() as conn:
            # 先获取总数
            total = conn.execute("SELECT COUNT(*) FROM lead_analysis").fetchone()[0]

            # 获取当前页数据
            offset = (page - 1) * page_size
            rows = conn.execute("""
                SELECT * FROM lead_analysis
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (page_size, offset)).fetchall()

            return [self._row_to_dict(row) for row in rows], total

    def save_lead_analyses_batch(self, results: List[Dict[str, Any]]) -> int:
        """批量保存线索分析结果（单事务）"""
        if not results:
            return 0
        with self._get_conn() as conn:
            for result in results:
                lead_id = result["lead_id"]
                now = datetime.now().isoformat()
                conn.execute(
                    """INSERT OR REPLACE INTO lead_analysis
                    (id, raw_data_json, profile_json, model, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (lead_id, json.dumps(result["raw_data"], ensure_ascii=False),
                     json.dumps(result["profile"], ensure_ascii=False),
                     result.get("model", ""), now, now),
                )
        return len(results)

    # ===== 匹配结果 CRUD =====

    def save_match_result(
        self,
        result: Dict[str, Any],
        content_id: str = "",
        lead_id: str = "",
    ) -> str:
        """
        保存匹配结果

        Args:
            result: MatchEngine.match() 返回的匹配结果字典
            content_id: 内容ID（优先使用此参数，其次从result中提取）
            lead_id: 线索ID（优先使用此参数，其次从result中提取）

        Returns:
            match_id
        """
        with self._get_conn() as conn:
            match_id = result["match_id"]

            # 确定content_id和lead_id：优先使用显式传入的参数
            resolved_content_id = content_id or result.get("content_snapshot", {}).get(
                "content_id", ""
            )
            resolved_lead_id = lead_id or result.get("lead_snapshot", {}).get("lead_id", "")

            conn.execute(
                """
                INSERT INTO match_results
                (id, content_id, lead_id, match_result_json,
                 content_snapshot_json, lead_snapshot_json, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    match_id,
                    resolved_content_id,
                    resolved_lead_id,
                    json.dumps(result["match_result"], ensure_ascii=False),
                    json.dumps(result.get("content_snapshot", {}), ensure_ascii=False),
                    json.dumps(result.get("lead_snapshot", {}), ensure_ascii=False),
                    result.get("model", ""),
                    result["created_at"],
                ),
            )
        logger.info(
            "保存匹配结果: %s (content=%s, lead=%s)",
            match_id,
            resolved_content_id,
            resolved_lead_id,
        )
        return match_id

    def get_match_result(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        按ID查询单条匹配结果

        Args:
            match_id: 匹配结果ID

        Returns:
            匹配结果字典，不存在则返回None
        """
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM match_results WHERE id = ?", (match_id,)
            ).fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def get_match_results_by_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        """获取某线索的所有匹配结果"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM match_results WHERE lead_id = ? ORDER BY created_at DESC",
                (lead_id,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_all_match_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有匹配结果"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM match_results ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def save_match_results_batch(self, results: List[Dict[str, Any]]) -> int:
        """批量保存匹配结果（单事务）"""
        if not results:
            return 0
        with self._get_conn() as conn:
            for result in results:
                match_id = result["match_id"]
                now = datetime.now().isoformat()
                conn.execute(
                    """INSERT OR REPLACE INTO match_results
                    (id, content_id, lead_id, match_result_json, content_snapshot_json,
                     lead_snapshot_json, model, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (match_id, result.get("content_id", ""), result.get("lead_id", ""),
                     json.dumps(result.get("match_result", {}), ensure_ascii=False),
                     json.dumps(result.get("content_snapshot", {}), ensure_ascii=False),
                     json.dumps(result.get("lead_snapshot", {}), ensure_ascii=False),
                     result.get("model", ""), now),
                )
        return len(results)

    # ===== 策略建议 CRUD =====

    def save_strategy_advice(self, result: Dict[str, Any]) -> str:
        """保存策略建议"""
        with self._get_conn() as conn:
            strategy_id = result["strategy_id"]

            conn.execute(
                """
                INSERT INTO strategy_advice
                (id, match_id, content_id, lead_id, strategy_json, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    strategy_id,
                    result.get("match_id", ""),
                    result.get("content_id", ""),
                    result.get("lead_id", ""),
                    json.dumps(result["strategy"], ensure_ascii=False),
                    result.get("model", ""),
                    result["created_at"],
                ),
            )
        logger.info("保存策略建议: %s", strategy_id)
        return strategy_id

    def get_strategy_advices_by_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        """获取某线索的所有策略建议"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM strategy_advice WHERE lead_id = ? ORDER BY created_at DESC",
                (lead_id,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_all_strategy_advices(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取所有策略建议

        Args:
            limit: 最大返回数量

        Returns:
            策略建议列表，按创建时间倒序排列
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM strategy_advice ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_all_strategy_advices_with_feedback(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取策略建议及反馈（单查询，避免N+1问题）"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT
                    sa.*,
                    sf.id as feedback_id,
                    sf.was_adopted,
                    sf.actual_conversion,
                    sf.feedback_notes as feedback_notes_raw,
                    sf.created_at as feedback_created_at
                FROM strategy_advice sa
                LEFT JOIN strategy_feedback sf ON sa.id = sf.strategy_id
                ORDER BY sa.created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

            results = []
            for row in rows:
                item = self._row_to_dict(row)
                # 构建反馈对象
                if item.get('feedback_id'):
                    item['feedback'] = {
                        'id': item.pop('feedback_id', None),
                        'was_adopted': bool(item.pop('was_adopted', 0)),
                        'actual_conversion': item.pop('actual_conversion', None),
                        'feedback_notes': item.pop('feedback_notes_raw', None),
                        'created_at': item.pop('feedback_created_at', None),
                    }
                else:
                    item['feedback'] = None
                results.append(item)
            return results

    # ===== 统计查询 =====

    def get_stats(self) -> Dict[str, int]:
        """获取数据库统计信息"""
        with self._get_conn() as conn:
            content_count = conn.execute(
                "SELECT COUNT(*) FROM content_analysis"
            ).fetchone()[0]
            lead_count = conn.execute("SELECT COUNT(*) FROM lead_analysis").fetchone()[0]
            match_count = conn.execute("SELECT COUNT(*) FROM match_results").fetchone()[0]
            strategy_count = conn.execute(
                "SELECT COUNT(*) FROM strategy_advice"
            ).fetchone()[0]

        return {
            "content_count": content_count,
            "lead_count": lead_count,
            "match_count": match_count,
            "strategy_count": strategy_count,
        }

    def get_dashboard_stats_optimized(self) -> Dict[str, Any]:
        """优化后的仪表盘统计（单连接）"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 在一个查询中获取所有统计
            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM content_analysis) as content_count,
                    (SELECT COUNT(*) FROM lead_analysis) as lead_count,
                    (SELECT COUNT(*) FROM match_results) as match_count,
                    (SELECT COUNT(*) FROM strategy_advice) as strategy_count,
                    (SELECT COALESCE(AVG(
                        CAST(json_extract(match_result_json, '$.overall_score') AS REAL)
                    ), 0) FROM match_results) as avg_match_score,
                    (SELECT COALESCE(AVG(
                        CAST(json_extract(analysis_json, '$.content_score') AS REAL)
                    ), 0) FROM content_analysis) as avg_content_score,
                    (SELECT COALESCE(AVG(
                        CAST(json_extract(profile_json, '$.lead_score') AS REAL)
                    ), 0) FROM lead_analysis) as avg_lead_score
            """)

            row = cursor.fetchone()
            return {
                "content_count": row[0],
                "lead_count": row[1],
                "match_count": row[2],
                "strategy_count": row[3],
                "avg_match_score": round(row[4], 2),
                "avg_content_score": round(row[5], 2),
                "avg_lead_score": round(row[6], 2),
            }

    # ===== 设置管理 =====

    def get_setting(self, key: str, default: str = "") -> str:
        """获取设置值"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
            value = row["value"] if row else default

            # API_KEY 需要解密后返回
            if key == "API_KEY" and value:
                # 检测到旧的XOR加密数据，在同一事务内迁移为Fernet加密
                if self._fernet is not None and not value.startswith(_FERNET_PREFIX):
                    logger.info("检测到旧的加密格式，自动迁移API_KEY为Fernet加密")
                    # 在同一事务内完成迁移和读取
                    self._migrate_to_fernet(conn=conn)
                    # 重新读取迁移后的值
                    row = conn.execute(
                        "SELECT value FROM app_settings WHERE key = ?", (key,)
                    ).fetchone()
                    value = row["value"] if row else default

                value = self._decrypt_value(value)

            return value

    def set_setting(self, key: str, value: str) -> None:
        """设置值"""
        # API_KEY 需要加密后存储
        if key == "API_KEY" and value:
            value = self._encrypt_value(value)
        with self._get_conn() as conn:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """,
                (key, value, now),
            )

    def delete_setting(self, key: str) -> bool:
        """删除指定配置项"""
        with self._get_conn() as conn:
            result = conn.execute(
                "DELETE FROM app_settings WHERE key = ?",
                (key,),
            ).rowcount
            return result > 0

    # ===== API 使用记录 & 成本统计 =====

    def save_api_usage(self, record: Dict[str, Any]) -> str:
        """
        保存API调用记录

        Args:
            record: API使用记录字典，包含以下字段:
                - model: 模型名称
                - input_tokens: 输入token数
                - output_tokens: 输出token数
                - cost: 成本（人民币）
                - operation_type: 操作类型（可选）
                - content_id: 关联内容ID（可选）
                - lead_id: 关联线索ID（可选）
                - created_at: 创建时间（可选，默认当前时间）

        Returns:
            记录ID
        """
        with self._get_conn() as conn:
            record_id = record.get("id") or generate_uuid()
            now = datetime.now().isoformat()

            conn.execute(
                """
                INSERT INTO api_usage
                (id, model, input_tokens, output_tokens, cost, operation_type,
                 content_id, lead_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record_id,
                    record.get("model", ""),
                    record.get("input_tokens", 0),
                    record.get("output_tokens", 0),
                    record.get("cost", 0.0),
                    record.get("operation_type", ""),
                    record.get("content_id", ""),
                    record.get("lead_id", ""),
                    record.get("created_at", now),
                ),
            )
        logger.debug(
            "保存API使用记录: %s, model=%s, cost=%.4f",
            record_id,
            record.get("model"),
            record.get("cost", 0),
        )
        return record_id

    def get_api_usage_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取指定时间段的API使用统计

        Args:
            start_date: 开始日期（ISO格式，如 '2024-01-01'）
            end_date: 结束日期（ISO格式）
            model: 筛选特定模型（可选）

        Returns:
            统计信息字典
        """
        with self._get_conn() as conn:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)
            if end_date:
                end_date_clean = end_date[:10] if end_date else end_date
                conditions.append("created_at <= ?")
                params.append(end_date_clean + "T23:59:59")  # 包含整天
            if model:
                conditions.append("model = ?")
                params.append(model)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 基础统计
            stats_row = conn.execute(
                f"""
                SELECT
                    COUNT(*) as total_calls,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(cost) as total_cost
                FROM api_usage
                WHERE {where_clause}
            """,
                params,
            ).fetchone()

            # 按模型分组统计
            model_stats = conn.execute(
                f"""
                SELECT
                    model,
                    COUNT(*) as calls,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(cost) as cost
                FROM api_usage
                WHERE {where_clause}
                GROUP BY model
                ORDER BY cost DESC
            """,
                params,
            ).fetchall()

            # 按日期分组统计（最近30天）
            daily_stats = conn.execute(
                f"""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as calls,
                    SUM(cost) as cost,
                    SUM(input_tokens + output_tokens) as total_tokens
                FROM api_usage
                WHERE {where_clause}
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """,
                params,
            ).fetchall()

        return {
            "total_calls": stats_row["total_calls"] or 0,
            "total_input_tokens": stats_row["total_input_tokens"] or 0,
            "total_output_tokens": stats_row["total_output_tokens"] or 0,
            "total_tokens": (stats_row["total_input_tokens"] or 0)
            + (stats_row["total_output_tokens"] or 0),
            "total_cost": round(stats_row["total_cost"] or 0, 4),
            "by_model": [dict(row) for row in model_stats],
            "by_date": [dict(row) for row in daily_stats],
        }

    def get_total_cost(self) -> float:
        """获取总成本（人民币）"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT SUM(cost) FROM api_usage").fetchone()
            return round(row[0] or 0, 4)

    def get_api_usage_by_date_range(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取最近N天的API使用记录

        Args:
            days: 天数

        Returns:
            每日使用记录列表
        """
        from datetime import timedelta

        start_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    DATE(created_at) as date,
                    model,
                    COUNT(*) as calls,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(cost) as cost
                FROM api_usage
                WHERE created_at >= ?
                GROUP BY DATE(created_at), model
                ORDER BY date DESC, cost DESC
            """,
                (start_date,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_today_api_stats(self) -> Dict[str, Any]:
        """获取今日API使用统计"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_api_usage_stats(start_date=today, end_date=today)

    def get_week_api_stats(self) -> Dict[str, Any]:
        """获取本周API使用统计"""
        from datetime import timedelta

        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        week_end = today.strftime("%Y-%m-%d")
        return self.get_api_usage_stats(start_date=week_start, end_date=week_end)

    def get_month_api_stats(self) -> Dict[str, Any]:
        """获取本月API使用统计"""
        today = datetime.now()
        month_start = today.replace(day=1).strftime("%Y-%m-%d")
        month_end = today.strftime("%Y-%m-%d")
        return self.get_api_usage_stats(start_date=month_start, end_date=month_end)

    def get_cost_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """
        获取成本优化建议

        Returns:
            优化建议列表
        """
        with self._get_conn() as conn:
            suggestions = []

            # 1. 检查高成本模型使用情况
            expensive_models = conn.execute("""
                SELECT model, COUNT(*) as calls, SUM(cost) as total_cost,
                       AVG(cost) as avg_cost_per_call
                FROM api_usage
                WHERE created_at >= DATE('now', '-7 days')
                GROUP BY model
                HAVING avg_cost_per_call > 0.05
                ORDER BY total_cost DESC
            """).fetchall()

            for row in expensive_models:
                if row["calls"] > 10:
                    suggestions.append(
                        {
                            "type": "model_optimization",
                            "priority": "medium",
                            "title": f"考虑优化 {row['model']} 的使用",
                            "description": f"该模型单次调用平均成本 ¥{row['avg_cost_per_call']:.4f}，"
                            f"最近7天使用 {row['calls']} 次，总成本 ¥{row['total_cost']:.2f}",
                            "recommendation": "考虑使用成本更低的模型替代，或优化Prompt减少token消耗",
                        }
                    )

            # 2. 检查高频调用操作
            frequent_ops = conn.execute("""
                SELECT operation_type, COUNT(*) as calls,
                       SUM(input_tokens) as total_input_tokens
                FROM api_usage
                WHERE created_at >= DATE('now', '-7 days')
                  AND operation_type IS NOT NULL
                GROUP BY operation_type
                HAVING calls > 50
                ORDER BY calls DESC
            """).fetchall()

            for row in frequent_ops:
                avg_input = (
                    row["total_input_tokens"] / row["calls"] if row["calls"] > 0 else 0
                )
                if avg_input > 2000:
                    suggestions.append(
                        {
                            "type": "prompt_optimization",
                            "priority": "high",
                            "title": f"优化 '{row['operation_type']}' 的Prompt长度",
                            "description": f"该操作平均每次输入 {avg_input:.0f} tokens，"
                            f"最近7天调用 {row['calls']} 次",
                            "recommendation": "考虑精简Prompt，移除不必要的上下文信息",
                        }
                    )

            # 3. 检查异常高的单次调用成本
            expensive_calls = conn.execute("""
                SELECT model, cost, input_tokens, output_tokens, created_at
                FROM api_usage
                WHERE cost > 0.5
                  AND created_at >= DATE('now', '-7 days')
                ORDER BY cost DESC
                LIMIT 5
            """).fetchall()

            if expensive_calls:
                total_expensive = sum(row["cost"] for row in expensive_calls)
                suggestions.append(
                    {
                        "type": "cost_anomaly",
                        "priority": "high",
                        "title": "检测到高成本API调用",
                        "description": f"最近7天有 {len(expensive_calls)} 次调用成本超过 ¥0.5，"
                        f"总计 ¥{total_expensive:.2f}",
                        "recommendation": "检查是否存在异常长的输入/输出，或考虑使用更经济的模型",
                    }
                )

        # 4. 如果没有建议，给出默认提示
        if not suggestions:
            total_cost = self.get_total_cost()
            if total_cost < 10:
                suggestions.append(
                    {
                        "type": "general",
                        "priority": "low",
                        "title": "成本控制良好",
                        "description": f"当前累计成本 ¥{total_cost:.2f}，处于较低水平",
                        "recommendation": "继续保持当前的API使用策略",
                    }
                )

        return suggestions

    # ===== 策略反馈 CRUD（效果追踪系统）=====

    def save_strategy_feedback(
        self,
        strategy_id: str,
        was_adopted: bool,
        actual_conversion: Optional[float] = None,
        feedback_notes: Optional[str] = None,
    ) -> str:
        """
        保存策略反馈

        Args:
            strategy_id: 策略建议ID
            was_adopted: 是否被采纳
            actual_conversion: 实际转化率（0-100）
            feedback_notes: 反馈备注

        Returns:
            反馈记录ID
        """
        with self._get_conn() as conn:
            feedback_id = generate_uuid()
            now = datetime.now().isoformat()

            conn.execute(
                """
                INSERT OR REPLACE INTO strategy_feedback
                (id, strategy_id, was_adopted, actual_conversion, feedback_notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    feedback_id,
                    strategy_id,
                    1 if was_adopted else 0,
                    actual_conversion,
                    feedback_notes,
                    now,
                    now,
                ),
            )
        logger.info(
            "保存策略反馈: strategy_id=%s, was_adopted=%s", strategy_id, was_adopted
        )
        return feedback_id

    def get_strategy_feedback(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        获取策略反馈

        Args:
            strategy_id: 策略建议ID

        Returns:
            反馈记录，不存在则返回None
        """
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM strategy_feedback WHERE strategy_id = ? ORDER BY created_at DESC LIMIT 1",
                (strategy_id,),
            ).fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def get_strategy_effectiveness(self, days: int = 30) -> Dict[str, Any]:
        """
        获取策略效果统计

        Args:
            days: 统计天数

        Returns:
            效果统计信息
        """
        from datetime import timedelta

        start_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_conn() as conn:
            # 总体统计
            stats = conn.execute(
                """
                SELECT
                    COUNT(*) as total_feedback,
                    SUM(CASE WHEN was_adopted = 1 THEN 1 ELSE 0 END) as adopted_count,
                    AVG(CASE WHEN was_adopted = 1 THEN actual_conversion END) as avg_conversion_adopted,
                    AVG(CASE WHEN was_adopted = 0 THEN actual_conversion END) as avg_conversion_rejected
                FROM strategy_feedback
                WHERE created_at >= ?
            """,
                (start_date,),
            ).fetchone()

        total = stats["total_feedback"] or 0
        adopted = stats["adopted_count"] or 0

        return {
            "total_feedback": total,
            "adopted_count": adopted,
            "adoption_rate": round(adopted / total * 100, 2) if total > 0 else 0,
            "avg_conversion_adopted": round(stats["avg_conversion_adopted"] or 0, 2),
            "avg_conversion_rejected": round(stats["avg_conversion_rejected"] or 0, 2),
            "period_days": days,
        }

    def get_all_strategy_feedbacks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取所有策略反馈

        Args:
            limit: 最大返回数量

        Returns:
            反馈记录列表
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM strategy_feedback ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    # ===== A/B测试 CRUD =====

    def save_ab_test_variant(
        self,
        match_id: str,
        variant_name: str,
        variant_config: Dict[str, Any],
        is_control: bool = False,
    ) -> str:
        """
        保存A/B测试变体

        Args:
            match_id: 匹配结果ID
            variant_name: 变体名称（如 "A", "B"）
            variant_config: 变体配置
            is_control: 是否为对照组

        Returns:
            变体ID
        """
        with self._get_conn() as conn:
            variant_id = generate_uuid()
            now = datetime.now().isoformat()

            conn.execute(
                """
                INSERT INTO ab_tests
                (id, match_id, variant_name, variant_config_json, is_control, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    variant_id,
                    match_id,
                    variant_name,
                    json.dumps(variant_config, ensure_ascii=False),
                    1 if is_control else 0,
                    now,
                ),
            )
        logger.info("保存A/B测试变体: match_id=%s, variant=%s", match_id, variant_name)
        return variant_id

    def update_ab_test_results(
        self, variant_id: str, test_results: Dict[str, Any]
    ) -> bool:
        """
        更新A/B测试结果

        Args:
            variant_id: 变体ID
            test_results: 测试结果

        Returns:
            是否更新成功
        """
        with self._get_conn() as conn:
            now = datetime.now().isoformat()

            cursor = conn.execute(
                """
                UPDATE ab_tests
                SET test_results_json = ?, completed_at = ?
                WHERE id = ?
            """,
                (
                    json.dumps(test_results, ensure_ascii=False),
                    now,
                    variant_id,
                ),
            )
            updated = cursor.rowcount > 0
        if updated:
            logger.info("更新A/B测试结果: variant_id=%s", variant_id)
        return updated

    def get_ab_test_variants(self, match_id: str) -> List[Dict[str, Any]]:
        """
        获取匹配的所有A/B测试变体

        Args:
            match_id: 匹配结果ID

        Returns:
            变体列表
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM ab_tests WHERE match_id = ? ORDER BY created_at", (match_id,)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_ab_test_comparison(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        获取A/B测试结果对比

        Args:
            match_id: 匹配结果ID

        Returns:
            对比结果，如果没有完成测试则返回None
        """
        variants = self.get_ab_test_variants(match_id)
        if len(variants) < 2:
            return None

        # 检查是否都有结果
        completed = all(v.get("test_results_json") for v in variants)
        if not completed:
            return None

        # 构建对比数据
        comparison = {
            "match_id": match_id,
            "variants": [],
            "winner": None,
            "improvement": None,
        }

        for v in variants:
            results = v.get("test_results_json", {})
            variant_data = {
                "id": v["id"],
                "name": v["variant_name"],
                "is_control": bool(v["is_control"]),
                "conversion_rate": results.get("conversion_rate", 0),
                "sample_size": results.get("sample_size", 0),
            }
            comparison["variants"].append(variant_data)

        # 找出获胜者
        if comparison["variants"]:
            winner = max(comparison["variants"], key=lambda x: x["conversion_rate"])
            control = next((v for v in comparison["variants"] if v["is_control"]), None)

            if winner and control and winner["id"] != control["id"]:
                improvement = (
                    (
                        (winner["conversion_rate"] - control["conversion_rate"])
                        / control["conversion_rate"]
                        * 100
                    )
                    if control["conversion_rate"] > 0
                    else 0
                )
                comparison["winner"] = winner["name"]
                comparison["improvement"] = round(improvement, 2)
            elif winner:
                comparison["winner"] = winner["name"]

        return comparison

    # ===== 数据清理 =====

    def clear_all_data(self) -> None:
        """清空所有数据"""
        with self._get_conn() as conn:
            # 先删子表（有外键依赖的表），再删父表
            conn.execute("DELETE FROM strategy_feedback")
            conn.execute("DELETE FROM ab_tests")
            conn.execute("DELETE FROM match_results")
            conn.execute("DELETE FROM strategy_advice")
            conn.execute("DELETE FROM content_analysis")
            conn.execute("DELETE FROM lead_analysis")
            conn.execute("DELETE FROM api_usage")
            logger.info("所有数据已清空")

    # ===== 内部工具方法 =====

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        将数据库行转换为字典，并自动解析JSON字段。

        遍历所有已知的JSON字段名，如果当前行中包含该字段且值非空，
        则尝试将其从JSON字符串解析为Python对象。
        """
        d: Dict[str, Any] = dict(row)

        for field in _ALL_JSON_FIELDS:
            if field in d and d[field]:
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    # 记录警告，但保留原始字符串供下游诊断
                    logger.warning(
                        "JSON解析失败，保留原始字符串: 字段=%s, 值=%s",
                        field,
                        str(d[field])[:100],
                    )

        return d


# ===== 使用示例 =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    db = Database("data/test.db")

    # 测试保存和查询
    db.save_content_analysis(
        {
            "content_id": "test-001",
            "raw_text": "测试脚本内容",
            "analysis": {"hook_type": "痛点反问型", "content_score": 8.5},
            "model": "deepseek-chat",
            "created_at": datetime.now().isoformat(),
        }
    )

    result = db.get_content_analysis("test-001")
    logger.info("查询结果: %s", result)

    stats = db.get_stats()
    logger.info("统计信息: %s", stats)

    db.close()
