"""Optional floating-icon animation using Pillow; never blocks Tysm chat."""
from pathlib import Path

class PendantAnimator:
    def __init__(self, root, canvas, icon_item, assets_dir, state_getter):
        self.root, self.canvas, self.icon_item = root, canvas, icon_item
        self.state_getter = state_getter
        self.assets_dir = Path(assets_dir)
        self.mode = "idle"
        self.index = 0
        self.transition_loops_remaining = 0
        self.transition_target = "hologram"
        self.hologram_until = 0
        self.hologram_loops_remaining = 0
        self.frames = {}
        self.header_frames = {}
        self.compact_frames = {}
        self.compact = False
        self.paused = False
        self.header_avatar = None
        self.durations = {}
        try:
            from PIL import Image, ImageTk, ImageSequence
            for key, filename in (("idle", "pendant_idle.gif"), ("thinking", "pendant_thinking.gif"),
                                  ("transition", "glitch_transition.gif"), ("hologram", "tysm_hologram.gif")):
                image = Image.open(self.assets_dir / filename)
                self.frames[key] = []
                self.header_frames[key] = []
                self.compact_frames[key] = []
                self.durations[key] = []
                for frame in ImageSequence.Iterator(image):
                    f = frame.convert("RGBA")
                    f.thumbnail((70, 70), Image.Resampling.NEAREST)
                    self.frames[key].append(ImageTk.PhotoImage(f, master=root))
                    header_f = frame.convert("RGBA")
                    # Keep the hologram larger, with room for a full character.
                    # Both frames remain centered inside the dedicated chat stage.
                    target = (192, 192) if key == "hologram" else (178, 178)
                    header_f.thumbnail(target, Image.Resampling.NEAREST)
                    self.header_frames[key].append(ImageTk.PhotoImage(header_f, master=root))
                    mini_f = frame.convert("RGBA")
                    mini_f.thumbnail((108, 108), Image.Resampling.NEAREST)
                    self.compact_frames[key].append(ImageTk.PhotoImage(mini_f, master=root))
                    # Two gentle 6-frame loops take roughly 2.5 seconds.
                    self.durations[key].append(210 if key == "hologram" else max(35, frame.info.get("duration", 80)))
            self.enabled = True
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            print("Pillow GIF loader unavailable; trying built-in Tk GIF support:", exc)
            self.frames.clear()
            self.header_frames.clear()
            self.compact_frames.clear()
            self.durations.clear()
            try:
                import tkinter as tk
                for key, filename in (("idle", "pendant_idle.gif"),
                                      ("thinking", "pendant_thinking.gif"),
                                      ("transition", "glitch_transition.gif"),
                                      ("hologram", "tysm_hologram.gif")):
                    path = self.assets_dir / filename
                    if not path.exists():
                        raise FileNotFoundError(str(path))
                    sequence = []
                    index = 0
                    while True:
                        try:
                            image = tk.PhotoImage(master=root, file=str(path),
                                                  format=f"gif -index {index}")
                            factor = max(1, (max(image.width(), image.height()) + 69) // 70)
                            if factor > 1:
                                image = image.subsample(factor, factor)
                            sequence.append(image)
                            index += 1
                        except tk.TclError:
                            break
                    if not sequence:
                        raise RuntimeError(f"No GIF frames loaded: {path}")
                    self.frames[key] = sequence
                    # Load larger GIF frames directly for the chat stage.
                    # Tk's integer subsampling is less precise than Pillow.
                    large = []
                    for idx in range(len(sequence)):
                        photo = tk.PhotoImage(master=root, file=str(path),
                                              format=f"gif -index {idx}")
                        target = 192 if key == "hologram" else 178
                        factor = max(1, (max(photo.width(), photo.height()) + target - 1) // target)
                        if factor > 1:
                            photo = photo.subsample(factor, factor)
                        large.append(photo)
                    self.header_frames[key] = large
                    # Compact mode uses the existing ~70px small frames.
                    self.compact_frames[key] = sequence
                    self.durations[key] = [210 if key == "hologram" else 80] * len(sequence)
                self.enabled = True
                print("Tysm GIF animations loaded using built-in Tk support.")
            except Exception as fallback_exc:
                self.enabled = False
                print("Tysm animations could not load:", repr(fallback_exc))
                print("Check assets/animations and try: py -m pip install pillow")

    def attach_header_avatar(self, label):
        """Animate the chat-window header in sync with the desktop pendant."""
        self.header_avatar = label
        if self.enabled and self.header_frames.get(self.mode):
            images = self.compact_frames if self.compact else self.header_frames
            label.configure(image=images[self.mode][0])

    def set_compact(self, enabled):
        """Scale only the chat avatar; keep desktop animation and timing intact."""
        self.compact = bool(enabled)
        if self.enabled and self.header_avatar is not None and self.header_avatar.winfo_exists():
            images = self.compact_frames if self.compact else self.header_frames
            self.header_avatar.configure(image=images[self.mode][self.index % len(images[self.mode])])

    def play_reply_transition(self):
        """Start the approved glitch when a reply completes (not a polled guess)."""
        if not self.enabled:
            return
        self.mode = "transition"
        self.index = 0
        # The original glitch asset is ~0.4 sec. Two passes make it visible
        # without changing any of the approved GIF artwork.
        self.transition_loops_remaining = 2
        self.transition_target = "hologram"
        self.hologram_until = 0
        self.hologram_loops_remaining = 0
        print("Tysm animation: reply -> glitch transition")

    def start(self):
        if self.enabled:
            self.tick()

    def tick(self):
        if not self.enabled:
            return
        if self.paused:
            self.root.after(40, self.tick)
            return
        import time
        state = self.state_getter()
        now = time.monotonic()

        # The hologram ends after TWO COMPLETE passes through its frames,
        # not on a wall-clock timer that might cut off a loop halfway.

        if self.mode == "transition":
            desired = "transition"
        elif self.mode == "hologram":
            desired = "hologram"
        elif state == "thinking":
            desired = "thinking"
        else:
            desired = "idle"

        if desired != self.mode:
            self.mode, self.index = desired, 0

        seq = self.frames[self.mode]
        self.canvas.itemconfigure(self.icon_item, image=seq[self.index])
        if self.header_avatar is not None and self.header_avatar.winfo_exists():
            image_bank = self.compact_frames if self.compact else self.header_frames
            self.header_avatar.configure(image=image_bank[self.mode][self.index])

        delay = self.durations[self.mode][self.index]
        self.index += 1

        if self.index >= len(seq):
            self.index = 0
            if self.mode == "hologram":
                self.hologram_loops_remaining -= 1
                if self.hologram_loops_remaining <= 0:
                    self.mode = "transition"
                    self.transition_target = "idle"
                    self.transition_loops_remaining = 2
                    self.index = 0
                    print("Tysm animation: hologram -> return glitch")
            elif self.mode == "transition":
                self.transition_loops_remaining -= 1
                if self.transition_loops_remaining <= 0:
                    destination = self.transition_target
                    self.mode = destination
                    self.index = 0
                    if destination == "hologram":
                        self.hologram_loops_remaining = 2
                        self.hologram_until = 0
                        print("Tysm animation: glitch -> hologram (2 slow loops)")
                    else:
                        self.hologram_until = 0
                        print("Tysm animation: return glitch -> idle")

        self.root.after(delay, self.tick)
