"""User-operated Spotify playlist browser + explicitly supplied music preferences.

Spotify API content is displayed to the user ONLY; never injected into AI prompts,
conversation history, semantic memory, or training data.
"""
import base64
import hashlib
import json
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REDIRECT = 'http://127.0.0.1:8888/callback'
API = 'https://api.spotify.com/v1'
SCOPES = 'playlist-read-private playlist-read-collaborative user-read-playback-state user-modify-playback-state'


class SpotifyMusic:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.settings_file = self.directory / 'music_settings.json'
        self.memory_file = self.directory / 'music_preferences.json'
        self.favorites_file = self.directory / 'music_playlist_aliases.json'
        self.access_token = None  # Tokens deliberately kept in RAM only.
        self.refresh_token = None
        self.expires_at = 0
        self._pending = False
        self.playlists = []
        self._load_settings()

    def _load_settings(self):
        try:
            config = json.loads(self.settings_file.read_text(encoding='utf-8'))
            self.client_id = str(config.get('client_id', '')).strip()
        except (OSError, ValueError, TypeError):
            self.client_id = ''

    def set_client_id(self, value):
        value = value.strip()
        if not re.fullmatch(r'[A-Za-z0-9]{32}', value):
            raise ValueError('Client ID must be the 32-character ID from Spotify Developer Dashboard.')
        self.client_id = value
        self.settings_file.write_text(json.dumps({'client_id': value}, indent=2), encoding='utf-8')

    def _load_preferences(self):
        try:
            data = json.loads(self.memory_file.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return [str(p) for p in data if isinstance(p, str)][:150]
        except (OSError, ValueError, TypeError):
            pass
        return []

    def remember(self, preference):
        preference = preference.strip()
        if not 1 <= len(preference) <= 240:
            raise ValueError('Tell me one music preference (up to 240 characters).')
        existing = self._load_preferences()
        if preference.casefold() not in [v.casefold() for v in existing]:
            existing.append(preference)
            self.memory_file.write_text(json.dumps(existing[-150:], indent=2, ensure_ascii=False), encoding='utf-8')
        return preference

    def _token(self):
        if not self.access_token:
            raise RuntimeError('Not connected. Run /spotify connect first.')
        if time.time() > self.expires_at - 60:
            if not self.refresh_token:
                raise RuntimeError('Spotify session expired. Run /spotify connect again.')
            self._exchange({'grant_type': 'refresh_token', 'refresh_token': self.refresh_token,
                            'client_id': self.client_id})
        return self.access_token

    def _exchange(self, body):
        request = urllib.request.Request('https://accounts.spotify.com/api/token',
            data=urllib.parse.urlencode(body).encode('ascii'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.load(response)
        self.access_token = data['access_token']
        self.refresh_token = data.get('refresh_token', self.refresh_token)
        self.expires_at = time.time() + int(data.get('expires_in', 3600))

    def connect(self, notify):
        if not self.client_id:
            raise RuntimeError('First run /spotify setup YOUR_CLIENT_ID')
        if self._pending:
            raise RuntimeError('A Spotify sign-in is already underway.')
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        state = secrets.token_urlsafe(24)
        auth_url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
            'client_id': self.client_id, 'response_type': 'code', 'redirect_uri': REDIRECT,
            'code_challenge_method': 'S256', 'code_challenge': challenge,
            'state': state, 'scope': SCOPES,
        })
        self._pending = True

        def worker():
            try:
                music = self
                class Callback(BaseHTTPRequestHandler):
                    def do_GET(self):
                        query = urllib.parse.urlparse(self.path)
                        params = urllib.parse.parse_qs(query.query)
                        if query.path != '/callback' or params.get('state', [''])[0] != state:
                            self.send_response(400)
                            self.end_headers()
                            self.wfile.write(b'Invalid Spotify login callback.')
                            return
                        self.server.oauth_result = params
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(b'<h2>Spotify authorization received.</h2><p>You can close this tab and return to Tysm.</p>')
                    def log_message(self, *args):
                        pass
                server = HTTPServer(('127.0.0.1', 8888), Callback)
                server.timeout = 1
                try:
                    notify('Spotify sign-in opened in your browser. Approve access there.')
                    webbrowser.open(auth_url)
                    start = time.monotonic()
                    while time.monotonic() - start < 180 and not getattr(server, 'oauth_result', None):
                        server.handle_request()
                    result = getattr(server, 'oauth_result', {})
                finally:
                    server.server_close()
                code = result.get('code', [''])[0]
                if not code:
                    raise RuntimeError(result.get('error', ['Authorization timed out or was canceled.'])[0])
                music._exchange({'grant_type': 'authorization_code', 'code': code,
                                 'redirect_uri': REDIRECT, 'client_id': music.client_id,
                                 'code_verifier': verifier})
                notify('Spotify connected. Use /spotify playlists to browse your playlists.')
            except Exception as exc:
                notify('Spotify connection failed: ' + str(exc)[:180])
            finally:
                self._pending = False
        threading.Thread(target=worker, daemon=True).start()

    def _get(self, path, params=None):
        url = API + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        request = urllib.request.Request(url,
            headers={'Authorization': 'Bearer ' + self._token(), 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise RuntimeError('Spotify restricts tracks to playlists you own or collaborate on.') from None
            if exc.code == 429:
                raise RuntimeError('Spotify rate limit reached. Try again later.') from None
            if exc.code == 401:
                raise RuntimeError('Spotify authorization expired. Run /spotify connect again.') from None
            raise RuntimeError(f'Spotify API returned HTTP {exc.code}.') from None

    def list_playlists(self):
        data = self._get('/me/playlists', {'limit': 50})
        self.playlists = list(data.get('items') or [])
        lines = []
        for idx, playlist in enumerate(self.playlists, 1):
            if not playlist:
                continue
            lines.append(f'{idx}. {playlist.get("name", "Untitled")}  —  {playlist.get("external_urls", {}).get("spotify", "") }')
        more = '\nMore playlists exist; this view shows the first 50.' if data.get('next') else ''
        return ('Your Spotify playlists:\n' + '\n'.join(lines) + more) if lines else 'No playlists found.'

    def playlist_items(self, index):
        if not 1 <= index <= len(self.playlists):
            raise ValueError('Run /spotify playlists, then /spotify songs NUMBER (e.g., /spotify songs 1).')
        p = self.playlists[index - 1]
        data = self._get(f'/playlists/{p["id"]}/items', {'limit': 50})
        lines = []
        for item in data.get('items') or []:
            track = item.get('item') or item.get('track') or {}
            if not isinstance(track, dict):
                continue
            artists = ', '.join(a.get('name', '?') for a in track.get('artists', []) if isinstance(a, dict))
            lines.append(f'{len(lines)+1}. {track.get("name", "Unknown")} — {artists}  {track.get("external_urls", {}).get("spotify", "")}')
        more = '\nShowing first 50 songs.' if data.get('next') else ''
        return f'Spotify playlist: {p.get("name", "Untitled")}\n' + ('\n'.join(lines) or 'No tracks found.') + more

    def _aliases(self):
        try:
            data = json.loads(self.favorites_file.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return {name: val for name, val in data.items()
                        if name in ('main', 'chill') and isinstance(val, dict)
                        and re.fullmatch(r'[A-Za-z0-9]{10,50}', str(val.get('id', '')))}
        except (OSError, ValueError, TypeError):
            pass
        return {}

    def favorite_playlist(self, index, nickname):
        nickname = nickname.lower().strip()
        if nickname not in ('main', 'chill'):
            raise ValueError('Use main or chill as your playlist nickname.')
        if not self.playlists:
            raise ValueError('Run /spotify playlists first.')
        if not 1 <= index <= len(self.playlists):
            raise ValueError('Playlist number not found. Run /spotify playlists again.')
        playlist = self.playlists[index - 1]
        if not isinstance(playlist, dict) or not playlist.get('id'):
            raise ValueError('That playlist is unavailable.')
        aliases = self._aliases()
        aliases[nickname] = {'id': playlist['id'], 'name': playlist.get('name', 'Untitled')}
        self.favorites_file.write_text(json.dumps(aliases, indent=2, ensure_ascii=False), encoding='utf-8')
        return f'{nickname} now points to: {playlist.get("name", "Untitled")}. Try /spotify play {nickname}.'

    def favorite_list(self):
        aliases = self._aliases()
        if not aliases:
            return 'No playlist shortcuts yet. Run /spotify playlists, then /spotify favorite 1 main.'
        return 'Saved playlist shortcuts:\n' + '\n'.join(
            f'- {name}: {details.get("name", "Untitled")}' for name, details in aliases.items())

    def _player_request(self, method, path, data=None, params=None):
        url = API + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        body = None if data is None else json.dumps(data).encode('utf-8')
        headers = {'Authorization': 'Bearer ' + self._token(), 'Accept': 'application/json'}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = response.read()
                return json.loads(result) if result else None
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise RuntimeError('Spotify authorization expired. Run /spotify connect again.') from None
            if exc.code == 403:
                raise RuntimeError('Spotify refused playback control. Reconnect with /spotify connect to grant playback permissions.') from None
            if exc.code == 404:
                raise RuntimeError('No active Spotify device. Open Spotify and start a song, then try again.') from None
            if exc.code == 429:
                raise RuntimeError('Spotify rate limit reached. Try again later.') from None
            raise RuntimeError(f'Spotify playback request failed (HTTP {exc.code}).') from None

    def play_playlist(self, nickname):
        nickname = nickname.lower().strip()
        playlists = self._aliases()
        chosen = playlists.get(nickname)
        if chosen is None:
            raise ValueError(f'No playlist saved as {nickname}. Run /spotify playlists and /spotify favorite NUMBER {nickname}.')
        self._player_request('PUT', '/me/player/play',
                             data={'context_uri': 'spotify:playlist:' + chosen['id']})
        return f'Playing {nickname}: {chosen.get("name", "Untitled")}.'

    def player_control(self, action):
        endpoints = {'pause': ('PUT', '/me/player/pause'),
                     'resume': ('PUT', '/me/player/play'),
                     'skip': ('POST', '/me/player/next')}
        method, path = endpoints[action]
        self._player_request(method, path)
        return {'pause': 'Spotify paused.', 'resume': 'Resuming Spotify.',
                'skip': 'Skipping to the next track.'}[action]

    def handle(self, text, notify):
        clean = text.strip()
        lower = clean.lower()
        if lower.startswith('/spotify setup '):
            self.set_client_id(clean[len('/spotify setup '):])
            return 'Spotify Client ID saved locally. Now use /spotify connect.'
        if lower == '/spotify connect':
            self.connect(notify)
            return 'Starting Spotify authorization in your browser...'
        if lower == '/spotify disconnect':
            self.access_token = self.refresh_token = None
            self.playlists = []
            return 'Spotify disconnected. Session tokens cleared from memory.'
        if lower == '/spotify playlists':
            return self.list_playlists()
        match = re.fullmatch(r'/spotify favorite\s+(\d+)\s+(main|chill)', lower)
        if match:
            return self.favorite_playlist(int(match.group(1)), match.group(2))
        if lower in ('/spotify favorites', '/spotify aliases'):
            return self.favorite_list()
        match = re.fullmatch(r'/spotify play\s+(main|chill)', lower)
        if match:
            return self.play_playlist(match.group(1))
        if lower in ('/spotify pause', '/spotify resume', '/spotify skip'):
            return self.player_control(lower.split()[-1])
        match = re.fullmatch(r'/spotify songs\s+(\d+)', lower)
        if match:
            return self.playlist_items(int(match.group(1)))
        if lower.startswith('/music remember '):
            return 'Music preference saved: ' + self.remember(clean[len('/music remember '):])
        if lower == '/music memories':
            facts = self._load_preferences()
            return 'Music preferences you told me:\n' + '\n'.join('- ' + fact for fact in facts) if facts else 'No music preferences saved yet. Try /music remember I love synth-pop.'
        if lower in ('/spotify check', '/spotify status'):
            return ('Spotify command handler active (playlist shortcuts fix). '
                    + ('Account authorized for this session.' if self.access_token else 'Connect using /spotify connect if needed.')
                    + f' {len(self.playlists)} playlists loaded; '
                    + ', '.join(sorted(self._aliases())) + ' shortcuts saved.')
        if lower in ('/spotify', '/spotify help', '/music help'):
            return ('Music commands:\n'
                    '/spotify setup CLIENT_ID\n/spotify connect\n/spotify playlists\n'
                    '/spotify songs 1\n/spotify favorite 1 main\n/spotify favorite 2 chill\n'
                    '/spotify favorites\n/spotify check\n/spotify play main\n/spotify play chill\n'
                    '/spotify pause\n/spotify resume\n/spotify skip\n/spotify disconnect\n'
                    '/music remember YOUR_PREFERENCE\n/music memories\n\n'
                    'Spotify browsing is separate from Ollama; songs are not analyzed or saved as AI memory.')
        if lower.startswith('/spotify') or lower.startswith('/music'):
            return 'Unknown music command. Use /spotify help to see commands.'
        return None
