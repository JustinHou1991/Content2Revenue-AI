"""
备份管理器 - 数据库和应用状态备份

提供完整的备份、恢复和回滚功能，确保数据安全。
"""
import os
import shutil
import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """
    备份管理器
    
    功能：
    1. 数据库备份（SQLite）
    2. 配置文件备份
    3. 应用状态备份
    4. 增量备份支持
    5. 自动清理旧备份
    
    使用示例：
        bm = BackupManager("data/backups")
        backup_path = bm.create_backup("data/content2revenue.db")
        bm.restore_backup(backup_path)
    """
    
    def __init__(self, backup_dir: str = "data/backups"):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份存储目录
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 元数据文件
        self.metadata_file = self.backup_dir / "backups.json"
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """加载备份元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {"backups": []}
    
    def _save_metadata(self) -> None:
        """保存备份元数据"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def create_backup(self, db_path: str, 
                     config_paths: Optional[List[str]] = None,
                     name: str = "",
                     description: str = "") -> str:
        """
        创建完整备份
        
        Args:
            db_path: 数据库文件路径
            config_paths: 配置文件路径列表
            name: 备份名称
            description: 备份描述
            
        Returns:
            备份路径
        """
        # 生成备份ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = name or f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(exist_ok=True)
        
        try:
            # 1. 备份数据库（使用 SQLite 的在线备份）
            db_backup_path = backup_path / "database.db"
            self._backup_database(db_path, str(db_backup_path))
            
            # 2. 备份配置文件
            if config_paths:
                config_backup_path = backup_path / "configs"
                config_backup_path.mkdir(exist_ok=True)
                for config_path in config_paths:
                    if Path(config_path).exists():
                        shutil.copy2(config_path, config_backup_path)
            
            # 3. 计算校验和
            checksum = self._calculate_checksum(str(backup_path))
            
            # 4. 记录元数据
            backup_info = {
                "id": backup_id,
                "timestamp": timestamp,
                "description": description,
                "checksum": checksum,
                "db_path": db_path,
                "config_paths": config_paths or [],
                "size": self._get_directory_size(str(backup_path))
            }
            self.metadata["backups"].append(backup_info)
            self._save_metadata()
            
            logger.info(f"备份创建成功: {backup_id}")
            return str(backup_path)
            
        except Exception as e:
            # 清理失败的备份
            shutil.rmtree(backup_path, ignore_errors=True)
            logger.error(f"备份创建失败: {e}")
            raise
    
    def _backup_database(self, source: str, destination: str) -> None:
        """
        备份数据库（使用 SQLite 在线备份API）
        
        优点：
        - 不锁定数据库
        - 支持并发写入
        - 事务安全
        """
        source_conn = sqlite3.connect(source)
        try:
            dest_conn = sqlite3.connect(destination)
            try:
                with dest_conn:
                    source_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            source_conn.close()
    
    def restore_backup(self, backup_id: str, 
                      target_db_path: Optional[str] = None,
                      dry_run: bool = False) -> bool:
        """
        从备份恢复
        
        Args:
            backup_id: 备份ID
            target_db_path: 目标数据库路径（默认覆盖原路径）
            dry_run: 仅验证不执行
            
        Returns:
            是否成功
        """
        # 查找备份
        backup_info = self._get_backup_info(backup_id)
        if not backup_info:
            logger.error(f"备份不存在: {backup_id}")
            return False
        
        backup_path = self.backup_dir / backup_id
        
        # 验证备份完整性
        if not self._verify_backup(backup_id):
            logger.error(f"备份验证失败: {backup_id}")
            return False
        
        if dry_run:
            logger.info(f"备份验证通过: {backup_id}")
            return True

        temp_backup = None
        target = None

        try:
            # 1. 恢复数据库
            db_backup = backup_path / "database.db"
            target = target_db_path or backup_info["db_path"]

            # 创建当前状态的临时备份（用于回滚）
            temp_backup = f"{target}.rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(target, temp_backup)

            # 恢复备份
            shutil.copy2(db_backup, target)

            # 2. 恢复配置文件
            config_backup = backup_path / "configs"
            if config_backup.exists():
                for config_file in config_backup.iterdir():
                    target_config = Path(backup_info["db_path"]).parent / config_file.name
                    shutil.copy2(config_file, target_config)

            logger.info(f"备份恢复成功: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"备份恢复失败: {e}")
            # 尝试从临时备份恢复
            if os.path.exists(temp_backup):
                try:
                    shutil.copy2(temp_backup, target)
                    logger.info(f"已从临时备份恢复: {temp_backup}")
                except Exception as restore_err:
                    logger.error(f"从临时备份恢复也失败: {restore_err}")
            return False
    
    def rollback(self, steps: int = 1) -> bool:
        """
        回滚到之前的版本
        
        Args:
            steps: 回滚步数（1=上一个版本）
            
        Returns:
            是否成功
        """
        backups = self.list_backups()
        if len(backups) < steps + 1:
            logger.error(f"没有足够的备份进行回滚，当前备份数: {len(backups)}")
            return False
        
        target_backup = backups[-(steps + 1)]
        return self.restore_backup(target_backup["id"])
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        return sorted(self.metadata["backups"], 
                     key=lambda x: x["timestamp"])
    
    def cleanup_old_backups(self, keep_count: int = 10) -> None:
        """
        清理旧备份
        
        Args:
            keep_count: 保留的备份数量
        """
        backups = self.list_backups()
        if len(backups) <= keep_count:
            return
        
        to_delete = backups[:-keep_count]
        for backup in to_delete:
            backup_path = self.backup_dir / backup["id"]
            shutil.rmtree(backup_path, ignore_errors=True)
            self.metadata["backups"].remove(backup)
            logger.info(f"清理旧备份: {backup['id']}")
        
        self._save_metadata()
    
    def _get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """获取备份信息"""
        for backup in self.metadata["backups"]:
            if backup["id"] == backup_id:
                return backup
        return None
    
    def _verify_backup(self, backup_id: str) -> bool:
        """验证备份完整性"""
        backup_info = self._get_backup_info(backup_id)
        if not backup_info:
            return False
        
        backup_path = self.backup_dir / backup_id
        if not backup_path.exists():
            return False
        
        # 重新计算校验和
        current_checksum = self._calculate_checksum(str(backup_path))
        return current_checksum == backup_info["checksum"]
    
    def _calculate_checksum(self, path: str) -> str:
        """计算目录校验和"""
        hash_obj = hashlib.sha256()
        for file in sorted(Path(path).rglob("*")):
            if file.is_file():
                hash_obj.update(file.read_bytes())
        return hash_obj.hexdigest()[:16]
    
    def _get_directory_size(self, path: str) -> int:
        """获取目录大小"""
        total = 0
        for file in Path(path).rglob("*"):
            if file.is_file():
                total += file.stat().st_size
        return total


# 为兼容性添加 BackupMetadata 类
class BackupMetadata:
    """备份元数据"""
    def __init__(self, id: str, timestamp: str, description: str = "", checksum: str = "", **kwargs):
        self.id = id
        self.timestamp = timestamp
        self.description = description
        self.checksum = checksum
        for k, v in kwargs.items():
            setattr(self, k, v)
