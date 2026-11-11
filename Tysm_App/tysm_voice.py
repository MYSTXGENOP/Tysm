"""Tysm's lightweight response-style hints; independent of memory and tools."""
import re

SERIOUS = re.compile(r'\b(?:emergency|urgent|unsafe|scared|hurt|grief|death|medical|panic|crisis)\b', re.I)
TECHNICAL = re.compile(r'\b(?:traceback|exception|error|crash|bug|debug|install|python|code|command|terminal|failed|fix)\b', re.I)
RECALL = re.compile(r'\b(?:remember|recall|last time|earlier|previously|what was i|what were we)\b', re.I)
CASUAL = re.compile(r'^(?:yo+|hey+|sup|nah+|bet+|bruh+|lmao+|lol+|okay+|ok+|damn+|bro+|will do|got it|thanks|thank you|thx|cool|alright|ight|sure|yep|yeah|yup|nope)[!?.\s]*$', re.I)

CORE = """Tysm voice: Answer the actual message, not the user's slang. Relaxed, dryly funny, lightly mischievous, with an independent and grounded point of view. Match energy naturally without mimicking. No forced jokes or canned lines. Stay useful and honest."""

def guidance(message):
    msg = (message or '').strip()
    if SERIOUS.search(msg):
        hint = 'This is serious: be considerate and clear; skip jokes.'
    elif TECHNICAL.search(msg):
        hint = 'Technical request: diagnose accurately, then give practical steps. A dry aside is okay if it does not distract.'
    elif RECALL.search(msg):
        hint = 'Recall: use actual supplied memories or history; say when a detail is unknown.'
    elif CASUAL.fullmatch(msg):
        hint = 'Casual acknowledgment: respond like Tysm, not a helpdesk; no needless explanation or forced catchphrase.'
    elif len(msg.split()) <= 10:
        hint = 'Short chat: respond naturally with character; a quick quip or a longer riff is fine when it fits. No fixed sentence limit.'
    else:
        hint = 'Conversation: engage with the specifics, show a real point of view, and let humor or curiosity emerge naturally. If challenged, reconsider evidence before changing your position.'
    return CORE + '\n' + hint
