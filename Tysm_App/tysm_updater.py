"""User-approved GitHub release updater. Never runs an installer without consent."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import urllib.error
import urllib.request

APP_VERSION = "1.2.0"
# Set this to YOUR GitHub repository (public GitHub releases).
GITHUB_REPOSITORY = "MYSTXGENOP/Tysm"
USER_AGENT = "Tysm-Updater/" + APP_VERSION
MAX_INSTALLER_BYTES = 250 * 1024 * 1024

def _version(v):
    v = v.lstrip("vV")
    parts = v.split(".")
    if len(parts) != 3 or not all(x.isdigit() for x in parts):
        raise ValueError("Release tag must be vMAJOR.MINOR.PATCH")
    return tuple(map(int, parts))

def _read_url(url, limit=2*1024*1024):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        content = resp.read(limit + 1)
        if len(content) > limit:
            raise ValueError("Response exceeded size limit")
        return content

def _release():
    if GITHUB_REPOSITORY.startswith("REPLACE_WITH_") or GITHUB_REPOSITORY.count("/") != 1:
        raise ValueError("Set GITHUB_REPOSITORY in tysm_updater.py before building")
    owner, repo = GITHUB_REPOSITORY.split("/")
    if not all(c.isalnum() or c in "-_ ." for c in owner + repo) or ' ' in owner + repo:
        raise ValueError("Invalid GitHub repository")
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    return json.loads(_read_url(url))

def _asset(release, filename):
    for item in release.get("assets", []):
        if item.get("name") == filename:
            url = item.get("browser_download_url", "")
            if url.startswith("https://github.com/"):
                return url
    raise ValueError(f"Release missing required asset: {filename}")

def _download_installer(url, expected_hash):
    folder = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Tysm" / "Updates"
    folder.mkdir(parents=True, exist_ok=True)
    temp_path = folder / "Tysm_Setup.exe.part"
    final_path = folder / "Tysm_Setup.exe"
    digest = hashlib.sha256()
    total = 0
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response, temp_path.open("wb") as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_INSTALLER_BYTES:
                    raise ValueError("Installer exceeds allowed size")
                digest.update(block)
                out.write(block)
        if digest.hexdigest().lower() != expected_hash.lower():
            raise ValueError("SHA-256 mismatch. Update cancelled.")
        temp_path.replace(final_path)
        return final_path
    finally:
        temp_path.unlink(missing_ok=True)

def _check(dialog, on_ready):
    release = _release()
    tag = release.get("tag_name", "")
    if _version(tag) <= _version(APP_VERSION):
        return ("info", f"You're up to date (v{APP_VERSION}).", None)
    url = _asset(release, "Tysm_Setup.exe")
    checksum_url = _asset(release, "Tysm_Setup.exe.sha256")
    # Read checksum before asking for download approval.
    checksum = _read_url(checksum_url, 4096).decode("utf-8").strip().split()[0]
    if len(checksum) != 64 or any(c not in "0123456789abcdefABCDEF" for c in checksum):
        raise ValueError("Invalid release checksum")
    return ("offer", f"Tysm {tag} is available.\n\nDownload and install this update?\nYour saved data will be kept.", (url, checksum))

def check_for_updates_async(root, status_label, dialog, on_ready):
    status_label.config(text="Checking GitHub releases...")
    def run():
        try:
            kind, message, payload = _check(dialog, on_ready)
        except Exception as exc:
            kind, message, payload = "error", str(exc), None
        def finish():
            status_label.config(text="Ready")
            if kind == "error":
                dialog.showerror("Tysm Updates", message)
            elif kind == "info":
                dialog.showinfo("Tysm Updates", message)
            elif dialog.askyesno("Tysm Update Available", message):
                status_label.config(text="Downloading verified update...")
                def download():
                    try:
                        path = _download_installer(*payload)
                        error = None
                    except Exception as exc:
                        path, error = None, str(exc)
                    def done():
                        status_label.config(text="Ready")
                        if error:
                            dialog.showerror("Tysm Updates", error)
                        elif dialog.askyesno("Tysm Update Downloaded", "Checksum verified. Close Tysm and launch the installer now?"):
                            on_ready(path)
                    root.after(0, done)
                threading.Thread(target=download, daemon=True).start()
        root.after(0, finish)
    threading.Thread(target=run, daemon=True).start()
