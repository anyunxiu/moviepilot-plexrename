"""
元数据客户端 - 简化版

提供 TMDB 和豆瓣的元数据搜索功能
"""
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 尝试导入 TMDB API
try:
    from tmdbv3api import TMDb, Movie, TV, Episode
    TMDB_AVAILABLE = True
except ImportError:
    logger.warning("tmdbv3api not installed, TMDB features disabled")
    TMDB_AVAILABLE = False


class MetadataClient:
    """元数据客户端 - 简化版"""
    
    def __init__(self, tmdb_api_key: str = None):
        """
        初始化元数据客户端
        
        :param tmdb_api_key: TMDB API 密钥（可选，从环境变量读取）
        """
        self.tmdb_api_key = tmdb_api_key or os.getenv("TMDB_API_KEY")
        self._init_tmdb()
    
    def _init_tmdb(self):
        """初始化 TMDB API"""
        if not TMDB_AVAILABLE or not self.tmdb_api_key:
            logger.warning("TMDB not configured")
            self.tmdb = None
            return
        
        try:
            self.tmdb = TMDb()
            self.tmdb.api_key = self.tmdb_api_key
            self.tmdb.language = 'zh-CN'
            self.movie_api = Movie()
            self.tv_api = TV()
            logger.info("TMDB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TMDB: {e}")
            self.tmdb = None
    
    def search(self, title: str, year: Optional[str] = None, 
              media_type: str = "movie", tmdb_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        搜索元数据
        
        :param title: 标题
        :param year: 年份（可选）
        :param media_type: 媒体类型 (movie/tv)
        :param tmdb_id: TMDB ID（可选，精确匹配）
        :return: 元数据字典
        """
        if not self.tmdb:
            logger.warning("TMDB not available, using fallback")
            return self._fallback_metadata(title, year, media_type)
        
        try:
            if media_type == "tv":
                return self._search_tv(title, year, tmdb_id)
            else:
                return self._search_movie(title, year, tmdb_id)
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return self._fallback_metadata(title, year, media_type)
    
    def _search_movie(self, title: str, year: Optional[str], tmdb_id: Optional[int]) -> -Optional[Dict[str, Any]]:
        """搜索电影"""
        try:
            # 精确 ID 查询
            if tmdb_id:
                details = self.movie_api.details(tmdb_id)
                return self._format_movie_metadata(details)
            
            # 标题搜索
            results = self.movie_api.search(title)
            if not results:
                return None
            
            # 如果有年份，尝试匹配
            if year:
                for item in results:
                    release_date = getattr(item, 'release_date', '')
                    if release_date and release_date.startswith(year):
                        details = self.movie_api.details(item.id)
                        return self._format_movie_metadata(details)
            
            # 返回第一个结果
            details = self.movie_api.details(results[0].id)
            return self._format_movie_metadata(details)
            
        except Exception as e:
            logger.error(f"Movie search failed: {e}")
            return None
    
    def _search_tv(self, title: str, year: Optional[str], tmdb_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """搜索电视剧"""
        try:
            # 精确 ID 查询
            if tmdb_id:
                details = self.tv_api.details(tmdb_id)
                return self._format_tv_metadata(details)
            
            # 标题搜索
            results = self.tv_api.search(title)
            if not results:
                return None
            
            # 如果有年份，尝试匹配
            if year:
                for item in results:
                    first_air_date = getattr(item, 'first_air_date', '')
                    if first_air_date and first_air_date.startswith(year):
                        details = self.tv_api.details(item.id)
                        return self._format_tv_metadata(details)
            
            # 返回第一个结果
            details = self.tv_api.details(results[0].id)
            return self._format_tv_metadata(details)
            
        except Exception as e:
            logger.error(f"TV search failed: {e}")
            return None
    
    def _format_movie_metadata(self, details) -> Dict[str, Any]:
        """格式化电影元数据"""
        return {
            "provider": "tmdb",
            "tmdb_id": getattr(details, 'id', None),
            "title": getattr(details, 'title', ''),
            "year": getattr(details, 'release_date', '')[:4] if getattr(details, 'release_date', '') else '',
            "type": "movie"
        }
    
    def _format_tv_metadata(self, details) -> Dict[str, Any]:
        """格式化电视剧元数据"""
        return {
            "provider": "tmdb",
            "tmdb_id": getattr(details, 'id', None),
            "title": getattr(details, 'name', ''),
            "year": getattr(details, 'first_air_date', '')[:4] if getattr(details, 'first_air_date', '') else '',
            "type": "tv"
        }
    
    def _fallback_metadata(self, title: str, year: Optional[str], media_type: str) -> Dict[str, Any]:
        """降级元数据（无 API 时使用）"""
        logger.info(f"Using fallback metadata for: {title}")
        return {
            "provider": "fallback",
            "title": title,
            "year": year or "Unknown",
            "type": media_type
        }
    
    def get_episode_title(self, tmdb_id: int, season: int, episode: int) -> Optional[str]:
        """
        获取单集标题
        
        :param tmdb_id: TMDB ID
        :param season: 季数
        :param episode: 集数
        :return: 单集标题
        """
        if not self.tmdb or not TMDB_AVAILABLE:
            return None
        
        try:
            ep_api = Episode()
            details = ep_api.details(tmdb_id, season, episode)
            return getattr(details, 'name', None)
        except Exception as e:
            logger.debug(f"Failed to get episode title: {e}")
            return None
