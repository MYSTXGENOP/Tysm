"""Low-interruption, local-only proactive check-in scheduling."""
from datetime import datetime
import random
import time


class CheckinPolicy:
    def __init__(self, rng=None, clock=None):
        self.rng = rng or random.Random()
        self.clock = clock or time.monotonic
        self.last_activity = self.clock()
        self.next_due = self.clock() + self._delay()
        self.day = None
        self.sent_today = 0
        self.last_topic = None

    def _delay(self):
        return self.rng.randint(35, 65) * 60

    def record_activity(self):
        self.last_activity = self.clock()
        self.next_due = max(self.next_due, self.last_activity + 25 * 60)

    def due(self, enabled, busy, panel_visible, now=None):
        now = now or datetime.now()
        today = now.date()
        if self.day != today:
            self.day, self.sent_today = today, 0
        if not enabled or busy or panel_visible or not (9 <= now.hour < 23):
            return False
        tick = self.clock()
        return (self.sent_today < 3 and tick >= self.next_due
                and tick - self.last_activity >= 25 * 60)

    def make_prompt(self, recent_context=""):
        topics = [
            ('casual', 'Offer one brief, natural observation or low-pressure check-in. Do not repeatedly ask how the day is going.'),
            ('humor', 'Make one brief, lightly sarcastic or playful remark, without insulting the user.'),
            ('project', 'If a relevant ongoing project is genuinely known from the supplied context, ask one specific, useful follow-up about it. Otherwise make a casual remark.'),
            ('quiet', 'Write a very brief, optional invitation to continue something later, without pressuring the user to respond.'),
        ]
        choices = [item for item in topics if item[0] != self.last_topic]
        topic, instruction = self.rng.choice(choices)
        self.last_topic = topic
        context = recent_context[:350].replace('\n', ' ')
        return (
            'You are Tysm sending an occasional unsolicited check-in. '
            'Keep it to ONE short sentence, conversational and varied. '
            'Never claim to see the screen, know what the user is doing, or know their mood. '
            'Do not use generic customer-service greetings. Do not demand a response. '
            'Do not invent memories or activities. ' + instruction +
            (' Recent conversation topic (may be stale): ' + context if context else '')
        )

    def mark_sent(self):
        self.sent_today += 1
        self.next_due = self.clock() + self._delay()
