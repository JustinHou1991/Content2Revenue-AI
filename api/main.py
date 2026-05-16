#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content2Revenue AI - API开放平台
基于FastAPI的企业级RESTful API

作者: AI Assistant
创建日期: 2026-05-10
版本: 1.0.0
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.auth_manager import AuthManager, AuthConfig, UserRole, UserStatus, create_auth_manager
from core.tenant_manager import TenantManager, Tenant, TenantPlan
from core.rate_limiter import RateLimiter, RateLimitConfig
from utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

# ==================== 配置 ====================

API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# 初始化核心组件
_jwt_secret = os.getenv("JWT_SECRET_KEY")
if not _jwt_secret:
    import secrets
    _jwt_secret = secrets.token_urlsafe(32)
    import logging
    logging.getLogger(__name__).warning(
        "未设置 JWT_SECRET_KEY 环境变量，使用随机密钥。"
        "生产环境必须设置 JWT_SECRET_KEY 以保持会话持久性。"
    )

auth_config = AuthConfig(
    secret_key=_jwt_secret,
    access_token_expire_minutes=30,
    refresh_token_expire_days=7
)

auth_manager = AuthManager(auth_config)
tenant_manager = TenantManager()
rate_limiter = RateLimiter()
audit_logger = AuditLogger()

# ==================== Pydantic模型 ====================

class UserRegister(BaseModel):
    email: str = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=8, description="密码（至少8位）")
    tenant_name: Optional[str] = Field(None, description="租户名称（可选）")

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str
    tenant_id: Optional[str]
    created_at: str

class ContentAnalysisRequest(BaseModel):
    script_text: str = Field(..., max_length=10000, description="抖音脚本内容")
    title: Optional[str] = Field(None, description="内容标题")

class ContentAnalysisResponse(BaseModel):
    id: str
    title: Optional[str]
    hook_type: str
    emotion_tone: str
    structure_type: str
    cta_type: str
    overall_score: float
    analysis_timestamp: str

class LeadAnalysisRequest(BaseModel):
    lead_data: Dict[str, Any] = Field(..., description="线索数据")

class MatchRequest(BaseModel):
    content_id: str
    lead_id: str

class MatchResponse(BaseModel):
    match_score: float
    audience_fit: float
    pain_point_relevance: float
    stage_alignment: float
    cta_appropriateness: float
    emotional_resonance: float
    recommendations: List[str]

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$", description="租户标识")
    plan: TenantPlan = TenantPlan.FREE

class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    status: str
    created_at: str

# ==================== FastAPI应用 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 Content2Revenue API 启动中...")
    yield
    # 关闭时
    print("👋 Content2Revenue API 关闭中...")

app = FastAPI(
    title="Content2Revenue AI API",
    description="AI驱动的内容-商业转化智能平台 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# ==================== 中间件 ====================

# CORS配置
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# 可信主机
_allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=_allowed_hosts
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start_time).total_seconds()
    
    audit_logger.log_api_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=duration,
        client_ip=request.client.host if request.client else None
    )
    
    return response

# 限流中间件
_rate_limit_exclusions = {"/health", "/", "/docs", "/openapi.json", "/redoc"}

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path in _rate_limit_exclusions:
        return await call_next(request)

    client_id = request.headers.get("X-API-Key") or request.client.host
    
    if not rate_limiter.allow_request(client_id):
        return JSONResponse(
            status_code=429,
            content={"error_code": "RATE_LIMIT_EXCEEDED", "message": "请求过于频繁，请稍后重试"}
        )
    
    return await call_next(request)

# ==================== 认证依赖 ====================

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前认证用户"""
    token = credentials.credentials
    try:
        payload = auth_manager.verify_token(token)
        user = auth_manager.get_user(payload["sub"])
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"无效的认证令牌: {str(e)}"
        )

async def require_admin(user = Depends(get_current_user)):
    """要求管理员权限"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return user

# ==================== 错误处理 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("未处理的异常: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="服务器内部错误，请稍后重试"
        ).model_dump()
    )

# ==================== API路由 ====================

@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "Content2Revenue AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# -------------------- 认证路由 --------------------

