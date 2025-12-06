from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="")

    PROJECT_NAME: str = "MoviePilot Slim"
    HOST: str = "0.0.0.0"
    PORT: int = 3060

    TMDB_API_KEY: str
    DOUBAN_COOKIE: Optional[str] = None

    RENAME_MOVIE_FORMAT: str = "{{title}} ({{year}})"
    RENAME_TV_FORMAT: str = "{{title}} ({{year}})/Season {{season}}/{{title}} - S{{season}}E{{episode}}"

    ROOT_PATH: Path = Path(".").resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
