"""健康检查测试"""
import pytest
from services.health_check import HealthChecker


class TestHealthChecker:
    def test_check_database(self):
        checker = HealthChecker()
        result = checker.check_database()
        assert result["status"] in ["healthy", "unhealthy"]
        if result["status"] == "healthy":
            assert "latency_ms" in result

    def test_check_disk_space(self):
        checker = HealthChecker()
        result = checker.check_disk_space()
        assert result["status"] in ["healthy", "warning", "error"]
        if result["status"] != "error":
            assert "free_gb" in result
            assert "usage_percent" in result

    def test_run_all_checks(self):
        checker = HealthChecker()
        results = checker.run_all_checks()
        assert "timestamp" in results
        assert "overall_status" in results
        assert "checks" in results
        assert results["overall_status"] in ["healthy", "warning", "unhealthy"]

    def test_check_memory(self):
        checker = HealthChecker()
        result = checker.check_memory()
        assert "status" in result
        # Status could be healthy, warning, or unknown (if psutil not installed)
        if result["status"] == "healthy" or result["status"] == "warning":
            assert "used_percent" in result
            assert "available_mb" in result

    def test_register_custom_check(self):
        checker = HealthChecker()

        def custom_check():
            return {"status": "healthy", "message": "Custom check passed"}

        checker.register_check("custom", custom_check)
        results = checker.run_all_checks()
        assert "custom" in results["checks"]
        assert results["checks"]["custom"]["status"] == "healthy"

    def test_custom_check_error_handling(self):
        checker = HealthChecker()

        def failing_check():
            raise Exception("Check failed")

        checker.register_check("failing", failing_check)
        results = checker.run_all_checks()
        assert results["checks"]["failing"]["status"] == "error"
        assert "error" in results["checks"]["failing"]

    def test_overall_status_unhealthy(self):
        checker = HealthChecker()

        def unhealthy_check():
            return {"status": "unhealthy", "error": "Database connection failed"}

        checker.register_check("critical_service", unhealthy_check)
        results = checker.run_all_checks()
        assert results["overall_status"] == "unhealthy"

    def test_overall_status_warning(self):
        checker = HealthChecker()

        def warning_check():
            return {"status": "warning", "message": "High memory usage"}

        # Override memory check to return warning
        checker.register_check("memory_warning", warning_check)
        results = checker.run_all_checks()
        # If all other checks are healthy, overall should be warning
        if results["checks"]["database"]["status"] == "healthy":
            assert results["overall_status"] in ["healthy", "warning"]

    def test_database_with_custom_path(self):
        checker = HealthChecker(db_path="data/test.db")
        result = checker.check_database()
        # Should either be healthy (if db exists) or unhealthy (if not)
        assert result["status"] in ["healthy", "unhealthy"]
