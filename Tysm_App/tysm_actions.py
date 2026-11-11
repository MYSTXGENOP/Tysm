"""Tysm V3 local commands: no LLM execution, no shell, no arbitrary paths."""
import os
import re
import subprocess
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse

KNOWN_SITES = {
    'youtube': 'https://www.youtube.com', 'gmail': 'https://mail.google.com',
    'google': 'https://www.google.com', 'spotify': 'https://open.spotify.com',
    'github': 'https://github.com', 'discord': 'https://discord.com/app',
    'reddit': 'https://www.reddit.com', 'twitch': 'https://www.twitch.tv',
    'wikipedia': 'https://www.wikipedia.org', 'instagram': 'https://www.instagram.com',
    'netflix': 'https://www.netflix.com', 'chatgpt': 'https://chatgpt.com',
    'roblox website': 'https://www.roblox.com', 'roblox.com': 'https://www.roblox.com',
}
BUILTIN_APPS = {'calculator':'calc.exe','calc':'calc.exe','notepad':'notepad.exe','paint':'mspaint.exe'}
BLOCKED_SHORTCUT_WORDS = ('uninstall', 'remove ', 'reset ', 'command prompt', 'powershell', 'terminal', 'registry editor', 'administrator')

@dataclass(frozen=True)
class ActionResult:
    message: str
    status: str


def normalize(text):
    text = re.sub(r'^\s*(?:hey\s+)?tysm(?:[,!: ]+|$)', '', text, flags=re.I).strip()
    return re.sub(r'[.!?]+$', '', text).strip()


def get_local_time_answer(text, now=None):
    s = normalize(text).lower()
    s = re.sub(r'^(?:please\s+|can you\s+|could you\s+|tell me\s+)', '', s).strip()
    now = now or datetime.now().astimezone()
    if s in {'what time is it', "what's the time", 'whats the time', 'current time', 'the time', 'tell me the time', 'give me the time', 'time right now', 'what time is it right now'}:
        return f"It's {now.strftime('%I:%M %p').lstrip('0')} on your PC clock."
    if s in {"what's today's date", 'whats todays date', "what is today's date", 'what is the date', "what's the date", 'whats the date', "today's date", 'todays date', 'current date', 'tell me the date'}:
        return f"Today's date is {now.strftime('%B')} {now.day}, {now.year}."
    if s in {'what day is it', 'what day is today', 'what day is it today', "what's today", 'whats today', "what's the day", 'whats the day', 'day of the week', 'what day of the week is it'}:
        return f'Today is {now.strftime("%A")}.'
    return None


# Exact aliases help with shortcut labels that include version numbers or launchers.
APP_ALIASES = {
    'blender': ('blender',),
    'after effects': ('adobe after effects', 'after effects'),
    'after effects 2025': ('adobe after effects 2025', 'after effects 2025'),
    'roblox': ('roblox player', 'roblox'),
    'play roblox': ('roblox player', 'roblox'),
    'roblox studio': ('roblox studio',),
    'steam': ('steam',), 'discord': ('discord',),
    'chrome': ('google chrome', 'chrome'),
    'edge': ('microsoft edge', 'edge'),
    'vs code': ('visual studio code',),
    'minecraft': ('minecraft launcher', 'minecraft'),
    'battle net': ('battle.net',),
}


