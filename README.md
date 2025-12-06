# MoviePilot Slim (Rename Only)

精简版，仅保留“媒体识别 + 重命名”能力，提供：

- API：`GET /api/v1/transfer/name` 查询推荐名称；`POST /api/v1/storage/rename` 实际重命名（含递归子文件智能命名）。
- CLI：`python rename_cli.py <path> [--apply]` 获取或直接执行重命名。
- 只支持本地文件/目录重命名，不含下载器、任务调度、插件等。
- 识别：优先 TMDB 搜索（需要 `TMDB_API_KEY`），可选 Douban 搜索（需要 `DOUBAN_COOKIE`）。
- Docker：精简版 `uvicorn` 镜像。

## 配置

环境变量（也可写 `.env`）：
- `TMDB_API_KEY`：必填，用于 TMDB 搜索。
- `DOUBAN_COOKIE`：可选，若提供则尝试豆瓣搜索标题。
- `RENAME_MOVIE_FORMAT`：可选，默认 `{{title}} ({{year}})`。
- `RENAME_TV_FORMAT`：可选，默认 `{{title}} ({{year}})/Season {{season}}/{{title}} - S{{season}}E{{episode}}`.

## 本地运行

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 3060
```

CLI 示例：
```bash
python rename_cli.py "/data/Movie.Title.2023.mkv"
python rename_cli.py "/data/Show.S01E02.mkv" --apply
```

## Docker

```bash
docker build -t moviepilot-slim .
docker run -it --rm -e TMDB_API_KEY=xxx -p 3060:3060 -v /data:/data moviepilot-slim
```

## API 示例

- 查询推荐名称  
`GET /api/v1/transfer/name?path=/data/Movie.Title.2023.mkv&filetype=file`

- 重命名  
`POST /api/v1/storage/rename`  
```json
{
  "path": "/data/Movie.Title.2023.mkv",
  "new_name": "Movie Title (2023).mkv",
  "recursive": false
}
```

若 `recursive=true` 且目标为目录，会为目录内媒体文件自动识别并重命名。
