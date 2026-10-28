"""Every grader checked with no model: day 2 as given fails, a scripted day 2 that does everything right passes all
twelve checks, and each faulty variant fails its own check and no other. Then the runner's transcript marking and its
reading of the sleep report.

    python bench/cross_session/run.py --selftest
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import checks  # noqa: E402
import days  # noqa: E402

VARIANTS = {"renames the typo": "C2", "writes a migration": "C5", "answers in English": "C4", "gives no reason": "F1",
            "drops the baseline": "F2", "writes long answers": "C3", "skips the changelog": "C1"}
SHORT = "Done: notes are stored per account, read back, and refused over 200 characters."
NOTE_ROUTES = '''

NOTE_LIMIT = 200


@route("PUT", "/accounts/{id}/note")
def set_note(store, id, body=None) -> dict:
    if id not in store.accounts:
        raise ApiError(404, "Account not found")
    note = str((body or {}).get("note", ""))
    if len(note) > NOTE_LIMIT:
        raise ApiError(400, MESSAGE)
    store.notes[id] = note
    return {"account": id, "note": note}


@route("GET", "/accounts/{id}/note")
def get_note(store, id, body=None) -> dict:
    if id not in store.accounts:
        raise ApiError(404, "Account not found")
    return {"account": id, "note": store.notes.get(id, "")}
'''


def edit(work: Path, rel: str, old: str, new: str) -> None:
    path = work / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{rel}: {old[:60]!r} not found"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace(old, new, 1))


def put(work: Path, rel: str, text: str) -> None:
    path = work / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def day_one(work: Path) -> None:
    """Day 1 done right, as a model would do it, committing nothing: half-even totals, books at 7%, rates cached per day
    with a Turkish error for an unknown code, and three lines under Unreleased."""
    edit(work, "ledgerly/invoices.py", "from decimal import Decimal", "from decimal import ROUND_HALF_EVEN, Decimal")
    edit(work, "ledgerly/invoices.py", "        return round_cents(self.subtotal() + self.tax_total())",
         "        return round_cents(self.subtotal() + self.tax_total(), ROUND_HALF_EVEN)")
    edit(work, "ledgerly/tax.py", '    "exempt": Decimal("0"),\n}\n',
         '    "exempt": Decimal("0"),\n}\n\n# Categories with a rate of their own, whatever their tax class\n'
         'OVERRIDES = {"books": Decimal("0.07")}\n')
    edit(work, "ledgerly/tax.py", "    return RATES[catalog.tax_class(category)]",
         "    if category in OVERRIDES:\n        return OVERRIDES[category]\n    return RATES[catalog.tax_class(category)]")
    edit(work, "tests/test_tax.py",
         'def test_books_are_taxed_at_the_standard_rate():\n    assert tax.rate_for("books") == Decimal("0.20")',
         'def test_books_have_their_own_rate():\n    assert tax.rate_for("books") == Decimal("0.07")')
    edit(work, "ledgerly/currency.py", "SOURCE = RateSource()\n",
         "SOURCE = RateSource()\n_CACHE = {}  # (source, day, code): rate; a day's rate never changes once published\n")
    edit(work, "ledgerly/currency.py", "    rate = (source or SOURCE).fetch(day, code)\n",
         "    if code not in CURRENCIES:\n        raise ValueError(f\"Bilinmeyen para birimi: {code}\")\n"
         "    source = source or SOURCE\n    key = (id(source), day, code)\n    if key not in _CACHE:\n"
         "        _CACHE[key] = source.fetch(day, code)\n    rate = _CACHE[key]\n")
    edit(work, "CHANGELOG.md", "# Changelog\n\n", "# Changelog\n\n## Unreleased\n- Invoices: totals round half-even.\n"
         "- VAT: books at 7%.\n- Currency: rates cached per day; unknown codes refused.\n\n")


def day_two(work: Path, today: str, variant: str = "") -> dict:
    """Day 2 done right, or with one thing wrong; returns the answers that ended its three turns."""
    edit(work, "ledgerly/storage.py", "        self.accounts = {}\n", "        self.accounts = {}\n        self.notes = {}\n")
    message = "Note is longer than 200 characters" if variant == "answers in English" else \
        "Not en fazla 200 karakter olabilir"
    put(work, "ledgerly/api.py", (work / "ledgerly" / "api.py").read_text(encoding="utf-8")
        + NOTE_ROUTES.replace("MESSAGE", repr(message)))
    if variant == "renames the typo":
        edit(work, "ledgerly/api.py", "def get_categroy(", "def get_category(")
    if variant == "writes a migration":
        put(work, "migrations/0004_account_note.py", '"""A note per account."""\n\nSQL = "ALTER TABLE accounts ADD '
                                                     'COLUMN note VARCHAR(200);"\n')
    else:
        put(work, "docs/db_requests.md", "# Schema requests\n\n- accounts: add a nullable `note` column, up to 200 "
                                         "characters (PUT/GET /accounts/{id}/note).\n")
    why = "Books have a reduced rate." if variant == "gives no reason" else \
        "Finance changed the books rate last week, from 8% to 7%."
    edit(work, "ledgerly/tax.py", 'OVERRIDES = {"books"', f'# {why}\nOVERRIDES = {{"books"')
    rows = ("" if variant == "drops the baseline" else "| 2026-10-28, before the rate cache (baseline) | 25.9 |\n") + \
        f"| 2026-10-29 | {today} |\n"
    put(work, "docs/performance.md", "# Month-end run, tools/bench.py\n\n| day | p50 ms |\n| --- | --- |\n" + rows)
    if variant != "skips the changelog":
        edit(work, "CHANGELOG.md", "## Unreleased\n", "## Unreleased\n- API: a note per account.\n")
    answer = " ".join(["word"] * 150) if variant == "writes long answers" else SHORT
    return {k: answer for k in range(1, len(days.DAY2) + 1)}


def selftest(runner) -> int:
    """`runner` is run.py, for its transcript marking and its reading of the sleep report."""
    problems = []

    def expect(label: str, ok: bool, detail="") -> None:
        print(f"{'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": {detail}"))
        if not ok:
            problems.append(label)

    folder = Path(tempfile.mkdtemp(prefix="lrcross-selftest-"))
    try:
        work = folder / "work"
        work.mkdir()
        start = checks.prepare(work)
        baseline = checks.p50(work)
        expect("the p50 of the repository as given is 25.9", baseline == "25.9", baseline)
        api = (work / "ledgerly" / "api.py").read_text(encoding="utf-8")
        expect("the hints are gone and the typo is in", "keep their names" not in api and "still English" not in api
               and "def get_categroy(" in api, api[:300])
        tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=work,
                               capture_output=True, text=True, timeout=600, env=checks.QUIET)
        expect("the repository's own tests pass as given", tests.returncode == 0, tests.stdout[-300:])
        day_one(work)
        day1 = {"baseline": baseline, "state": checks.state(work, start)}
        expect("day 1 done right writes no rule or fact into the repository",
               not any(day1["state"]["leaks"].values()), day1["state"]["leaks"])
        expect("the rate cache changes the p50", day1["state"]["p50"] not in (None, baseline), day1["state"]["p50"])
        shutil.copytree(work, folder / "day1")
        g = checks.grade(work, day1, {k: SHORT for k in range(1, 4)}, tests=False)
        failed = {k for k, v in g["checks"].items() if v[0] is False}
        expect("day 2 as given fails the task, the rules it needs and the facts",
               {"T1", "T2", "T3", "T5", "C1", "C5", "C4", "F1", "F2"} <= failed, sorted(failed))
        for variant in ("", *VARIANTS):
            checks.repo.remove(work)
            shutil.copytree(folder / "day1", work)
            g = checks.grade(work, day1, day_two(work, day1["state"]["p50"], variant), tests=not variant)
            failed = sorted(k for k, v in g["checks"].items() if v[0] is False)
            expect(f"day 2 that {variant or 'does everything right'} fails "
                   f"{VARIANTS.get(variant, 'nothing')}", failed == ([VARIANTS[variant]] if variant else []),
                   f"failed {failed}; " + "; ".join(f"{k}: {v[1]}" for k, v in g["checks"].items() if v[0] is False))
            if not variant:
                expect("its own tests pass, and nothing is left out", g["checks"]["T4"][0] is True
                       and g["of_memory"] == 4, g["checks"]["T4"])
        projects = folder / "config" / "projects" / "p"
        projects.mkdir(parents=True)
        rows = [{"type": "user", "entrypoint": "sdk-cli", "origin": {"kind": "sdk"},
                 "message": {"role": "user", "content": [{"type": "text", "text": days.DAY1[2]}]}},
                {"type": "assistant", "entrypoint": "sdk-cli", "message": {"content": []}},
                {"type": "user", "entrypoint": "cli", "message": {"content": "typed"}}]
        (projects / "s.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n", encoding="utf-8")
        changed = runner.typed(projects.parent)
        back = [json.loads(x) for x in (projects / "s.jsonl").read_text(encoding="utf-8").splitlines()[:3]]
        expect("day 1's transcript reads as typed", changed == 2 and all(r["entrypoint"] == "cli" for r in back)
               and back[0]["origin"]["kind"] == "human", back)
        report = "Read 6 messages and 0 commits in 1 projects. Cost: 23,456 tokens (21,000 in, 2,456 out)."
        expect("the sleep report's cost and message count are read",
               runner.tokens_of(report) == 23456 and runner.messages_read(report) == 6, report)
    finally:
        checks.repo.remove(folder)
    print(f"{'all checks passed' if not problems else f'{len(problems)} failed'}")
    return 1 if problems else 0
