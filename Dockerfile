# moviepilot v2 风格的硬链接/重命名镜像，适用于 Plex 识别
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    CONFIG_DIR=/config \
    PUID=1000 \
    PGID=1000

# 系统依赖：gosu 用于降权，tzdata 用于时区
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    tzdata \
    ca-certificates \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码与 Web 资源
COPY app /app/app
COPY web /app/web

# 入口脚本负责按 PUID/PGID 运行并生成默认配置
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

VOLUME ["/config", "/data"]
EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
