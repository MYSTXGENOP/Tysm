"""Local-only V4 HTML frontend bridge. No internet-facing listener."""
import json, threading, socket, webbrowser, subprocess, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from collections import deque
from threading import Lock

def start(root, frontend, on_send, on_action):
    frontend=Path(frontend).resolve()
    lock=Lock(); events=deque(maxlen=300); seq=[0]; window_size={"width":365,"height":290,"move_x":0,"move_y":0,"move_seq":0}
    def emit(kind, **kw):
        with lock:
            seq[0]+=1;events.append(dict(id=seq[0],type=kind,**kw))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def _json(self, obj, status=200):
            data=json.dumps(obj).encode('utf-8');self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            p=urlparse(self.path)
            if p.path=='/api/window':
                with lock: size=dict(window_size)
                self._json(size);return
            if p.path=='/api/poll':
                try:since=int(parse_qs(p.query).get('since',['0'])[0])
                except ValueError:since=0
                with lock:batch=[e for e in events if e['id']>since]
                self._json({'events':batch});return
            name=p.path.lstrip('/') or 'index.html'
            path=(frontend/name).resolve()
            if not path.is_relative_to(frontend) or not path.is_file():self.send_error(404);return
            typ='text/html' if path.suffix=='.html' else 'image/png' if path.suffix=='.png' else 'image/gif' if path.suffix=='.gif' else 'text/plain'
            data=path.read_bytes();self.send_response(200);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_POST(self):
            if self.path not in ('/api/send','/api/action','/api/window'):self.send_error(404);return
            try:
                if int(self.headers.get('Content-Length','0'))>100000:raise ValueError('Too large')
                data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
                if self.path=='/api/window' and data.get('kind')=='move':
                    with lock:
                        window_size['move_x']+=max(-500,min(500,int(data.get('dx',0))))
                        window_size['move_y']+=max(-500,min(500,int(data.get('dy',0))))
                        window_size['move_seq']+=1
                    self._json({'ok':True});return
                if self.path=='/api/window':
                    with lock:
                        window_size['width']=max(365,min(1200,int(data.get('width',275))+90))
                        window_size['height']=max(290,min(920,int(data.get('height',235))+45))
                    self._json({'ok':True});return
                value=data.get('text' if self.path.endswith('send') else 'action','')
                if not isinstance(value,str) or len(value)>20000:raise ValueError('Invalid input')
                if self.path.endswith('send'):root.after(0,on_send,value)
                else:root.after(0,on_action,value)
                self._json({'ok':True})
            except Exception as exc:self._json({'error':str(exc)},400)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/'
    def launch():
        # Real desktop overlay: no Chrome and no browser tab.
        import sys
        script=Path(__file__).with_name('tysm_v4_desktop.py')
        try:
            subprocess.Popen([sys.executable,str(script),url],cwd=str(script.parent))
        except Exception as exc:
            emit('message',who='Tysm',text='Desktop overlay failed to start: '+str(exc))
    root.after(200,launch)
    return emit
