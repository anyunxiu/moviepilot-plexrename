#!/bin/bash
set -euo pipefail

APP_USER="appuser"
APP_GROUP="appuser"
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# 创建用户和用户组，尽量匹配传入的 UID/GID
if ! getent group "${PGID}" >/dev/null 2>&1; then
    groupadd -g "${PGID}" "${APP_GROUP}"
else
    APP_GROUP="$(getent group "${PGID}" | cut -d: -f1)"
fi

if ! id -u "${PUID}" >/dev/null 2>&1; then
    useradd -u "${PUID}" -g "${PGID}" -M -s /usr/sbin/nologin "${APP_USER}"
else
    APP_USER="$(getent passwd "${PUID}" | cut -d: -f1)"
fi

# 准备目录并设置权限
for dir in /config /data /app/logs; do
    mkdir -p "$dir"
    chown -R "${PUID}:${PGID}" "$dir" || true
done

# 如果未提供配置文件，且传入了目录信息，则自动生成 config.json
if [ ! -f "/config/config.json" ] && [ -n "${SOURCE_DIR:-}" ] && [ -n "${DEST_DIR:-}" ]; then
    cat >/config/config.json <<EOF
{
  "TMDB_API_KEY": "${TMDB_API_KEY:-}",
  "DIRECTORIES": [
    {
      "name": "${DIRECTORY_NAME:-moviepilot}",
      "source_path": "${SOURCE_DIR}",
      "dest_path": "${DEST_DIR}",
      "media_type": "${MEDIA_TYPE:-auto}",
      "enabled": true
    }
  ],
  "TRANSFER_MODE": "${TRANSFER_MODE:-hardlink}",
  "LOG_LEVEL": "${LOG_LEVEL:-INFO}",
  "CONFIG_DIR": "/config"
}
EOF
    echo "[init] generated /config/config.json from environment"
fi

exec gosu "${APP_USER}" "$@"
