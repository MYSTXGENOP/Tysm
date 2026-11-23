"""Run from the repository root: python -m unittest discover -s tests -v"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tysm_App"))
from tysm_history import HistoryStore


class HistorySessionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.history = root / "tysm_history.json"
        self.settings = root / "tysm_history_settings.json"

    def tearDown(self):
        self.tmp.cleanup()

    def store(self, **kwargs):
        return HistoryStore(self.history, self.settings, **kwargs)

    def test_restart_keeps_old_chat_out_of_live_context(self):
        s = self.store()
        first_id = s.current_id
        s.append_exchange("yesterday", "previous reply")
        reopened = self.store()
        self.assertNotEqual(reopened.current_id, first_id)
        self.assertEqual(reopened.load_messages(), [])
        self.assertIn(first_id, reopened.list_sessions())
        self.assertIn("yesterday", reopened.show_session(first_id))

    def test_legacy_flat_history_is_archived_without_auto_replay(self):
        old = [{"role": "user", "content": "old subject"},
               {"role": "assistant", "content": "old answer"}]
        self.history.write_text(json.dumps(old), encoding="utf-8")
        s = self.store()
        self.assertEqual(s.load_messages(), [])
        self.assertIn("legacy", s.list_sessions())
        self.assertIn("old subject", s.show_session("legacy"))
        self.assertEqual(json.loads(self.history.read_text())["version"], 2)

    def test_manual_new_chat_does_not_erase_older_chat(self):
        s = self.store()
        first_id = s.current_id
        s.append_exchange("first", "reply")
        s.begin_session()
        self.assertEqual(s.load_messages(), [])
        self.assertIn("first", s.show_session(first_id))

    def test_bounded_history_and_session_count(self):
        s = self.store(max_messages=4, max_sessions=3)
        for i in range(4):
            s.append_exchange(f"user {i}", f"reply {i}")
        self.assertEqual(len(s.load_messages()), 4)
        for i in range(4):
            s.begin_session()
        self.assertEqual(len(json.loads(self.history.read_text())["sessions"]), 3)

    def test_disabled_history_does_not_save_exchanges(self):
        s = self.store()
        s.set_enabled(False)
        s.append_exchange("private user", "private answer")
        self.assertEqual(s.load_messages(), [])
        self.assertNotIn("private user", self.history.read_text(encoding="utf-8"))

    def test_clear_removes_all_history(self):
        s = self.store()
        s.append_exchange("old", "reply")
        s.clear()
        self.assertFalse(self.history.exists())
        s.begin_session()
        self.assertNotIn("old", s.list_sessions())


if __name__ == "__main__":
    unittest.main()
