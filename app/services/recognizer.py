import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import anitopy
import requests
from dateutil.parser import parse as date_parse

from app.core.config import settings
from app.models import MediaType, RecognizedMedia


TMDB_SEARCH_MOVIE = "https://api.themoviedb.org/3/search/movie"
TMDB_SEARCH_TV = "https://api.themoviedb.org/3/search/tv"

DOUBAN_SEARCH = "https://frodo.douban.com/api/v2/search"


@dataclass
class ParsedName:
    title: str
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    media_type: Optional[MediaType] = None


class NameRecognizer:
    """
    1) 本地文件名解析（anitopy + 正则）得到 title/year/season/episode
    2) TMDB 搜索补全 year/id
    3) 可选 Douban 搜索（弱校验）
    """

    def __init__(self):
        if not settings.TMDB_API_KEY:
            raise ValueError("TMDB_API_KEY is required")

    @staticmethod
    def _parse_filename(path: Path) -> ParsedName:
        tokens = anitopy.parse(path.name)
        title = tokens.get("anime_title") or tokens.get("title") or path.stem
        year = None
        season = None
        episode = None

        # 提取年份
        match_year = re.search(r"(19|20)\d{2}", path.name)
        if match_year:
            year = int(match_year.group())

        # 提取 SxxEyy
        match_tv = re.search(r"[Ss](\d{1,2})[Ee](\d{1,3})", path.name)
        if match_tv:
            season = int(match_tv.group(1))
            episode = int(match_tv.group(2))

        # 额外兼容 - S01 - 02
        match_season_only = re.search(r"[Ss](\d{1,2})", path.name)
        if match_season_only and not season:
            season = int(match_season_only.group(1))

        media_type = MediaType.tv if season or episode else MediaType.movie
        return ParsedName(title=title, year=year, season=season, episode=episode, media_type=media_type)

    def _tmdb_search(self, parsed: ParsedName) -> Optional[dict]:
        params = {
            "api_key": settings.TMDB_API_KEY,
            "query": parsed.title,
            "language": "zh-CN",
        }
        if parsed.year:
            params["year"] = parsed.year

        url = TMDB_SEARCH_TV if parsed.media_type == MediaType.tv else TMDB_SEARCH_MOVIE
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        return results[0] if results else None

    def _douban_search(self, parsed: ParsedName) -> Optional[dict]:
        if not settings.DOUBAN_COOKIE:
            return None
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": settings.DOUBAN_COOKIE,
        }
        params = {"q": parsed.title}
        resp = requests.get(DOUBAN_SEARCH, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        items = data.get("subjects") or data.get("items") or []
        return items[0] if items else None

    @staticmethod
    def _pick_year_from_tmdb(tmdb_obj: dict, parsed: ParsedName) -> Optional[int]:
        date_field = tmdb_obj.get("release_date") or tmdb_obj.get("first_air_date")
        if not date_field:
            return parsed.year
        try:
            return date_parse(date_field).year
        except Exception:
            return parsed.year

    def recognize(self, path: Path) -> Optional[RecognizedMedia]:
        parsed = self._parse_filename(path)
        tmdb_obj = self._tmdb_search(parsed)
        if not tmdb_obj:
            return None

        year = self._pick_year_from_tmdb(tmdb_obj, parsed)
        douban_obj = self._douban_search(parsed)
        douban_id = None
        if douban_obj:
            douban_id = str(douban_obj.get("id") or douban_obj.get("target_id") or "")

        return RecognizedMedia(
            title=tmdb_obj.get("title") or tmdb_obj.get("name") or parsed.title,
            year=year,
            media_type=parsed.media_type,
            season=parsed.season,
            episode=parsed.episode,
            tmdb_id=tmdb_obj.get("id"),
            douban_id=douban_id,
            candidates=[tmdb_obj],
        )
