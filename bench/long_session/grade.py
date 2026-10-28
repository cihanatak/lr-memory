"""Grades a finished long session. Sixteen checks, all mechanical:

  items  I1-I8  hidden.py in a fresh process; I3 also needs a commit in the history with the ';' export and a header
  rules  R1     migrations/ untouched, in every commit and on disk
         R2     at least eight commits with the prefix, and no other commits but reverts
         R3-R4  hidden.py: new error messages in Turkish, the old ones left; every name of api.py still there
  facts  F1     this morning's p50 in the answer to message 9
         F2     at least seven item commits named by hash in the answer to message 10
         F3     the revert of item 3 named there
         F4     hidden.py: the reports run against ledgerly_stg_2
"""
from __future__ import annotations

import ast
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hidden  # noqa: E402
import repo  # noqa: E402
import script  # noqa: E402

CHECKS = ("I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "R1", "R2", "R3", "R4", "F1", "F2", "F3", "F4")
PREFIX = re.compile(r"^ledgerly 0\.9\s*:\s*\S")
REVERT = re.compile(r"\brevert", re.I)
REVERTED = re.compile(r"revert|rolled back|backed out|undone|undid", re.I)
ITEM3 = re.compile(r"csv|export|separator|header|item\s*#?3\b|^\W*3\b", re.I)
P50 = re.compile(r"p50 ([\d.]+) ms")
PROBE = ("import sys; sys.path.insert(0, sys.argv[1]); from datetime import date; from decimal import Decimal; "
         "from ledgerly.export import to_csv; from ledgerly.storage import Entry; "
         "print(repr(to_csv([Entry('E-1', date(2026, 10, 1), '120.01', 'Kahve', Decimal('12.50')), "
         "Entry('E-2', date(2026, 10, 2), '320.01', 'Kira, ekim', Decimal('-8000.00'))])))")
QUIET = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
_baseline = []


def baseline() -> str:
    """This morning's p50: tools/bench.py on the repository as given. Its timings are modelled, not clocked, so it is the
    same on every machine (25.9)."""
    if not _baseline:
        folder = Path(tempfile.mkdtemp(prefix="lrlong-baseline-"))
        try:
            repo.materialize(folder, commit=False)
            out = subprocess.run([sys.executable, "tools/bench.py"], cwd=folder, capture_output=True, text=True,
                                 timeout=120, env=QUIET).stdout
        finally:
            repo.remove(folder)
        _baseline.append(P50.search(out).group(1))
    return _baseline[0]


def said(number: str, text: str) -> bool:
    return bool(re.search(rf"(?<![\d.]){re.escape(number)}(?!\d)", text.replace(",", ".")))


def hidden_checks(work: Path) -> dict:
    try:
        r = subprocess.run([sys.executable, str(HERE / "hidden.py"), str(work)], cwd=work, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=300, env=QUIET)
    except subprocess.TimeoutExpired:
        return {k: [False, "the hidden checks timed out"] for k in hidden.NAMES}
    line = next((x for x in reversed(r.stdout.splitlines()) if x.startswith("HIDDEN ")), None)
    if line is None:
        return {k: [False, f"the hidden checks did not run: {(r.stderr or r.stdout)[-300:]}"] for k in hidden.NAMES}
    return json.loads(line[len("HIDDEN "):])


def history(work: Path, base: str) -> list:
    """(hash, subject) of every commit since the base, oldest first."""
    out = repo.git(work, "log", "--reverse", "--format=%H%x09%s", f"{base}..HEAD")
    return [tuple(x.split("\t", 1)) if "\t" in x else (x, "") for x in out.splitlines() if x.strip()]


def export_format(work: Path, commit: str, tmp: Path) -> str:
    """What the CSV export of a commit gives: original, semicolon (';' with a header row), other or error."""
    data = subprocess.run(["git", "archive", "--format=tar", commit, "ledgerly"], cwd=work, capture_output=True,
                          check=True).stdout
    folder = tmp / commit
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(folder, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
    r = subprocess.run([sys.executable, "-c", PROBE, str(folder)], cwd=folder, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60, env=QUIET)
    if r.returncode or not r.stdout.strip():
        return "error"
    out = ast.literal_eval(r.stdout.strip().splitlines()[-1])
    if out == hidden.ORIGINAL_CSV:
        return "original"
    lines = out.splitlines()
    if len(lines) == 3 and all(";" in x for x in lines) and not re.match(r"\d{4}-", lines[0]):
        return "semicolon"
    return "other"


def revert_of(formats: list):
    """The commit that put the original export back after the ';' one, or None."""
    seen = False
    for commit, _, fmt in formats:
        seen = seen or fmt == "semicolon"
        if seen and fmt == "original":
            return commit
    return None


def grade(work: Path, base: str, answers: dict, tests: bool = True) -> dict:
    """The 16 checks as {check: [passed, detail]}, the score, the revert commit, the CSV export along the history, and
    whether the repository's own tests pass at the end."""
    checks = hidden_checks(work)
    log = history(work, base)
    with tempfile.TemporaryDirectory(prefix="lrlong-history-") as tmp:
        formats = [(h, s, export_format(work, h, Path(tmp))) for h, s in log]
    touched = repo.git(work, "log", "--format=", "--name-only", f"{base}..HEAD", "--", "migrations").split()
    on_disk = repo.git(work, "status", "--porcelain", "--untracked-files=all", "--", "migrations").splitlines()
    checks["R1"] = [not touched and not on_disk, f"in commits: {sorted(set(touched))[:4]}; on disk: {on_disk[:4]}"]
    items = [(h, s) for h, s in log if PREFIX.match(s) and not REVERT.search(s)]
    stray = [s for h, s in log if not PREFIX.match(s) and not REVERT.search(s)]
    checks["R2"] = [len(items) >= 8 and not stray, f"{len(items)} item commits; others: {stray[:3]}"]
    had = any(f == "semicolon" for _, _, f in formats)
    now_ok, now = checks["I3"]
    checks["I3"] = [had and now_ok, f"a ';' export with a header in the history: {had}; now: {now}"]
    nine, ten = answers.get(script.BASELINE, ""), answers.get(script.WRAP_UP, "")
    checks["F1"] = [said(baseline(), nine), f"baseline {baseline()} in the answer to message {script.BASELINE}"]
    named = [h for h, _ in items if h[:7] in ten.lower()]
    checks["F2"] = [len(named) >= 7, f"{len(named)} of {len(items)} item commits named"]
    lines = [x for x in ten.splitlines() if REVERTED.search(x) and ITEM3.search(x)]
    checks["F3"] = [bool(lines), lines[0][:200] if lines else "the revert of item 3 is not named"]
    ran = None
    if tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=work,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=QUIET)
        ran = r.returncode == 0
    checks = {k: checks[k] for k in CHECKS}
    return {"checks": checks, "score": sum(v[0] for v in checks.values()), "revert": revert_of(formats),
            "history": [(h[:8], s[:80], f) for h, s, f in formats], "tests": ran}


def grade_next(answer: str, revert) -> dict:
    """The next session's three answers: this morning's p50, why books are at 7% (finance changed it), and the revert's
    hash. The last one is None when the long session never reverted."""
    return {"p50": said(baseline(), answer), "reason": bool(re.search(r"financ", answer, re.I)),
            "revert": None if revert is None else revert[:7] in answer.lower()}
