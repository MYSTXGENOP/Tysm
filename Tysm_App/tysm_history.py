"""Local conversation sessions. Previous sessions are archived, never auto-injected.

The existing tysm_history.json is migrated without discarding the old messages.
Durable facts and adaptive learning remain in their separate stores.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class HistoryStore:
    def __init__(self, path, settings_path, max_messages=40, max_sessions=60):
        self.path = Path(path)
        self.settings_path = Path(settings_path)
        self.max_messages = max_messages
        self.max_sessions = max_sessions
        self.enabled = self._load_enabled()
        self._sessions = self._load()
        self.current_id = None
        # An app launch is a NEW conversation, not a continuation of the last
        # process's model context. The last transcript is retained as an archive.
        self.begin_session()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _valid_messages(messages):
        if not isinstance(messages, list):
            return []
        return [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if isinstance(m, dict)
            and m.get("role") in ("user", "assistant")
            and isinstance(m.get("content"), str)
            and len(m["content"]) <= 4000
        ]

    def _load_enabled(self):
        try:
            return bool(json.loads(self.settings_path.read_text(encoding="utf-8")).get("enabled", True))
        except (OSError, ValueError, AttributeError, TypeError):
            return True

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if isinstance(data, list):
            # Legacy history was one flat list with no timestamps or session IDs.
            # Label it legacy rather than pretending we know when it happened.
            messages = self._valid_messages(data)[-self.max_messages:]
            return ([{"id": "legacy", "started": "unknown", "ended": self._now(),
                      "messages": messages}] if messages else [])
        if not isinstance(data, dict) or data.get("version") != 2:
            return []
        sessions = []
        for item in data.get("sessions", []) if isinstance(data.get("sessions"), list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            sessions.append({
                "id": item["id"][:75],
                "started": str(item.get("started", "unknown"))[:48],
                "ended": str(item.get("ended", ""))[:48],
                "messages": self._valid_messages(item.get("messages", []))[-self.max_messages:]
            })
        return sessions[-self.max_sessions:]

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            temp.write_text(
                json.dumps({"version": 2, "sessions": self._sessions[-self.max_sessions:]},
                           ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temp.replace(self.path)
        finally:
            if temp.exists():
                temp.unlink()

    def _current(self):
        for s in reversed(self._sessions):
            if s["id"] == self.current_id:
                return s
        return None

    def begin_session(self):
        if self._sessions and not self._sessions[-1].get("ended"):
            self._sessions[-1]["ended"] = self._now()
        self.current_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self._sessions.append({
            "id": self.current_id, "started": self._now(), "ended": "",
            "messages": []
        })
        self._sessions = self._sessions[-self.max_sessions:]
        self._save()
        return self.current_id

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps({"enabled": self.enabled}, indent=2), encoding="utf-8")

    def load_messages(self):
        # Never load an archived session into a new conversation.
        current = self._current()
        if not self.enabled or not current:
            return []
        return list(current["messages"][-self.max_messages:])

    def append_exchange(self, user, assistant):
        if not self.enabled or not isinstance(user, str) or not isinstance(assistant, str):
            return
        if len(user) > 4000 or len(assistant) > 4000:
            return
        session = self._current()
        if session is None:
            self.begin_session()
            session = self._current()
        session["messages"].extend([
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant}
        ])
        session["messages"] = session["messages"][-self.max_messages:]
        self._save()

    def list_sessions(self):
        previous = [s for s in self._sessions if s["id"] != self.current_id]
        if not previous:
            return "No older conversations saved."
        result = ["Saved conversations (archives are NOT mixed into live chat):"]
        for s in reversed(previous[-12:]):
            count = len(s["messages"]) // 2
            result.append(f"{s['id']} | started {s['started']} | {count} exchanges")
        result.append("Use /session show ID to read an archived conversation.")
        return "\n".join(result)

    def show_session(self, session_id):
        session_id = session_id.strip()
        if not session_id or session_id == self.current_id:
            return "Choose an older conversation ID from /sessions."
        session = next((s for s in self._sessions if s["id"] == session_id), None)
        if session is None:
            return "No archived conversation with that ID."
        if not session["messages"]:
            return "This archived conversation has no saved messages."
        lines = [f"Archived conversation {session_id} (read-only; not loaded into current context):"]
        for m in session["messages"][-12:]:
            speaker = "You" if m["role"] == "user" else "Tysm"
            lines.append(f"{speaker}: {m['content'][:350]}")
        return "\n".join(lines)[:4500]

    def clear(self):
        self._sessions = []
        self.current_id = None
        if self.path.exists():
            self.path.unlink()

    def status(self):
        count = max(0, len(self._sessions) - 1)
        return (
            "Local chat history saving is " + ("ON" if self.enabled else "OFF")
            + f". Current conversation: {self.current_id}. Archived conversations: {count}."
            + " Commands: /session new, /sessions, /session show ID, "
              "/history on, /history off, /history clear."
        )
