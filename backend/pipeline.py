import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

from config import settings
from schemas import RenameResult
from state import state

log = logging.getLogger("pipeline")


class RenamerPipeline:
    def __init__(self) -> None:
        self.processed: Set[Path] = set()

    def is_video(self, path: Path) -> bool:
        return path.suffix.lower().lstrip(".") in settings.scan_extensions

    def run_on_path(self, source: Path) -> Optional[RenameResult]:
        source = source.resolve()
        if not source.exists() or not source.is_file():
            return None
        if source in self.processed:
            return None
        if not self.is_video(source):
            return None

        meta = self._analyze_filename(source)
        matched_type = meta.get("type", "unknown")
        plex_name = self._build_plex_name(source, meta)
        destination = self._build_destination(source, plex_name, meta)

        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            if destination.exists():
                log.info("Destination already exists, skipping hardlink: %s", destination)
            else:
                os.link(source, destination)
                log.info("Created hardlink: %s -> %s", source, destination)
        except OSError as exc:
            log.error("Failed to create hardlink for %s: %s", source, exc)
            return None

        self.processed.add(source)
        state.processed += 1
        return RenameResult(
            source=source,
            destination=destination,
            plex_name=plex_name,
            matched_type=matched_type,
            metadata=meta,
            created_at=datetime.utcnow(),
        )

    def scan_directory(self, directory: Path) -> int:
        if not directory.exists():
            log.warning("Directory missing: %s", directory)
            return 0
        count = 0
        for root, _, files in os.walk(directory):
            for name in files:
                result = self.run_on_path(Path(root) / name)
                if result:
                    count += 1
        return count

    def _analyze_filename(self, path: Path) -> Dict[str, object]:
        meta: Dict[str, object] = {"type": "movie", "title": path.stem}

        # Detect TV pattern S01E02 or 1x02
        tv_match = re.search(r"S(\d{1,2})E(\d{1,3})", path.stem, re.IGNORECASE)
        alt_match = re.search(r"(\d{1,2})x(\d{1,3})", path.stem, re.IGNORECASE)
        if tv_match or alt_match:
            season = int((tv_match or alt_match).group(1))
            episode = int((tv_match or alt_match).group(2))
            meta.update({"type": "tv", "season": season, "episode": episode})

        # Try extracting year for movies
        year_match = re.search(r"(19|20)\d{2}", path.stem)
        if year_match:
            meta["year"] = int(year_match.group(0))

        # Derive title from parent folder if looks meaningful
        parent_hint = path.parent.name
        if parent_hint and len(parent_hint) > 2:
            meta.setdefault("title", parent_hint)

        # Remove common dots/underscores
        cleaned = re.sub(r"[._]+", " ", meta.get("title", path.stem)).strip()
        meta["title"] = cleaned.title()

        # Minimal metadata completion placeholder
        meta.setdefault("metadata_filled", True)
        return meta

    def _build_plex_name(self, source: Path, meta: Dict[str, object]) -> str:
        suffix = source.suffix
        if meta.get("type") == "tv":
            season = int(meta.get("season", 1))
            episode = int(meta.get("episode", 1))
            title = meta.get("title", "Series")
            return f"{title} - S{season:02d}E{episode:02d}{suffix}"
        title = meta.get("title", "Movie")
        year = meta.get("year")
        if year:
            return f"{title} ({year}){suffix}"
        return f"{title}{suffix}"

    def _build_destination(self, source: Path, plex_name: str, meta: Dict[str, object]) -> Path:
        base = settings.output_dir
        if meta.get("type") == "tv":
            title = meta.get("title", "Series")
            season = int(meta.get("season", 1))
            return base / "tv" / title / f"Season {season:02d}" / plex_name
        title = meta.get("title", "Movie")
        return base / "movies" / title / plex_name


pipeline = RenamerPipeline()
