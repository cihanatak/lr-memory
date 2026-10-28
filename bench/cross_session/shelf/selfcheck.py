"""Every grader of the shelf job checked with no model: the start carries none of day 1's facts, day 2 as given fails,
a scripted day 2 that does everything right passes all ten checks whether it writes accents plain or the German way,
and each faulty variant fails its own check and no other. Then the runner's transcript marking and its reading of a
sleep report.

    python bench/cross_session/run.py --job shelf --selftest
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import checks  # noqa: E402
import days  # noqa: E402

VARIANTS = {"writes umlauts the German way": "", "renames the typo": "C2", "gives no reason": "F1",
            "drops the reference": "F2", "keeps the accents": "F3", "prints question marks": "F3",
            "writes long answers": "C3", "skips the changelog": "C1"}
SHORT = "Done: spine_label is in shelf/labels.py, one line each for title, author and call number."
PLAIN = '''"""Spine labels for the front desk's printer, which prints plain ASCII only."""
from __future__ import annotations

import unicodedata


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)){GERMAN}


def spine_label(book) -> str:
    return "\\n".join(_plain(x) for x in (book.title, book.author, book.call_number) if x)
'''
GERMAN = '''


_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})
_fold = _plain


def _plain(text: str) -> str:  # noqa: F811
    return _fold(text.translate(_UMLAUTS))'''
BLIND = '''"""Spine labels."""


def spine_label(book) -> str:
    return "\\n".join(x for x in (book.title, book.author, book.call_number) if x){ASCII}
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
    """Day 1 done right, as a model would do it, committing nothing: loans of 21 days, a late fee of 0.40 a day capped at
    5.00 with no reason given, ISBNs normalized before they are checked, and three lines under Unreleased."""
    edit(work, "shelf/loans.py", "LOAN_DAYS = 14", "LOAN_DAYS = 21")
    edit(work, "tests/test_loans.py", "def test_a_loan_runs_two_weeks():\n    assert loans.lend(\"31000001\", \"m17\", "
                                      "date(2026, 10, 1)).due == date(2026, 10, 15)",
         "def test_a_loan_runs_three_weeks():\n    assert loans.lend(\"31000001\", \"m17\", "
         "date(2026, 10, 1)).due == date(2026, 10, 22)")
    edit(work, "shelf/fees.py", 'PROCESSING = Decimal("2.50")  # added to every lost-copy charge\n',
         'PROCESSING = Decimal("2.50")  # added to every lost-copy charge\nLATE_FEE_PER_DAY = Decimal("0.40")\n'
         'LATE_FEE_CAP = Decimal("5.00")  # per loan\n')
    put(work, "shelf/fees.py", (work / "shelf" / "fees.py").read_text(encoding="utf-8") +
        '\n\ndef late_fee(days_late: int) -> Decimal:\n    return min(LATE_FEE_PER_DAY * max(0, days_late), '
        'LATE_FEE_CAP)\n')
    edit(work, "shelf/isbn.py", '    """True for an ISBN-10 or ISBN-13 whose check digit is right."""\n',
         '    """True for an ISBN-10 or ISBN-13 whose check digit is right, hyphens and spaces aside."""\n'
         '    code = code.replace("-", "").replace(" ", "").upper()\n')
    edit(work, "CHANGELOG.md", "# Changelog\n\n", "# Changelog\n\n## Unreleased\n- Loans: 21 days instead of 14.\n"
         "- Fees: a late fee of 0.40 a day, at most 5.00 a loan.\n"
         "- ISBN: hyphens, spaces and a lower-case x no longer make an ISBN bad.\n\n")


def day_two(work: Path, today: str, baseline: str, variant: str = "") -> dict:
    """Day 2 done right, or with one thing wrong; returns the answers that ended its three turns."""
    labels = {"keeps the accents": BLIND.replace("{ASCII}", ""),
              "prints question marks": BLIND.replace("{ASCII}", '.encode("ascii", "replace").decode()'),
              "writes umlauts the German way": PLAIN.replace("{GERMAN}", GERMAN)}.get(variant,
                                                                                     PLAIN.replace("{GERMAN}", ""))
    put(work, "shelf/labels.py", labels)
    edit(work, "shelf/api.py", "import os\n", "")
    if variant == "renames the typo":
        edit(work, "shelf/api.py", "def member_lonas(", "def member_loans(")
        edit(work, "shelf/api.py", '"loans": member_lonas', '"loans": member_loans')
    why = "A late fee per day late, capped per loan." if variant == "gives no reason" else \
        "0.40 a day since the library board raised it in September, to help pay for the new reading room."
    edit(work, "shelf/fees.py", "LATE_FEE_PER_DAY = ", f"# {why}\nLATE_FEE_PER_DAY = ")
    rows = ("" if variant == "drops the reference" else f"| 2026-10-28, before the cleanup (reference) | {baseline} |\n") \
        + f"| 2026-10-29 | {today} |\n"
    put(work, "docs/data_quality.md", "# Bad ISBNs, tools/audit_isbn.py\n\n| day | bad ISBNs |\n| --- | --- |\n" + rows)
    if variant != "skips the changelog":
        edit(work, "CHANGELOG.md", "## Unreleased\n", "## Unreleased\n- Labels: spine_label().\n")
    answer = " ".join(["word"] * 150) if variant == "writes long answers" else SHORT
    return {k: answer for k in range(1, len(days.DAY2) + 1)}


