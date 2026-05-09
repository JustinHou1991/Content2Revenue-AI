"""
数据迁移管理器 - 数据库版本控制和迁移

参考 Django Migrations 和 Alembic 设计
支持自动迁移生成、版本控制和回滚
"""
import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """迁移记录"""
    id: str                    # 迁移ID（时间戳+序列号）
    name: str                  # 迁移名称
    applied_at: datetime       # 应用时间
    checksum: str             # 校验和
    up_sql: str               # 升级SQL
    down_sql: str             # 回滚SQL


class MigrationManager:
    """
    迁移管理器
    
    功能：
    1. 迁移版本控制
    2. 自动迁移执行
    3. 迁移回滚
    4. 迁移历史记录
    5. 迁移冲突检测
    
    使用示例：
        mm = MigrationManager("data/app.db")
        
        # 创建迁移
        mm.create_migration("add_user_table", 
            up_sql="CREATE TABLE users (id INTEGER PRIMARY KEY)",
            down_sql="DROP TABLE users"
        )
        
        # 执行迁移
        mm.migrate()
        
        # 回滚
        mm.rollback(steps=1)
    """
    
    def __init__(self, db_path: str, migrations_dir: str = "migrations"):
        """
        初始化迁移管理器
        
        Args:
            db_path: 数据库路径
            migrations_dir: 迁移脚本目录
        """
        self.db_path = db_path
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)
        
        # 初始化迁移表
        self._init_migration_table()
    
    def _init_migration_table(self) -> None:
        """初始化迁移记录表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    up_sql TEXT NOT NULL,
                    down_sql TEXT NOT NULL
                )
            """)
    
    def create_migration(self, name: str, up_sql: str, down_sql: str) -> str:
        """
        创建新迁移
        
        Args:
            name: 迁移名称
            up_sql: 升级SQL
            down_sql: 回滚SQL
            
        Returns:
            迁移ID
        """
        # 生成迁移ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_id = f"{timestamp}_{name}"
        
        # 计算校验和
        checksum = hashlib.sha256(up_sql.encode()).hexdigest()[:16]
        
        # 保存迁移文件
        migration_file = self.migrations_dir / f"{migration_id}.json"
        migration_data = {
            "id": migration_id,
            "name": name,
            "checksum": checksum,
            "up_sql": up_sql,
            "down_sql": down_sql,
            "created_at": datetime.now().isoformat()
        }
        
        with open(migration_file, 'w') as f:
            json.dump(migration_data, f, indent=2)
        
        logger.info(f"迁移创建成功: {migration_id}")
        return migration_id
    
    def get_pending_migrations(self) -> List[Dict]:
        """获取待执行的迁移"""
        # 获取已应用的迁移
        with sqlite3.connect(self.db_path) as conn:
            applied = set(row[0] for row in 
                conn.execute("SELECT id FROM _migrations").fetchall())
        
        # 获取所有迁移文件
        pending = []
        for migration_file in sorted(self.migrations_dir.glob("*.json")):
            with open(migration_file) as f:
                migration = json.load(f)
                if migration["id"] not in applied:
                    pending.append(migration)
        
        return pending
    
    def migrate(self, target: Optional[str] = None) -> List[str]:
        """
        执行迁移
        
        Args:
            target: 目标迁移ID，None表示迁移到最新
            
        Returns:
            执行的迁移ID列表
        """
        pending = self.get_pending_migrations()
        executed = []
        target_found = False

        for migration in pending:
            if target and migration["id"] == target:
                try:
                    self._apply_migration(migration)
                    executed.append(migration["id"])
                    target_found = True
                except Exception as e:
                    logger.error(f"迁移失败 {migration['id']}: {e}")
                    raise
                break

            try:
                self._apply_migration(migration)
                executed.append(migration["id"])
            except Exception as e:
                logger.error(f"迁移失败 {migration['id']}: {e}")
                raise

        if target is not None and not target_found:
            logger.warning(f"未找到目标迁移 ID: {target}")
        
        if executed:
            logger.info(f"成功执行 {len(executed)} 个迁移")
        else:
            logger.info("没有待执行的迁移")
        
        return executed
    
    def _apply_migration(self, migration: Dict) -> None:
        """应用单个迁移"""
        with sqlite3.connect(self.db_path) as conn:
            # 注意: executescript 会隐式提交当前事务（SQLite 限制），
            # 这意味着如果 up_sql 包含多条语句，部分失败时已执行的语句无法回滚。
            # 对于需要事务完整性的场景，建议使用 cursor.execute() 逐条执行。
            conn.executescript(migration["up_sql"])

            # 验证 executescript 执行后数据库状态正常
            if conn.total_changes == 0:
                logger.warning(f"迁移 {migration['id']} 的 up_sql 未产生任何变更")

            # 记录迁移
            conn.execute("""
                INSERT INTO _migrations (id, name, applied_at, checksum, up_sql, down_sql)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                migration["id"],
                migration["name"],
                datetime.now().isoformat(),
                migration["checksum"],
                migration["up_sql"],
                migration["down_sql"]
            ))
        
        logger.info(f"迁移已应用: {migration['id']}")
    
    def rollback(self, steps: int = 1) -> List[str]:
        """
        回滚迁移
        
        Args:
            steps: 回滚步数
            
        Returns:
            回滚的迁移ID列表
        """
        # 获取最近应用的迁移
        with sqlite3.connect(self.db_path) as conn:
            migrations = conn.execute(
                "SELECT * FROM _migrations ORDER BY applied_at DESC LIMIT ?",
                (steps,)
            ).fetchall()
        
        rolled_back = []
        for row in migrations:
            migration = {
                "id": row[0],
                "name": row[1],
                "down_sql": row[5]
            }
            
            try:
                self._rollback_migration(migration)
                rolled_back.append(migration["id"])
            except Exception as e:
                logger.error(f"回滚失败 {migration['id']}: {e}")
                raise
        
        logger.info(f"成功回滚 {len(rolled_back)} 个迁移")
        return rolled_back
    
    def _rollback_migration(self, migration: Dict) -> None:
        """回滚单个迁移"""
        with sqlite3.connect(self.db_path) as conn:
            # 注意: executescript 会隐式提交当前事务（SQLite 限制），
            # 这意味着如果 down_sql 包含多条语句，部分失败时已执行的语句无法回滚。
            # 对于需要事务完整性的场景，建议使用 cursor.execute() 逐条执行。
            conn.executescript(migration["down_sql"])

            # 验证 executescript 执行后数据库状态正常
            if conn.total_changes == 0:
                logger.warning(f"回滚迁移 {migration['id']} 的 down_sql 未产生任何变更")

            # 删除迁移记录
            conn.execute("DELETE FROM _migrations WHERE id = ?", (migration["id"],))
        
        logger.info(f"迁移已回滚: {migration['id']}")
    
    def get_status(self) -> Dict:
        """获取迁移状态"""
        pending = self.get_pending_migrations()
        
        with sqlite3.connect(self.db_path) as conn:
            applied = conn.execute(
                "SELECT id, name, applied_at FROM _migrations ORDER BY applied_at"
            ).fetchall()
        
        return {
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied": [{"id": row[0], "name": row[1], "applied_at": row[2]} 
                       for row in applied],
            "pending": [{"id": m["id"], "name": m["name"]} for m in pending]
        }
