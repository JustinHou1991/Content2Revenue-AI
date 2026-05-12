#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证管理器 AuthManager - JWT用户认证与授权系统

设计灵感:
- FastAPI JWT认证
- Auth0身份管理
- AWS Cognito用户池

核心特性:
1. JWT令牌管理 - 访问令牌+刷新令牌
2. 用户注册/登录 - 支持邮箱+密码
3. 角色权限控制 - RBAC模型
4. 密码安全 - bcrypt哈希
5. 令牌黑名单 - 登出支持
6. 多租户支持 - 租户隔离

作者: AI Assistant
创建日期: 2026-05-10
版本: 1.0.0
"""

import jwt
import bcrypt
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import json

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """用户角色"""
    ADMIN = "admin"           # 管理员
    USER = "user"             # 普通用户
    GUEST = "guest"           # 访客
    API = "api"               # API用户


class UserStatus(Enum):
    """用户状态"""
    ACTIVE = "active"         # 活跃
    INACTIVE = "inactive"     # 未激活
    SUSPENDED = "suspended"   # 已暂停
    DELETED = "deleted"       # 已删除


@dataclass
class User:
    """用户实体"""
    id: str
    email: str
    password_hash: str
    role: UserRole
    status: UserStatus
    tenant_id: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        """转换为字典（不包含密码）"""
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role.value,
            "status": self.status.value,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "metadata": self.metadata
        }


@dataclass
class TokenPair:
    """令牌对"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


@dataclass
class AuthConfig:
    """认证配置"""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30


