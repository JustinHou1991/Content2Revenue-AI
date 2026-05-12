#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
租户管理器 TenantManager - 多租户架构支持

核心特性:
1. 租户隔离 - 数据、配置、配额完全隔离
2. 分级套餐 - Free/Pro/Enterprise 三级
3. 配额管理 - 按套餐限制使用量
4. 使用统计 - 实时监控租户使用情况

作者: AI Assistant
创建日期: 2026-05-10
"""

import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TenantPlan(Enum):
    """租户套餐"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantStatus(Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


@dataclass
class QuotaConfig:
    """配额配置"""
    content_analysis_per_month: int
    lead_analysis_per_month: int
    match_operations_per_month: int
    storage_mb: int
    api_calls_per_day: int


# 套餐配额定义
PLAN_QUOTAS = {
    TenantPlan.FREE: QuotaConfig(
        content_analysis_per_month=50,
        lead_analysis_per_month=50,
        match_operations_per_month=100,
        storage_mb=100,
        api_calls_per_day=100
    ),
    TenantPlan.PRO: QuotaConfig(
        content_analysis_per_month=float('inf'),
        lead_analysis_per_month=float('inf'),
        match_operations_per_month=float('inf'),
        storage_mb=1000,
        api_calls_per_day=1000
    ),
    TenantPlan.ENTERPRISE: QuotaConfig(
        content_analysis_per_month=float('inf'),
        lead_analysis_per_month=float('inf'),
        match_operations_per_month=float('inf'),
        storage_mb=10000,
        api_calls_per_day=10000
    )
}


@dataclass
class Tenant:
    """租户实体"""
    id: str
    name: str
    slug: str
    plan: TenantPlan
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageRecord:
    """使用记录"""
    tenant_id: str
    resource_type: str
    usage_count: int
    date: datetime


class TenantManager:
    """
    租户管理器
    
    使用示例:
        manager = TenantManager()
        
        # 创建租户
        tenant = manager.create_tenant("MyCompany", "mycompany", TenantPlan.PRO)
        
        # 检查配额
        if manager.check_quota(tenant.id, "content_analysis"):
            # 执行操作
            manager.record_usage(tenant.id, "content_analysis")
    """
    
    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}  # id -> Tenant
        self._tenants_by_slug: Dict[str, str] = {}  # slug -> id
        self._usage_records: Dict[str, List[UsageRecord]] = {}  # tenant_id -> records
        self._lock = threading.RLock()
    
    def create_tenant(self, name: str, slug: str, 
                      plan: TenantPlan = TenantPlan.FREE) -> Tenant:
        """
        创建租户
        
        Args:
            name: 租户名称
            slug: 租户标识（唯一）
            plan: 套餐类型
            
        Returns:
            创建的租户对象
        """
        with self._lock:
            if slug in self._tenants_by_slug:
                raise ValueError(f"租户标识 '{slug}' 已存在")
            
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name=name,
                slug=slug,
                plan=plan,
                status=TenantStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self._tenants[tenant.id] = tenant
            self._tenants_by_slug[slug] = tenant.id
            
            return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        return self._tenants.get(tenant_id)
    
    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """通过slug获取租户"""
        tenant_id = self._tenants_by_slug.get(slug)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None
    
    def list_tenants(self) -> List[Tenant]:
        """列出所有租户"""
        return list(self._tenants.values())
    
    def update_tenant_plan(self, tenant_id: str, plan: TenantPlan):
        """更新租户套餐"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                raise ValueError("租户不存在")
            
            tenant.plan = plan
            tenant.updated_at = datetime.now()
    
    def update_tenant_status(self, tenant_id: str, status: TenantStatus):
        """更新租户状态"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                raise ValueError("租户不存在")
            
            tenant.status = status
            tenant.updated_at = datetime.now()
    
    def check_quota(self, tenant_id: str, resource_type: str) -> bool:
        """
        检查配额
        
        Args:
            tenant_id: 租户ID
            resource_type: 资源类型 (content_analysis, lead_analysis, match_operations)
            
        Returns:
            是否还有配额
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        if tenant.status != TenantStatus.ACTIVE:
            return False
        
        quota = PLAN_QUOTAS[tenant.plan]
        limit = getattr(quota, f"{resource_type}_per_month", 0)
        
        if limit == float('inf'):
            return True
        
        # 计算本月使用量
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        usage = self._get_monthly_usage(tenant_id, resource_type, current_month)
        
        return usage < limit
    
    def record_usage(self, tenant_id: str, resource_type: str, count: int = 1):
        """
        记录使用
        
        Args:
            tenant_id: 租户ID
            resource_type: 资源类型
            count: 使用数量
        """
        with self._lock:
            record = UsageRecord(
                tenant_id=tenant_id,
                resource_type=resource_type,
                usage_count=count,
                date=datetime.now()
            )
            
            if tenant_id not in self._usage_records:
                self._usage_records[tenant_id] = []
            
            self._usage_records[tenant_id].append(record)
    
    def _get_monthly_usage(self, tenant_id: str, resource_type: str, 
                          month_start: datetime) -> int:
        """获取月度使用量"""
        records = self._usage_records.get(tenant_id, [])
        total = 0
        for record in records:
            if (record.resource_type == resource_type and 
                record.date >= month_start):
                total += record.usage_count
        return total
    
    def get_usage_stats(self, tenant_id: str) -> Dict[str, Any]:
        """获取使用统计"""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return {}
        
        quota = PLAN_QUOTAS[tenant.plan]
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        
        stats = {
            "tenant_id": tenant_id,
            "plan": tenant.plan.value,
            "period": current_month.strftime("%Y-%m"),
            "quotas": {},
            "usage": {}
        }
        
        for resource_type in ["content_analysis", "lead_analysis", "match_operations"]:
            limit = getattr(quota, f"{resource_type}_per_month", 0)
            used = self._get_monthly_usage(tenant_id, resource_type, current_month)
            
            stats["quotas"][resource_type] = "unlimited" if limit == float('inf') else limit
            stats["usage"][resource_type] = used
            
            if limit != float('inf'):
                stats["usage"][f"{resource_type}_percentage"] = round(used / limit * 100, 2)
        
        return stats
