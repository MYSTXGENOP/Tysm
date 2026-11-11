"""Local opt-in conversation history; keeps original memory file untouched."""
import json
from pathlib import Path


class HistoryStore:
    def __init__(self, path, settings_path, max_messages=40):
        self.path = Path(path)
        self.settings_path = Path(settings_path)
        self.max_messages = max_messages
        self.enabled = self._load_enabled()

    def _load_enabled(self):
        try:
            return bool(json.loads(self.settings_path.read_text(encoding="utf-8")).get("enabled", True))
        except (OSError, ValueError, AttributeError):
            return True

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.settings_path.write_text(json.dumps({"enabled": self.enabled}, indent=2), encoding="utf-8")

    def load_messages(self):
        if not self.enabled:
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            return [m for m in data[-self.max_messages:] if isinstance(m, dict)
                    and m.get("role") in ("user", "assistant")
                    and isinstance(m.get("content"), str) and len(m["content"]) <= 4000]
        except (OSError, ValueError):
            return []

    def append_exchange(self, user, assistant):
        if not self.enabled:
            return
        if len(user) > 4000 or len(assistant) > 4000:
            return
        data = self.load_messages() + [
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data[-self.max_messages:], ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def clear(self):
        if self.path.exists():
            self.path.unlink()

    def status(self):
        return ("Local chat history saving is " + ("ON" if self.enabled else "OFF")
                + ". Commands: /history on, /history off, /history clear.")
