"""Local, conservative adaptive memory. No network calls or model training."""
import re
import sqlite3
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

BLOCKED = re.compile(r'\b(password|passcode|secret|token|api key|address|phone number|medical|diagnos|sexual|religion|politic|credit card|ssn)\b', re.I)
PREFERENCE = re.compile(r"\b(?:i (?:really )?(?:like|love|prefer|dislike|hate)|my favorite (?:color|game|anime|style) is)\b", re.I)
CORRECTION = re.compile(r"\b(?:actually|instead|no longer|not anymore|i changed my mind)\b", re.I)
STOPWORDS = set('the and for with this that have from your about what when where will just into are was you its she her them they how can please would could really want like love prefer'.split())
PROJECT = re.compile(r'\b(?:i(?: am|\'m) (?:working on|building|making)|we(?: are|\'re) (?:working on|building|making))\b', re.I)

class AdaptiveMemory:
    def __init__(self, path):
        self.path = Path(path)
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.execute('PRAGMA busy_timeout=3000')
        return con

    def _init(self):
        with self._connect() as con:
            con.execute('CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE, category TEXT NOT NULL, seen INTEGER NOT NULL DEFAULT 1, pinned INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY, user_text TEXT NOT NULL, reply_text TEXT NOT NULL, created TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS summaries (id INTEGER PRIMARY KEY, content TEXT NOT NULL, created TEXT NOT NULL)')
            con.execute('CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category)')
            con.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            con.execute("INSERT OR IGNORE INTO settings VALUES ('learning', 'on')")

    def enabled(self):
        with self._connect() as con:
            return con.execute("SELECT value FROM settings WHERE key='learning'").fetchone()[0] == 'on'

    def set_enabled(self, enabled):
        with self._connect() as con:
            con.execute("UPDATE settings SET value=? WHERE key='learning'", ('on' if enabled else 'off',))

    def observe(self, user_text, reply_text):
        if not self.enabled():
            return
        text = user_text.strip()
        if not text or BLOCKED.search(text) or len(text) > 500:
            return
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as con:
            con.execute('INSERT INTO chat(user_text,reply_text,created) VALUES (?,?,?)', (text[:500], reply_text[:1000], now))
            # Extract only explicit user preferences and project statements, never AI guesses.
            if 8 <= len(text) <= 180 and (PREFERENCE.search(text) or PROJECT.search(text)):
                category = 'preference' if PREFERENCE.search(text) else 'project'
                existing = con.execute('SELECT id FROM notes WHERE lower(content)=lower(?)', (text,)).fetchone()
                if existing:
                    con.execute('UPDATE notes SET seen=seen+1 WHERE id=?', existing)
                else:
                    # Explicit corrections are stored as newer statements; never guess which unrelated fact to erase.
                    con.execute('INSERT OR IGNORE INTO notes(content,category,created) VALUES (?,?,?)', (text,category,now))
            # Retain 24 exchanges; older chat is reduced to a transparent extractive digest.
            old = con.execute('SELECT id,user_text FROM chat ORDER BY id DESC LIMIT -1 OFFSET 24').fetchall()
            if old:
                snippets = [t[:130] for _,t in reversed(old) if not BLOCKED.search(t) and (PREFERENCE.search(t) or PROJECT.search(t) or CORRECTION.search(t))]
                if snippets:
                    digest = 'Older explicit preferences, project statements, and corrections (extractive, not AI-generated): ' + ' | '.join(snippets[-6:])
                    con.execute('INSERT INTO summaries(content,created) VALUES (?,?)', (digest[:1100],now))
                con.executemany('DELETE FROM chat WHERE id=?', [(i,) for i,_ in old])
            con.execute('DELETE FROM summaries WHERE id NOT IN (SELECT id FROM summaries ORDER BY id DESC LIMIT 5)')
            # Only remove old low-confidence observations, never pinned notes.
            con.execute('DELETE FROM notes WHERE pinned=0 AND seen=1 AND id NOT IN (SELECT id FROM notes ORDER BY id DESC LIMIT 35)')

    def context(self, query=""):
        """Retrieve matching notes first, with a small stable baseline; no network or embeddings."""
        with self._connect() as con:
            notes = con.execute('SELECT content,pinned,seen,id FROM notes ORDER BY id DESC LIMIT 200').fetchall()
            summaries = con.execute('SELECT content FROM summaries ORDER BY id DESC LIMIT 2').fetchall()
        terms = {w for w in re.findall(r'[a-z0-9]{3,}', query.lower()) if w not in STOPWORDS}
        ranked = []
        for content, pinned, seen, ident in notes:
            tokens = set(re.findall(r'[a-z0-9]{3,}', content.lower())) - STOPWORDS
            overlap = len(terms & tokens)
            if terms and not overlap and not pinned:
                continue
            ranked.append((overlap, pinned, seen, ident, content))
        ranked.sort(reverse=True)
        chosen = ranked[:8] if terms else ranked[:10]
        lines = ['Locally saved explicit user statements; newer corrections take priority. Do not assume any statement is current without context:']
        lines += ['- ' + x[4][:200] for x in chosen]
        if not terms:
            lines += [s[0][:600] for s in reversed(summaries)]
        return '\n'.join(lines)[:2800]

    def recent_activity(self, query=""):
        """Ground vague recall questions in recent locally saved user exchanges."""
        if not self.enabled():
            return ""
        recall = re.search(r"\b(?:remember|recall|working on|doing earlier|doing before|last time|previously|where were we|what were we|continue)\b", query, re.I)
        if not recall:
            return ""
        with self._connect() as con:
            rows = con.execute('SELECT user_text FROM chat ORDER BY id DESC LIMIT 18').fetchall()
        # Prefer project/activity statements, then the most recent other messages.
        selected = [t for (t,) in rows if not BLOCKED.search(t) and
                    (PROJECT.search(t) or re.search(r"\b(?:blender|project|animation|model|coding|building|making|editing|drawing|studying)\b", t, re.I))]
        if not selected:
            selected = [t for (t,) in rows if not BLOCKED.search(t) and len(t) > 12]
        if not selected:
            return "No recent user activity is saved. Do not invent what the user was doing."
        return "Recent user statements (newest first; use these when answering recall questions):\n" + "\n".join("- " + t[:240] for t in selected[:6])

    def report(self):
        with self._connect() as con:
            rows = con.execute('SELECT id,content,pinned FROM notes ORDER BY id DESC LIMIT 35').fetchall()
            count = con.execute('SELECT count(*) FROM chat').fetchone()[0]
        notes = '\n'.join(f'#{i} {"[protected] " if p else ""}{t}' for i,t,p in rows) or '(no automatically learned notes yet)'
        return f'Automatic learning: {"ON" if self.enabled() else "OFF"}. Recent saved exchanges: {count}.\n{notes}\nCommands: /learn on, /learn off, /learn clear, /learn delete ID, /learn protect ID'

    def delete_note(self, note_id):
        with self._connect() as con:
            return con.execute('DELETE FROM notes WHERE id=?', (note_id,)).rowcount > 0

    def protect(self, note_id):
        with self._connect() as con:
            return con.execute('UPDATE notes SET pinned=1 WHERE id=?', (note_id,)).rowcount > 0

    def clear(self):
        with self._connect() as con:
            for table in ('notes','chat','summaries'):
                con.execute(f'DELETE FROM {table}')
