"""Small, autonomous Tysm portrait choices. No model-directed desktop actions."""
import random
import re
from pathlib import Path

PORTRAIT_DIR = Path(__file__).resolve().parent / "assets" / "v5_portraits"

class PortraitChooser:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.current = 1

    def choose(self, reply):
        text = (reply or "").lower()
        if re.search(r"\b(error|failed|sorry|can't|cannot)\b", text):
            weights = [1, 1, 1, 5, 2, 1]
        elif re.search(r"\b(lol|seriously|obviously|sure|really)\b", text):
            weights = [1, 1, 5, 1, 2, 2]
        elif re.search(r"\b(first|step|install|file|open|click|run)\b", text):
            weights = [1, 5, 1, 2, 1, 1]
        else:
            weights = [5, 2, 2, 2, 2, 2]
        # Usually retain the expression for continuity; occasionally shift.
        if self.rng.random() < 0.38:
            self.current = self.rng.choices(range(1, 7), weights=weights, k=1)[0]
        return self.current

def portrait_path(index):
    return PORTRAIT_DIR / f"face{index}.png"
