# Content2Revenue AI - 数据库迁移计划 (SQLite → PostgreSQL)

## 迁移背景

### 为什么需要迁移

| SQLite限制 | PostgreSQL优势 |
|-----------|---------------|
| 单文件，不适合并发 | 支持高并发连接 |
| 无用户权限管理 | 完善的权限系统 |
| 无网络访问能力 | 支持远程连接 |
| 数据类型有限 | 丰富的数据类型（JSON、数组等） |
| 不适合大规模数据 | 支持TB级数据 |
| 无复制/集群支持 | 主从复制、高可用 |

### 迁移时机
- **当前**: 开发/测试阶段，数据量小，迁移成本低
- **建议**: 在获取首批付费用户前完成迁移

## 目标架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Application   │────▶│  SQLAlchemy     │────▶│   PostgreSQL    │
│   (Python)      │     │  (ORM Layer)    │     │   (Database)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Alembic       │
                       │   (Migrations)  │
                       └─────────────────┘
```

## 迁移步骤

### Phase 1: 准备 (1周)

#### 1.1 安装PostgreSQL
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-15

# Docker
docker run -d \
  --name c2r-postgres \
  -e POSTGRES_USER=c2r \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=content2revenue \
  -p 5432:5432 \
  postgres:15
```

#### 1.2 更新依赖
```bash
pip install psycopg2-binary sqlalchemy alembic
```

#### 1.3 配置数据库连接
```python
# config/database.py
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://c2r:password@localhost:5432/content2revenue"
)

# SQLite兼容配置（开发环境）
SQLITE_URL = "sqlite:///./content2revenue.db"
```

### Phase 2: 模型改造 (1-2周)

#### 2.1 更新SQLAlchemy模型
```python
# models/base.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    status = Column(String(20), default="active")
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON, default={})
    
    # 关系
    tenant = relationship("Tenant", back_populates="users")
    contents = relationship("Content", back_populates="user")

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    plan = Column(String(50), default="free")  # free, pro, enterprise
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    users = relationship("User", back_populates="tenant")

class Content(Base):
    __tablename__ = "contents"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(500))
    script_text = Column(String(10000))
    analysis_result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="contents")
```

#### 2.2 数据库连接管理
```python
# database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./content2revenue.db")

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,  # 自动检测断开的连接
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    from models.base import Base
    Base.metadata.create_all(bind=engine)
```

### Phase 3: 数据迁移 (1周)

#### 3.1 创建迁移脚本
```python
# scripts/migrate_sqlite_to_postgres.py
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
import json
from datetime import datetime

def migrate():
    # 连接SQLite
    sqlite_conn = sqlite3.connect("content2revenue.db")
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    # 连接PostgreSQL
    pg_conn = psycopg2.connect(
        host="localhost",
        database="content2revenue",
        user="c2r",
        password="your_password"
    )
    pg_cur = pg_conn.cursor()
    
    # 获取所有表
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in sqlite_cur.fetchall()]
    
    for table in tables:
        print(f"Migrating table: {table}")
        
        # 读取SQLite数据
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()
        
        if not rows:
            continue
        
        # 构建INSERT语句
        columns = rows[0].keys()
        column_str = ", ".join(columns)
        placeholder_str = ", ".join(["%s"] * len(columns))
        
        # 转换数据
        data = []
        for row in rows:
            row_data = []
            for col in columns:
                val = row[col]
                # 处理JSON字段
                if isinstance(val, str) and val.startswith('{'):
                    try:
                        val = json.loads(val)
                    except:
                        pass
                row_data.append(val)
            data.append(tuple(row_data))
        
        # 批量插入PostgreSQL
        execute_batch(
            pg_cur,
            f"INSERT INTO {table} ({column_str}) VALUES ({placeholder_str})",
            data
        )
        pg_conn.commit()
        
        print(f"  Migrated {len(rows)} rows")
    
    sqlite_conn.close()
    pg_conn.close()
    print("Migration completed!")

if __name__ == "__main__":
    migrate()
```

#### 3.2 数据验证
```python
# scripts/validate_migration.py
def validate():
    """验证数据迁移完整性"""
    # 对比记录数
    # 抽样验证数据内容
    # 检查外键约束
    pass
```

### Phase 4: 应用改造 (1-2周)

#### 4.1 更新Database类
```python
# services/database_pg.py
from database.connection import get_db, init_db
from models.base import User, Content, Lead, MatchResult

class Database:
    """PostgreSQL数据库操作类"""
    
    def __init__(self):
        init_db()
    
    def create_user(self, email: str, password_hash: str, **kwargs) -> User:
        with get_db() as db:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=password_hash,
                **kwargs
            )
            db.add(user)
            db.refresh(user)
            return user
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        with get_db() as db:
            return db.query(User).filter(User.email == email).first()
    
    # ... 其他方法
```

