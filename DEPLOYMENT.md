# Content2Revenue AI - 部署指南

## 快速开始（3分钟启动）

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/content2revenue.git
cd content2revenue

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的API Key

# 3. 启动服务
docker-compose up -d

# 4. 访问应用
# 打开浏览器访问 http://localhost:8501
```

### 方式二：Docker直接运行

```bash
# 构建镜像
docker build -t content2revenue:latest .

# 运行容器
docker run -d \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e DEEPSEEK_API_KEY=your_key_here \
  --name content2revenue \
  content2revenue:latest
```

### 方式三：本地开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
streamlit run app.py
```

---

## 环境变量配置

创建 `.env` 文件：

```bash
# API配置（至少配置一个）
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
TONGYI_API_KEY=sk-...

# 数据库配置
DATABASE_PATH=/app/data/content2revenue.db

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=/app/logs

# 备份配置
BACKUP_DIR=/app/backups
BACKUP_RETENTION_DAYS=30

# 应用配置
ENVIRONMENT=production
```

---

## 生产环境部署

### 使用Nginx反向代理

```bash
# 启动完整生产环境（含Nginx）
docker-compose --profile production up -d
```

配置SSL证书：
```bash
# 将证书放入 nginx/ssl/ 目录
mkdir -p nginx/ssl
cp your-cert.pem nginx/ssl/cert.pem
cp your-key.pem nginx/ssl/key.pem
```

### 自动备份

```bash
# 启动备份服务
docker-compose --profile backup up -d

# 备份文件将保存在 ./backups/ 目录
# 默认每天凌晨2点自动备份
# 保留30天的备份历史
```

---

## 开发环境

```bash
# 启动开发环境（支持热重载）
docker-compose --profile dev up -d

# 开发环境特性：
# - 代码修改自动重载
# - 调试日志输出
# - 独立的数据库（content2revenue_dev.db）
# - 端口8502（避免与生产环境冲突）
```

---

## 系统要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2核 | 4核+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 20GB | 50GB+ |
| 网络 | 10Mbps | 100Mbps+ |

---

## 常见问题

### Q: 如何查看日志？
```bash
# 查看应用日志
docker-compose logs -f app

# 查看Nginx日志
docker-compose logs -f nginx
```

### Q: 如何更新应用？
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

### Q: 如何备份数据？
```bash
# 手动触发备份
docker exec content2revenue-app python -c "
from core.backup_manager import BackupManager
bm = BackupManager('/app/backups')
bm.create_backup('/app/data/content2revenue.db')
"
```

### Q: 如何恢复备份？
```bash
# 列出可用备份
docker exec content2revenue-app python -c "
from core.backup_manager import BackupManager
bm = BackupManager('/app/backups')
for b in bm.list_backups():
    print(f'{b['name']} - {b['created_at']}')
"

# 恢复指定备份
docker exec content2revenue-app python -c "
from core.backup_manager import BackupManager
bm = BackupManager('/app/backups')
bm.restore_backup('backup_name', '/app/data/content2revenue.db')
"
```

---

## 安全建议

1. **修改默认配置**：生产环境务必修改所有默认密码
2. **启用HTTPS**：使用Nginx配置SSL证书
3. **限制访问**：配置防火墙，仅开放必要端口
4. **定期备份**：启用自动备份，定期验证备份可恢复性
5. **监控告警**：配置健康检查，设置异常告警

---

## 技术支持

如有部署问题，请：
1. 查看日志：`docker-compose logs`
2. 检查健康状态：`docker-compose ps`
3. 提交Issue：[GitHub Issues](https://github.com/yourusername/content2revenue/issues)

---

*文档版本: 1.0 | 更新日期: 2026-05-10*
