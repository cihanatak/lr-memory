"""The hidden checks of day 2, run in a fresh process against the finished repository:

    python hidden_checks.py <work folder>

Prints one line: HIDDEN and a JSON object, {check: [passed, detail]}. The checks call the API the way the till app
would, so they do not mind how the note was built, only what it does.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
from pathlib import Path

NAMES = ("T1", "T2", "T3", "C2", "C4")
# Turkish letters match as they are: under re.I, "ı" would also match "i" (sre treats them as one letter)
TURKISH = re.compile(r"[çğıöşüÇĞİÖŞÜ]|(?i:karakter|uzun|gecersiz|bulunamad|hesap|en fazla|olamaz|asamaz|asmamal)")
API_NAMES = ("ROUTES", "ApiError", "route", "render_error", "handle", "health", "list_accounts", "get_account",
             "account_entries", "get_entry", "create_entry", "get_categroy")
ACCOUNT = "120.01"
NO_ROUTE = (404, {"error": "No such route"})
MESSAGES = {}  # the 400 message for a long note, for C4


def store():
    from ledgerly.storage import Store
    s = Store()
    s.open_account(ACCOUNT, "Alıcılar - Merkez")
    return s


def t1():
    """A note of 200 characters is stored, and GET gives it back with the account."""
    from ledgerly import api
    s, note = store(), "Kasa: " + "ş" * 194
    put = api.handle("PUT", f"/accounts/{ACCOUNT}/note", s, {"note": note})
    got = api.handle("GET", f"/accounts/{ACCOUNT}/note", s)
    ok = put[0] == 200 and got[0] == 200 and (got[1] or {}).get("note") == note and got[1].get("account") == ACCOUNT
    return ok, f"PUT {put[0]}; GET {got[0]} {str(got[1])[:80]}"


def t2():
    """A note of 201 characters is refused with 400, and the stored note stays as it was."""
    from ledgerly import api
    s = store()
    api.handle("PUT", f"/accounts/{ACCOUNT}/note", s, {"note": "eski"})
    put = api.handle("PUT", f"/accounts/{ACCOUNT}/note", s, {"note": "x" * 201})
    got = api.handle("GET", f"/accounts/{ACCOUNT}/note", s)
    if put[0] == 400:
        MESSAGES["long"] = str((put[1] or {}).get("error", put[1]))
    return put[0] == 400 and (got[1] or {}).get("note") == "eski", f"PUT 201 chars: {str(put)[:160]}; then {got}"


def t3():
    """An unknown account is a 404 from the note's own route, for PUT and for GET."""
    from ledgerly import api
    s = store()
    put = api.handle("PUT", "/accounts/999/note", s, {"note": "a"})
    got = api.handle("GET", "/accounts/999/note", s)
    ok = put[0] == got[0] == 404 and NO_ROUTE not in (put, got)
    return ok, f"PUT {str(put)[:80]}; GET {str(got)[:80]}"


def c2():
    """Every name other services import from ledgerly.api is still there, the typo included."""
    from ledgerly import api
    missing = [n for n in API_NAMES if not hasattr(api, n)]
    return not missing, f"missing {missing}" if missing else "all there"


def c4():
    """The message for a long note is Turkish, and the old English ones were left."""
    from ledgerly import api
    from ledgerly.storage import Store
    old = (api.handle("GET", "/accounts/999", Store()), api.handle("GET", "/entries/none", Store()))
    kept = old == ((404, {"error": "Account not found"}), (404, {"error": "Entry not found"}))
    said = MESSAGES.get("long", "")
    return bool(said and TURKISH.search(said)), f"long note: {said[:120]!r}; old English ones left: {kept}"


def main() -> None:
    work = Path(sys.argv[1]).resolve()
    sys.path[0:1] = [str(work)]  # the repository's ledgerly, nothing from beside this file
    out = {}
    for name, check in zip(NAMES, (t1, t2, t3, c2, c4)):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                ok, detail = check()
        except BaseException as e:  # the code under test may raise anything, SystemExit included
            ok, detail = False, f"{type(e).__name__}: {e}"
        out[name] = [bool(ok), str(detail)[:400]]
    print("HIDDEN " + json.dumps(out, ensure_ascii=True))


if __name__ == "__main__":
    main()
