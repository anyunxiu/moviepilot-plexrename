from enum import Enum
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel


class FileType(str, Enum):
    file = "file"
    dir = "dir"


class MediaType(str, Enum):
    movie = "movie"
    tv = "tv"


class RenameRequest(BaseModel):
    path: Path
    new_name: str
    recursive: bool = False


class RenameResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class RecommendedName(BaseModel):
    success: bool
    name: Optional[str] = None
    message: Optional[str] = None


class RecognizedEpisode(BaseModel):
    season: Optional[int] = None
    episode: Optional[int] = None


class RecognizedMedia(BaseModel):
    title: str
    year: Optional[int] = None
    media_type: MediaType
    season: Optional[int] = None
    episode: Optional[int] = None
    tmdb_id: Optional[int] = None
    douban_id: Optional[str] = None
    candidates: Optional[List[dict]] = None
