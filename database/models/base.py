#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content2Revenue AI - PostgreSQL数据库模型
基于SQLAlchemy 2.0的ORM模型定义

注意：此文件使用 PostgreSQL 方言（UUID、JSONB、枚举类型），适用于生产环境部署。
当前项目默认使用 SQLite 作为数据库后端（通过 services/database.py），此 ORM 模型层
用于配合 SQLAlchemy + PostgreSQL 的迁移路径。

作者: AI Assistant
创建日期: 2026-05-10
版本: 1.0.0
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum as PyEnum

from sqlalchemy import (
    create_engine, Column, String, Integer, DateTime, Boolean, 
    ForeignKey, Text, JSON, Float, Index, Enum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

Base = declarative_base()

# ==================== 枚举定义 ====================

class UserRole(str, PyEnum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    API = "api"

class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class TenantPlan(str, PyEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class TenantStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class ContentStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class LeadStatus(str, PyEnum):
    NEW = "new"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    LOST = "lost"

# ==================== 模型定义 ====================

class Tenant(Base):
    """租户模型 - 多租户架构核心"""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(Enum(TenantPlan), default=TenantPlan.FREE)
    status = Column(Enum(TenantStatus), default=TenantStatus.ACTIVE)
    settings = Column(JSONB, default={})
    quota_limits = Column(JSONB, default={
        "content_analysis_per_month": 50,
        "lead_analysis_per_month": 50,
        "match_operations_per_month": 100,
        "storage_mb": 100,
        "api_calls_per_day": 100
    })
    billing_info = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    contents = relationship("Content", back_populates="tenant", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="tenant", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_tenants_slug', 'slug'),
        Index('idx_tenants_plan', 'plan'),
        Index('idx_tenants_status', 'status'),
    )

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    
    # 个人信息
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(50))
    avatar_url = Column(String(500))
    
    # 租户关联
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # 安全
    last_login_at = Column(DateTime(timezone=True))
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    
    # 元数据
    preferences = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant", back_populates="users")
    contents = relationship("Content", back_populates="user")
    leads = relationship("Lead", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_tenant', 'tenant_id'),
        Index('idx_users_role', 'role'),
    )

class ApiKey(Base):
    """API密钥模型"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(100))
    permissions = Column(JSONB, default=["read"])
    rate_limit = Column(Integer, default=1000)  # 每小时请求数
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index('idx_api_keys_user', 'user_id'),
        Index('idx_api_keys_hash', 'key_hash'),
    )

class Content(Base):
    """内容分析模型"""
    __tablename__ = "contents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # 内容信息
    title = Column(String(500))
    script_text = Column(Text)
    content_type = Column(String(50), default="script")  # script, video, article
    platform = Column(String(50))  # douyin, xiaohongshu, etc.
    
    # 分析结果
    analysis_result = Column(JSONB)
    hook_type = Column(String(50))
    emotion_tone = Column(String(50))
    structure_type = Column(String(50))
    cta_type = Column(String(50))
    overall_score = Column(Float)
    
    # 状态
    status = Column(Enum(ContentStatus), default=ContentStatus.PENDING)
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="contents")
    tenant = relationship("Tenant", back_populates="contents")
    matches = relationship("MatchResult", back_populates="content")
    
    __table_args__ = (
        Index('idx_contents_user', 'user_id'),
        Index('idx_contents_tenant', 'tenant_id'),
        Index('idx_contents_status', 'status'),
        Index('idx_contents_created', 'created_at'),
    )

class Lead(Base):
    """销售线索模型"""
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # 基本信息
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    company = Column(String(255))
    title = Column(String(100))
    
    # 线索数据
    source = Column(String(100))  # 来源渠道
    source_data = Column(JSONB)   # 原始数据
    
    # 分析结果
    analysis_result = Column(JSONB)
    pain_points = Column(JSONB, default=[])
    needs = Column(JSONB, default=[])
    budget_range = Column(String(50))
    timeline = Column(String(50))
    decision_stage = Column(String(50))
    
    # 状态
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW)
    score = Column(Float)
    
    # 交互记录
    last_contact_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="leads")
    tenant = relationship("Tenant", back_populates="leads")
    matches = relationship("MatchResult", back_populates="lead")
    
    __table_args__ = (
        Index('idx_leads_user', 'user_id'),
        Index('idx_leads_tenant', 'tenant_id'),
        Index('idx_leads_status', 'status'),
        Index('idx_leads_email', 'email'),
        Index('idx_leads_score', 'score'),
    )

class MatchResult(Base):
    """内容-线索匹配结果模型"""
    __tablename__ = "match_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.id"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 匹配分数
    match_score = Column(Float, nullable=False)
    audience_fit = Column(Float)
    pain_point_relevance = Column(Float)
    stage_alignment = Column(Float)
    cta_appropriateness = Column(Float)
    emotional_resonance = Column(Float)
    
    # 分析结果
    recommendations = Column(JSONB, default=[])
    gap_analysis = Column(JSONB)
    strategy_suggestions = Column(JSONB)
    
    # 执行状态
    is_executed = Column(Boolean, default=False)
    execution_result = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    content = relationship("Content", back_populates="matches")
    lead = relationship("Lead", back_populates="matches")
    
    __table_args__ = (
        Index('idx_matches_content', 'content_id'),
        Index('idx_matches_lead', 'lead_id'),
        Index('idx_matches_user', 'user_id'),
        Index('idx_matches_score', 'match_score'),
        UniqueConstraint('content_id', 'lead_id', name='uix_content_lead_match'),
    )

class UsageRecord(Base):
    """资源使用记录模型"""
    __tablename__ = "usage_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 使用详情
    resource_type = Column(String(50), nullable=False)  # content_analysis, lead_analysis, match, api_call
    quantity = Column(Integer, default=1)
    metadata = Column(JSONB, default={})
    
    # 成本追踪
    cost_estimate = Column(Float)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    tenant = relationship("Tenant", back_populates="usage_records")
    
    __table_args__ = (
        Index('idx_usage_tenant', 'tenant_id'),
        Index('idx_usage_user', 'user_id'),
        Index('idx_usage_type', 'resource_type'),
        Index('idx_usage_date', 'recorded_at'),
    )

class AuditLog(Base):
    """审计日志模型 - 合规要求"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # 操作详情
    action = Column(String(100), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    resource_type = Column(String(100))  # user, content, lead, etc.
    resource_id = Column(String(36))
    
    # 变更内容
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    
    # 上下文
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    request_id = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_tenant', 'tenant_id'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_created', 'created_at'),
    )

# ==================== 数据库连接管理 ====================

class DatabaseManager:
    """数据库连接管理器"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False,  # 生产环境设为False
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """删除所有表（仅用于测试）"""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()

# 全局数据库管理器实例
db_manager: Optional[DatabaseManager] = None

def init_db(database_url: str):
    """初始化数据库"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager

def get_db():
    """获取数据库会话生成器（用于依赖注入）"""
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()