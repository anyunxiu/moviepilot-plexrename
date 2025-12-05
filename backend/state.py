import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from config import settings


@dataclass
class DirectoryConfig:
    path: Path
    enabled: bool = True


@dataclass
class Message:
    level: str
    text: str


@dataclass
class AppState:
    watching: bool = False
    directories: List[DirectoryConfig] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    processed: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        if settings.source_dirs:
            self.directories = [DirectoryConfig(path=path, enabled=True) for path in settings.source_dirs]

    def add_message(self, level: str, text: str, max_messages: Optional[int] = None) -> None:
        with self.lock:
            self.messages.append(Message(level=level, text=text))
            limit = max_messages or settings.max_messages
            if len(self.messages) > limit:
                self.messages = self.messages[-limit:]

    def get_messages(self) -> List[Message]:
        with self.lock:
            return list(self.messages)

    def set_directories(self, dirs: List[DirectoryConfig]) -> None:
        with self.lock:
            self.directories = dirs


state = AppState()
