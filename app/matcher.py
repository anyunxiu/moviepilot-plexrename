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
            pattern=r'(导演剪辑版|加长版|未删减版|(?i)Extended|Director\'?s?\s*Cut|Unrated)',
            match_type=MatchType.EDITION
        )
    ]
    
    def __init__(self, custom_rules: List[MatchingRule] = None):
        """
        初始化匹配器
        :param custom_rules: 自定义规则列表，如果为 None 则使用默认规则
        """
        rules = custom_rules if custom_rules is not None else self.DEFAULT_RULES
        # 按优先级排序
        self.rules = sorted(rules, key=lambda x: x.priority)
        logger.info(f"Initialized PriorityMatcher with {len(self.rules)} rules")
    
    def match(self, filename: str) -> MatchResult:
        """
        按优先级依次匹配文件名
        :param filename: 文件名（可包含路径）
        :return: 匹配结果
        """
        # 提取文件名（去除路径和扩展名）
        import os
        basename = os.path.basename(filename)
        name_without_ext = os.path.splitext(basename)[0]
        
        # 初始化结果
        result_data = {
            'title': name_without_ext,
            'applied_rules': []
        }
        
        # 用于清理的文本
        clean_text = name_without_ext
        
        # 按优先级依次应用规则
        for rule in self.rules:
            match = rule.apply(clean_text)
            if match:
                # 提取信息
                extracted = rule.extract(match)
                result_data.update(extracted)
                result_data['applied_rules'].append(rule.name)
                
                # 从文本中移除匹配的内容（用于下次匹配）
                clean_text = clean_text[:match.start()] + ' ' + clean_text[match.end():]
                
                logger.debug(f"Rule '{rule.name}' matched: {extracted}")
        
        # 清理标题（移除多余空格和分隔符）
        result_data['title'] = self._clean_title(clean_text)
        
        return MatchResult(**result_data)
    
    def _clean_title(self, text: str) -> str:
        """清理标题，移除多余的分隔符和空格"""
        # 替换常见分隔符为空格
        text = re.sub(r'[\._\-]+', ' ', text)
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空格
        return text.strip()
    
    def add_rule(self, rule: MatchingRule):
        """添加新规则并重新排序"""
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.priority)
        logger.info(f"Added rule '{rule.name}' with priority {rule.priority}")
    
    def remove_rule(self, rule_name: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Removed rule '{rule_name}'")
