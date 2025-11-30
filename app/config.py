"""
配置管理模块

管理应用配置，包括：
- 匹配规则配置
- 目录配置
- API 密钥
- 传输模式等
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


class DirectoryConfig(BaseModel):
    """目录配置"""
    name: str
    source_path: str
    dest_path: str
    media_type: str = "auto"  # auto/movie/tv
    enabled: bool = True


class Settings(BaseModel):
    """应用配置"""
    # API 配置
    TMDB_API_KEY: str = Field(default="", description="TMDB API密钥")
    
    # 目录配置
    DIRECTORIES: List[DirectoryConfig] = Field(default_factory=list)
    
    # 传输模式
    TRANSFER_MODE: str = Field(default="hardlink", description="文件传输模式")
    
    # 日志级别
    LOG_LEVEL: str = Field(default="INFO")
    
    # 配置目录
    CONFIG_DIR: str = Field(default="/config")
    
    # 媒体扩展名
    MEDIA_EXTENSIONS: tuple = Field(default=('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.iso'))


# 全局配置实例
_settings: Optional[Settings] = None


def _load_directories_from_env() -> List[DirectoryConfig]:
    """
    从环境变量加载目录配置。
    
    支持两种方式：
    1. DIRECTORIES_JSON 提供完整数组
    2. SOURCE_DIR/DEST_DIR 快速配置单个目录
    """
    directories: List[DirectoryConfig] = []
    
    # 完整 JSON 配置
    if os.getenv("DIRECTORIES_JSON"):
        try:
            data = json.loads(os.getenv("DIRECTORIES_JSON"))
            for item in data:
                directories.append(DirectoryConfig(**item))
            logger.info(f"Loaded {len(directories)} directories from DIRECTORIES_JSON")
        except Exception as e:
            logger.error(f"Failed to parse DIRECTORIES_JSON: {e}")
        return directories
    
    # 简单环境变量配置
    source = os.getenv("SOURCE_DIR")
    dest = os.getenv("DEST_DIR")
    if source and dest:
        directories.append(DirectoryConfig(
            name=os.getenv("DIRECTORY_NAME", "moviepilot"),
            source_path=source,
            dest_path=dest,
            media_type=os.getenv("MEDIA_TYPE", "auto")
        ))
        logger.info(f"Loaded directory from env: {source} -> {dest}")
    
    return directories


def get_settings() -> Settings:
    """获取全局配置实例"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def load_settings(config_path: str = None) -> Settings:
    """
    加载配置
    
    :param config_path: 配置文件路径（默认从环境变量或 /config/config.json）
    :return: Settings 实例
    """
    if config_path is None:
        config_dir = os.getenv("CONFIG_DIR", "/config")
        config_path = os.path.join(config_dir, "config.json")
    
    # 如果配置文件不存在，使用默认配置
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found: {config_path}, using defaults")
        settings = Settings()
    else:
        # 加载配置文件
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            settings = Settings(**config_data)
            
            logger.info(f"Configuration loaded from: {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            settings = Settings()
    
    # 环境变量优先级更高
    if os.getenv("TMDB_API_KEY"):
        settings.TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    
    if os.getenv("TRANSFER_MODE"):
        settings.TRANSFER_MODE = os.getenv("TRANSFER_MODE")
    
    if os.getenv("LOG_LEVEL"):
        settings.LOG_LEVEL = os.getenv("LOG_LEVEL")
    
    # 支持通过环境变量直接注入目录配置
    env_directories = _load_directories_from_env()
    if env_directories:
        settings.DIRECTORIES = env_directories
    
    return settings


def save_settings(settings: Settings, config_path: str = None):
    """
    保存配置
    
    :param settings: Settings 实例
    :param config_path: 配置文件路径
    """
    if config_path is None:
        config_dir = settings.CONFIG_DIR
        config_path = os.path.join(config_dir, "config.json")
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 保存配置（排除敏感信息）
        config_data = settings.dict()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Configuration saved to: {config_path}")
        
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


def add_directory(name: str, source_path: str, dest_path: str, 
                 media_type: str = "auto") -> bool:
    """添加目录配置"""
    settings = get_settings()
    
    # 检查是否已存在
    for dir_config in settings.DIRECTORIES:
        if dir_config.source_path == source_path:
            logger.warning(f"Directory already exists: {source_path}")
            return False
    
    # 添加新配置
    new_dir = DirectoryConfig(
        name=name,
        source_path=source_path,
        dest_path=dest_path,
        media_type=media_type
    )
    
    settings.DIRECTORIES.append(new_dir)
    save_settings(settings)
    
    logger.info(f"Added directory: {name} ({source_path} -> {dest_path})")
    return True


def remove_directory(source_path: str) -> bool:
    """移除目录配置"""
    settings = get_settings()
    
    original_count = len(settings.DIRECTORIES)
    settings.DIRECTORIES = [d for d in settings.DIRECTORIES if d.source_path != source_path]
    
    if len(settings.DIRECTORIES) <original_count:
        save_settings(settings)
        logger.info(f"Removed directory: {source_path}")
        return True
    
    logger.warning(f"Directory not found: {source_path}")
    return False
