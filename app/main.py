"""
PlexRename 主程序 - 简化版

核心功能：
1. 使用 Matcher 提取文件信息
2. 使用 Metadata Client 获取元数据
3. 使用 Plex Namer 生成标准路径
4. 使用 Organizer 执行文件整理
5. 支持目录监控
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from logging.handlers import RotatingFileHandler
from pydantic import BaseModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

from .config import get_settings, Settings
from .config import save_settings, DirectoryConfig
from .matcher import PriorityMatcher
from .metadata import MetadataClient
from .organizer import FileOrganizer, TransferMode
from .monitor import DirectoryMonitor


# 全局实例
settings: Settings = None
matcher: PriorityMatcher = None
metadata_client: MetadataClient = None
organizer: FileOrganizer = None
monitor: DirectoryMonitor = None
LOG_FILE_PATH = "/app/logs/plexrename.log"
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
INDEX_PATH = WEB_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global settings, matcher, metadata_client, organizer, monitor
    
    logger.info("Starting PlexRename...")
    
    # 加载配置
    settings = get_settings()
    logging.getLogger().setLevel(settings.LOG_LEVEL)
    logger.setLevel(settings.LOG_LEVEL)
    _setup_file_logging(settings.LOG_LEVEL)
    
    # 初始化组件
    matcher = PriorityMatcher()
    metadata_client = MetadataClient(settings.TMDB_API_KEY)

    try:
        transfer_mode = TransferMode(settings.TRANSFER_MODE)
    except ValueError:
        logger.warning(f"Invalid TRANSFER_MODE '{settings.TRANSFER_MODE}', fallback to hardlink")
        transfer_mode = TransferMode.HARDLINK
    organizer = FileOrganizer(
        metadata_client=metadata_client,
        matcher=matcher,
        transfer_mode=transfer_mode
    )
    
    # 初始化目录监控
    monitor = DirectoryMonitor()
    
    # 添加配置的目录到监控
    for dir_config in settings.DIRECTORIES:
        _add_monitor_for_directory(dir_config)
    
    # 启动监控
    monitor.start()
    
    logger.info("PlexRename started successfully")
    
    yield
    
    # 清理
    logger.info("Shutting down PlexRename...")
    monitor.stop()
    _remove_file_logging()


# FastAPI 应用
app = FastAPI(
    title="PlexRename",
    description="媒体文件整理工具 - 优先级匹配 + Plex 标准命名",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/", include_in_schema=False)
def serve_root():
    """返回前端页面，如果缺失则提示服务运行"""
    if INDEX_PATH.exists():
        return FileResponse(str(INDEX_PATH))
    fallback_html = """
    <!doctype html>
    <html><head><meta charset='utf-8'><title>PlexRename</title></head>
    <body style="font-family:Arial;padding:32px;">
      <h2>PlexRename 服务运行中</h2>
      <p>前端文件缺失或未挂载到 /app/web。请确认镜像构建时包含 web/index.html，或将 web 目录挂载到容器 /app/web。</p>
    </body></html>
    """
    return HTMLResponse(content=fallback_html, media_type="text/html")


@app.get("/api/health")
def read_root():
    """健康检查"""
    return {"message": "PlexRename is running", "version": "2.0.0"}


@app.get("/api/status")
def get_status():
    """获取系统状态"""
    return {
        "monitor_running": monitor.is_running() if monitor else False,
        "directories_count": len(settings.DIRECTORIES) if settings else 0,
        "transfer_mode": settings.TRANSFER_MODE if settings else "unknown"
    }


@app.post("/api/scan")
def trigger_scan():
    """手动触发扫描"""
    if not organizer or not settings:
        return {"error": "Not initialized"}
    
    results = []
    for dir_config in settings.DIRECTORIES:
        if not dir_config.enabled:
            continue
        
        stats = organizer.scan_directory(
            dir_config.source_path,
            dir_config.dest_path,
            settings.MEDIA_EXTENSIONS
        )
        
        results.append({
            "directory": dir_config.name,
            "stats": stats
        })
    
    return {"results": results}


@app.get("/api/config")
def get_config():
    """获取配置信息（脱敏）"""
    if not settings:
        return {"error": "Not initialized"}
    
    return {
        "directories": [
            {
                "name": d.name,
                "source_path": d.source_path,
                "dest_path": d.dest_path,
                "media_type": d.media_type,
                "enabled": d.enabled
            }
            for d in settings.DIRECTORIES
        ],
        "transfer_mode": settings.TRANSFER_MODE,
        "log_level": settings.LOG_LEVEL
    }


@app.get("/api/logs")
def get_logs(lines: int = Query(200, ge=10, le=1000)):
    """获取最近日志"""
    if not os.path.exists(LOG_FILE_PATH):
        return {"logs": [], "path": LOG_FILE_PATH}
    
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
            content = f.readlines()
        tail = content[-lines:]
        return {"logs": tail, "path": LOG_FILE_PATH}
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        return {"logs": [], "path": LOG_FILE_PATH, "error": str(e)}


class DirectoryPayload(BaseModel):
    name: str
    source_path: str
    dest_path: str
    media_type: str = "auto"
    enabled: bool = True


@app.post("/api/directories")
def add_directory_api(payload: DirectoryPayload):
    """添加监控目录并立即开始监控"""
    global settings
    if any(d.source_path == payload.source_path for d in settings.DIRECTORIES):
        raise HTTPException(status_code=400, detail="该源目录已存在")
    
    dir_config = DirectoryConfig(
        name=payload.name,
        source_path=payload.source_path,
        dest_path=payload.dest_path,
        media_type=payload.media_type,
        enabled=payload.enabled
    )
    settings.DIRECTORIES.append(dir_config)
    save_settings(settings)
    
    # 即时添加监控
    _add_monitor_for_directory(dir_config)
    
    return {"message": "added", "directory": dir_config}


@app.delete("/api/directories")
def remove_directory_api(source_path: str = Query(..., description="要移除的源目录")):
    """移除监控目录并停止监控"""
    global settings
    before = len(settings.DIRECTORIES)
    settings.DIRECTORIES = [d for d in settings.DIRECTORIES if d.source_path != source_path]
    if len(settings.DIRECTORIES) == before:
        raise HTTPException(status_code=404, detail="未找到该源目录")
    
    save_settings(settings)
    if monitor:
        monitor.remove_watch(source_path)
    return {"message": "removed", "source_path": source_path}


# 静态文件（Web UI）
try:
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True, check_dir=False), name="static")
except RuntimeError:
    logger.warning("Web UI not found, only API available")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


def _setup_file_logging(level: str):
    """添加文件日志处理器"""
    try:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        handler.setLevel(level)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
    except Exception as e:
        logger.error(f"Failed to setup file logging: {e}")


def _remove_file_logging():
    """移除文件日志处理器（优雅退出时调用）"""
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            root_logger.removeHandler(handler)
            handler.close()


def _add_monitor_for_directory(dir_config: DirectoryConfig):
    """启动指定目录的监控并注册回调"""
    if not dir_config.enabled:
        return
    
    if not monitor:
        logger.warning("Monitor not initialized")
        return
    
    def callback(file_path: str):
        if not organizer:
            logger.warning("Organizer not ready")
            return
        organizer.organize_file(file_path, dir_config.dest_path)
    
    extensions = settings.MEDIA_EXTENSIONS if settings else ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.iso')
    added = monitor.add_watch(
        dir_config.source_path,
        callback,
        extensions
    )
    if added:
        logger.info(f"Monitoring: {dir_config.name} ({dir_config.source_path})")
