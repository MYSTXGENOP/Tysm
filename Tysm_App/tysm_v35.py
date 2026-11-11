"""Optional, local-only V3.5 helpers. Never reads screen pixels or window contents."""
import ctypes
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

STOP = set('the and for with this that have from your about what when where will just into are was you its she her them they how can'.split())

class ContextTools:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.last_external_app = None
        self.app_switches = []
        self._last_seen_pid = None
        with sqlite3.connect(self.db_path) as con:
            con.execute('CREATE TABLE IF NOT EXISTS v35_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            con.execute("INSERT OR IGNORE INTO v35_settings VALUES ('desktop_awareness','off')")
            con.execute('CREATE TABLE IF NOT EXISTS v35_reflections (id INTEGER PRIMARY KEY, note TEXT NOT NULL, created TEXT NOT NULL)')

    def awareness_enabled(self):
        with sqlite3.connect(self.db_path) as con:
            return con.execute("SELECT value FROM v35_settings WHERE key='desktop_awareness'").fetchone()[0] == 'on'

    def set_awareness(self, enabled):
        with sqlite3.connect(self.db_path) as con:
            con.execute("UPDATE v35_settings SET value=? WHERE key='desktop_awareness'", ('on' if enabled else 'off',))
        if not enabled:
            self.last_external_app = None
            self.app_switches.clear()
            self._last_seen_pid = None

    def _foreground_process(self):
        """Read only the foreground process ID/name; never inspect window contents."""
        if sys.platform != 'win32':
            return None, 'Active-app detection is only supported on Windows.'
        try:
            from ctypes import wintypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None, 'No active application detected.'
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return None, 'Active application unavailable.'
            try:
                import psutil
                name = psutil.Process(pid.value).name()[:100]
            except ImportError:
                return None, 'Install psutil into Tysm\'s Python environment to detect application names.'
            except Exception:
                return None, 'Could not read the active process name.'
            return (pid.value, name), None
        except Exception:
            return None, 'Active application unavailable.'

    def poll_application(self):
        """Called periodically by Tkinter while opted in. Keeps history in RAM only."""
        if not self.awareness_enabled():
            return
        process, _ = self._foreground_process()
        if not process:
            return
        pid, name = process
        if pid == os.getpid():
            return  # Tysm itself should not replace the last external application.
        if pid != self._last_seen_pid:
            self._last_seen_pid = pid
            self.last_external_app = name
            self.app_switches.append(name)
            self.app_switches = self.app_switches[-8:]

    def active_application(self):
        if not self.awareness_enabled():
            return None
        process, error = self._foreground_process()
        if error:
            return error
        pid, name = process
        if pid == os.getpid():
            if self.last_external_app:
                return 'Tysm is focused. Last external application: ' + self.last_external_app
            return 'Tysm is focused. Switch to another application briefly, then ask again.'
        self.poll_application()
        return 'Active application: ' + name

    def awareness_summary(self):
        if not self.awareness_enabled():
            return 'Desktop awareness is off. Use /awareness on to opt in.'
        current = self.active_application()
        if self.app_switches:
            return current + '\nRecent application switches (newest last): ' + ' -> '.join(self.app_switches[-5:])
        return current

    def relevant_memory(self, user_text, limit=6):
        words = {w for w in re.findall(r'[a-z0-9]{3,}', user_text.lower()) if w not in STOP}
        if not words:
            return ''
        try:
            with sqlite3.connect(self.db_path) as con:
                rows = con.execute('SELECT content,pinned,seen FROM notes ORDER BY pinned DESC,seen DESC,id DESC LIMIT 150').fetchall()
        except sqlite3.Error:
            return ''
        ranked = []
        for content,pinned,seen in rows:
            tokens = set(re.findall(r'[a-z0-9]{3,}', content.lower())) - STOP
            score = len(words & tokens)
            if score:
                ranked.append((score, pinned, seen, content))
        ranked.sort(reverse=True)
        return '\n'.join('- ' + x[3][:220] for x in ranked[:limit])

    def reflect(self, user_text):
        """Conservative reflection: explicit corrections only, no inferred emotional profiles."""
        if re.search(r'\b(?:no,? (?:i meant|that.s wrong)|actually,? i (?:meant|prefer)|stop (?:saying|calling)|don.t call me)\b', user_text, re.I):
            note = 'User corrected Tysm; prioritize the latest explicit instruction over older inferred preferences.'
            with sqlite3.connect(self.db_path) as con:
                con.execute('INSERT INTO v35_reflections(note,created) VALUES (?,?)', (note, datetime.now(timezone.utc).isoformat()))
                con.execute('DELETE FROM v35_reflections WHERE id NOT IN (SELECT id FROM v35_reflections ORDER BY id DESC LIMIT 15)')

    def reflection_context(self):
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute('SELECT note FROM v35_reflections ORDER BY id DESC LIMIT 2').fetchall()
        return '\n'.join(dict.fromkeys(r[0] for r in rows))

    def diagnostics(self, model='llama3.2:3b'):
        lines = ['TYSM diagnostics (local checks):']
        lines.append('Python: ' + sys.version.split()[0])
        lines.append('Memory DB: ' + ('available' if self.db_path.exists() else 'missing'))
        lines.append('Desktop awareness: ' + ('ON' if self.awareness_enabled() else 'OFF'))
        try:
            import urllib.request
            with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=2) as r:
                import json
                names = [m.get('name','') for m in json.load(r).get('models', [])]
            lines.append('Ollama: reachable')
            lines.append('Model: ' + ('installed' if any(n == model or n.startswith(model + '-') for n in names) else 'not found in local model list'))
        except Exception:
            lines.append('Ollama: unreachable (start Ollama and retry)')
        return '\n'.join(lines)
