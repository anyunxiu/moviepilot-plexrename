"""
Plex 标准命名器

严格遵循 Plex 官方命名规范：
- 电影: /Movies/Movie Title (Year)/Movie Title (Year).ext
- 电视剧: /TV Shows/Show Title/Season XX/Show Title - S01E01 - Episode Title.ext
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PlexNamer:
    """Plex 标准命名器"""
    
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """清理文件名中的非法字符"""
        # Plex 支持的字符，移除文件系统非法字符
        illegal_chars = r'<>:"/\|?*'
        for char in illegal_chars:
            name = name.replace(char, '')
        # 移除首尾空格和点
        return name.strip(). strip('.')
    
    @staticmethod
    def format_movie_filename(title: str, year: str, version: Optional[str] = None, ext: str = ".mp4") -> str:
        """
        生成 Plex 标准电影文件名
        
        格式: Movie Title (Year) - version.ext
        示例: Avatar (2009) - 1080p.mp4
        
        :param title: 电影标题
        :param year: 年份
        :param version: 版本（如 1080p, 4K, 导演剪辑版等）
        :param ext: 文件扩展名
        :return: 文件名
        """
        safe_title = PlexNamer.sanitize_filename(title)
        filename = f"{safe_title} ({year})"
        
        if version:
            safe_version = PlexNamer.sanitize_filename(version)
            filename += f" - {safe_version}"
        
        return filename + ext
    
    @staticmethod
    def format_movie_folder(title: str, year: str) -> str:
        """
        生成 Plex 标准电影文件夹名
        
        格式: Movie Title (Year)
        示例: Avatar (2009)
        """
        safe_title = PlexNamer.sanitize_filename(title)
        return f"{safe_title} ({year})"
    
    @staticmethod
    def format_tv_filename(show_title: str, season: int, episode: int, 
                          episode_title: Optional[str] = None, ext: str = ".mp4") -> str:
        """
        生成 Plex 标准电视剧文件名
        
        格式: Show Title - S01E01 - Episode Title.ext
        示例: Game of Thrones - S08E06 - The Iron Throne.mkv
        
        :param show_title: 剧集标题
        :param season: 季数
        :param episode: 集数
        :param episode_title: 单集标题（可选）
        :param ext: 文件扩展名
        :return: 文件名
        """
        safe_title = PlexNamer.sanitize_filename(show_title)
        filename = f"{safe_title} - S{season:02d}E{episode:02d}"
        
        if episode_title:
            safe_ep_title = PlexNamer.sanitize_filename(episode_title)
            filename += f" - {safe_ep_title}"
        
        return filename + ext
    
    @staticmethod
    def format_tv_show_folder(show_title: str, year: Optional[str] = None) -> str:
        """
        生成 Plex 标准剧集文件夹名
        
        格式: Show Title (Year)
        示例: Game of Thrones (2011)
        """
        safe_title = PlexNamer.sanitize_filename(show_title)
        if year:
            return f"{safe_title} ({year})"
        return safe_title
    
    @staticmethod
    def format_season_folder(season: int) -> str:
        """
        生成 Plex 标准季文件夹名
        
        格式: Season XX
        示例: Season 01
        """
        return f"Season {season:02d}"
    
    @staticmethod
    def build_movie_path(base_path: str, title: str, year: str, 
                        version: Optional[str] = None, ext: str = ".mp4") -> str:
        """
        构建完整的 Plex 电影路径
        
        路径结构: /base_path/Movies/Movie Title (Year)/Movie Title (Year) - version.ext
        
        :return: 完整路径
        """
        folder = PlexNamer.format_movie_folder(title, year)
        filename = PlexNamer.format_movie_filename(title, year, version, ext)
        return os.path.join(base_path, "Movies", folder, filename)
    
    @staticmethod
    def build_tv_path(base_path: str, show_title: str, season: int, episode: int,
                     year: Optional[str] = None, episode_title: Optional[str] = None, 
                     ext: str = ".mp4") -> str:
        """
        构建完整的 Plex 电视剧路径
        
        路径结构: /base_path/TV Shows/Show Title (Year)/Season XX/Show Title - S01E01 - Episode Title.ext
        
        :return: 完整路径
        """
        show_folder = PlexNamer.format_tv_show_folder(show_title, year)
        season_folder = PlexNamer.format_season_folder(season)
        filename = PlexNamer.format_tv_filename(show_title, season, episode, episode_title, ext)
        
        return os.path.join(base_path, "TV Shows", show_folder, season_folder, filename)


# 便捷函数
def get_plex_movie_path(base: str, title: str, year: str, version: str = None, ext: str = ".mp4") -> str:
    """便捷函数：获取电影完整路径"""
    return PlexNamer.build_movie_path(base, title, year, version, ext)


def get_plex_tv_path(base: str, show: str, s: int, e: int, year: str = None, 
                    ep_title: str = None, ext: str = ".mp4") -> str:
    """便捷函数：获取电视剧完整路径"""
    return PlexNamer.build_tv_path(base, show, s, e, year, ep_title, ext)
