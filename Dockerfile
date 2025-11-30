# 使用轻量级 Python 镜像
FROM python:3.11-slim-bookworm

WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    PUID=0 \
    PGID=0

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app /app/app
COPY web /app/web

# 创建数据目录
RUN mkdir -p /config /data /app/logs && \
    chown -R appuser:appuser /config /data /app

# 声明卷
VOLUME ["/config", "/data"]

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