class AuthManager:
    """
    认证管理器
    
    使用示例:
        auth = AuthManager(secret_key="your-secret-key")
        
        # 注册用户
        user = auth.register_user("user@example.com", "password123")
        
        # 登录
        tokens = auth.login("user@example.com", "password123")
        
        # 验证令牌
        payload = auth.verify_token(tokens.access_token)
    """
    
    def __init__(self, config: AuthConfig, db_path: str = None):
        self.config = config
        self.db_path = db_path
        self._users: Dict[str, User] = {}  # email -> User
        self._users_by_id: Dict[str, User] = {}  # id -> User
        self._token_blacklist: set = set()
        self._login_attempts: Dict[str, List[datetime]] = {}  # email -> 尝试时间列表
        self._lock = threading.RLock()
        
        # 创建默认管理员
        self._create_default_admin()
    
    def _create_default_admin(self):
        """创建默认管理员账户"""
        admin_email = "admin@content2revenue.ai"
        if admin_email not in self._users:
            admin = User(
                id=str(uuid.uuid4()),
                email=admin_email,
                password_hash=self._hash_password("admin123"),  # 首次登录后必须修改
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE
            )
            self._users[admin_email] = admin
            self._users_by_id[admin.id] = admin
            logger.info(f"创建默认管理员: {admin_email} (密码: admin123，请立即修改)")
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    
    def _create_token(self, user: User, token_type: str = "access") -> str:
        """创建JWT令牌"""
        now = datetime.utcnow()
        
        if token_type == "access":
            expire = now + timedelta(minutes=self.config.access_token_expire_minutes)
        else:  # refresh
            expire = now + timedelta(days=self.config.refresh_token_expire_days)
        
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
            "tenant_id": user.tenant_id,
            "type": token_type,
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4())  # 令牌唯一标识
        }
        
        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)
    
    def _is_account_locked(self, email: str) -> bool:
        """检查账户是否被锁定"""
        if email not in self._login_attempts:
            return False
        
        attempts = self._login_attempts[email]
        cutoff = datetime.now() - timedelta(minutes=self.config.lockout_duration_minutes)
        recent_attempts = [a for a in attempts if a > cutoff]
        
        self._login_attempts[email] = recent_attempts
        return len(recent_attempts) >= self.config.max_login_attempts
    
    def _record_login_attempt(self, email: str):
        """记录登录尝试"""
        if email not in self._login_attempts:
            self._login_attempts[email] = []
        self._login_attempts[email].append(datetime.now())
    
    # ==================== 公共API ====================
    
    def register_user(self, email: str, password: str, 
                     role: UserRole = UserRole.USER,
                     tenant_id: Optional[str] = None) -> User:
        """
        注册用户
        
        Args:
            email: 邮箱地址
            password: 密码（至少8位）
            role: 用户角色
            tenant_id: 租户ID（多租户场景）
            
        Returns:
            创建的用户对象
            
        Raises:
            ValueError: 邮箱已存在或密码太短
        """
        with self._lock:
            if email in self._users:
                raise ValueError(f"邮箱 {email} 已被注册")
            
            if len(password) < self.config.password_min_length:
                raise ValueError(f"密码长度至少 {self.config.password_min_length} 位")
            
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=self._hash_password(password),
                role=role,
                status=UserStatus.ACTIVE,
                tenant_id=tenant_id
            )
            
            self._users[email] = user
            self._users_by_id[user.id] = user
            
            logger.info(f"用户注册成功: {email} (ID: {user.id})")
            return user
    
    def login(self, email: str, password: str) -> TokenPair:
        """
        用户登录
        
        Args:
            email: 邮箱地址
            password: 密码
            
        Returns:
            令牌对（访问令牌+刷新令牌）
            
        Raises:
            ValueError: 登录失败
        """
        with self._lock:
            # 检查账户锁定
            if self._is_account_locked(email):
                raise ValueError("账户已被锁定，请30分钟后重试")
            
            user = self._users.get(email)
            
            if not user or user.status != UserStatus.ACTIVE:
                self._record_login_attempt(email)
                raise ValueError("邮箱或密码错误")
            
            if not self._verify_password(password, user.password_hash):
                self._record_login_attempt(email)
                raise ValueError("邮箱或密码错误")
            
            # 登录成功，清除尝试记录
            if email in self._login_attempts:
                del self._login_attempts[email]
            
            # 更新最后登录时间
            user.last_login = datetime.now()
            
            # 创建令牌
            access_token = self._create_token(user, "access")
            refresh_token = self._create_token(user, "refresh")
            
            logger.info(f"用户登录成功: {email}")
            
            return TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self.config.access_token_expire_minutes * 60
            )
    
    def verify_token(self, token: str) -> Dict:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            令牌payload
            
        Raises:
            ValueError: 令牌无效或已过期
        """
        try:
            # 检查黑名单
            if token in self._token_blacklist:
                raise ValueError("令牌已被撤销")
            
            payload = jwt.decode(
                token, 
                self.config.secret_key, 
                algorithms=[self.config.algorithm]
            )
            
            # 验证令牌类型
            if payload.get("type") != "access":
                raise ValueError("无效的令牌类型")
            
            # 验证用户存在且活跃
            user_id = payload.get("sub")
            user = self._users_by_id.get(user_id)
            
            if not user or user.status != UserStatus.ACTIVE:
                raise ValueError("用户不存在或已被禁用")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValueError("令牌已过期")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"无效的令牌: {e}")
    
    def refresh_token(self, refresh_token: str) -> TokenPair:
        """
        刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            新的令牌对
        """
        try:
            payload = jwt.decode(
                refresh_token,
                self.config.secret_key,
                algorithms=[self.config.algorithm]
            )
            
            if payload.get("type") != "refresh":
                raise ValueError("无效的刷新令牌")
            
            user_id = payload.get("sub")
            user = self._users_by_id.get(user_id)
            
            if not user or user.status != UserStatus.ACTIVE:
                raise ValueError("用户不存在或已被禁用")
            
            # 创建新令牌
            new_access = self._create_token(user, "access")
            new_refresh = self._create_token(user, "refresh")
            
            logger.info(f"令牌刷新成功: {user.email}")
            
            return TokenPair(
                access_token=new_access,
                refresh_token=new_refresh,
                expires_in=self.config.access_token_expire_minutes * 60
            )
            
        except jwt.ExpiredSignatureError:
            raise ValueError("刷新令牌已过期，请重新登录")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"无效的刷新令牌: {e}")
    
    def logout(self, token: str):
        """
        用户登出（将令牌加入黑名单）
        
        Args:
            token: 要撤销的令牌
        """
        with self._lock:
            self._token_blacklist.add(token)
            logger.info("用户登出成功")
    
    def change_password(self, user_id: str, old_password: str, new_password: str):
        """
        修改密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
        """
        with self._lock:
            user = self._users_by_id.get(user_id)
            if not user:
                raise ValueError("用户不存在")
            
            if not self._verify_password(old_password, user.password_hash):
                raise ValueError("旧密码错误")
            
            if len(new_password) < self.config.password_min_length:
                raise ValueError(f"密码长度至少 {self.config.password_min_length} 位")
            
            user.password_hash = self._hash_password(new_password)
            user.updated_at = datetime.now()
            
            logger.info(f"密码修改成功: {user.email}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        return self._users_by_id.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        return self._users.get(email)
    
    def list_users(self, tenant_id: Optional[str] = None) -> List[User]:
        """
        列出用户
        
        Args:
            tenant_id: 租户ID（None则返回所有用户）
        """
        users = list(self._users.values())
        if tenant_id:
            users = [u for u in users if u.tenant_id == tenant_id]
        return users
    
    def update_user_status(self, user_id: str, status: UserStatus):
        """更新用户状态"""
        with self._lock:
            user = self._users_by_id.get(user_id)
            if not user:
                raise ValueError("用户不存在")
            
            user.status = status
            user.updated_at = datetime.now()
            
            logger.info(f"用户状态更新: {user.email} -> {status.value}")
    
    def delete_user(self, user_id: str):
        """删除用户（软删除）"""
        with self._lock:
            user = self._users_by_id.get(user_id)
            if not user:
                raise ValueError("用户不存在")
            
            user.status = UserStatus.DELETED
            user.updated_at = datetime.now()
            
            logger.info(f"用户已删除: {user.email}")
    
    def check_permission(self, user_id: str, required_role: UserRole) -> bool:
        """
        检查用户权限
        
        Args:
            user_id: 用户ID
            required_role: 所需角色
            
        Returns:
            是否有权限
        """
        user = self._users_by_id.get(user_id)
        if not user or user.status != UserStatus.ACTIVE:
            return False
        
        # 角色层级：ADMIN > USER > GUEST > API
        role_hierarchy = {
            UserRole.ADMIN: 4,
            UserRole.USER: 3,
            UserRole.GUEST: 2,
            UserRole.API: 1
        }
        
        return role_hierarchy.get(user.role, 0) >= role_hierarchy.get(required_role, 0)


# 便捷函数
def create_auth_manager(secret_key: str = None, **kwargs) -> AuthManager:
    """创建认证管理器实例"""
    if secret_key is None:
        # 生成随机密钥（仅用于开发）
        import secrets
        secret_key = secrets.token_urlsafe(32)
        logger.warning("使用随机生成的密钥，生产环境请配置固定密钥")
    
    config = AuthConfig(secret_key=secret_key, **kwargs)
    return AuthManager(config)
