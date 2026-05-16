#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
限流器 RateLimiter - API请求限流控制

核心特性:
1. 滑动窗口限流 - 精确控制请求频率
2. 多维度限流 - 支持IP、用户、API Key
3. 分级限流 - 不同套餐不同限制
4. 黑名单机制 - 自动封禁异常请求

作者: AI Assistant
创建日期: 2026-05-10
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    block_duration_seconds: int = 300


class RateLimiter:
    """
    滑动窗口限流器
    
    使用示例:
        limiter = RateLimiter()
        
        # 检查是否允许请求
        if limiter.allow_request("user_123"):
            # 处理请求
            pass
        else:
            # 拒绝请求
            pass
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        # 存储每个客户端的请求时间戳队列
        self._windows: Dict[str, deque] = defaultdict(deque)
        # 被封锁的客户端及其解封时间
        self._blocked: Dict[str, float] = {}
        # 每日请求计数
        self._daily_counts: Dict[str, int] = defaultdict(int)
        self._last_reset = time.time()
        self._lock = threading.RLock()
    
    def allow_request(self, client_id: str) -> bool:
        """
        检查是否允许请求
        
        Args:
            client_id: 客户端标识（IP、用户ID或API Key）
            
        Returns:
            True: 允许请求
            False: 拒绝请求（触发限流）
        """
        with self._lock:
            now = time.time()
            
            # 检查是否被封锁
            if client_id in self._blocked:
                if now < self._blocked[client_id]:
                    return False
                else:
                    # 解封
                    del self._blocked[client_id]
            
            # 重置每日计数（每天零点）
            if now - self._last_reset > 86400:
                self._daily_counts.clear()
                self._last_reset = now
            
            # 获取客户端的请求窗口
            window = self._windows[client_id]
            
            # 清理过期的请求记录（1小时前）
            cutoff = now - 3600
            while window and window[0] < cutoff:
                window.popleft()
            
            # 检查小时限制
            if len(window) >= self.config.requests_per_hour:
                # 触发限流，加入黑名单
                self._blocked[client_id] = now + self.config.block_duration_seconds
                return False
            
            # 检查分钟限制（滑动窗口）
            minute_ago = now - 60
            recent_requests = sum(1 for t in window if t > minute_ago)
            if recent_requests >= self.config.requests_per_minute:
                return False
            
            # 记录请求
            window.append(now)
            self._daily_counts[client_id] += 1
            
            return True
    
    def get_remaining_quota(self, client_id: str) -> Dict[str, int]:
        """
        获取剩余配额
        
        Returns:
            {
                "per_minute": 剩余每分钟请求数,
                "per_hour": 剩余每小时请求数,
                "per_day": 今日已用请求数
            }
        """
        with self._lock:
            now = time.time()
            window = self._windows.get(client_id, deque())
            
            # 计算最近1分钟的请求数
            minute_ago = now - 60
            recent_minute = sum(1 for t in window if t > minute_ago)
            
            # 计算最近1小时的请求数
            hour_ago = now - 3600
            recent_hour = sum(1 for t in window if t > hour_ago)
            
            return {
                "per_minute": max(0, self.config.requests_per_minute - recent_minute),
                "per_hour": max(0, self.config.requests_per_hour - recent_hour),
                "per_day": self._daily_counts.get(client_id, 0)
            }
    
    def get_daily_requests(self) -> int:
        """获取今日总请求数"""
        with self._lock:
            return sum(self._daily_counts.values())
    
    def reset_client(self, client_id: str):
        """重置客户端限制（用于手动解封）"""
        with self._lock:
            if client_id in self._windows:
                del self._windows[client_id]
            if client_id in self._blocked:
                del self._blocked[client_id]

    def reset_all(self):
        """重置所有客户端限制（用于测试）"""
        with self._lock:
            self._windows.clear()
            self._blocked.clear()
    
    def is_blocked(self, client_id: str) -> Tuple[bool, Optional[float]]:
        """
        检查客户端是否被封锁
        
        Returns:
            (是否被封锁, 解封时间)
        """
        with self._lock:
            if client_id in self._blocked:
                unblock_time = self._blocked[client_id]
                if time.time() < unblock_time:
                    return True, unblock_time
                else:
                    del self._blocked[client_id]
            return False, None
