# Approved Tysm startup animation — 4.5s handoff

This update leaves the old startup untouched as a fallback and keeps all memory, personality, music and idle animation data unchanged.

## Sequence

- 0.0–4.2 seconds: approved Tysm portrait animation
- 4.2–4.5 seconds: sharp magenta/green eye glitch
- 4.5–5.15 seconds: original winged-ankh pendant shrinks into its usual desktop position
- After 5.15 seconds: existing `pendant_idle.gif` loop continues
- `startup.wav` plays once at app launch for its complete 15 seconds

## Required asset

Place the pixel-art GIF exactly here:

`Tysm_App/assets/animations/tysm_startup_intro.gif`

The file is deliberately NOT in this draft pull request because the GitHub connector cannot upload the compiled binary GIF. Until it is added, the app automatically uses the old working startup, with no visual change. The original GIFs and music should not be replaced.

## Scope

- `Tysm_App/assistant.py`: switches to the optional Tysm intro subclass
- `Tysm_App/tysm_startup_intro.py`: new isolated Tk-only startup animation controller
- Original `tysm_startup.py`, `tysm_animations.py`, music and all user data remain unchanged

## Test before merge

1. Add `tysm_startup_intro.gif` to this branch, then test in a separate clone/copy on Windows.
2. Confirm that the portrait plays through 4.2 seconds; the eye glitch covers 4.2–4.5 seconds; and the pendant immediately appears and shrinks.
3. Confirm the pendant spins continuously after the shrink, and chat opens.
4. Confirm the full 15-second audio plays only once after launching Tysm; closing and reopening chat does not replay it.
5. If the asset is missing, confirm the old 2.7-second startup still works.
6. Test at the user's Windows screen resolution; native Tk overlay animation has not been validated on that PC.

Do not merge until that test is approved.