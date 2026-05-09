"""健康检查 - 系统状态监控"""
import time
import sqlite3
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HealthChecker:
    """健康检查器"""

    def __init__(self, db_path: str = "data/content2revenue.db"):
        self.db_path = db_path
        self._checks = {}

    def register_check(self, name: str, check_func):
        """注册健康检查项"""
        self._checks[name] = check_func

    def check_database(self) -> Dict[str, Any]:
        """检查数据库健康"""
        start = time.time()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("SELECT 1")
            conn.close()
            return {
                "status": "healthy",
                "latency_ms": round((time.time() - start) * 1000, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        import shutil
        try:
            stat = shutil.disk_usage("/workspace")
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            usage_percent = (stat.used / stat.total) * 100

            status = "healthy" if usage_percent < 90 else "warning"

            return {
                "status": status,
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "usage_percent": round(usage_percent, 2)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def check_memory(self) -> Dict[str, Any]:
        """检查内存使用"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "status": "healthy" if mem.percent < 90 else "warning",
                "used_percent": mem.percent,
                "available_mb": round(mem.available / (1024**2), 2)
            }
        except ImportError:
            return {"status": "unknown", "message": "psutil not installed"}

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }

        # 内置检查
        results["checks"]["database"] = self.check_database()
        results["checks"]["disk"] = self.check_disk_space()
        results["checks"]["memory"] = self.check_memory()

        # 自定义检查
        for name, check_func in self._checks.items():
            try:
                results["checks"][name] = check_func()
            except Exception as e:
                results["checks"][name] = {"status": "error", "error": str(e)}

        # 确定整体状态
        for check in results["checks"].values():
            if check.get("status") == "unhealthy":
                results["overall_status"] = "unhealthy"
                break
            elif check.get("status") == "warning" and results["overall_status"] == "healthy":
                results["overall_status"] = "warning"

        return results
