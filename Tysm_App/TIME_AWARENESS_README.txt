TYSM TIME AWARENESS
===================
Tysm already used the Windows clock to answer time/date questions.
This update also lets her know how long it has been since the last
successful ordinary chat reply. She should refer to that only when useful.

New file: tysm_time_awareness.py
New state after first ordinary chat: tysm_time_state.json

The state stores only one timestamp, not messages or private details.
Your memories, chat history, Spotify data and animations are unchanged.

If you want to remove the time-gap feature, remove the module and its
assistant.py integration; deleting tysm_time_state.json only resets
the timestamp, not any conversation memories.

Launch as before: Tysm_Updated/START_HERE/assistant.py
