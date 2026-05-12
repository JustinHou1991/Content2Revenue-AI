# Content2Revenue AI - Docker部署文件
# 支持生产环境和开发环境
# 作者: AI Assistant
# 日期: 2026-05-10

FROM python:3.11-slim as base

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data /app/logs /app/backups

# 设置环境变量
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ============================================
# 生产环境构建阶段
# ============================================
FROM base as production

# 生产环境特定配置
ENV LOG_LEVEL=INFO
ENV ENVIRONMENT=production

# 使用非root用户运行（安全最佳实践）
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ============================================
# 开发环境构建阶段
# ============================================
FROM base as development

# 开发环境特定配置
ENV LOG_LEVEL=DEBUG
ENV ENVIRONMENT=development

# 安装开发依赖
RUN pip install --no-cache-dir pytest pytest-cov black flake8 mypy

# 开发模式启动（支持热重载）
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.runOnSave=true"]
