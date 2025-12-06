from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


class DirectoryEntry(BaseModel):
    path: Path
    enabled: bool = True


class MessageEntry(BaseModel):
    level: str
    text: str


class StatusResponse(BaseModel):
    watching: bool
    processed: int
    directories: List[DirectoryEntry]
    messages: List[MessageEntry]
    logs: List[str]


class RunOnceResponse(BaseModel):
    started_at: datetime
    items: int


class ToggleRequest(BaseModel):
    enabled: bool


class DirectoryUpdateRequest(BaseModel):
    directories: List[DirectoryEntry]


class WatchRequest(BaseModel):
    path: Path
    enabled: bool = True


class RenameResult(BaseModel):
    source: Path
    destination: Path
    plex_name: str
    matched_type: str
    metadata: dict
    created_at: datetime

