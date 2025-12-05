import logging
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from logger import setup_logging
from pipeline import pipeline
from schemas import (
    DirectoryEntry,
    DirectoryUpdateRequest,
    RenameResult,
    RunOnceResponse,
    StatusResponse,
    ToggleRequest,
)
from state import DirectoryConfig, state
from watcher import watcher

log_buffer, _listener = setup_logging(max_lines=settings.max_messages)
app = FastAPI(title="Plex Rename Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"]
)


@app.on_event("startup")
def startup_event():
    state.add_message("info", "Service started")


@app.on_event("shutdown")
def shutdown_event():
    watcher.stop()


@app.get("/api/status", response_model=StatusResponse)
def get_status():
    return StatusResponse(
        watching=watcher.running,
        processed=state.processed,
        directories=[DirectoryEntry(path=entry.path, enabled=entry.enabled) for entry in state.directories],
        messages=[{\"level\": m.level, \"text\": m.text} for m in state.get_messages()],
        logs=log_buffer.dump(),
    )


@app.post("/api/toggle")
def toggle_watch(request: ToggleRequest):
    if request.enabled:
        watcher.start(state.directories)
        state.watching = True
        state.add_message("info", "Watcher enabled")
    else:
        watcher.stop()
        state.watching = False
        state.add_message("info", "Watcher disabled")
    return {"watching": watcher.running}


@app.post("/api/run-once", response_model=RunOnceResponse)
def run_once():
    total = 0
    for entry in state.directories:
        if entry.enabled:
            total += pipeline.scan_directory(entry.path)
    state.add_message("info", f"Manual scan finished: {total} item(s)")
    return RunOnceResponse(started_at=datetime.utcnow(), items=total)


@app.post("/api/directories", response_model=List[DirectoryEntry])
def update_directories(payload: DirectoryUpdateRequest):
    new_entries: List[DirectoryConfig] = []
    for item in payload.directories:
        path = item.path.resolve()
        new_entries.append(DirectoryConfig(path=path, enabled=item.enabled))
    state.set_directories(new_entries)
    state.add_message("info", "Updated directories")
    if watcher.running:
        watcher.stop()
        watcher.start(new_entries)
    return [DirectoryEntry(path=entry.path, enabled=entry.enabled) for entry in new_entries]


@app.get("/api/logs")
def get_logs():
    return {"logs": log_buffer.dump()}


# Static UI
ui_dir = (Path(__file__).resolve().parent.parent / "frontend").resolve()
if ui_dir.exists():
    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")
else:
    logging.getLogger("app").warning("UI directory missing: %s", ui_dir)
