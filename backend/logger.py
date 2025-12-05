import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import List


class InMemoryLog:
    """Thread-safe in-memory log buffer for UI streaming."""

    def __init__(self, max_lines: int = 500) -> None:
        self.max_lines = max_lines
        self._buffer: List[str] = []

    def append(self, message: str) -> None:
        self._buffer.append(message)
        if len(self._buffer) > self.max_lines:
            self._buffer = self._buffer[-self.max_lines :]

    def dump(self) -> List[str]:
        return list(self._buffer)


def setup_logging(max_lines: int = 500):
    buffer = InMemoryLog(max_lines=max_lines)
    queue: Queue = Queue()

    class UIHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
            except Exception:
                msg = record.getMessage()
            buffer.append(msg)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    ui_handler = UIHandler()
    ui_handler.setFormatter(formatter)

    queue_handler = QueueHandler(queue)
    queue_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(queue_handler)

    listener = QueueListener(queue, console_handler, ui_handler, respect_handler_level=True)
    listener.start()

    return buffer, listener
