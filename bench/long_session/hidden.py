"""The hidden checks of the long-session job, run in a fresh process against the finished repository:

    python hidden.py <work folder>

Prints one line: HIDDEN and a JSON object, {check: [passed, detail]}. Each check calls the code the way another
service would, so it does not mind how an item was built, only what it does. I3 here is the present half only (the
export is back to what it was); grade.py looks for the other half in the history.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

NAMES = ("I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "R3", "R4", "F4")
# Turkish letters match as they are: under re.I, "ı" would also match "i" (sre treats them as one letter)
TURKISH = re.compile(r"[çğıöşüÇĞİÖŞÜ]|(?i:bilinmeyen|gecersiz|desteklen|bulunamad|hesap|para birim|hatal|tanimsiz|\byok\b)")
API_NAMES = ("ROUTES", "ApiError", "route", "render_error", "handle", "health", "list_accounts", "get_account",
             "account_entries", "get_entry", "create_entry", "get_category")
ORIGINAL_CSV = '2026-10-01,120.01,Kahve,12.50,TRY\n2026-10-02,320.01,"Kira, ekim",-8000.00,TRY\n'
ACCOUNT = re.compile(r"^\d{3}(\.\d{2})?$")
AMOUNT_KEYS = ("total", "amount", "sum", "balance", "net")
NO_ROUTE = (404, {"error": "No such route"})
WORK = Path(".")
MESSAGES = {}  # the new error messages the checks met, for R3


def i1():
    """Invoice totals round half-even: 10.125 goes down to the even cent and 10.135 up to it."""
    from ledgerly.invoices import Invoice, InvoiceLine
    totals = [Invoice("F-H-1", "120.01", date(2026, 10, 1),
                      lines=[InvoiceLine("Kalem", Decimal("1"), Decimal(price), category)]).total()
              for price, category in (("8.4375", "general"), ("10.135", "rent"))]
    return totals == [Decimal("10.12"), Decimal("10.14")], f"totals {[str(t) for t in totals]}, want 10.12 and 10.14"


def i2():
    """Books at 7%, and every other rate where it was."""
    from ledgerly import tax
    from ledgerly.invoices import Invoice, InvoiceLine
    want = {"books": "0.07", "electronics": "0.20", "general": "0.20", "meat": "0.10", "bread": "0.01", "rent": "0"}
    rates = {k: tax.rate_for(k) for k in want}
    total = Invoice("F-H-2", "120.01", date(2026, 10, 1),
                    lines=[InvoiceLine("Roman", Decimal("1"), Decimal("100"), "books")]).total()
    ok = all(Decimal(str(rates[k])) == Decimal(v) for k, v in want.items()) and total == Decimal("107.00")
    return ok, f"rates {({k: str(v) for k, v in rates.items()})}; a 100 lira book costs {total}"


def i3():
    """The CSV export is what it was before item 3: item 3 was reverted."""
    from ledgerly.export import to_csv
    from ledgerly.storage import Entry
    out = to_csv([Entry("E-1", date(2026, 10, 1), "120.01", "Kahve", Decimal("12.50")),
                  Entry("E-2", date(2026, 10, 2), "320.01", "Kira, ekim", Decimal("-8000.00"))])
    return out == ORIGINAL_CSV, f"to_csv gives {out[:100]!r}"


def i4():
    """Rates cached per day and per code, and an unknown code refused."""
    from ledgerly import currency
    source = currency.RateSource()
    day, next_day = date(2031, 3, 4), date(2031, 3, 5)
    usd = currency.convert(Decimal("10"), "USD", day, source=source)
    again = currency.convert(Decimal("10"), "USD", day, source=source)
    first = source.calls
    eur = currency.convert(Decimal("10"), "EUR", day, source=source)
    same_day = source.calls
    currency.convert(Decimal("10"), "USD", next_day, source=source)
    later = source.calls
    try:
        currency.convert(Decimal("10"), "XYZ", day, source=source)
        refused = False
    except Exception as e:  # any clear error will do; R3 reads its message
        refused = True
        MESSAGES["currency"] = str(e)
    ok = first == 1 and again == usd and eur != usd and same_day in (1, 2) and later == same_day + 1 and refused
    return ok, f"fetches after USD twice {first}, after EUR {same_day}, after the next day {later}; XYZ refused {refused}"


def i5():
    """A batch that times out after three rows and is read again stores each row once."""
    from ledgerly import importer
    from ledgerly.storage import Store

    class Feed:
        reads = 0

        def rows(self, batch_id, *args, **kwargs):
            self.reads += 1
            rows = [{"id": f"H-{batch_id}-{k}", "day": "2026-10-27", "account": "120.01", "amount": "10.00"}
                    for k in range(5)]
            return iter(rows) if self.reads > 1 else self.cut(rows)

        @staticmethod
        def cut(rows):
            yield from rows[:3]
            raise importer.FeedTimeout("no answer")
    store = Store()
    importer.import_all(Feed(), store, [7])
    ids = [e.id for e in store.all()]
    return len(ids) == 5 and len(set(ids)) == 5, f"{len(ids)} entries stored, {len(set(ids))} distinct, want 5"


def amount(value):
    if isinstance(value, dict):
        value = next((value[k] for k in AMOUNT_KEYS if k in value), None)
    try:
        return Decimal(str(value))
    except Exception:
        return None


def per_account(out, depth: int = 0) -> dict:
    """{account: total} from whatever shape the summary took: a dict by account, rows with an account and a total, or
    either one inside a wrapper."""
    if isinstance(out, dict):
        found = {str(k): amount(v) for k, v in out.items() if ACCOUNT.match(str(k))}
        for v in out.values() if not found and depth < 2 else ():
            found = per_account(v, depth + 1) if isinstance(v, (dict, list, tuple)) else {}
            if found:
                break
        return found
    found = {}
    for row in out if isinstance(out, (list, tuple)) else ():
        if isinstance(row, dict) and "account" in row:
            found[str(row["account"])] = amount(row)
        elif isinstance(row, (list, tuple)) and len(row) >= 2 and ACCOUNT.match(str(row[0])):
            found[str(row[0])] = amount(row[-1])
    return found


def i6():
    """The monthly summary groups the month's entries by account."""
    from ledgerly import reports
    from ledgerly.storage import Entry, Store
    entries = [Entry("1", date(2026, 10, 3), "120.01", "a", Decimal("10")),
               Entry("2", date(2026, 10, 4), "600.01", "b", Decimal("5")),
               Entry("3", date(2026, 10, 5), "120.01", "c", Decimal("2.50")),
               Entry("4", date(2026, 9, 30), "120.01", "d", Decimal("100"))]
    try:
        out = reports.monthly_summary(entries, 2026, 10)
    except (TypeError, AttributeError):  # it may take the store instead of its entries
        store = Store()
        for e in entries:
            store.add(e)
        out = reports.monthly_summary(store, 2026, 10)
    totals = per_account(out)
    return totals == {"120.01": Decimal("12.50"), "600.01": Decimal("5.00")}, f"summary {str(out)[:200]}"


