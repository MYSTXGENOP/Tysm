"""Local SQLite reminders and opt-in ntfy phone notifications. No external deps."""
import json
import re
import secrets
import sqlite3
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

class PhoneReminders:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.settings = self.folder / 'tysm_phone_settings.json'
        self.database = self.folder / 'tysm_reminders.sqlite3'
        self._initialize()

    def _connect(self):
        con = sqlite3.connect(self.database, timeout=5)
        con.row_factory = sqlite3.Row
        return con

    def _initialize(self):
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, message TEXT NOT NULL, due_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT "pending", attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT NOT NULL DEFAULT "")')

    def topic(self):
        try:
            return json.loads(self.settings.read_text(encoding='utf-8')).get('topic','')
        except (OSError, ValueError, AttributeError):
            return ''

    def setup(self):
        topic = self.topic()
        if not topic:
            topic = 'tysm-' + secrets.token_urlsafe(24).replace('_','-')
            self.settings.write_text(json.dumps({'topic':topic},indent=2), encoding='utf-8')
        return topic

    def send(self, message, title='Tysm reminder'):
        topic = self.topic()
        if not topic:
            raise RuntimeError('Phone is not connected. Use /phone setup first.')
        if not message.strip():
            raise ValueError('Empty notification')
        req = urllib.request.Request('https://ntfy.sh/'+topic,
            data=message.encode('utf-8'), method='POST',
            headers={'Title':title,'Tags':'bell','Content-Type':'text/plain; charset=utf-8'})
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status not in (200,201,202):
                raise RuntimeError('Notification service returned '+str(response.status))
        return True

    @staticmethod
    def parse(text, now=None):
        now = now or datetime.now()
        s = text.strip()
        m = re.fullmatch(r'(?:/remind|remind me)\s+in\s+(\d+)\s*(minutes?|mins?|hours?|hrs?|days?)\s+(?:to\s+)?(.+)',s,re.I)
        if m:
            n=int(m.group(1))
            if n<1 or n>10080: raise ValueError('Choose a time between 1 minute and 10080 units.')
            unit=m.group(2).lower()
            delta=timedelta(days=n) if unit.startswith('day') else timedelta(hours=n) if unit.startswith(('hour','hr')) else timedelta(minutes=n)
            return now+delta,m.group(3).strip()
        m=re.fullmatch(r'(?:/remind|remind me)\s+(tomorrow|today)\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s+(?:to\s+)?(.+)',s,re.I)
        if m:
            hour=int(m.group(2)); minute=int(m.group(3) or 0)
            if not 1<=hour<=12 or minute>59: raise ValueError('Invalid clock time.')
            hour=hour%12+(12 if m.group(4).lower()=='pm' else 0)
            day=now.date()+timedelta(days=(m.group(1).lower()=='tomorrow'))
            due=datetime.combine(day,datetime.min.time()).replace(hour=hour,minute=minute)
            if due<=now: raise ValueError('That time has already passed.')
            return due,m.group(5).strip()
        return None

    def add(self,due,message):
        if not self.topic(): raise RuntimeError('Set up your phone with /phone setup first.')
        if not message or len(message)>500: raise ValueError('Reminder must contain 1–500 characters.')
        with self._connect() as db:
            cur=db.execute('INSERT INTO reminders (message,due_at) VALUES (?,?)',(message,due.isoformat(timespec='seconds')))
            return cur.lastrowid

    def list(self):
        with self._connect() as db:
            return [dict(x) for x in db.execute("SELECT id,message,due_at,status FROM reminders WHERE status IN ('pending','failed') ORDER BY due_at LIMIT 30")]

    def cancel(self,id):
        with self._connect() as db:
            return db.execute("UPDATE reminders SET status='cancelled' WHERE id=? AND status IN ('pending','failed')",(id,)).rowcount>0

    def due(self,now=None):
        now=now or datetime.now()
        with self._connect() as db:
            return [dict(x) for x in db.execute("SELECT id,message FROM reminders WHERE status='pending' AND due_at<=? ORDER BY due_at LIMIT 5",(now.isoformat(timespec='seconds'),))]

    def deliver(self,record):
        try:
            self.send(record['message'])
        except Exception as exc:
            with self._connect() as db:
                db.execute("UPDATE reminders SET status='failed', attempts=attempts+1,last_error=? WHERE id=?",(str(exc)[:200],record['id']))
            return False
        with self._connect() as db:
            db.execute("UPDATE reminders SET status='sent',last_error='' WHERE id=?",(record['id'],))
        return True

    def retry(self,id):
        with self._connect() as db:
            return db.execute("UPDATE reminders SET status='pending',last_error='' WHERE id=? AND status='failed'",(id,)).rowcount>0
