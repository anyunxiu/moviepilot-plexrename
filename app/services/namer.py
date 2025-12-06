from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.models import RecognizedMedia, MediaType


class Namer:
    """
    根据识别结果渲染推荐路径/名称。
    简单模板：{{title}} {{year}}，剧集包含 Season/Episode。
    """

    def render(self, media: RecognizedMedia, original_path: Path) -> Optional[Path]:
        if media.media_type == MediaType.movie:
            name = settings.RENAME_MOVIE_FORMAT \
                .replace("{{title}}", media.title) \
                .replace("{{year}}", str(media.year or "")) \
                .strip()
            return original_path.with_name(f"{name}{original_path.suffix}")

        # TV
        season = f"{(media.season or 1):02d}"
        episode = f"{(media.episode or 1):02d}"
        tmpl = settings.RENAME_TV_FORMAT \
            .replace("{{title}}", media.title) \
            .replace("{{year}}", str(media.year or "")) \
            .replace("{{season}}", season) \
            .replace("{{episode}}", episode) \
            .strip()

        if original_path.is_dir():
            return original_path.with_name(Path(tmpl).name)

        # For files, only use filename part; directory structure is up to caller.
        new_filename = Path(tmpl).name
        return original_path.with_name(f"{new_filename}{original_path.suffix}")
