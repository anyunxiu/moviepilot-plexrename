import os
from pathlib import Path
from typing import List


class Settings:
    """Runtime settings loaded from environment variables."""

    def __init__(self) -> None:
        self.source_dirs: List[Path] = self._parse_path_list(os.getenv("PR_SOURCE_DIRS", ""))
        self.output_dir: Path = Path(os.getenv("PR_OUTPUT_DIR", "./output")).resolve()
        self.scan_extensions = {ext.strip().lower() for ext in os.getenv("PR_EXTENSIONS", "mkv,mp4,avi,ts,flv,wmv,mpg").split(",") if ext.strip()}
        self.enable_watchdog = os.getenv("PR_ENABLE_WATCHDOG", "1") == "1"
        self.max_messages = int(os.getenv("PR_MAX_MESSAGES", "200"))

    @staticmethod
    def _parse_path_list(value: str) -> List[Path]:
        results: List[Path] = []
        for item in value.split(","):
            item = item.strip()
            if item:
                results.append(Path(item).expanduser().resolve())
        return results


settings = Settings()
