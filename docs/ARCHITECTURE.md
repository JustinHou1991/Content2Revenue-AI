# Content2Revenue 架构文档

本文档详细描述 Content2Revenue 的系统架构、设计原则和核心组件。

---

## 目录

- [架构概览](#架构概览)
- [分层架构](#分层架构)
- [核心组件](#核心组件)
- [数据流](#数据流)
- [安全架构](#安全架构)
- [性能设计](#性能设计)
- [扩展性设计](#扩展性设计)

---

## 架构概览

Content2Revenue 采用**分层架构**设计，将系统划分为展示层、服务层、基础设施层、能力层和数据层，每层职责清晰，通过定义良好的接口进行交互。

### 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              展示层 (Presentation)                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │   仪表盘     │ │  内容分析    │ │  线索分析    │ │  匹配中心    │       │
│  │  Dashboard   │ │   Content    │ │    Lead      │ │    Match     │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                        │
│  │   策略建议   │ │  成本分析    │ │  系统设置    │                        │
│  │   Strategy   │ │    Cost      │ │   Settings   │                        │
│  └──────────────┘ └──────────────┘ └──────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              服务层 (Services)                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Orchestrator 编排器                          │   │
│  │              (端到端流程协调：内容 → 线索 → 匹配 → 策略)              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ │
│  │ ContentAnalyzer│ │  LeadAnalyzer  │ │  MatchEngine   │ │StrategyAdvisor│ │
│  │   (内容分析)    │ │   (线索分析)    │ │   (匹配引擎)    │ │  (策略顾问)   │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────────┘ │
│                                                                             │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ │
│  │  ScoringModel  │ │  ABTestEngine  │ │  DataCleaner   │ │HealthChecker │ │
│  │   (评分模型)    │ │   (A/B测试)    │ │   (数据清洗)    │ │  (健康检查)   │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      BaseAnalyzer (抽象基类)                         │   │
│  │              模板方法模式：定义分析器标准流程和扩展点                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           基础设施层 (Infrastructure)                        │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │    Config    │ │    Logger    │ │CacheManager  │ │   Export     │       │
│  │   (配置管理)  │ │   (日志系统)  │ │  (缓存管理)  │ │   (数据导出)  │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │InputValidator│ │ AuditLogger  │ │  Performance │ │FieldMapping  │       │
│  │  (输入验证)  │ │   (审计日志)  │ │   (性能监控)  │ │  (字段映射)  │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              能力层 (Capabilities)                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          LLM Client                                  │   │
│  │              统一LLM接口：DeepSeek / 通义千问 / OpenAI                │   │
│  │              JSON Mode + 自动重试 + 结构化输出 + 成本追踪              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          Prompts                                     │   │
│  │              Prompt模板管理 + 版本控制 + A/B测试支持                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据层 (Data)                                   │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │   content_   │ │    lead_     │ │   match_     │ │  strategy_   │       │
│  │  analysis    │ │  analysis    │ │   results    │ │   advice     │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │    ab_       │ │   api_usage  │ │   audit_     │ │analysis_cache│       │
│  │   tests      │ │              │ │    logs      │ │              │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 分层架构

### 1. 展示层 (Presentation Layer)

**职责**：用户界面展示和交互处理

**技术栈**：Streamlit

**组件**：
| 组件 | 文件 | 功能 |
|------|------|------|
| Dashboard | `ui/pages/dashboard.py` | 数据仪表盘，展示关键指标 |
| Content Analysis | `ui/pages/content_analysis.py` | 脚本上传和分析 |
| Lead Analysis | `ui/pages/lead_analysis.py` | 线索导入和画像 |
| Match Center | `ui/pages/match_center.py` | 内容-线索匹配结果 |
| Strategy | `ui/pages/strategy.py` | AI策略建议 |
| Cost Analytics | `ui/pages/cost_analytics.py` | API调用成本统计 |
| Settings | `ui/pages/settings.py` | 配置管理 |

**设计原则**：
- 页面组件化，复用UI组件
- 状态管理简化，依赖Streamlit的session_state
- 响应式设计，适配不同屏幕

### 2. 服务层 (Service Layer)

**职责**：业务逻辑处理，协调各组件完成业务流程

**核心组件**：

#### Orchestrator (编排器)
- 端到端流程协调
- 管理分析流程：内容 → 线索 → 匹配 → 策略
- 错误处理和重试机制
- 事务管理

#### BaseAnalyzer (抽象基类)
- 模板方法模式实现
- 定义标准分析流程：验证 → 构建提示词 → 调用LLM → 解析 → 验证输出
- 抽象方法：`_get_system_prompt`、`_build_prompt`、`_parse_response`
- 提供默认实现：输入验证、输出验证、历史记录

#### 具体分析器
| 分析器 | 职责 | 输出 |
|--------|------|------|
| ContentAnalyzer | 分析抖音脚本内容特征 | Hook类型、情感基调、叙事结构、CTA等 |
| LeadAnalyzer | 构建客户画像 | 行业、痛点、购买阶段、意向度、决策因素 |
| MatchEngine | 评估内容与线索适配度 | 5维度匹配分数、总体匹配度 |
| StrategyAdvisor | 生成内容策略建议 | 内容策略、分发策略、转化预测、A/B测试建议 |

#### 辅助组件
| 组件 | 职责 |
|------|------|
| ScoringModel | 基于历史数据训练轻量级评分模型 |
| ABTestEngine | A/B测试框架，支持统计显著性检验 |
| DataCleaner | 数据清洗Pipeline |
| HealthChecker | 系统健康状态监控 |

### 3. 基础设施层 (Infrastructure Layer)

**职责**：提供通用技术能力，支撑上层业务

**组件**：
| 组件 | 文件 | 功能 |
|------|------|------|
| Config | `config.py` | 三级配置管理（环境变量 > secrets.toml > 数据库） |
| Logger | `utils/logger.py` | 结构化日志，支持轮转和级别控制 |
| CacheManager | `utils/cache_manager.py` | 统一内存缓存，TTL过期，LRU淘汰 |
| InputValidator | `utils/input_validator.py` | 输入验证，XSS/SQL/Prompt注入防护 |
| AuditLogger | `utils/audit_logger.py` | 审计日志，记录敏感操作 |
| Performance | `utils/performance.py` | 性能监控，执行时间追踪 |
| Export | `utils/export.py` | 数据导出（Excel/PDF） |
| FieldMapping | `utils/field_mapping.py` | 智能字段映射 |

### 4. 能力层 (Capabilities Layer)

**职责**：提供AI能力和Prompt管理

**LLM Client**：
- 统一接口封装：DeepSeek / 通义千问 / OpenAI
- JSON Mode支持
- 自动重试机制
- 成本追踪

**Prompts**：
- Prompt模板管理
- 版本控制
- A/B测试支持

### 5. 数据层 (Data Layer)

**职责**：数据持久化存储

**存储**：SQLite

**数据表**：
| 表名 | 用途 |
|------|------|
| content_analysis | 内容分析结果 |
| lead_analysis | 线索分析结果 |
| match_results | 匹配结果 |
| strategy_advice | 策略建议 |
| ab_tests | A/B测试数据 |
| api_usage | API调用记录 |
| audit_logs | 审计日志 |
| analysis_cache | 分析缓存 |

---

## 核心组件

### BaseAnalyzer 设计

```python
class BaseAnalyzer(ABC):
    """分析器抽象基类 - 模板方法模式"""
    
    def analyze(self, input_data: Any) -> Dict[str, Any]:
        """模板方法：定义标准分析流程"""
        # 1. 输入验证
        self._validate_input(input_data)
        
        # 2. 构建提示词
        user_prompt = self._build_prompt_from_input(input_data)
        
        # 3. 调用LLM
        response = self.llm.chat_json(
            system_prompt=self.system_prompt,
            user_content=user_prompt,
            temperature=self._get_temperature()
        )
        
        # 4. 解析响应
        parsed = self._parse_response(response)
        
        # 5. 验证输出
        validated = self._validate_output(parsed)
        
        # 6. 构建结果
        result = self._build_result(validated, input_data)
        
        # 7. 记录历史
        self._record_analysis(result)
        
        return result
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """子类实现：返回系统提示词"""
        pass
    
    @abstractmethod
    def _build_prompt(self, **kwargs) -> str:
        """子类实现：构建用户提示词"""
        pass
    
    @abstractmethod
    def _parse_response(self, response: Dict) -> Dict:
        """子类实现：解析LLM响应"""
        pass
```

**设计优势**：
1. **一致性**：所有分析器遵循相同流程
2. **可扩展**：子类只需实现特定逻辑
3. **可维护**：公共逻辑集中管理
4. **可测试**：各步骤可独立测试

### CacheManager 设计

```python
class CacheManager:
    """缓存管理器 - 线程安全 + LRU淘汰"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._cache: Dict[str, Dict] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._cache.get(key)
            if item and time.time() <= item["expires"]:
                self._hits += 1
                return item["value"]
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            self._cache[key] = {
                "value": value,
                "expires": time.time() + (ttl or self._default_ttl),
                "created": time.time()
            }
```

**设计特点**：
1. **线程安全**：使用锁保护共享数据
2. **LRU淘汰**：超出容量时淘汰最旧条目
3. **TTL过期**：支持自定义过期时间
4. **统计信息**：命中率、大小等统计

### InputValidator 设计

```python
class InputValidator:
    """输入验证器 - 多层安全防护"""
    
    # 危险模式定义
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',                # JS协议
        r'on\w+\s*=',                  # 事件处理器
        r'\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b',  # SQL注入
    ]
    
    INJECTION_PATTERNS = [
        r'忽略.*指令',                 # Prompt注入（中文）
        r'ignore.*instruction',        # Prompt注入（英文）
    ]
    
    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 10000) -> str:
        """文本清洗：HTML转义 + 危险模式过滤"""
        # 长度限制
        if len(text) > max_length:
            text = text[:max_length]
        
        # HTML转义
        text = html.escape(text)
        
        # 危险模式过滤
        for pattern in cls.DANGEROUS_PATTERNS:
            text = re.sub(pattern, '[REMOVED]', text, flags=re.IGNORECASE)
        
        return text
    
    @classmethod
    def check_prompt_injection(cls, text: str) -> Tuple[bool, str]:
        """检测Prompt注入攻击"""
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True, f"检测到可能的Prompt注入: {pattern}"
        return False, ""
```

**防护层次**：
1. **输入层**：长度限制、格式验证
2. **内容层**：HTML转义、危险模式过滤
3. **语义层**：Prompt注入检测

---

## 数据流

### 端到端分析流程

```
用户上传CSV
    │
    ▼
┌─────────────┐
│ DataCleaner │ ← 数据清洗、字段映射、格式验证
└──────┬──────┘
       │
       ▼
┌─────────────┐
│InputValidator│ ← 安全防护：XSS/SQL/Prompt注入检测
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ ContentAnalyzer │ ← 提取内容特征（Hook、情感、CTA等）
│  LeadAnalyzer   │ ← 构建客户画像（行业、痛点、意向度）
└────────┬────────┘
         │
         ▼
┌─────────────┐
│ MatchEngine │ ← 5维度匹配评估
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ StrategyAdvisor │ ← 生成策略建议
└────────┬────────┘
         │
         ▼
┌─────────────┐
│ AuditLogger │ ← 记录操作日志
└─────────────┘
```

### 缓存策略

```
分析请求
    │
    ▼
┌─────────────┐
│ CacheManager │ ← 检查缓存
└──────┬──────┘
       │
   命中 │    未命中
   ┌───┘    └───┐
   ▼            ▼
返回缓存    调用LLM
结果        分析处理
               │
               ▼
           缓存结果
               │
               ▼
           返回结果
```

---

## 安全架构

### 安全层次

```
┌─────────────────────────────────────────┐
│           应用层安全                      │
│  - 用户认证（未来）                       │
│  - 权限控制（未来）                       │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           输入层安全                      │
│  - InputValidator 输入验证               │
│  - Prompt注入检测                         │
│  - XSS/SQL注入防护                        │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           处理层安全                      │
│  - BaseAnalyzer 内置验证                 │
│  - 内容包装（防注入）                      │
│  - 输出验证                               │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           数据层安全                      │
│  - AuditLogger 审计日志                  │
│  - 操作追溯                               │
│  - 敏感数据记录                           │
└─────────────────────────────────────────┘
```

### 安全机制

| 层级 | 机制 | 实现 |
|------|------|------|
| 输入层 | XSS防护 | `InputValidator.sanitize_text()` |
| 输入层 | SQL注入防护 | 正则表达式过滤SQL关键字 |
| 输入层 | Prompt注入防护 | 检测"忽略指令"等攻击模式 |
| 处理层 | 内容包装 | `_wrap_user_content()` 方法 |
| 处理层 | 输入验证 | `BaseAnalyzer._validate_input()` |
| 处理层 | 输出验证 | `BaseAnalyzer._validate_output()` |
| 数据层 | 审计日志 | `AuditLogger` 记录所有操作 |
| 数据层 | 访问记录 | `log_data_access()` 方法 |

---

## 性能设计

### 优化策略

| 策略 | 实现 | 效果 |
|------|------|------|
| 智能缓存 | `CacheManager` + `@cached` 装饰器 | 减少重复API调用，命中率80%+ |
| 批量处理 | `batch_analyze()` 方法 | 减少IO开销，提升吞吐量 |
| 连接复用 | SQLite连接上下文管理器 | 减少数据库连接开销 |
| 线程安全 | 锁保护共享资源 | 支持并发访问 |
| 异步处理 | 线程池执行LLM调用 | 提升响应速度 |

### 性能监控

```python
# 性能监控装饰器
from utils.performance import monitor_performance

@monitor_performance(threshold_ms=1000)
def expensive_operation():
    # 耗时操作
    pass

# 监控结果
# {
#     "function": "expensive_operation",
#     "duration_ms": 1500,
#     "threshold_ms": 1000,
#     "exceeded": True
# }
```

### 缓存策略配置

```python
# 分析器缓存（1小时）
@cached(ttl=3600)
def analyze(self, input_data):
    return super().analyze(input_data)

# 用户配置缓存（5分钟）
@cached(ttl=300)
def get_user_settings(self, user_id):
    return self.db.get_settings(user_id)

# 静态数据缓存（24小时）
@cached(ttl=86400)
def get_reference_data(self):
    return self.load_reference()
```

---

## 扩展性设计

### 分析器扩展

```python
# 继承 BaseAnalyzer 实现新的分析器
class VideoAnalyzer(BaseAnalyzer):
    """视频内容分析器"""
    
    def _get_system_prompt(self) -> str:
        return "你是一个视频内容分析专家..."
    
    def _build_prompt(self, **kwargs) -> str:
        video_info = kwargs.get('data')
        return f"分析视频：{video_info}"
    
    def _parse_response(self, response: Dict) -> Dict:
        return {
            "visual_style": response.get("visual_style"),
            "pacing": response.get("pacing"),
            "engagement_hooks": response.get("engagement_hooks", [])
        }
```

### 健康检查扩展

```python
# 注册自定义健康检查
checker = HealthChecker()

checker.register_check("redis", lambda: {
    "status": "healthy" if redis.ping() else "unhealthy",
    "latency_ms": measure_latency()
})

checker.register_check("external_api", check_external_service)
```

### 审计日志扩展

```python
# 自定义审计事件类型
audit.log(
    event_type="CUSTOM_EVENT",
    action="custom_action",
    details={"custom_field": "value"}
)
```

---

## 部署架构

### 单机部署

```
┌─────────────────────────────────────┐
│           用户浏览器                  │
└─────────────┬───────────────────────┘
              │ HTTP
              ▼
┌─────────────────────────────────────┐
│         Streamlit Server            │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │   UI    │ │ Services│ │  Utils │ │
│  └─────────┘ └─────────┘ └────────┘ │
│  ┌─────────┐ ┌─────────┐            │
│  │  SQLite │ │  Logs   │            │
│  └─────────┘ └─────────┘            │
└─────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Streamlit | Python全栈，快速构建数据应用 |
| 后端 | Python 3.11+ | 异步支持，类型注解 |
| 数据库 | SQLite | 轻量、零依赖、单文件 |
| AI | DeepSeek/通义千问 | OpenAI兼容API |
| 部署 | Docker (可选) | 容器化部署 |

---

## 相关文档

- [API文档](API.md) - 核心API接口说明
- [项目README](../README.md) - 项目概览和快速开始
- [CHANGELOG](../CHANGELOG.md) - 版本更新记录
