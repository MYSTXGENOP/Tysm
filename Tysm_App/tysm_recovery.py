"""Conservative local backups for Tysm user data."""
from pathlib import Path
from datetime import datetime, timezone
import json, sqlite3, tempfile, zipfile, shutil, time
from contextlib import closing
DATA = ('tysm_memory.json','tysm_history.json','tysm_history_settings.json','tysm_adaptive.sqlite3','tysm_reminders.sqlite3','tysm_phone_settings.json')
def backups(folder):
    return sorted((Path(folder)/'tysm_backups').glob('tysm_backup_*.zip'),reverse=True)
def create(folder, keep=12):
    folder=Path(folder); dest=folder/'tysm_backups'; dest.mkdir(exist_ok=True)
    name='tysm_backup_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.zip'
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp); names=[]
        for file in DATA:
            src=folder/file
            if not src.is_file(): continue
            dst=stage/file
            if file.endswith('.sqlite3'):
                with closing(sqlite3.connect(src, timeout=15)) as original:
                    with closing(sqlite3.connect(dst, timeout=15)) as copy:
                        original.backup(copy)
                        if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise RuntimeError("SQLite backup integrity check failed: " + file)
            else:
                shutil.copy2(src,dst)
                if file.endswith('.json'): json.loads(dst.read_text(encoding='utf-8'))
            names.append(file)
        if not names: raise RuntimeError('No data files to back up')
        with zipfile.ZipFile(dest/name,'x',zipfile.ZIP_DEFLATED) as z:
            for file in names: z.write(stage/file,file)
            z.writestr('manifest.json',json.dumps({'files':names,'utc':datetime.now(timezone.utc).isoformat()}))
    verify(dest/name)
    for old in backups(folder)[max(1,keep):]: old.unlink()
    return dest/name
def verify(path):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None: raise ValueError('Corrupt backup')
        manifest=json.loads(z.read('manifest.json'))
        if not set(manifest['files']).issubset(DATA) or set(z.namelist()) != set(manifest['files'])|{'manifest.json'}:
            raise ValueError('Unexpected backup contents')
        for file in manifest['files']:
            if file.endswith('.json'): json.loads(z.read(file))
    return manifest
def daily(folder):
    found=backups(folder)
    if not found or time.time()-found[0].stat().st_mtime>86400: return create(folder)
    return None
