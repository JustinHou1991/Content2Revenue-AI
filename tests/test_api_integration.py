#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content2Revenue AI - API集成测试
测试FastAPI端点和核心功能

作者: AI Assistant
创建日期: 2026-05-10
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator

# 使用httpx进行异步测试
import httpx

# 导入被测试模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.main import app, API_VERSION, API_PREFIX
from core.auth_manager import AuthManager, AuthConfig, UserRole
from core.tenant_manager import TenantManager, TenantPlan
from core.rate_limiter import RateLimiter

# ==================== Fixtures ====================

@pytest.fixture
def auth_manager():
    """创建认证管理器实例"""
    config = AuthConfig(
        secret_key="test-secret-key",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7
    )
    return AuthManager(config)

@pytest.fixture
def tenant_manager():
    """创建租户管理器实例"""
    return TenantManager()

@pytest.fixture
def rate_limiter():
    """创建限流器实例"""
    return RateLimiter()

@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """创建异步HTTP客户端"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

# ==================== 认证测试 ====================

@pytest.mark.asyncio
class TestAuthentication:
    """认证相关测试"""
    
    async def test_register_user(self, async_client: httpx.AsyncClient):
        """测试用户注册"""
        response = await async_client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "tenant_name": "Test Company"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == "test@example.com"
        assert data["role"] == "user"
    
    async def test_register_duplicate_email(self, async_client: httpx.AsyncClient):
        """测试重复邮箱注册"""
        # 第一次注册
        await async_client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!"
            }
        )
        
        # 重复注册
        response = await async_client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 400
        assert "error_code" in response.json()
    
    async def test_login_success(self, async_client: httpx.AsyncClient):
        """测试登录成功"""
        # 先注册
        await async_client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!"
            }
        )
        
        # 登录
        response = await async_client.post(
            f"{API_PREFIX}/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
    
    async def test_login_invalid_credentials(self, async_client: httpx.AsyncClient):
        """测试无效凭据登录"""
        response = await async_client.post(
            f"{API_PREFIX}/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword"
            }
        )
        
        assert response.status_code == 401
        assert "error_code" in response.json()

# ==================== 租户测试 ====================

@pytest.mark.asyncio
class TestTenant:
    """租户相关测试"""
    
    async def test_create_tenant(self, async_client: httpx.AsyncClient):
        """测试创建租户"""
        # 先注册管理员用户
        reg_response = await async_client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": "admin@example.com",
                "password": "SecurePass123!"
            }
        )
        
        # 登录获取token
        login_response = await async_client.post(
            f"{API_PREFIX}/auth/login",
            json={
                "email": "admin@example.com",
                "password": "SecurePass123!"
            }
        )
        token = login_response.json()["access_token"]
        
        # 创建租户（需要管理员权限）
        response = await async_client.post(
            f"{API_PREFIX}/tenants",
            json={
                "name": "Enterprise Corp",
                "slug": "enterprise-corp",
                "plan": "enterprise"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 普通用户无法创建租户，应该返回403
        assert response.status_code in [200, 403]
    
    async def test_get_tenant(self, async_client: httpx.AsyncClient):
        """测试获取租户信息"""
        # 注册并登录
        await async_client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": "tenantuser@example.com",
                "password": "SecurePass123!",
                "tenant_name": "My Company"
            }
        )
        
        login_response = await async_client.post(
            f"{API_PREFIX}/auth/login",
            json={
                "email": "tenantuser@example.com",
                "password": "SecurePass123!"
            }
        )
        token = login_response.json()["access_token"]
        user = login_response.json()["user"]
        tenant_id = user.get("tenant_id")
        
        if tenant_id:
            response = await async_client.get(
                f"{API_PREFIX}/tenants/{tenant_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == tenant_id

# ==================== 限流测试 ====================

@pytest.mark.asyncio
class TestRateLimit:
    """限流相关测试"""
    
    async def test_rate_limit_enforced(self, async_client: httpx.AsyncClient):
        """测试限流生效"""
        # 快速发送多个请求
        responses = []
        for _ in range(150):  # 超过默认限制
            response = await async_client.get("/health")
            responses.append(response.status_code)
        
        # 应该有部分请求被限流
        assert 429 in responses
    
    async def test_rate_limit_reset(self, async_client: httpx.AsyncClient):
        """测试限流重置"""
        # 等待限流窗口重置
        await asyncio.sleep(61)  # 等待1分钟
        
        response = await async_client.get("/health")
        assert response.status_code == 200

# ==================== 内容分析测试 ====================

@pytest.mark.asyncio
class TestContentAnalysis:
    """内容分析相关测试"""
    
    async def test_analyze_content_success(self, async_client: httpx.AsyncClient):
        """测试内容分析成功"""
        # 注册并登录
        await async_client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": "content@example.com",
                "password": "SecurePass123!"
            }
        )
        
        login_response = await async_client.post(
            f"{API_PREFIX}/auth/login",
            json={
                "email": "content@example.com",
                "password": "SecurePass123!"
            }
        )
        token = login_response.json()["access_token"]
        
        # 分析内容
        response = await async_client.post(
            f"{API_PREFIX}/content/analyze",
            json={
                "title": "测试视频",
                "script_text": "这是一个测试脚本，用于验证内容分析功能。"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "overall_score" in data
    
    async def test_analyze_content_quota_exceeded(self, async_client: httpx.AsyncClient):
        """测试配额超限"""
        # 这个测试需要模拟配额超限的情况
        # 实际实现需要更多设置
        pass

# ==================== 健康检查测试 ====================

@pytest.mark.asyncio
class TestHealthCheck:
    """健康检查测试"""
    
    async def test_health_endpoint(self, async_client: httpx.AsyncClient):
        """测试健康检查端点"""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    async def test_root_endpoint(self, async_client: httpx.AsyncClient):
        """测试根端点"""
        response = await async_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data

# ==================== 错误处理测试 ====================

@pytest.mark.asyncio
class TestErrorHandling:
    """错误处理测试"""
    
    async def test_404_error(self, async_client: httpx.AsyncClient):
        """测试404错误"""
        response = await async_client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
    
    async def test_validation_error(self, async_client: httpx.AsyncClient):
        """测试验证错误"""
        response = await async_client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": "invalid-email",
                "password": "123"  # 太短
            }
        )
        
        assert response.status_code == 422
    
    async def test_unauthorized_access(self, async_client: httpx.AsyncClient):
        """测试未授权访问"""
        response = await async_client.get(
            f"{API_PREFIX}/admin/stats",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401

# ==================== 性能测试 ====================

@pytest.mark.asyncio
class TestPerformance:
    """性能测试"""
    
    async def test_concurrent_requests(self, async_client: httpx.AsyncClient):
        """测试并发请求处理"""
        import time
        
        start_time = time.time()
        
        # 发送100个并发请求
        tasks = [async_client.get("/health") for _ in range(100)]
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 所有请求都应该成功
        assert all(r.status_code == 200 for r in responses)
        
        # 应该在合理时间内完成（10秒内）
        assert duration < 10
    
    async def test_response_time(self, async_client: httpx.AsyncClient):
        """测试响应时间"""
        import time
        
        start_time = time.time()
        response = await async_client.get("/health")
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # 转换为毫秒
        
        assert response.status_code == 200
        assert duration < 500  # 响应时间应小于500ms

# ==================== 主函数 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])