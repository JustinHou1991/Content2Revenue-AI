"""审计日志 - 记录用户操作和系统事件"""
import json
import os
from datetime import datetime
from typing import Dict, Optional
import sqlite3
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, db_path: str = "data/audit.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_table()

    def _init_table(self):
        """初始化审计表"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    session_id TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    duration_ms INTEGER
                )
            """)

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)")

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def log(self, event_type: str, action: str,
            user_id: Optional[str] = None,
            resource_type: Optional[str] = None,
            resource_id: Optional[str] = None,
            details: Optional[Dict] = None,
            ip_address: Optional[str] = None,
            session_id: Optional[str] = None,
            success: bool = True,
            error_message: Optional[str] = None,
            duration_ms: Optional[int] = None):
        """记录审计日志"""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO audit_logs
                    (timestamp, event_type, user_id, action, resource_type, resource_id,
                     details, ip_address, session_id, success, error_message, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    event_type,
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    json.dumps(details, ensure_ascii=False) if details else None,
                    ip_address,
                    session_id,
                    success,
                    error_message,
                    duration_ms
                ))
        except Exception as e:
            logger.error(f"审计日志记录失败: {e}")

    def log_api_call(self, endpoint: str, method: str,
                    status_code: int, duration_ms: int,
                    user_id: Optional[str] = None):
        """记录 API 调用"""
        self.log(
            event_type="API_CALL",
            action=f"{method} {endpoint}",
            user_id=user_id,
            details={"status_code": status_code},
            success=200 <= status_code < 300,
            duration_ms=duration_ms
        )

    def log_api_request(self, method: str, path: str,
                        status_code: int, duration: float,
                        client_ip: Optional[str] = None):
        """记录 API 请求（中间件使用）"""
        self.log(
            event_type="API_REQUEST",
            action=f"{method} {path}",
            details={"status_code": status_code, "duration_s": round(duration, 4)},
            ip_address=client_ip,
            success=200 <= status_code < 300,
            duration_ms=int(duration * 1000)
        )

    def log_data_access(self, action: str, resource_type: str,
                       resource_id: str, user_id: Optional[str] = None):
        """记录数据访问"""
        self.log(
            event_type="DATA_ACCESS",
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id
        )

    def get_recent_logs(self, limit: int = 100) -> list:
        """获取最近的日志"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
