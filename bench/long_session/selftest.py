"""Every grader checked with no model: the job as given fails, a scripted session that does everything right passes all
16 checks, and each faulty variant fails exactly its own check.

    python bench/long_session/run.py --selftest
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grade  # noqa: E402
import repo  # noqa: E402
import script  # noqa: E402

VARIANTS = {"keeps 8%": "I2", "touches a migration": "R1", "wrong baseline": "F1", "no revert": "I3"}


def edit(work: Path, rel: str, old: str, new: str) -> None:
    path = work / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{rel}: {old[:60]!r} not found"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace(old, new, 1))


def commit(work: Path, message: str) -> str:
    repo.git(work, "add", "-A")
    repo.git(work, "commit", "-q", "-m", message)
    return repo.git(work, "rev-parse", "HEAD")


def solve(work: Path, variant: str = "") -> tuple:
    """The session done right, edit by edit and commit by commit, as a model would do it; a variant gets one thing
    wrong. Returns the answers to messages 9 and 10, and the revert commit."""
    edit(work, "ledgerly/invoices.py", "from decimal import Decimal", "from decimal import ROUND_HALF_EVEN, Decimal")
    edit(work, "ledgerly/invoices.py", "        return round_cents(self.subtotal() + self.tax_total())",
         "        return round_cents(self.subtotal() + self.tax_total(), ROUND_HALF_EVEN)")
    commit(work, "ledgerly 0.9: invoice totals round half-even")
    edit(work, "ledgerly/tax.py", '    "exempt": Decimal("0"),\n}\n',
         '    "exempt": Decimal("0"),\n}\n\n# Categories with a rate of their own, whatever their tax class\n'
         'OVERRIDES = {"books": Decimal("0.08")}\n')
    edit(work, "ledgerly/tax.py", "    return RATES[catalog.tax_class(category)]",
         "    if category in OVERRIDES:\n        return OVERRIDES[category]\n    return RATES[catalog.tax_class(category)]")
    edit(work, "tests/test_tax.py",
         'def test_books_are_taxed_at_the_standard_rate():\n    assert tax.rate_for("books") == Decimal("0.20")',
         'def test_books_have_their_own_rate():\n    assert tax.rate_for("books") == Decimal("0.08")')
    if variant == "touches a migration":
        with open(work / "migrations" / "0004_books_rate.py", "w", encoding="utf-8", newline="\n") as f:
            f.write("SQL = \"INSERT INTO tax_rates (class, rate) VALUES ('books', 0.08);\"\n")
    commit(work, "ledgerly 0.9: books at a reduced VAT rate")
    if variant != "keeps 8%":
        edit(work, "ledgerly/tax.py", 'OVERRIDES = {"books": Decimal("0.08")}', 'OVERRIDES = {"books": Decimal("0.07")}')
        edit(work, "tests/test_tax.py", 'Decimal("0.08")', 'Decimal("0.07")')
        commit(work, "ledgerly 0.9: books VAT rate is 7%")
    edit(work, "ledgerly/export.py", 'delimiter=","', 'delimiter=";"')
    edit(work, "ledgerly/export.py", "    writer.writerows(rows(entries))",
         "    writer.writerow(COLUMNS)\n    writer.writerows(rows(entries))")
    edit(work, "tests/test_export.py", "def test_csv_is_comma_separated_without_a_header():",
         "def test_csv_has_a_header_and_semicolons():")
    edit(work, "tests/test_export.py",
         r"""'2026-10-01,120.01,Kahve,12.50,TRY\n2026-10-02,320.01,"Kira, ekim",-8000.00,TRY\n'""",
         r"""'date;account;description;amount;currency\n2026-10-01;120.01;Kahve;12.50;TRY\n"""
         r"""2026-10-02;320.01;Kira, ekim;-8000.00;TRY\n'""")
    csv = commit(work, "ledgerly 0.9: CSV export with ';' and a header row")
    edit(work, "ledgerly/currency.py", "SOURCE = RateSource()\n",
         "SOURCE = RateSource()\n_CACHE = {}  # (source, day, code): rate; a day's rate never changes once published\n")
    edit(work, "ledgerly/currency.py", "    rate = (source or SOURCE).fetch(day, code)\n",
         "    if code not in CURRENCIES:\n        raise ValueError(f\"Bilinmeyen para birimi: {code}\")\n"
         "    source = source or SOURCE\n    key = (id(source), day, code)\n    if key not in _CACHE:\n"
         "        _CACHE[key] = source.fetch(day, code)\n    rate = _CACHE[key]\n")
    commit(work, "ledgerly 0.9: rates cached per day, unknown currencies refused")
    edit(work, "ledgerly/importer.py", "                check_row(row)\n                store.add(Entry.from_row(row))\n",
         "                check_row(row)\n                if store.find(str(row[\"id\"])) is not None:\n"
         "                    continue  # stored before the feed timed out\n"
         "                store.add(Entry.from_row(row))\n")
    commit(work, "ledgerly 0.9: a batch read again stores each row once")
    edit(work, "ledgerly/reports.py", '    raise NotImplementedError("monthly_summary is planned for 0.9")\n',
         "    totals = defaultdict(lambda: ZERO)\n    for e in in_month(entries, year, month):\n"
         "        totals[e.account] += e.amount\n    return {k: round_cents(v) for k, v in sorted(totals.items())}\n")
    edit(work, "config/reports.toml", 'name = "ledgerly_stg"', 'name = "ledgerly_stg_2"')
    edit(work, "tests/test_reports.py", '== "ledgerly_stg"', '== "ledgerly_stg_2"')
    commit(work, "ledgerly 0.9: monthly summary per account, on ledgerly_stg_2")
    revert = ""
    if variant != "no revert":
        repo.git(work, "revert", "--no-edit", csv)
        revert = repo.git(work, "rev-parse", "HEAD")
    edit(work, "ledgerly/api.py", "from . import catalog\n", "from . import accounts, catalog\n")
    edit(work, "ledgerly/api.py", '@route("GET", "/entries/{id}")\n',
         '@route("GET", "/accounts/{id}/balance")\ndef account_balance(store, id, body=None) -> dict:\n'
         '    if id not in store.accounts:\n        raise ApiError(404, "Hesap bulunamadı")\n'
         '    return {"account": id, "balance": f"{accounts.balance(store, id):.2f}"}\n\n\n'
         '@route("GET", "/entries/{id}")\n')
    commit(work, "ledgerly 0.9: GET /accounts/{id}/balance")
    edit(work, "CHANGELOG.md", "# Changelog\n\n",
         "# Changelog\n\n## 0.9 (2026-10-28)\n- Invoices: totals round half-even.\n- VAT: books at 7%.\n"
         "- Currency: rates cached per day; unknown codes refused.\n"
         "- Import: a batch read again after a timeout stores each row once.\n"
         "- Reports: a monthly summary per account, on ledgerly_stg_2.\n- API: GET /accounts/{id}/balance.\n\n")
    commit(work, "ledgerly 0.9: changelog")
    p50 = "31.2" if variant == "wrong baseline" else grade.baseline()
    log = repo.git(work, "log", "--reverse", "--format=%h %s").splitlines()[1:]  # the base commit aside
    ten = "\n".join(f"- {x.split(' ', 1)[1]}: {x.split(' ', 1)[0]}" for x in log)
    ten += f"\nItem 3, the CSV export change, was reverted in {(revert or csv)[:8]}.\nNothing else is left undone."
    answers = {script.BASELINE: f"p50 now 0.7 ms, against this morning's baseline of {p50} ms.", script.WRAP_UP: ten}
    return answers, revert


