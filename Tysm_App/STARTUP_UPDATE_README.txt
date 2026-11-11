TYSM STARTUP + CONVERSATION UPDATE

Open START_HERE/assistant.py as before.

On each new program launch only:
  - play assets/audio/startup.wav (approved 15-second producer-tag mix)
  - display an enlarged version of the ORIGINAL pendant_idle.gif
  - rotate and shrink it smoothly toward the normal desktop icon
  - open the regular Tysm chat window once the shrink finishes

Reopening chat during that launch DOES NOT replay the intro or song.
All existing animation files, Spotify integration, and saved memory files are unchanged.
Personality instructions have been adjusted to encourage grounded disagreement,
less excessive validation, and more natural replies, without mood tags.

Windows sound uses built-in winsound. The intro uses Pillow (already an
optional dependency for current GIF display). If unavailable, Tysm still
opens normally and plays the audio. The original desktop icon and chat UI
continue to use the existing animation controller.

Keep your previous folder backed up and extract this update into a fresh folder.
Memories gained after this ZIP was uploaded cannot be included automatically.
