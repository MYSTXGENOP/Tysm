"""Context-aware, weighted, persistent, user-independent portrait choice."""
import random
import re
from pathlib import Path
PORTRAIT_DIR = Path(__file__).resolve().parent / "assets" / "v5_portraits"
class PortraitChooser:
    def __init__(self):
        self.current = 1
        self.hold = 0
        self.rng = random.Random()
    def choose(self, reply):
        text = (reply or "").lower()
        if re.search(r"\b(error|failed|sorry|can't|cannot)\b", text): weights=[1,1,1,5,2,1]
        elif re.search(r"\b(lol|seriously|obviously|really)\b", text): weights=[1,1,5,1,2,2]
        elif re.search(r"\b(first|step|install|file|open|click|run)\b", text): weights=[1,5,1,2,1,1]
        else: weights=[5,2,2,2,2,2]
        self.hold += 1
        if self.hold >= 2 or self.rng.random() < .45:
            self.current = self.rng.choices(range(1,7),weights=weights,k=1)[0]
            self.hold = 0
        return self.current
def portrait_path(index):
    return PORTRAIT_DIR / f"face{index}.png"
