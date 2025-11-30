# PlexRename (moviepilot v2 style)

硬链接优先的自动重命名/整理服务，参考 moviepilot v2 流程，生成 Plex 友好的目录结构。

## 特性
- 默认硬链接，不破坏下载目录
- 支持 SOURCE_DIR/DEST_DIR 环境变量一键配置
- PUID/PGID 运行，匹配 NAS 权限
- 内置 Web UI 与 REST API（端口 8000）

## 构建镜像
```bash
docker build -t plexrename .
```

## 运行示例
```bash
docker run -d \
  --name plexrename \
  --network host \
  -e TMDB_API_KEY=你的TMDBKEY \
  -e SOURCE_DIR=/downloads \
  -e DEST_DIR=/library \
  -e TRANSFER_MODE=hardlink \
  -e LOG_LEVEL=INFO \
  -e PUID=1000 -e PGID=1000 \
  -v /share:/share \  # 确保源/目标在同一文件系统以支持硬链接
  -v $(pwd)/config:/config \
  plexrename
```

也可以使用 `docker-compose.yml` 中的示例，按需修改 `SOURCE_DIR`、`DEST_DIR` 和挂载。

## 环境变量
- `TMDB_API_KEY`：TMDB 密钥
- `SOURCE_DIR` / `DEST_DIR`：源/目标目录（提供时自动生成配置）
- `DIRECTORY_NAME`：目录标识，默认 `moviepilot`
- `MEDIA_TYPE`：`auto`/`movie`/`tv`
- `TRANSFER_MODE`：`hardlink`/`copy`/`move`/`symlink`
- `LOG_LEVEL`：日志级别，默认 `INFO`
- `PUID` / `PGID`：容器运行 UID/GID

## 注意事项
- 硬链接要求源目录和目标目录在同一挂载点。
- 如需自定义复杂目录，挂载 `/config/config.json`，或传入 `DIRECTORIES_JSON`。
- Web UI/接口监听 `8000`，若不用 host 网络，可自行映射端口。 