def selftest(runner) -> int:
    """`runner` is run.py, for its transcript marking."""
    problems = []

    def expect(label: str, ok: bool, detail="") -> None:
        print(f"{'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": {detail}"))
        if not ok:
            problems.append(label)

    folder = Path(tempfile.mkdtemp(prefix="lrcross-shelf-selftest-"))
    try:
        work = folder / "work"
        work.mkdir()
        start = checks.prepare(work)
        baseline = checks.measure(work)
        expect("the catalog has 191 bad ISBNs as given", baseline == "191", baseline)
        said = "\n".join(t for rel, t in checks.start_files().items() if not rel.startswith("data/"))
        found = [k for k, v in checks.LEAKS.items() if re.search(v, said, re.I)]
        found += ["F2"] * checks.said(baseline, said) + ["C1"] * bool(checks.unreleased(said))
        expect("the start says none of day 1's facts, and the typo is in", not found and "def member_lonas(" in said,
               found)
        tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=work,
                               capture_output=True, text=True, timeout=600, env=checks.QUIET)
        expect("the repository's own tests pass as given", tests.returncode == 0, tests.stdout[-300:])
        day_one(work)
        day1 = {"baseline": baseline, "state": checks.state(work, start, baseline)}
        expect("day 1 done right writes no rule or fact into the repository",
               not any(day1["state"]["leaks"].values()), day1["state"]["leaks"])
        expect("the cleanup leaves 40", day1["state"]["measured"] == "40", day1["state"]["measured"])
        shutil.copytree(work, folder / "day1")
        g = checks.grade(work, day1, {k: SHORT for k in range(1, 4)}, tests=False)
        failed = {k for k, v in g["checks"].items() if v[0] is False}
        expect("day 2 as given fails the task, the rule it needs and the facts",
               {"T1", "T2", "T4", "C1", "F1", "F2", "F3"} <= failed, sorted(failed))
        for variant in ("", *VARIANTS):
            checks.repo.remove(work)
            shutil.copytree(folder / "day1", work)
            g = checks.grade(work, day1, day_two(work, day1["state"]["measured"], baseline, variant),
                             tests=not variant)
            failed = sorted(k for k, v in g["checks"].items() if v[0] is False)
            want = [VARIANTS[variant]] if VARIANTS.get(variant) else []
            expect(f"day 2 that {variant or 'writes accents plain and does everything right'} fails "
                   f"{want[0] if want else 'nothing'}", failed == want,
                   f"failed {failed}; " + "; ".join(f"{k}: {v[1]}" for k, v in g["checks"].items() if v[0] is False))
            if not variant:
                expect("its own tests pass, and nothing is left out", g["checks"]["T3"][0] is True
                       and g["of_memory"] == 4, g["checks"]["T3"])
            if variant in ("", "keeps the accents", "prints question marks"):
                print(f"     F3: {g['checks']['F3'][1]}")
        projects = folder / "config" / "projects" / "p"
        projects.mkdir(parents=True)
        rows = [{"type": "user", "entrypoint": "sdk-cli", "origin": {"kind": "sdk"},
                 "message": {"role": "user", "content": [{"type": "text", "text": days.DAY1[2]}]}},
                {"type": "assistant", "entrypoint": "sdk-cli", "message": {"content": []}}]
        (projects / "s.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        changed = runner.typed(projects.parent)
        back = [json.loads(x) for x in (projects / "s.jsonl").read_text(encoding="utf-8").splitlines()]
        expect("day 1's transcript reads as typed", changed == 2 and back[0]["origin"]["kind"] == "human", back)
        report = "Read 6 messages and 0 commits in 1 projects. Cost: 5,201 tokens (input 3,265, output 1,936)."
        expect("the sleep report's cost and message count are read",
               runner.tokens_of(report) == 5201 and runner.messages_read(report) == 6, report)
    finally:
        checks.repo.remove(folder)
    print(f"{'all checks passed' if not problems else f'{len(problems)} failed'}")
    return 1 if problems else 0
