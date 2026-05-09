"""
配置中心 - 集中式配置管理

支持多环境配置、动态刷新、配置加密
参考 Spring Cloud Config 设计
"""
import os
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from pathlib import Path
import threading
import hashlib
import base64
import fnmatch
import logging

try:
    import yaml
    _yaml_available = True
except ImportError:
    _yaml_available = False

try:
    from cryptography.fernet import Fernet
    _crypto_available = True
except ImportError:
    _crypto_available = False
    Fernet = None

logger = logging.getLogger(__name__)


@dataclass
class ConfigProfile:
    """配置环境档案"""
    name: str  # dev, test, prod
    properties: Dict[str, Any] = field(default_factory=dict)
    parent: Optional[str] = None  # 继承的父环境


class ConfigChangeListener:
    """配置变更监听器"""
    
    def __init__(self, key_pattern: str, callback: Callable):
        """
        初始化监听器
        
        Args:
            key_pattern: 监听的配置键模式（支持通配符 *）
            callback: 变更回调函数 (key, old_value, new_value) -> None
        """
        self.key_pattern = key_pattern
        self.callback = callback
    
    def matches(self, key: str) -> bool:
        """检查键是否匹配模式"""
        return fnmatch.fnmatch(key, self.key_pattern)


class ConfigCenter:
    """
    配置中心
    
    功能：
    1. 多环境配置管理
    2. 动态配置刷新
    3. 配置加密存储
    4. 配置变更监听
    5. 配置版本控制
    
    使用示例：
        config = ConfigCenter()
        config.load_from_file("config.yaml", profile="dev")
        
        # 获取配置
        db_url = config.get("database.url")
        
        # 监听变更
        config.add_listener("database.*", on_db_config_change)
        
        # 动态刷新
        config.refresh()
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化配置中心
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置存储
        self._configs: Dict[str, Any] = {}
        self._profiles: Dict[str, ConfigProfile] = {}
        self._active_profile: str = "default"
        
        # 加密
        self._encryption_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
        
        # 监听器
        self._listeners: List[ConfigChangeListener] = []
        self._lock = threading.RLock()
        
        # 加载环境变量
        self._load_from_env()
    
    def set_encryption_key(self, key: str) -> None:
        """
        设置加密密钥
        
        Args:
            key: 加密密钥字符串
        """
        if not _crypto_available:
            raise ImportError(
                "cryptography 库未安装，无法使用加密功能。"
                "请运行: pip install cryptography"
            )
        # 从密钥生成 Fernet 密钥
        key_bytes = hashlib.sha256(key.encode()).digest()
        self._encryption_key = base64.urlsafe_b64encode(key_bytes)
        self._fernet = Fernet(self._encryption_key)
    
    def load_from_file(self, filepath: str, profile: str = "default") -> None:
        """
        从文件加载配置
        
        Args:
            filepath: 配置文件路径
            profile: 配置环境
        """
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"配置文件不存在: {filepath}")
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix in ['.yaml', '.yml']:
                    if not _yaml_available:
                        raise ImportError(
                            "PyYAML 库未安装，无法加载 YAML 配置文件。"
                            "请运行: pip install pyyaml"
                        )
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            self._load_data(data, profile)
            logger.info(f"配置加载成功: {filepath} (profile: {profile})")
            
        except Exception as e:
            logger.error(f"配置加载失败 {filepath}: {e}")
            raise
    
    def _load_data(self, data: Dict, profile: str) -> None:
        """加载配置数据"""
        with self._lock:
            if profile not in self._profiles:
                self._profiles[profile] = ConfigProfile(name=profile)
            
            # 合并配置
            self._profiles[profile].properties.update(data)
            
            # 如果是当前激活的环境，更新主配置
            if profile == self._active_profile:
                self._configs = self._get_merged_config(profile)
    
    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        env_prefix = "C2R_"
        
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                # C2R_DATABASE_URL -> database.url
                config_key = key[len(env_prefix):].lower().replace("_", ".")
                self._configs[config_key] = value
    
    def _get_merged_config(self, profile: str) -> Dict[str, Any]:
        """获取合并后的配置（包含继承）"""
        result = {}
        
        # 先加载父环境
        prof = self._profiles.get(profile)
        if prof and prof.parent:
            result.update(self._get_merged_config(prof.parent))
        
        # 再加载当前环境
        if prof:
            result.update(prof.properties)
        
        return result
    
    def get(self, key: str, default: Any = None, 
            profile: Optional[str] = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点号分隔，如 database.url）
            default: 默认值
            profile: 指定环境，默认使用当前环境
            
        Returns:
            配置值
        """
        with self._lock:
            configs = self._configs
            
            if profile and profile != self._active_profile:
                configs = self._get_merged_config(profile)
            
            # 支持嵌套键
            keys = key.split(".")
            value = configs
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            # 解密加密值
            if isinstance(value, str) and value.startswith("ENC:"):
                return self._decrypt_value(value[4:])
            
            return value
    
    def set(self, key: str, value: Any, 
            profile: Optional[str] = None,
            encrypt: bool = False) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            profile: 指定环境
            encrypt: 是否加密存储
        """
        with self._lock:
            prof_name = profile or self._active_profile
            
            if prof_name not in self._profiles:
                self._profiles[prof_name] = ConfigProfile(name=prof_name)
            
            # 加密敏感值
            if encrypt and isinstance(value, str):
                value = "ENC:" + self._encrypt_value(value)
            
            # 设置值
            keys = key.split(".")
            config = self._profiles[prof_name].properties
            
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            old_value = config.get(keys[-1])
            config[keys[-1]] = value
            
            # 触发变更监听
            if old_value != value:
                self._notify_change(key, old_value, value)
            
            # 更新主配置
            if prof_name == self._active_profile:
                self._configs = self._get_merged_config(prof_name)
    
    def _encrypt_value(self, value: str) -> str:
        """加密值"""
        if not self._fernet:
            raise ValueError("未设置加密密钥")
        return self._fernet.encrypt(value.encode()).decode()
    
    def _decrypt_value(self, value: str) -> str:
        """解密值"""
        if not self._fernet:
            raise ValueError("未设置加密密钥")
        return self._fernet.decrypt(value.encode()).decode()
    
    def add_listener(self, key_pattern: str, 
                     callback: Callable[[str, Any, Any], None]) -> None:
        """
        添加配置变更监听器
        
        Args:
            key_pattern: 键模式（支持通配符 *）
            callback: 回调函数 (key, old_value, new_value) -> None
        """
        listener = ConfigChangeListener(key_pattern, callback)
        self._listeners.append(listener)
        logger.debug(f"添加配置监听器: {key_pattern}")
    
    def _notify_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知配置变更"""
        for listener in self._listeners:
            if listener.matches(key):
                try:
                    listener.callback(key, old_value, new_value)
                except Exception as e:
                    logger.error(f"配置变更回调错误: {e}")
    
    def switch_profile(self, profile: str) -> None:
        """
        切换配置环境
        
        Args:
            profile: 环境名称
        """
        with self._lock:
            if profile not in self._profiles:
                raise ValueError(f"配置环境不存在: {profile}")
            
            old_profile = self._active_profile
            self._active_profile = profile
            self._configs = self._get_merged_config(profile)
            
            logger.info(f"配置环境切换: {old_profile} -> {profile}")
    
    def refresh(self) -> None:
        """刷新配置（重新加载文件）"""
        # 重新加载所有配置文件
        for profile in self._profiles.values():
            # 这里可以实现从远程配置中心刷新
            pass
        
        # 更新当前配置
        with self._lock:
            self._configs = self._get_merged_config(self._active_profile)
        
        logger.info("配置已刷新")
    
    def save_to_file(self, filepath: str, 
                     profile: Optional[str] = None) -> None:
        """
        保存配置到文件
        
        Args:
            filepath: 文件路径
            profile: 指定环境，默认保存当前环境
        """
        prof_name = profile or self._active_profile
        config = self._get_merged_config(prof_name)
        
        path = Path(filepath)
        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                if not _yaml_available:
                    raise ImportError(
                        "PyYAML 库未安装，无法保存 YAML 配置文件。"
                        "请运行: pip install pyyaml"
                    )
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"配置已保存: {filepath}")


# 全局配置中心实例
config_center = ConfigCenter()
