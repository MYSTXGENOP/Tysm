"""Privacy-conscious, local-only technical event logging for Tysm.

Never pass user prompts, model responses, tokens, or file contents as event details.
"""
from collections import deque
from datetime import datetime
from pathlib import Path
import json
import os
import threading

LOG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Tysm" / "logs"
LOG_FILE = LOG_DIR / "activity.jsonl"
MAX_BYTES = 1_000_000
ALLOWED_EVENTS = {"startup", "shutdown", "provider", "action", "update", "backup", "error", "system"}
_ALLOWED_STATUSES = {"info", "success", "warning", "error"}
_lock = threading.Lock()
_recent = deque(maxlen=100)


def record(event, status="info", detail=""):
    """Write a bounded technical event. Detail is deliberately not persisted."""
    event = str(event).lower()
    status = str(status).lower()
    if event not in ALLOWED_EVENTS:
        event = "system"
    if status not in _ALLOWED_STATUSES:
        status = "info"
    item = {
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "event": event,
        "status": status,
    }
    # Do not store arbitrary details: they may contain private chat or secrets.
    with _lock:
        _recent.append(item)
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            if LOG_FILE.exists() and LOG_FILE.stat().st_size >= MAX_BYTES:
                rotated = LOG_DIR / "activity.previous.jsonl"
                os.replace(LOG_FILE, rotated)
            with LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return item


def recent(limit=30):
    """Return recent events without reading conversation data."""
    limit = max(1, min(int(limit), 100))
    with _lock:
        if _recent:
            return list(_recent)[-limit:]
        try:
            if not LOG_FILE.exists():
                return []
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-limit:]
            return [json.loads(line) for line in lines if line.strip()]
        except (OSError, ValueError):
            return []


def export_path():
    """Location of the technical log; never auto-uploads it."""
    return LOG_FILE
