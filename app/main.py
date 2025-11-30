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
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

from .config import get_settings, Settings
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global settings, matcher, metadata_client, organizer, monitor
    
    logger.info("Starting PlexRename...")
    
    # 加载配置
    settings = get_settings()
    
    # 初始化组件
    matcher = PriorityMatcher()
    metadata_client = MetadataClient(settings.TMDB_API_KEY)
    
    transfer_mode = TransferMode(settings.TRANSFER_MODE)
    organizer = FileOrganizer(
        metadata_client=metadata_client,
        matcher=matcher,
        transfer_mode=transfer_mode
    )
    
    # 初始化目录监控
    monitor = DirectoryMonitor()
    
    # 添加配置的目录到监控
    for dir_config in settings.DIRECTORIES:
        if not dir_config.enabled:
            continue
        
        def create_callback(dest_path):
            def callback(file_path):
                organizer.organize_file(file_path, dest_path)
            return callback
        
        monitor.add_watch(
            dir_config.source_path,
            create_callback(dir_config.dest_path),
            settings.MEDIA_EXTENSIONS
        )
        
        logger.info(f"Monitoring: {dir_config.name} ({dir_config.source_path})")
    
    # 启动监控
    monitor.start()
    
    logger.info("PlexRename started successfully")
    
    yield
    
    # 清理
    logger.info("Shutting down PlexRename...")
    monitor.stop()


# FastAPI 应用
app = FastAPI(
    title="PlexRename",
    description="媒体文件整理工具 - 优先级匹配 + Plex 标准命名",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/")
def read_root():
    """根路径"""
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


# 静态文件（Web UI）
try:
    app.mount("/", StaticFiles(directory="web/dist", html=True), name="static")
except RuntimeError:
    logger.warning("Web UI not found, only API available")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