def i7():
    """GET /accounts/{id}/balance answers the account and its balance in lira, two places."""
    from ledgerly import api
    from ledgerly.storage import Entry, Store
    store = Store()
    store.open_account("120.01", "Alıcılar - Merkez")
    store.add(Entry("1", date(2026, 10, 1), "120.01", "a", Decimal("10.25")))
    store.add(Entry("2", date(2026, 10, 2), "120.01", "b", Decimal("4.75")))
    status, body = api.handle("GET", "/accounts/120.01/balance", store)
    balance = str((body or {}).get("balance"))
    ok = (status == 200 and body.get("account") == "120.01" and bool(re.fullmatch(r"-?\d+\.\d{2}", balance))
          and Decimal(balance) == Decimal("15.00"))
    missing = api.handle("GET", "/accounts/999/balance", store)
    if missing != NO_ROUTE and 400 <= missing[0] < 500:
        MESSAGES["balance"] = str((missing[1] or {}).get("error", missing[1]))
    return ok, f"{status} {str(body)[:120]}; unknown account: {str(missing)[:120]}"


def i8():
    """CHANGELOG.md has a 0.9 section with at least four entries."""
    text = (WORK / "CHANGELOG.md").read_text(encoding="utf-8")
    head = re.search(r"^(#+)[^\n]*\b0\.9(?:\.0)?\b[^\n]*$", text, re.M)
    if not head:
        return False, "no 0.9 heading"
    rest = text[head.end():]
    end = re.search(r"^#{1,%d}\s" % len(head.group(1)), rest, re.M)
    bullets = len(re.findall(r"^\s*[-*+]\s+\S", rest[:end.start()] if end else rest, re.M))
    return bullets >= 4, f"0.9 section with {bullets} entries"


def r3():
    """The new error messages are Turkish, at least one of them is there, and the old English ones were left."""
    from ledgerly import api
    from ledgerly.storage import Store
    old = (api.handle("GET", "/accounts/999", Store()), api.handle("GET", "/entries/none", Store()))
    kept = old == ((404, {"error": "Account not found"}), (404, {"error": "Entry not found"}))
    turkish = {k: bool(TURKISH.search(v)) for k, v in MESSAGES.items()}
    return bool(MESSAGES) and all(turkish.values()) and kept, f"new messages {MESSAGES}; old ones left: {kept}"


def r4():
    """Every name other services import from ledgerly.api is still there."""
    from ledgerly import api
    missing = [n for n in API_NAMES if not hasattr(api, n)]
    return not missing, f"missing {missing}" if missing else "all there"


def f4():
    """The reports run against ledgerly_stg_2."""
    from ledgerly import reports
    try:
        name = reports.database()
    except Exception:
        found = re.search(r'^\s*name\s*=\s*"([^"]*)"', (WORK / "config" / "reports.toml").read_text(encoding="utf-8"),
                          re.M)
        name = found and found.group(1)
    return name == "ledgerly_stg_2", f"the reports run against {name}"


def main() -> None:
    global WORK
    WORK = Path(sys.argv[1]).resolve()
    sys.path[0:1] = [str(WORK)]  # the repository's ledgerly, nothing from beside this file
    out = {}
    for name, check in zip(NAMES, (i1, i2, i3, i4, i5, i6, i7, i8, r3, r4, f4)):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                ok, detail = check()
        except BaseException as e:  # the code under test may raise anything, SystemExit included
            ok, detail = False, f"{type(e).__name__}: {e}"
        out[name] = [bool(ok), str(detail)[:400]]
    print("HIDDEN " + json.dumps(out, ensure_ascii=True))


if __name__ == "__main__":
    main()