#### 4.2 多租户支持
```python
# middleware/tenant.py
from fastapi import Request, HTTPException
from database.connection import get_db

class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # 从JWT获取tenant_id
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = verify_token(token)
        tenant_id = payload.get("tenant_id")
        
        # 设置租户上下文
        request.state.tenant_id = tenant_id
        
        response = await call_next(request)
        return response
```

### Phase 5: 测试与上线 (1周)

#### 5.1 测试清单
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 性能测试（并发连接）
- [ ] 数据一致性验证
- [ ] 回滚方案测试

#### 5.2 上线策略
```
1. 备份现有SQLite数据库
2. 部署PostgreSQL实例
3. 运行数据迁移脚本
4. 验证数据完整性
5. 切换应用连接到PostgreSQL
6. 监控运行状态
7. 保留SQLite备份1周（应急回滚）
```

## 多租户设计

### 租户隔离方案

```sql
-- 方案1: 行级安全 (RLS) - 推荐
ALTER TABLE contents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON contents
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- 方案2: 分表 (每个租户独立表)
-- 适用于企业级大客户
CREATE TABLE contents_tenant_a (...);
CREATE TABLE contents_tenant_b (...);

-- 方案3: 分库 (每个租户独立数据库)
-- 最高隔离级别，成本也最高
```

### 租户表结构
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    status VARCHAR(20) DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE tenant_usage (
    tenant_id UUID REFERENCES tenants(id),
    date DATE NOT NULL,
    api_calls INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    PRIMARY KEY (tenant_id, date)
);
```

## 性能优化

### 索引策略
```sql
-- 用户表索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tenant ON users(tenant_id);

-- 内容表索引
CREATE INDEX idx_contents_user ON contents(user_id);
CREATE INDEX idx_contents_created ON contents(created_at);
CREATE INDEX idx_contents_tenant ON contents(tenant_id);

-- 复合索引
CREATE INDEX idx_contents_user_created ON contents(user_id, created_at);
```

### 连接池配置
```python
# 生产环境推荐配置
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # 基础连接数
    max_overflow=10,        # 额外连接数
    pool_timeout=30,        # 获取连接超时
    pool_recycle=1800,      # 连接回收时间
    pool_pre_ping=True,     # 连接健康检查
)
```

## 备份与恢复

### 自动备份脚本
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="content2revenue"

# 创建备份
pg_dump -h localhost -U c2r $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# 保留最近30天备份
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: backup_$DATE.sql.gz"
```

### 恢复命令
```bash
# 解压并恢复
gunzip -c backup_20260101_120000.sql.gz | psql -h localhost -U c2r content2revenue
```

## 监控指标

| 指标 | 告警阈值 | 说明 |
|------|---------|------|
| 连接数 | > 80% | 连接池使用率 |
| 查询时间 | > 1s | 慢查询 |
| 磁盘使用 | > 80% | 存储空间 |
| 复制延迟 | > 5s | 主从同步延迟 |

## 成本估算

### 自托管
- **服务器**: $50-100/月 (2核4G)
- **存储**: $10-20/月 (100GB SSD)
- **备份**: $5-10/月
- **总计**: $65-130/月

### 托管服务 (AWS RDS / Azure / 阿里云)
- **db.t3.small**: $15-25/月
- **db.t3.medium**: $50-80/月
- **db.t3.large**: $100-150/月

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 数据丢失 | 高 | 完整备份、验证脚本、灰度迁移 |
| 性能下降 | 中 | 提前做压力测试、优化索引 |
| 迁移失败 | 中 | 保留回滚方案、分批迁移 |
| 兼容性问题 | 低 | 充分测试、SQL方言差异处理 |

## 时间线

| 阶段 | 工期 | 产出 |
|------|------|------|
| Phase 1: 准备 | 1周 | PostgreSQL实例、依赖更新 |
| Phase 2: 模型改造 | 1-2周 | SQLAlchemy模型、连接管理 |
| Phase 3: 数据迁移 | 1周 | 迁移脚本、数据验证 |
| Phase 4: 应用改造 | 1-2周 | Database类更新、多租户 |
| Phase 5: 测试上线 | 1周 | 测试通过、生产上线 |
| **总计** | **5-7周** | 完整PostgreSQL支持 |

---

*文档版本: 1.0 | 更新日期: 2026-05-10*
