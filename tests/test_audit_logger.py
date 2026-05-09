"""审计日志测试"""
import pytest
import os
import tempfile
from utils.audit_logger import AuditLogger


class TestAuditLogger:
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            path = f.name
        yield path
        os.unlink(path)

    def test_log_creation(self, temp_db):
        logger = AuditLogger(temp_db)
        logger.log("TEST", "test_action", user_id="user1")

        logs = logger.get_recent_logs(10)
        assert len(logs) == 1
        assert logs[0]["action"] == "test_action"

    def test_log_api_call(self, temp_db):
        logger = AuditLogger(temp_db)
        logger.log_api_call("/api/test", "GET", 200, 150, user_id="user1")

        logs = logger.get_recent_logs(10)
        assert logs[0]["event_type"] == "API_CALL"
        assert logs[0]["duration_ms"] == 150

    def test_log_data_access(self, temp_db):
        logger = AuditLogger(temp_db)
        logger.log_data_access("READ", "users", "user123", user_id="admin1")

        logs = logger.get_recent_logs(10)
        assert logs[0]["event_type"] == "DATA_ACCESS"
        assert logs[0]["resource_type"] == "users"
        assert logs[0]["resource_id"] == "user123"

    def test_log_with_details(self, temp_db):
        logger = AuditLogger(temp_db)
        details = {"key": "value", "count": 42}
        logger.log("CUSTOM", "custom_action", details=details)

        logs = logger.get_recent_logs(10)
        import json
        assert json.loads(logs[0]["details"]) == details

    def test_log_with_error(self, temp_db):
        logger = AuditLogger(temp_db)
        logger.log("TEST", "failed_action", success=False, error_message="Something went wrong")

        logs = logger.get_recent_logs(10)
        assert logs[0]["success"] == 0  # SQLite stores boolean as 0/1
        assert logs[0]["error_message"] == "Something went wrong"

    def test_get_recent_logs_limit(self, temp_db):
        logger = AuditLogger(temp_db)
        for i in range(15):
            logger.log("TEST", f"action_{i}")

        logs = logger.get_recent_logs(5)
        assert len(logs) == 5
        # Most recent should be last inserted
        assert logs[0]["action"] == "action_14"

    def test_log_with_ip_and_session(self, temp_db):
        logger = AuditLogger(temp_db)
        logger.log(
            "LOGIN",
            "user_login",
            user_id="user1",
            ip_address="192.168.1.1",
            session_id="sess_abc123"
        )

        logs = logger.get_recent_logs(10)
        assert logs[0]["ip_address"] == "192.168.1.1"
        assert logs[0]["session_id"] == "sess_abc123"

    def test_multiple_logs_ordering(self, temp_db):
        logger = AuditLogger(temp_db)
        logger.log("TEST", "first")
        logger.log("TEST", "second")
        logger.log("TEST", "third")

        logs = logger.get_recent_logs(10)
        assert len(logs) == 3
        # Should be in reverse chronological order
        assert logs[0]["action"] == "third"
        assert logs[1]["action"] == "second"
        assert logs[2]["action"] == "first"

    def test_log_api_call_failure(self, temp_db):
        logger = AuditLogger(temp_db)
        logger.log_api_call("/api/test", "POST", 500, 2000, user_id="user1")

        logs = logger.get_recent_logs(10)
        assert logs[0]["success"] == 0
        import json
        details = json.loads(logs[0]["details"])
        assert details["status_code"] == 500