def _shortcut_roots():
    roots = []
    for env in ('APPDATA', 'PROGRAMDATA'):
        base = os.environ.get(env)
        if base:
            roots.append(Path(base) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs')
    # Both user and shared desktops are relevant to installed games.
    roots.append(Path.home() / 'Desktop')
    roots.append(Path.home() / 'OneDrive' / 'Desktop')
    public = os.environ.get('PUBLIC')
    if public:
        roots.append(Path(public) / 'Desktop')
    return roots


def _shortcuts():
    result = {}
    for folder in dict.fromkeys(_shortcut_roots()):
        if not folder.is_dir():
            continue
        try:
            for extension in ('*.lnk', '*.url'):
                for path in folder.rglob(extension):
                    label = path.stem.strip()
                    key = label.casefold()
                    if any(word in key for word in BLOCKED_SHORTCUT_WORDS):
                        continue
                    result.setdefault(key, (label, path))
        except (OSError, PermissionError):
            continue
    return result


def _find_app(name):
    needle = name.strip().casefold()
    shortcuts = _shortcuts()
    # Exact labels win; aliases only select unique, relevant shortcuts.
    if needle in shortcuts:
        return shortcuts[needle][1], None
    for alias in APP_ALIASES.get(needle, (needle,)):
        if alias in shortcuts:
            return shortcuts[alias][1], None
        matches = [(label, path) for key, (label, path) in shortcuts.items()
                   if key.startswith(alias + ' ') or key.startswith(alias + '-')]
        # Never accidentally open Studio when the user requests Roblox Player.
        if needle in ('roblox', 'play roblox'):
            matches = [(label, path) for label, path in matches if 'studio' not in label.casefold()]
        if len(matches) == 1:
            return matches[0][1], None
        if len(matches) > 1:
            return None, 'Multiple apps match: ' + ', '.join(label for label, _ in matches[:5]) + '. Use the full name.'
    return None, f"I couldn't find '{name}' in your Windows Desktop or Start Menu shortcuts."


def _target(text):
    raw=text.strip().strip('.,!? ')
    key=re.sub(r'^the\s+','',raw,flags=re.I).casefold()
    if key in KNOWN_SITES:
        return ('url',KNOWN_SITES[key])
    if re.fullmatch(r'(?:https?://)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d{1,5})?(?:/[\w\-./?=&%+#~]*)?',key):
        url=raw if raw.lower().startswith(('https://','http://')) else 'https://'+raw
        parsed=urlparse(url)
        if parsed.scheme in ('http','https') and parsed.hostname:
            return ('url',url)
    if key in BUILTIN_APPS:
        return ('builtin',BUILTIN_APPS[key])
    if key in ('documents','my documents','downloads','my downloads'):
        name='Documents' if 'document' in key else 'Downloads'
        return ('folder',name)
    if re.fullmatch(r'[\w][\w .+&()\-]{0,79}',raw,flags=re.UNICODE):
        return ('installed',raw)
    return None


def _open_folder(name):
    home=Path.home()
    candidates=[home/name,home/'OneDrive'/name]
    existing=[path for path in candidates if path.is_dir()]
    if not existing:
        return False,f"Couldn't find your {name} folder."
    if len(existing)>1:
        return False,f"Found more than one {name} folder. Please open the one you want manually."
    os.startfile(str(existing[0]))
    return True,f'Asked Windows to open {name}.'


def _perform(target):
    kind,value=target
    try:
        if kind=='url':
            ok=webbrowser.open_new_tab(value)
            return (True,f'Browser accepted: {value}') if ok else (False,f'Browser did not confirm opening {value}.')
        if kind=='builtin':
            subprocess.Popen([value],shell=False)
            return True,f'Asked Windows to launch {value}.'
        if kind=='folder':
            return _open_folder(value)
        if kind=='installed':
            shortcut,error=_find_app(value)
            if error:
                return False,error
            os.startfile(str(shortcut))
            return True,f'Asked Windows to launch {shortcut.stem}.'
    except (OSError,ValueError) as exc:
        return False,f'Could not open {value}: {exc}'
    return False,'Unsupported action.'


def execute_command(text):
    s=normalize(text)
    # Explicit slash commands are user shortcuts, not prompts for Ollama.
    # Strip a slash ONLY for verbs handled by this restricted action router.
    # This does not enable arbitrary commands or executable paths.
    s=re.sub(r'^/(open|launch|start|play|search|google|look|go|bring)\b', r'\1', s, flags=re.I)
    search=re.fullmatch(r'(?:please\s+)?(?:search(?:\s+(?:the\s+)?web)?\s+for|google|look\s+up)\s+(.+)',s,flags=re.I)
    if search:
        query=search.group(1).strip()
        ok,msg=_perform(('url','https://www.google.com/search?q='+quote_plus(query)))
        return ActionResult((f'Search opened for: {query}' if ok else msg),('Browser request sent' if ok else 'Browser action failed'))
    match=re.fullmatch(r'(?:please\s+)?(?:open|launch|start|play|go\s+to|bring\s+up)\s+(.+)',s,flags=re.I)
    if not match:
        return None
    raw=re.sub(r'\s+for\s+me\s*$','',match.group(1),flags=re.I).strip()
    raw=re.sub(r'^(?:the\s+)?(?:app|game)\s+', '', raw, flags=re.I).strip()
    parts=[p.strip() for p in re.split(r'\s*(?:,|\band\b)\s*',raw,flags=re.I) if p.strip()]
    if not parts or len(parts)>5:
        return ActionResult('Please request between one and five apps or sites at a time.','Action not run')
    targets=[_target(p) for p in parts]
    if any(t is None for t in targets):
        unknown=', '.join(p for p,t in zip(parts,targets) if t is None)
        return ActionResult(f"I couldn't safely identify: {unknown}. Nothing was opened.",'Action not run')
    results=[_perform(t) for t in targets]
    return ActionResult('\n'.join(('✓ ' if ok else '✕ ')+msg for ok,msg in results),'Requests sent' if all(ok for ok,_ in results) else 'Some actions failed')
