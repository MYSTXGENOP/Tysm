"""Local time awareness for Tysm, independent of chat and personal memory files.

Only stores the timestamp of the last successful user/assistant exchange.
No message content, inferred habits, or scheduled jobs are saved here.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


class TimeAwareness:
    def __init__(self, directory):
        self.path = Path(directory) / 'tysm_time_state.json'

    def last_exchange(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            timestamp = data.get('last_exchange_utc')
            previous = datetime.fromisoformat(timestamp)
            if previous.tzinfo is not None:
                return previous.astimezone(timezone.utc)
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return None

    def context(self, now=None):
        """Accurate clock context for the model; never invent prior activity."""
        now = now or datetime.now().astimezone()
        if now.tzinfo is None:
            now = now.astimezone()
        local = now.astimezone()
        timestamp = local.strftime('%A, %B %d, %Y at %I:%M:%S %p %Z (UTC%z)')
        lines = [f'Current Windows local date/time: {timestamp}.',
                 'Use the PC clock for dates and relative time; do not guess the time.',
                 'Time information is background context, not a reason to announce the time or comment on the user returning.',
                 'Use any elapsed-time context only when directly relevant. Do not imply you watched the user or know what happened while they were away.']
        previous = self.last_exchange()
        if previous is None:
            lines.append('No reliable saved timestamp of a previous completed conversation.')
        else:
            delta = now.astimezone(timezone.utc) - previous
            seconds = delta.total_seconds()
            if seconds < 0:
                lines.append('Stored last exchange timestamp is in the future; ignore it (system clock may have changed).')
            else:
                hours = seconds / 3600
                if hours < 1:
                    gap = f'about {max(1, round(seconds / 60))} minute(s)'
                elif hours < 48:
                    gap = f'about {hours:.1f} hours'
                else:
                    gap = f'about {hours / 24:.1f} days'
                previous_local = previous.astimezone(local.tzinfo)
                lines.append('Last successful chat reply was completed at '
                             f'{previous_local.strftime("%A, %B %d at %I:%M %p")} local time '
                             f'({gap} ago). This is a reply timestamp, not evidence of what the user did afterward.')
        return '\n'.join(lines)

    def mark_exchange(self, now=None):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError('mark_exchange requires an aware datetime')
        now = now.astimezone(timezone.utc)
        data = {'last_exchange_utc': now.isoformat(timespec='seconds')}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, indent=2), encoding='utf-8')
        temp.replace(self.path)
