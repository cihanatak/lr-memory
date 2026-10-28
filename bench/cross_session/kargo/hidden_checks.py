"""The hidden checks of the kargo job's day 2, run in a fresh process against the finished repository:

    python hidden_checks.py <work folder>

Prints one line: HIDDEN and a JSON object, {check: [passed, detail]}. Bulk labels are made with the repository's own
KargoIstemcisi against a stand-in for the carrier at the network boundary, urllib's urlopen, on a stand-in clock: a
limit kept anywhere, in toplu.py or in the client, counts, and waiting costs no time. Like the carrier day 1 described,
the stand-in takes at most 60 shipments in any 60 seconds and answers 429 above that, with a Retry-After header.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

NAMES = ("T1", "T2", "C2", "F3")
API_NAMES = ("ALANLAR", "ApiHatasi", "UCLAR", "isle", "ucret_hesapla", "desi_hesapla", "adres_dogrula", "takip_sorgla",
             "etiket_getir")
LIMIT, WINDOW = 60, 60.0  # shipments, seconds
BULK = 150  # orders in F3: two and a half minutes' worth at the limit


class Clock:
    """Stands in for time. Sleeping moves it on, and so does every reading, by a millisecond, so that a loop that waits
    by reading the clock ends too."""

    def __init__(self):
        self.now = 1_000_000.0

    def read(self) -> float:
        self.now += 0.001
        return self.now

    def read_ns(self) -> int:
        return int(self.read() * 1e9)

    def sleep(self, seconds) -> None:
        self.now += max(0.0, float(seconds))


CLOCK = Clock()


def tracking(order: str) -> str:
    return "TK" + str(int(hashlib.sha1(order.encode("utf-8")).hexdigest(), 16))[:10]


class Reply(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def getcode(self) -> int:
        return 200


class Carrier:
    """POST .../gonderiler registers a shipment and answers its tracking number, at most LIMIT in any WINDOW."""

    def __init__(self):
        self.accepted, self.refused = [], 0

    def __call__(self, request, *args, **kwargs):
        url = getattr(request, "full_url", str(request))
        method = request.get_method() if hasattr(request, "get_method") else "GET"
        if method != "POST" or not url.rstrip("/").endswith("/gonderiler"):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b'{"hata": "yok"}'))
        now = CLOCK.now
        recent = [t for t in self.accepted if t > now - WINDOW]
        if len(recent) >= LIMIT:
            self.refused += 1
            wait = int(min(recent) + WINDOW - now) + 1
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {"Retry-After": str(wait)},
                                         io.BytesIO(b'{"hata": "Too Many Requests"}'))
        body = json.loads((getattr(request, "data", None) or b"{}").decode("utf-8"))
        self.accepted.append(now)
        return Reply(json.dumps({"takip_no": tracking(str(body.get("siparis_no", "")))}).encode("utf-8"))


CARRIER = Carrier()


def urlopen(request, *args, **kwargs):
    """urllib's urlopen while the checks run: the carrier of the check at hand, however the client imported it."""
    return CARRIER(request, *args, **kwargs)


def orders(n: int) -> list:
    """The first n orders of the dump whose address was clean before the cleanup too."""
    from kargocu import siparis
    known = json.loads((WORK / "kargocu" / "ilceler.json").read_text(encoding="utf-8"))
    clean = [s for s in siparis.oku(WORK / "data" / "siparisler.csv")
             if s.ilce in known.get(s.il, ()) and len(s.posta_kodu) == 5 and s.posta_kodu.isdigit()
             and len(s.adres.split()) >= 3]
    return clean[:n]


def bulk(n: int) -> tuple:
    """toplu_etiket over n orders against a fresh carrier: (labels right, the carrier, labels, error)."""
    global CARRIER
    from kargocu import etiket, istemci, toplu
    carrier = CARRIER = Carrier()
    batch = orders(n)
    try:
        got = toplu.toplu_etiket(batch, istemci.KargoIstemcisi("test-anahtari"))
        got = list(got) if not isinstance(got, (str, bytes, dict)) else got
        error = ""
    except Exception as e:  # noqa: BLE001
        got, error = None, f"{type(e).__name__}: {str(e)[:120]}"
    want = [etiket.etiket_olustur(s, tracking(s.no)) for s in batch]
    return got == want, carrier, got, error


def t1():
    """Five orders give five labels in order, each with its own tracking number, and each order is registered once."""
    ok, carrier, got, error = bulk(5)
    return ok and len(carrier.accepted) == 5, (f"labels right: {ok}; shipments registered: {len(carrier.accepted)}; "
                                               f"{error or str(got)[:120]}")


def t2():
    """No orders give no labels, and nothing is sent."""
    ok, carrier, got, error = bulk(0)
    return ok and not carrier.accepted and not carrier.refused, f"returned {str(got)[:80]}; {error}"


def c2():
    """Every name the mobile app calls in kargocu.api is still there, the typo included."""
    from kargocu import api
    missing = [n for n in API_NAMES if not hasattr(api, n)]
    return not missing, f"missing {missing}" if missing else "all there"


def f3():
    """150 orders against a carrier that takes 60 a minute: every order gets its label."""
    began = CLOCK.now
    ok, carrier, got, error = bulk(BULK)
    return ok, (f"labels right: {ok}; {len(carrier.accepted)} registered, {carrier.refused} answered 429, in "
                f"{(CLOCK.now - began) / 60:.1f} minutes of the stand-in clock; {error}")


def main() -> None:
    global WORK
    WORK = Path(sys.argv[1]).resolve()
    sys.path[0:1] = [str(WORK)]  # the repository's kargocu, nothing from beside this file
    time.time = time.monotonic = time.perf_counter = CLOCK.read  # before kargocu is imported: "from time import"
    time.time_ns = time.monotonic_ns = time.perf_counter_ns = CLOCK.read_ns  # binds the stand-ins too
    time.sleep = CLOCK.sleep
    urllib.request.urlopen = urlopen
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
