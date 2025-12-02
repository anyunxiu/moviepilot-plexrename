"""
优先级匹配器 - PlexRename 核心模块

实现类似 MoviePilot v2 的多规则优先级匹配机制。
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MatchType(Enum):
    """匹配类型"""
    TMDB_ID = "tmdb_id"
    DOUBAN_ID = "douban_id"
    TV_STANDARD = "tv_standard"  # SxxExx
    TV_CHINESE = "tv_chinese"    # 第x季第x集
    YEAR = "year"
    RESOLUTION = "resolution"
    EDITION = "edition"
""    SOURCE = "source"
    VIDEO_CODEC = "video_codec"
    AUDIO_CODEC = "audio_codec"
    GROUP = "group"


@dataclass
class MatchingRule:
    """匹配规则定义"""
    priority: int
    name: str
    pattern: str
    match_type: MatchType
    enabled: bool = True
    
    def apply(self, text: str) -> Optional[re.Match]:
        """应用规则进行匹配"""
        if not self.enabled:
            return None
        try:
            return re.search(self.pattern, text, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern in rule '{self.name}': {e}")
            return None
    
    def extract(self, match: re.Match) -> Dict[str, Any]:
        """从匹配结果中提取信息"""
        if not match:
            return {}
        
        result = {}
        if self.match_type == MatchType.TMDB_ID:
            result['tmdb_id'] = int(match.group(1))
        elif self.match_type == MatchType.DOUBAN_ID:
            result['douban_id'] = match.group(1)
        elif self.match_type == MatchType.TV_STANDARD:
            result['season'] = int(match.group(1))
            result['episode'] = int(match.group(2))
            result['media_type'] = 'tv'
        elif self.match_type == MatchType.TV_CHINESE:
            result['season'] = int(match.group(1))
    GROUP = "group"


@dataclass
class MatchingRule:
    """匹配规则定义"""
    priority: int
    name: str
    pattern: str
    match_type: MatchType
    enabled: bool = True
    
    def apply(self, text: str) -> Optional[re.Match]:
        """应用规则进行匹配"""
        if not self.enabled:
            return None
        try:
            return re.search(self.pattern, text, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern in rule '{self.name}': {e}")
            return None
    
    def extract(self, match: re.Match) -> Dict[str, Any]:
        """从匹配结果中提取信息"""
        if not match:
            return {}
        
        result = {}
        if self.match_type == MatchType.TMDB_ID:
            result['tmdb_id'] = int(match.group(1))
        elif self.match_type == MatchType.DOUBAN_ID:
            result['douban_id'] = match.group(1)
        elif self.match_type == MatchType.TV_STANDARD:
            result['season'] = int(match.group(1))
            result['episode'] = int(match.group(2))
            result['media_type'] = 'tv'
        elif self.match_type == MatchType.TV_CHINESE:
            result['season'] = int(match.group(1))
            result['episode'] = int(match.group(2))
            result['media_type'] = 'tv'
        elif self.match_type == MatchType.YEAR:
            result['year'] = match.group(1)
        elif self.match_type == MatchType.RESOLUTION:
            result['resolution'] = match.group(1).upper()
        elif self.match_type == MatchType.EDITION:
            result['edition'] = match.group(1)
        elif self.match_type == MatchType.SOURCE:
            result['source'] = match.group(1)
        elif self.match_type == MatchType.VIDEO_CODEC:
            result['video_codec'] = match.group(1)
        elif self.match_type == MatchType.AUDIO_CODEC:
            result['audio_codec'] = match.group(1)
        elif self.match_type == MatchType.GROUP:
            result['group'] = match.group(1)
        
        return result


@dataclass
class MatchResult:
    """匹配结果"""
    title: str
    media_type: str = "movie"  # movie or tv
    year: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    tmdb_id: Optional[int] = None
    douban_id: Optional[str] = None
    resolution: Optional[str] = None
    edition: Optional[str] = None
    source: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    group: Optional[str] = None
    applied_rules: List[str] = None  # 应用的规则名称列表
    
    def __post_init__(self):
        if self.applied_rules is None:
            self.applied_rules = []


class PriorityMatcher:
    """优先级匹配器 - 核心匹配引擎"""
    
    # 默认匹配规则（按优先级排序）
    DEFAULT_RULES = [
        MatchingRule(
            priority=1,
            name="TMDB ID 精确匹配",
            pattern=r'\{tmdbid=(\d+)\}',
            match_type=MatchType.TMDB_ID
        ),
        MatchingRule(
            priority=2,
            name="豆瓣 ID 精确匹配",
            pattern=r'\{doubanid=(\d+)\}',
            match_type=MatchType.DOUBAN_ID
        ),
        MatchingRule(
            priority=3,
            name="标准季集格式 SxxExx",
            pattern=r'(?i)S(\d{1,2})E(\d{1,3})',
            match_type=MatchType.TV_STANDARD
        ),
        MatchingRule(
            priority=4,
            name="中文季集格式",
            pattern=r'第(\d{1,2})季.*?第(\d{1,4})[集話话]',
            match_type=MatchType.TV_CHINESE
        ),
        MatchingRule(
            priority=5,
            name="年份识别",
            pattern=r'[\.\s\-\(](19\d{2}|20\d{2})[\.\s\-\)]',
            match_type=MatchType.YEAR
        ),
        MatchingRule(
            priority=6,
            name="分辨率识别",
            pattern=r'(?i)(2160p|4K|1080p|720p|480p)',
            match_type=MatchType.RESOLUTION
        ),
        MatchingRule(
            priority=7,
            name="版本识别",
            pattern=r'(导演剪辑版|加长版|未删减版|Extended|Director\'?s?\s*Cut|Unrated)',
            match_type=MatchType.EDITION
        ),
        MatchingRule(
            priority=8,
            name="来源识别",
            pattern=r'(?i)(BluRay|UHD|Remux|WEB-DL|WEBRip|HDTV|DVD|DVDRip)',
            match_type=MatchType.SOURCE
        ),
        MatchingRule(
            priority=9,
            name="视频编码识别",
            pattern=r'(?i)(x264|x265|h264|h265|hevc|avc|mpeg2)',
            match_type=MatchType.VIDEO_CODEC
        ),
        MatchingRule(
            priority=10,
            name="音频编码识别",
            pattern=r'(?i)(dts-hd|dts|truehd|ac3|aac|eac3|flac|atmos)',
            match_type=MatchType.AUDIO_CODEC
        ),
        MatchingRule(
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.priority)
        logger.info(f"Added rule '{rule.name}' with priority {rule.priority}")
    
    def remove_rule(self, rule_name: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Removed rule '{rule_name}'")
