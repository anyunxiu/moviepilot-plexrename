import logging
import threading
from pathlib import Path
from typing import Callable, List, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from pipeline import pipeline
from state import state, DirectoryConfig

log = logging.getLogger("watcher")


class _Handler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[Path], None]):
        self._callback = callback

    def on_created(self, event):
        if not event.is_directory:
            self._callback(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._callback(Path(event.dest_path))


class DirectoryWatcher:
    def __init__(self) -> None:
        self.observer: Optional[Observer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def start(self, directories: List[DirectoryConfig]):
        if self.running:
            return
        self.observer = Observer()
        for entry in directories:
            if entry.enabled:
                path = entry.path
                if path.exists():
                    log.info("Watching %s", path)
                    self.observer.schedule(_Handler(self._on_change), str(path), recursive=True)
                else:
                    log.warning("Skip missing watch path: %s", path)
        self.observer.start()
        self.running = True

    def stop(self):
        if not self.running or not self.observer:
            return
        self.observer.stop()
        self.observer.join()
        self.running = False
        log.info("Watcher stopped")

    def _on_change(self, path: Path):
        log.info("Detected change: %s", path)
        result = pipeline.run_on_path(path)
        if result:
            state.add_message("info", f"Hardlinked: {result.plex_name}")
        else:
            state.add_message("debug", f"Ignored: {path}")


watcher = DirectoryWatcher()
