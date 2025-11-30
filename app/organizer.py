"""
文件整理器 - 集成 Matcher 和 Plex Namer

负责：
1. 使用 Matcher 提取文件信息
2. 使用 Metadata Client 获取元数据
3. 使用 Plex Namer 生成目标路径
4. 执行文件操作（硬链接/复制/移动）
"""
import os
import logging
from typing import Optional, Dict, Any
from enum import Enum

from .matcher import PriorityMatcher, MatchResult
from .plex_namer import PlexNamer
from .metadata import MetadataClient

logger = logging.getLogger(__name__)


class TransferMode(Enum):
    """文件传输模式"""
    HARDLINK = "hardlink"
    COPY = "copy"
    MOVE = "move"
    SYMLINK = "symlink"


class FileOrganizer:
    """文件整理器"""
    
    def __init__(self, metadata_client: MetadataClient, 
                 matcher: PriorityMatcher = None,
                 transfer_mode: TransferMode = TransferMode.HARDLINK):
        """
        初始化文件整理器
        
        :param metadata_client: 元数据客户端
        :param matcher: 优先级匹配器（默认使用默认规则）
        :param transfer_mode: 文件传输模式
        """
        self.metadata_client = metadata_client
        self.matcher = matcher or PriorityMatcher()
        self.transfer_mode = transfer_mode
        logger.info(f"Initialized FileOrganizer with mode: {transfer_mode.value}")
    
    def organize_file(self, source_path: str, dest_base: str) -> Optional[str]:
        """
        整理单个文件
        
        :param source_path: 源文件路径
        :param dest_base: 目标基础路径
        :return: 成功返回目标路径，失败返回 None
        """
        if not os.path.exists(source_path):
            logger.error(f"Source file not found: {source_path}")
            return None
        
        # 1. 使用 Matcher 提取文件信息
        filename = os.path.basename(source_path)
        match_result = self.matcher.match(filename)
        
        logger.info(f"Processing: {filename}")
        logger.debug(f"Match result: type={match_result.media_type}, "
                    f"title={match_result.title}, year={match_result.year}")
        
        # 2. 获取元数据
        metadata = self._fetch_metadata(match_result)
        
        if not metadata:
            logger.warning(f"Metadata not found  for: {filename}")
            return None
        
        # 3. 生成 Plex 路径
        dest_path = self._build_plex_path(
            dest_base, 
            match_result, 
            metadata, 
            os.path.splitext(source_path)[1]
        )
        
        if not dest_path:
            logger.error(f"Failed to build Plex path for: {filename}")
            return None
        
        # 4. 执行文件操作
        if self._transfer_file(source_path, dest_path):
            logger.info(f"Successfully organized: {filename} -> {dest_path}")
            return dest_path
        
        return None
    
    def _fetch_metadata(self, match_result: MatchResult) -> Optional[Dict[str, Any]]:
        """获取元数据"""
        # 如果有精确 ID，直接使用
        if match_result.tmdb_id:
            logger.debug(f"Using TMDB ID: {match_result.tmdb_id}")
            # TODO: 实现通过 ID 直接获取
        
        # 通过标题和年份搜索
        media_type = "tv" if match_result.media_type == "tv" else "movie"
        metadata = self.metadata_client.search(
            match_result.title,
            match_result.year,
            media_type=media_type,
            tmdb_id=match_result.tmdb_id
        )
        
        return metadata
    
    def _build_plex_path(self, dest_base: str, match_result: MatchResult, 
                        metadata: Dict[str, Any], ext: str) -> Optional[str]:
        """构建 Plex 标准路径"""
        title = metadata.get("title", match_result.title)
        year = metadata.get("year", match_result.year)
        
        if match_result.media_type == "tv":
            # 电视剧路径
            season = match_result.season or 1
            episode = match_result.episode or 1
            
            # 尝试获取剧集标题
            episode_title = None
            if metadata.get("tmdb_id"):
                episode_title = self.metadata_client.get_episode_title(
                    metadata["tmdb_id"],
                    season,
                    episode
                )
            
            return PlexNamer.build_tv_path(
                dest_base,
                title,
                season,
                episode,
                year=year,
                episode_title=episode_title,
                ext=ext
            )
        else:
            # 电影路径
            # 优先使用分辨率，其次版本
            version = match_result.resolution or match_result.edition
            
            return PlexNamer.build_movie_path(
                dest_base,
                title,
                year or "Unknown",
                version=version,
                ext=ext
            )
    
    def _transfer_file(self, source: str, dest: str) -> bool:
        """执行文件传输"""
        # 确保目标目录存在
        dest_dir = os.path.dirname(dest)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory {dest_dir}: {e}")
            return False
        
        # 如果目标文件已存在，跳过
        if os.path.exists(dest):
            logger.info(f"Destination already exists: {dest}")
            return True
        
        # 执行传输
        try:
            if self.transfer_mode == TransferMode.HARDLINK:
                os.link(source, dest)
                logger.debug(f"Hardlinked: {source} -> {dest}")
            elif self.transfer_mode == TransferMode.COPY:
                import shutil
                shutil.copy2(source, dest)
                logger.debug(f"Copied: {source} -> {dest}")
            elif self.transfer_mode == TransferMode.MOVE:
                import shutil
                shutil.move(source, dest)
                logger.debug(f"Moved: {source} -> {dest}")
            elif self.transfer_mode == TransferMode.SYMLINK:
                os.symlink(source, dest)
                logger.debug(f"Symlinked: {source} -> {dest}")
            
            return True
        except OSError as e:
            logger.error(f"Transfer failed ({self.transfer_mode.value}): {source} -> {dest} | Error: {e}")
            return False
    
    def scan_directory(self, source_dir: str, dest_base: str, 
                      extensions: tuple = ('.mp4', '.mkv', '.avi', '.mov')) -> Dict[str, Any]:
        """
        扫描并整理整个目录
        
        :param source_dir: 源目录
        :param dest_base: 目标基础路径
        :param extensions: 要处理的文件扩展名
        :return: 统计信息
        """
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        logger.info(f"Scanning directory: {source_dir}")
        
        for root, _, files in os.walk(source_dir):
            for file in files:
                if not file.lower().endswith(extensions):
                    continue
                
                stats['total'] += 1
                file_path = os.path.join(root, file)
                
                result = self.organize_file(file_path, dest_base)
                if result:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
        
        logger.info(f"Scan complete: {stats}")
        return stats