def run(variant: str = "", solved: bool = True) -> tuple:
    base = Path(tempfile.mkdtemp(prefix="lrlong-selftest-"))
    try:
        work = base / "work"
        work.mkdir()
        start = repo.materialize(work)
        answers, revert = solve(work, variant) if solved else ({}, "")
        return grade.grade(work, start, answers, tests=solved and not variant), revert
    finally:
        repo.remove(base)


def failed(result: dict) -> list:
    return [k for k, (ok, _) in result["checks"].items() if not ok]


def selftest() -> int:
    problems = []
    given, _ = run(solved=False)
    print(f"as given: {16 - given['score']} of 16 checks fail ({' '.join(failed(given))})")
    if given["score"] > 4:
        problems.append(f"the job as given passes {given['score']} checks")
    perfect, revert = run()
    print(f"done right: {perfect['score']} of 16; the repository's tests pass: {perfect['tests']}; "
          f"revert found: {perfect['revert'] == revert}")
    if perfect["score"] != 16 or not perfect["tests"] or perfect["revert"] != revert:
        problems.append(f"done right: {[(k, perfect['checks'][k][1]) for k in failed(perfect)]}, "
                        f"tests {perfect['tests']}, revert {perfect['revert']} vs {revert}")
    right = grade.grade_next(f"1. {grade.baseline()} ms\n2. Finance changed the books rate last week.\n3. {revert[:8]}",
                             revert)
    wrong = grade.grade_next("1. 30 ms\n2. Books have a reduced rate.\n3. 0123abc", revert)
    print(f"next session: right answers {sum(right.values())} of 3, wrong answers {sum(wrong.values())} of 3")
    if right != {"p50": True, "reason": True, "revert": True} or any(wrong.values()):
        problems.append(f"next session: {right} {wrong}")
    for variant, check in VARIANTS.items():
        result, _ = run(variant)
        print(f"{variant}: fails {' '.join(failed(result)) or 'nothing'} (should fail {check})")
        if failed(result) != [check]:
            problems.append(f"{variant}: fails {failed(result)}, should fail only {check}: "
                            f"{[(k, result['checks'][k][1]) for k in failed(result)]}")
    for p in problems:
        print("PROBLEM:", p)
    if not problems:
        print("graders: each check passes on the work done right and fails on its own fault")
    return 1 if problems else 0
