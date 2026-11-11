"""Conservative Windows window/volume controls. No closing, keystroke injection into apps, or shell."""
import ctypes
import os
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class DesktopResult:
    message: str
    status: str


def _windows():
    if os.name != 'nt':
        return []
    from ctypes import wintypes
    u = ctypes.windll.user32
    found = []
    cbtype = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def collect(hwnd, _):
        if not u.IsWindowVisible(hwnd) or u.GetWindowTextLengthW(hwnd) <= 0:
            return True
        size = u.GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(size)
        u.GetWindowTextW(hwnd, buf, size)
        title = buf.value.strip()
        if title:
            found.append((hwnd, title))
        return True
    cb = cbtype(collect)
    u.EnumWindows(cb, 0)
    return found


def _find_window(name):
    name = name.casefold().strip()
    matches = [(hwnd, title) for hwnd, title in _windows() if name in title.casefold()]
    if not matches:
        return None, f"I can't find an open window matching '{name}'."
    exact = [(h,t) for h,t in matches if t.casefold() == name]
    if len(exact) == 1:
        return exact[0], None
    if len(matches) != 1:
        return None, 'Several windows match: ' + ', '.join(t for _,t in matches[:4]) + '. Be more specific.'
    return matches[0], None


def _volume(direction, steps=3):
    if os.name != 'nt':
        return False, 'Volume controls are available on Windows only.'
    key = {'up':0xAF, 'down':0xAE, 'mute':0xAD}[direction]
    user32 = ctypes.windll.user32
    try:
        for _ in range(steps if direction != 'mute' else 1):
            user32.keybd_event(key, 0, 0, 0)
            user32.keybd_event(key, 0, 0x0002, 0)
        return True, ('Toggled system mute.' if direction == 'mute' else f'Adjusted system volume {direction} {steps} steps.')
    except (OSError, AttributeError) as e:
        return False, f'Volume control failed: {e}'


def execute(text):
    s = re.sub(r'^\s*(?:hey\s+)?tysm[,!: ]*', '', text, flags=re.I).strip().rstrip('!? .')
    if re.fullmatch(r'(?:what(?: apps| applications| windows)? (?:are )?(?:running|open)|list open windows|show open windows)', s, re.I):
        windows = _windows()
        titles = [title for _, title in windows if title and not title.startswith('TYSM')]
        return DesktopResult('Open windows: ' + ', '.join(titles[:12]) if titles else 'No other visible windows found.', 'Windows inspected')
    if re.fullmatch(r'(?:mute|unmute|toggle mute)(?: (?:the )?(?:sound|audio|volume))?', s, re.I):
        ok, msg = _volume('mute')
        return DesktopResult(msg, 'Volume updated' if ok else 'Volume unavailable')
    match = re.fullmatch(r'(?:turn (?:the )?volume|volume)\s+(up|down)(?:\s+(?:a bit|a little))?', s, re.I)
    if match:
        ok, msg = _volume(match.group(1).lower())
        return DesktopResult(msg, 'Volume updated' if ok else 'Volume unavailable')
    match = re.fullmatch(r'(switch to|focus|bring (?:up|forward)|minimize|restore)\s+(.+)', s, re.I)
    if not match:
        return None
    verb, name = match.group(1).lower(), match.group(2).strip()
    if not name or len(name) > 80:
        return DesktopResult('Please name the window.', 'No action')
    found, error = _find_window(name)
    if error:
        return DesktopResult(error, 'Window not found')
    hwnd, title = found
    if os.name != 'nt':
        return DesktopResult('Window controls require Windows.', 'Unavailable')
    try:
        user32 = ctypes.windll.user32
        if verb == 'minimize':
            ok = user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE; return value is previous visibility, not success
            return DesktopResult(f'Asked Windows to minimize {title}.', 'Window action sent')
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        foreground = bool(user32.SetForegroundWindow(hwnd))
        return DesktopResult(f'Asked Windows to bring {title} forward.' if foreground else f'Windows may have blocked focusing {title}; try clicking it.', 'Window action sent' if foreground else 'Focus not confirmed')
    except (OSError, AttributeError) as exc:
        return DesktopResult(f'Could not control {title}: {exc}', 'Window action failed')
