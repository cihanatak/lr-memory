"""Was a block right? The assistant's own words after it, read at the next stop. Zero tokens.

Counting every block as help overstates a checker: in the setup COL comes from, 2 of the first 13 interventions were
right once labelled by hand. An assistant that answers a block with "I had already answered that in my previous
message" names a wrong block; one that answers "I missed it" names a right one. Only clear cues label; anything else
stays unclear, so the counts are a floor, not an estimate of every block.
"""
from __future__ import annotations

import re

WRONG = re.compile(r"zaten\s+(?:\S+\s+){0,3}?(?:cevapla|yap|gönder|ekle|söyle|ver|yayınla|anlat)\w*"
                   r"|(?:bir\s+)?önceki\s+(?:mesaj|tur|cevab)\w*\s+(?:\S+\s+){0,5}?"
                   r"(?:cevapla|gönder|söyle|ver|yap|ekle|anlat)\w*"
                   r"|cevabı değişmedi|yanlış alarm|false alarm|false positive"
                   r"|the (?:file|commit|path) (?:does )?exists?"
                   r"|already\s+(?:answered|done|did|sent|published|added|exists?)"
                   r"|(?:in|from) (?:the|my) previous (?:turn|message)", re.I)
RIGHT = re.compile(r"fark ettim|atlamışım|atladığımı|unutmuşum|unuttuğumu|yazmadığımı|değinmemişim|değinmediğimi"
                   r"|eksik bırakmışım|kaçırmışım|kaçırdığımı|haklısın|yanlış yazmışım|uydurmuşum"
                   r"|i missed|i forgot|i skipped|i overlooked|you'?re right|the hook is right|good catch"
                   r"|i was wrong|i misstated|i shouldn'?t have claimed|i have no evidence"
                   r"|tak(?:e|ing) (?:that|the|this|my) claim back|withdraw\w* (?:that|the|this|my) claim"
                   r"|iddia\w* geri al\w*|geri alıyorum|kanıtım yok", re.I)


def label(texts: list) -> tuple:
    """('right' | 'wrong' | 'unclear', the words that decided it)."""
    said = "\n".join(t for t in texts if t)
    right, wrong = RIGHT.search(said), WRONG.search(said)
    if right and not wrong:
        return "right", right.group(0)
    if wrong and not right:
        return "wrong", wrong.group(0)
    return "unclear", ""
