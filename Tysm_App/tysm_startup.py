"""One-time, transparent full-screen-scale pendant entrance for Tysm.

Uses ONLY the Python standard library and Tk. The pixel-art frames are
pre-rendered from assets/animations/pendant_idle.gif at build time, so users
do not need Pillow/PIL to see the startup animation. The original idle GIF,
normal pendant animator, and startup audio remain untouched.
"""
from pathlib import Path
import sys
import time
import traceback
import tkinter as tk


class TysmStartup:
    DURATION_MS = 2700
    STEPS = 60
    STEP_MS = 38
    END_PX = 76
    AVAILABLE_SIZES = (500, 700, 900, 1000, 1300, 1500, 2000)

    def __init__(self, root, icon_window, icon_canvas, image_item,
                 pendant_animator, gif_path, wav_path, on_complete):
        self.root = root
        self.icon_window = icon_window
        self.canvas = icon_canvas
        self.image_item = image_item
        self.animator = pendant_animator
        self.gif_path = Path(gif_path)
        self.wav_path = Path(wav_path)
        self.frames_dir = self.gif_path.parent.parent / 'startup_frames'
        self.on_complete = on_complete
        self.played = False
        self.started_zoom = False
        self.original_geometry = None
        self.original_canvas_size = None
        self.photo = None
        self.last_frame_index = 0
        self._done = False

    def _log(self, message):
        print('Tysm startup:', message)
        try:
            with (self.gif_path.parent.parent.parent / 'tysm_startup_debug.log').open(
                    'a', encoding='utf-8') as log:
                log.write(message + '\n')
        except OSError:
            pass

    def _play_audio(self):
        if sys.platform == 'win32' and self.wav_path.is_file():
            try:
                import winsound
                winsound.PlaySound(str(self.wav_path),
                                   winsound.SND_FILENAME | winsound.SND_ASYNC |
                                   winsound.SND_NODEFAULT)
            except (OSError, RuntimeError) as exc:
                self._log('Startup audio unavailable: ' + repr(exc))

    def start(self):
        if self.played:
            return
        self.played = True
        self._play_audio()
        try:
            self.icon_window.update_idletasks()
            x, y = self.icon_window.winfo_x(), self.icon_window.winfo_y()
            w, h = max(1, self.icon_window.winfo_width()), max(1, self.icon_window.winfo_height())
            self.original_geometry = (x, y, w, h)
            self.original_canvas_size = (int(self.canvas.cget('width')),
                                         int(self.canvas.cget('height')))
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.start_center = (sw / 2, sh / 2)
            self.end_center = (x + w / 2, y + h / 2)
            target = min(sw, sh) * 0.93
            # Pre-rendered sizes preserve detailed pixel-art shading and require
            # no Pillow installation. Choose the closest size that fits.
            candidates = [s for s in self.AVAILABLE_SIZES if s <= min(sw, sh)]
            if not candidates:
                raise RuntimeError('Screen too small for startup animation')
            self.start_size = min(candidates, key=lambda s: abs(s - target))
            self.variant_dir = self.frames_dir / str(self.start_size)
            if not (self.variant_dir / '000.png').is_file():
                raise FileNotFoundError('Missing startup PNG frames: ' + str(self.variant_dir))
            self.animator.paused = True
            self.started_zoom = True
            self.icon_window.deiconify()
            self.icon_window.attributes('-topmost', True)
            self.icon_window.lift()
            self.start_time = time.monotonic()
            self._log(f'PIL-free startup: {self.start_size}px on {sw}x{sh} screen; '
                      f'{self.STEPS + 1} transparent frames')
            self._tick()
        except Exception:
            self._log('Startup error:\n' + traceback.format_exc())
            self._finish()

    def _tick(self):
        if self._done:
            return
        try:
            if not self.icon_window.winfo_exists():
                self._finish()
                return
            elapsed = max(0, int((time.monotonic() - self.start_time) * 1000))
            t = min(1.0, elapsed / self.DURATION_MS)
            step = min(self.STEPS, round(t * self.STEPS))
            eased = (step / self.STEPS) ** 2 * (3 - 2 * (step / self.STEPS))
            size = max(self.END_PX, round(self.start_size + (self.END_PX - self.start_size) * eased))
            cx = self.start_center[0] + (self.end_center[0] - self.start_center[0]) * eased
            cy = self.start_center[1] + (self.end_center[1] - self.start_center[1]) * eased
            path = self.variant_dir / f'{step:03d}.png'
            self.photo = tk.PhotoImage(master=self.root, file=str(path))
            self.canvas.configure(width=size, height=size)
            self.canvas.coords(self.image_item, size / 2, size / 2)
            self.canvas.itemconfigure(self.image_item, image=self.photo)
            self.icon_window.geometry(
                f'{size}x{size}+{round(cx - size / 2)}+{round(cy - size / 2)}')
            self.icon_window.lift()
            self.last_frame_index = (elapsed // 80) % 16
            if t < 1:
                self.root.after(self.STEP_MS, self._tick)
            else:
                self._finish()
        except Exception:
            self._log('Zoom frame error:\n' + traceback.format_exc())
            self._finish()

    def _finish(self):
        if self._done:
            return
        self._done = True
        try:
            if self.original_geometry:
                x, y, w, h = self.original_geometry
                self.icon_window.geometry(f'{w}x{h}+{x}+{y}')
                cw, ch = self.original_canvas_size or (w, h)
                self.canvas.configure(width=cw, height=ch)
                self.canvas.coords(self.image_item, cw / 2, ch / 2)
            if self.animator.enabled and self.animator.frames.get('idle'):
                self.animator.mode = 'idle'
                count = len(self.animator.frames['idle'])
                idx = self.last_frame_index % count
                self.canvas.itemconfigure(self.image_item,
                                          image=self.animator.frames['idle'][idx])
                self.animator.index = (idx + 1) % count
            self.animator.paused = False
            self.icon_window.deiconify()
            self.icon_window.lift()
        except Exception:
            self._log('Restoration error:\n' + traceback.format_exc())
            self.animator.paused = False
        self.photo = None
        self._log('Zoom complete; opening chat')
        if self.on_complete is not None:
            self.root.after(90, self.on_complete)
