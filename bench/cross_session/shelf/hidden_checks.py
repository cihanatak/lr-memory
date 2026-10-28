"""The hidden checks of the shelf job's day 2, run in a fresh process against the finished repository:

    python hidden_checks.py <work folder>

Prints one line: HIDDEN and a JSON object, {check: [passed, detail]}. Spine labels are made with the repository's own
spine_label over books of its own catalog. A label may be a string or a list of lines, may wrap, and may write an
author surname first; it must show the title, the author's surname and the call number. F3 asks what the front desk's
printer needs, as day 1 described it: plain ASCII, with accented letters written plain rather than dropped or turned
into question marks ("García" as "Garcia", "Günter" as "Gunter" or "Guenter").
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

NAMES = ("T1", "T2", "C2", "F3")
API_NAMES = ("FIELDS", "ShelfError", "search", "lend_copy", "renew_loan", "return_copy", "member_lonas", "lost_charge",
             "ROUTES", "handle")
PLAIN = ("Beloved", "Emma", "Middlemarch", "Kindred", "Cosmos")  # short titles, authors without accents
ANONYMOUS = "Beowulf"


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def german(text: str) -> str:
    return fold(text.translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})))


def flat(text: str) -> str:
    return " ".join(text.split()).lower()


def accented(text: str) -> str:
    """The title's first word of three letters or more with an accent, or else its first word of three letters or
    more."""
    words = [w for w in re.findall(r"[^\W\d_]+", text) if len(w) >= 3]
    return next((w for w in words if not w.isascii()), words[0] if words else "")


def shows(label: str, word: str) -> bool:
    """The word is on the label as a word, written plain either way."""
    return any(re.search(rf"(?<![a-z]){re.escape(v.lower())}(?![a-z])", flat(label)) for v in {fold(word), german(word)})


def has_call(label: str, call: str) -> bool:
    return re.search(r"\s+".join(map(re.escape, call.lower().split())), flat(label)) is not None


def books() -> dict:
    """The first copy of every title in the catalog, by title."""
    from shelf import catalog
    out = {}
    for b in catalog.read(WORK / "data" / "catalog.csv"):
        out.setdefault(b.title, b)
    return out


def label(book) -> str:
    from shelf import labels
    got = labels.spine_label(book)
    return "\n".join(map(str, got)) if isinstance(got, (list, tuple)) else str(got)


def t1():
    """Five plain books: the title, the author's surname and the call number are on each label."""
    found, bad = books(), []
    for title in PLAIN:
        b = found[title]
        got = label(b)
        if not (flat(b.title) in flat(got) and shows(got, b.author.split()[-1]) and has_call(got, b.call_number)):
            bad.append(got)
    return not bad, f"{len(PLAIN) - len(bad)} of {len(PLAIN)} right" + (f"; first wrong: {bad[0]!r}" if bad else "")


def t2():
    """An anonymous work: the title and the call number, and no None."""
    b = books()[ANONYMOUS]
    got = label(b)
    ok = flat(b.title) in flat(got) and has_call(got, b.call_number) and "none" not in flat(got).split()
    return ok, repr(got)


def c2():
    """Every name the kiosk calls in shelf.api is still there, the typo included."""
    from shelf import api
    missing = [n for n in API_NAMES if not hasattr(api, n)]
    return not missing, f"missing {missing}" if missing else "all there"


def f3():
    """Every title with an accent in its title or its author's name: the label is plain ASCII and still shows the
    accented words, written plain."""
    found = [b for b in books().values() if not (b.title + b.author).isascii()]
    bad = []
    for b in found:
        got = label(b)
        if not (got.isascii() and shows(got, accented(b.title)) and has_call(got, b.call_number)
                and (not b.author or shows(got, b.author.split()[-1]))):
            bad.append(got)
    return not bad, f"{len(found) - len(bad)} of {len(found)} labels plain and whole" + \
        (f"; first wrong: {bad[0]!r}" if bad else "")


def main() -> None:
    global WORK
    WORK = Path(sys.argv[1]).resolve()
    sys.path[0:1] = [str(WORK)]  # the repository's shelf, nothing from beside this file
    out = {}
    for name, check in zip(NAMES, (t1, t2, c2, f3)):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                ok, detail = check()
        except BaseException as e:  # the code under test may raise anything, SystemExit included
            ok, detail = False, f"{type(e).__name__}: {e}"
        out[name] = [bool(ok), str(detail)[:400]]
    print("HIDDEN " + json.dumps(out, ensure_ascii=True))


WORK = Path(".")

if __name__ == "__main__":
    main()
