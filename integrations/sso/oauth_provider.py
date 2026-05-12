#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content2Revenue AI - OAuth 2.0 / OIDC SSO 集成
支持Google Workspace, Microsoft 365, 企业微信, 钉钉等

作者: AI Assistant
创建日期: 2026-05-10
版本: 1.0.0
"""

import jwt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlencode, parse_qs, urlparse
import httpx

class OAuthProviderType(str, Enum):
    """OAuth提供商类型"""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    WECHAT_WORK = "wechat_work"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    OKTA = "okta_oidc"
    CUSTOM = "custom_oidc"

@dataclass
class OAuthConfig:
    """OAuth配置"""
    provider_type: OAuthProviderType
    client_id: str
    client_secret: str
    
    # 端点配置
    authorize_url: str
    token_url: str
    userinfo_url: str
    jwks_url: Optional[str] = None
    
    # 可选配置
    scope: str = "openid email profile"
    redirect_uri: str = "https://api.content2revenue.com/auth/oauth/callback"
    
    # 高级配置
    pkce_enabled: bool = True
    state_check: bool = True
    nonce_check: bool = True
    
    # 属性映射
    attribute_mapping: Dict[str, str] = None
    
    def __post_init__(self):
        if self.attribute_mapping is None:
            self.attribute_mapping = {
                "email": "email",
                "name": "name",
                "first_name": "given_name",
                "last_name": "family_name",
                "picture": "picture",
                "sub": "sub"
            }

@dataclass
class OAuthUser:
    """OAuth认证用户"""
    email: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    picture: Optional[str] = None
    sub: Optional[str] = None  # 提供商唯一标识
    provider: str = ""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    raw_attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.raw_attributes is None:
            self.raw_attributes = {}

class OAuthProvider:
    """OAuth 2.0 / OIDC 提供商"""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    def generate_authorize_url(self, state: Optional[str] = None, 
                               nonce: Optional[str] = None,
                               additional_params: Optional[Dict] = None) -> Dict[str, str]:
        """
        生成授权URL
        
        Returns:
            {
                "url": "授权URL",
                "state": "state参数",
                "code_verifier": "PKCE code_verifier（如果启用）"
            }
        """
        # 生成state
        if state is None and self.config.state_check:
            state = secrets.token_urlsafe(32)
        
        # 生成PKCE参数
        code_verifier = None
        code_challenge = None
        if self.config.pkce_enabled:
            code_verifier = secrets.token_urlsafe(64)
            code_challenge = self._generate_code_challenge(code_verifier)
        
        # 生成nonce
        if nonce is None and self.config.nonce_check:
            nonce = secrets.token_urlsafe(32)
        
        # 构建参数
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": self.config.scope,
        }
        
        if state:
            params["state"] = state
        if nonce:
            params["nonce"] = nonce
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        
        if additional_params:
            params.update(additional_params)
        
        # 构建URL
        separator = "&" if "?" in self.config.authorize_url else "?"
        authorize_url = f"{self.config.authorize_url}{separator}{urlencode(params)}"
        
        return {
            "url": authorize_url,
            "state": state,
            "code_verifier": code_verifier,
            "nonce": nonce
        }
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """生成PKCE code_challenge"""
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip('=')
    
    async def exchange_code(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        """
        交换授权码获取令牌
        
        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "id_token": "...",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri,
        }
        
        if code_verifier:
            data["code_verifier"] = code_verifier
        
        response = await self._http_client.post(
            self.config.token_url,
            data=data,
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        
        return response.json()
    
    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """获取用户信息"""
        response = await self._http_client.get(
            self.config.userinfo_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        response.raise_for_status()
        
        return response.json()
    
    async def process_callback(self, code: str, state: Optional[str] = None,
                               expected_state: Optional[str] = None,
                               code_verifier: Optional[str] = None) -> OAuthUser:
        """
        处理OAuth回调
        
        Args:
            code: 授权码
            state: 返回的state
            expected_state: 期望的state
            code_verifier: PKCE code_verifier
            
        Returns:
            OAuthUser对象
        """
        # 验证state
        if self.config.state_check and expected_state and state != expected_state:
            raise ValueError("Invalid state parameter")
        
        # 交换令牌
        token_data = await self.exchange_code(code, code_verifier)
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        id_token = token_data.get("id_token")
        expires_in = token_data.get("expires_in", 3600)
        
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # 获取用户信息
        userinfo = await self.get_userinfo(access_token)
        
        # 映射属性
        mapping = self.config.attribute_mapping
        
        email = self._get_nested_value(userinfo, mapping.get('email', 'email'))
        name = self._get_nested_value(userinfo, mapping.get('name', 'name'))
        first_name = self._get_nested_value(userinfo, mapping.get('first_name', 'given_name'))
        last_name = self._get_nested_value(userinfo, mapping.get('last_name', 'family_name'))
        picture = self._get_nested_value(userinfo, mapping.get('picture', 'picture'))
        sub = self._get_nested_value(userinfo, mapping.get('sub', 'sub'))
        
        return OAuthUser(
            email=email,
            name=name,
            first_name=first_name,
            last_name=last_name,
            picture=picture,
            sub=sub,
            provider=self.config.provider_type.value,
            access_token=access_token,
            refresh_token=refresh_token,
            id_token=id_token,
            expires_at=expires_at,
            raw_attributes=userinfo
        )
    
    def _get_nested_value(self, data: Dict, key: str) -> Optional[Any]:
        """获取嵌套字典值"""
        keys = key.split('.')
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新访问令牌"""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        
        response = await self._http_client.post(
            self.config.token_url,
            data=data,
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        
        return response.json()
    
    async def close(self):
        """关闭HTTP客户端"""
        await self._http_client.aclose()


# 预定义的提供商配置
PROVIDER_CONFIGS = {
    OAuthProviderType.GOOGLE: {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
        "scope": "openid email profile"
    },
    OAuthProviderType.MICROSOFT: {
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "jwks_url": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
        "scope": "openid email profile User.Read"
    },
    OAuthProviderType.GITHUB: {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email"
    }
}


def create_oauth_config(provider_type: OAuthProviderType, 
                        client_id: str, 
                        client_secret: str,
                        **kwargs) -> OAuthConfig:
    """
    创建OAuth配置
    
    Args:
        provider_type: 提供商类型
        client_id: 客户端ID
        client_secret: 客户端密钥
        **kwargs: 额外配置
        
    Returns:
        OAuthConfig对象
    """
    config_data = PROVIDER_CONFIGS.get(provider_type, {})
    config_data.update(kwargs)
    
    return OAuthConfig(
        provider_type=provider_type,
        client_id=client_id,
        client_secret=client_secret,
        **config_data
    )


class OAuthConfigManager:
    """OAuth配置管理器"""
    
    def __init__(self):
        self._configs: Dict[str, OAuthConfig] = {}
        self._providers: Dict[str, OAuthProvider] = {}
    
    def register_provider(self, tenant_id: str, config: OAuthConfig) -> None:
        """注册OAuth提供商"""
        self._configs[tenant_id] = config
        self._providers[tenant_id] = OAuthProvider(config)
    
    def get_provider(self, tenant_id: str) -> Optional[OAuthProvider]:
        """获取OAuth提供商"""
        return self._providers.get(tenant_id)
    
    def remove_provider(self, tenant_id: str) -> None:
        """移除OAuth提供商"""
        provider = self._providers.pop(tenant_id, None)
        if provider:
            # 异步关闭需要await，这里只是移除引用
            pass
        self._configs.pop(tenant_id, None)
    
    def list_providers(self) -> Dict[str, OAuthConfig]:
        """列出所有OAuth配置"""
        return self._configs.copy()


# 全局OAuth配置管理器
oauth_config_manager = OAuthConfigManager()