@app.post(f"{API_PREFIX}/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister):
    """用户注册"""
    try:
        # 如果提供了租户名称，创建租户
        tenant_id = None
        if data.tenant_name:
            tenant = tenant_manager.create_tenant(
                name=data.tenant_name,
                slug=data.tenant_name.lower().replace(" ", "-"),
                plan=TenantPlan.FREE
            )
            tenant_id = tenant.id
        
        # 创建用户
        user = auth_manager.register_user(
            email=data.email,
            password=data.password,
            role=UserRole.USER,
            tenant_id=tenant_id
        )
        
        return UserResponse(**user.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post(f"{API_PREFIX}/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    """用户登录"""
    try:
        tokens = auth_manager.login(data.email, data.password)
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post(f"{API_PREFIX}/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """刷新访问令牌"""
    try:
        tokens = auth_manager.refresh_token(refresh_token)
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post(f"{API_PREFIX}/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """用户登出"""
    auth_manager.logout(credentials.credentials)
    return {"message": "登出成功"}

@app.get(f"{API_PREFIX}/auth/me", response_model=UserResponse)
async def get_me(user = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(**user.to_dict())

# -------------------- 租户路由 --------------------

@app.post(f"{API_PREFIX}/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(data: TenantCreate, user = Depends(require_admin)):
    """创建租户（仅管理员）"""
    try:
        tenant = tenant_manager.create_tenant(
            name=data.name,
            slug=data.slug,
            plan=data.plan
        )
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            plan=tenant.plan.value,
            status=tenant.status.value,
            created_at=tenant.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get(f"{API_PREFIX}/tenants/{{tenant_id}}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, user = Depends(get_current_user)):
    """获取租户信息"""
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    # 检查权限
    if user.tenant_id != tenant_id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无权访问此租户")
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan.value,
        status=tenant.status.value,
        created_at=tenant.created_at.isoformat()
    )

# -------------------- 内容分析路由 --------------------

@app.post(f"{API_PREFIX}/content/analyze", response_model=ContentAnalysisResponse)
async def analyze_content(
    data: ContentAnalysisRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """分析内容"""
    # 检查租户配额
    tenant = tenant_manager.get_tenant(user.tenant_id) if user.tenant_id else None
    if tenant and not tenant_manager.check_quota(tenant.id, "content_analysis"):
        raise HTTPException(status_code=429, detail="已达到本月分析配额上限")
    
    # TODO: 调用实际的内容分析服务
    # 这里返回模拟数据
    import uuid
    
    response = ContentAnalysisResponse(
        id=str(uuid.uuid4()),
        title=data.title,
        hook_type="question",
        emotion_tone="positive",
        structure_type="problem_solution",
        cta_type="direct",
        overall_score=85.5,
        analysis_timestamp=datetime.now().isoformat()
    )
    
    # 异步记录使用
    if tenant:
        background_tasks.add_task(
            tenant_manager.record_usage,
            tenant.id,
            "content_analysis"
        )
    
    return response

@app.get(f"{API_PREFIX}/content/{{content_id}}")
async def get_content(content_id: str, user = Depends(get_current_user)):
    """获取内容分析结果"""
    # TODO: 实现内容查询
    raise HTTPException(status_code=501, detail="功能开发中")

# -------------------- 线索管理路由 --------------------

@app.post(f"{API_PREFIX}/leads/analyze")
async def analyze_lead(
    data: LeadAnalysisRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """分析销售线索"""
    # 检查配额
    tenant = tenant_manager.get_tenant(user.tenant_id) if user.tenant_id else None
    if tenant and not tenant_manager.check_quota(tenant.id, "lead_analysis"):
        raise HTTPException(status_code=429, detail="已达到本月分析配额上限")
    
    # TODO: 调用实际的线索分析服务
    
    if tenant:
        background_tasks.add_task(
            tenant_manager.record_usage,
            tenant.id,
            "lead_analysis"
        )
    
    return {"message": "分析完成", "lead_id": "mock-id"}

# -------------------- 匹配引擎路由 --------------------

@app.post(f"{API_PREFIX}/match", response_model=MatchResponse)
async def match_content_lead(
    data: MatchRequest,
    user = Depends(get_current_user)
):
    """内容-线索匹配"""
    # TODO: 调用实际的匹配引擎
    return MatchResponse(
        match_score=87.5,
        audience_fit=90.0,
        pain_point_relevance=85.0,
        stage_alignment=88.0,
        cta_appropriateness=82.0,
        emotional_resonance=91.0,
        recommendations=[
            "建议在视频前3秒强化痛点共鸣",
            "CTA按钮颜色建议改为橙色",
            "目标受众与内容调性高度匹配"
        ]
    )

@app.post(f"{API_PREFIX}/match/batch")
async def batch_match(
    content_ids: List[str],
    lead_ids: List[str],
    user = Depends(get_current_user)
):
    """批量匹配"""
    # TODO: 实现批量匹配
    return {"message": "批量匹配完成", "matches": []}

# -------------------- 管理路由 --------------------

@app.get(f"{API_PREFIX}/admin/users", response_model=List[UserResponse])
async def list_users(user = Depends(require_admin)):
    """列出所有用户（仅管理员）"""
    users = auth_manager.list_users()
    return [UserResponse(**u.to_dict()) for u in users]

@app.get(f"{API_PREFIX}/admin/stats")
async def get_stats(user = Depends(require_admin)):
    """获取系统统计（仅管理员）"""
    return {
        "total_users": len(auth_manager.list_users()),
        "total_tenants": len(tenant_manager.list_tenants()),
        "api_requests_today": rate_limiter.get_daily_requests(),
        "timestamp": datetime.now().isoformat()
    }

# ==================== 启动 ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
        workers=int(os.getenv("API_WORKERS", 1))
    )
