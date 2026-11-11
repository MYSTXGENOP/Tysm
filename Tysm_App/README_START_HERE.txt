TYSM — SPOTIFY MAIN / CHILL PLAYBACK
===================================
Run START_HERE/assistant.py to launch Tysm, not tysm_music.py.

First time: Spotify has new playback permissions.
  /spotify connect      (approve the new permissions in the browser)
  /spotify playlists    (list playlists and their numbers)
  /spotify favorite 1 main
  /spotify favorite 2 chill
  /spotify favorites
  /spotify play main
  /spotify play chill
  /spotify pause
  /spotify resume
  /spotify skip

Replace the playlist numbers 1 and 2 with your own.
Your actual playlist names are unchanged.

Spotify playback commands require Spotify Premium and an active playback device.
If no device is active, open Spotify, start a song manually, and retry.
If you see an authorization error, run /spotify connect again.

Spotify song data stays outside Ollama; user-entered music preferences
are stored separately in music_preferences.json.

Only outdated README documents, old backup COPIES, Python cache, and
old test scripts were removed from this packaged version. Existing
memory, history, SQLite databases, settings, personality files, and
approved animations remain intact.

NOTE: The ZIP reflects the data present in the ZIP you supplied.
If your live running copy has NEWER memories, preserve those files
before extracting this update over it.
