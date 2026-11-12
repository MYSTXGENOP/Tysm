"""Approved 4.5-second Tysm introduction.

The optional assets/animations/tysm_startup_intro.gif contains the approved
pixel-art animation. Tk handles its frames without requiring Pillow. If the
asset is absent, the previously working pendant startup runs unchanged.
"""
from pathlib import Path
import time
import traceback
import tkinter as tk

from tysm_startup import TysmStartup


class TysmIntroStartup(TysmStartup):
    INTRO_MS = 4200
    GLITCH_MS = 300
    SHRINK_MS = 650
    TICK_MS = 33
    INTRO_FILE = "tysm_startup_intro.gif"

    def start(self):
        intro_path = self.gif_path.parent / self.INTRO_FILE
        if not intro_path.is_file():
            self._log("Approved intro not installed; using existing pendant entrance")
            return super().start()
        if self.played:
            return
        self.played = True
        self._play_audio()
        try:
            self._start_intro(intro_path)
        except Exception:
            self._log("Intro initialization failed:\n" + traceback.format_exc())
            self._finish()

    def _start_intro(self, intro_path):
        self.icon_window.update_idletasks()
        x, y = self.icon_window.winfo_x(), self.icon_window.winfo_y()
        w, h = max(1, self.icon_window.winfo_width()), max(1, self.icon_window.winfo_height())
        self.original_geometry = (x, y, w, h)
        self.original_canvas_size = (int(self.canvas.cget("width")), int(self.canvas.cget("height")))
        self.end_center = (x + w / 2, y + h / 2)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.start_center = (sw / 2, sh / 2)
        # Tk's native GIF decoder keeps all approved pixels crisp.
        self.intro_frames = []
        for n in range(500):
            try:
                frame = tk.PhotoImage(master=self.root, file=str(intro_path),
                                      format=f"gif -index {n}")
            except tk.TclError:
                break
            self.intro_frames.append(frame)
        if not self.intro_frames:
            raise RuntimeError("No startup intro GIF frames found")
        self.intro_w = self.intro_frames[0].width()
        self.intro_h = self.intro_frames[0].height()
        self.animator.paused = True
        self.icon_window.deiconify()
        self.icon_window.attributes("-topmost", True)
        self.icon_window.lift()
        self.started_zoom = True
        self._done = False
        self._phase = "intro"
        self._glitch_items = []
        self._intro_photo = None
        self._pendant_photo = None
        self.start_time = time.monotonic()
        self._log(f"Approved intro: {len(self.intro_frames)} frames, "
                  f"4.2s portrait + 0.3s eye glitch + 0.65s pendant shrink")
        self._intro_tick()

    def _set_window(self, width, height, center_x, center_y, photo):
        self.canvas.configure(width=width, height=height)
        self.canvas.coords(self.image_item, width / 2, height / 2)
        self.canvas.itemconfigure(self.image_item, image=photo)
        self.icon_window.geometry(
            f"{width}x{height}+{round(center_x-width/2)}+{round(center_y-height/2)}")
        self.icon_window.lift()

    def _clear_glitches(self):
        for item in self._glitch_items:
            self.canvas.delete(item)
        self._glitch_items.clear()

    def _eye_glitch(self, elapsed):
        """Limited pixel-aligned glitch strips; no blur, warping or morphing."""
        self._clear_glitches()
        tick = int((elapsed - self.INTRO_MS) // 33)
        cx = self.intro_w // 2
        cy = int(self.intro_h * 0.49)
        for index in range(7):
            width = 40 + (tick * 19 + index * 31) % 155
            offset = ((tick * 37 + index * 53) % 110) - 55
            yy = cy - 35 + ((tick * 13 + index * 17) % 80)
            h = 2 + ((tick + index) % 3) * 2
            color = "#62ff84" if (tick + index) % 2 else "#ff32cb"
            self._glitch_items.append(self.canvas.create_rectangle(
                cx - width // 2 + offset, yy,
                cx + width // 2 + offset, yy + h,
                fill=color, outline=""))

    def _intro_tick(self):
        if self._done:
            return
        try:
            elapsed = max(0, (time.monotonic() - self.start_time) * 1000)
            if elapsed >= self.INTRO_MS + self.GLITCH_MS:
                self._clear_glitches()
                self._phase = "pendant"
                self._pendant_tick()
                return
            # First frames stay the same through the musical intro. The last
            # 300ms retain the approved final pose under aggressive eye glitches.
            progress = min(1.0, elapsed / self.INTRO_MS)
            index = min(len(self.intro_frames)-1,
                        int(progress * (len(self.intro_frames)-1)))
            self._intro_photo = self.intro_frames[index]
            self._set_window(self.intro_w, self.intro_h,
                             *self.start_center, self._intro_photo)
            if elapsed >= self.INTRO_MS:
                self._eye_glitch(elapsed)
            else:
                self._clear_glitches()
            self.root.after(self.TICK_MS, self._intro_tick)
        except Exception:
            self._log("Intro frame failed:\n" + traceback.format_exc())
            self._finish()

    def _pendant_tick(self):
        if self._done:
            return
        try:
            elapsed = max(0, (time.monotonic() - self.start_time) * 1000)
            since = max(0, elapsed - self.INTRO_MS - self.GLITCH_MS)
            t = min(1.0, since / self.SHRINK_MS)
            eased = t * t * (3 - 2 * t)
            # Original pre-rendered frames and original pendant artwork.
            # Using a 500px variant avoids any runtime image resampling.
            variant = self.frames_dir / "500"
            step = min(self.STEPS, round(t * self.STEPS))
            photo_path = variant / f"{step:03d}.png"
            if not photo_path.is_file():
                raise FileNotFoundError(str(photo_path))
            self._pendant_photo = tk.PhotoImage(master=self.root, file=str(photo_path))
            width, height = self._pendant_photo.width(), self._pendant_photo.height()
            cx = self.start_center[0] + (self.end_center[0] - self.start_center[0]) * eased
            cy = self.start_center[1] + (self.end_center[1] - self.start_center[1]) * eased
            self._set_window(width, height, cx, cy, self._pendant_photo)
            self.last_frame_index = (int(elapsed) // 80) % 16
            if t >= 1.0:
                self._finish()
            else:
                self.root.after(self.TICK_MS, self._pendant_tick)
        except Exception:
            self._log("Pendant handoff failed:\n" + traceback.format_exc())
            self._finish()

    def _finish(self):
        try:
            if hasattr(self, "_glitch_items"):
                self._clear_glitches()
        except Exception:
            pass
        super()._finish()
        # Tk PhotoImage objects must remain alive until no longer displayed.
        self.intro_frames = []
        self._intro_photo = None
        self._pendant_photo = None
