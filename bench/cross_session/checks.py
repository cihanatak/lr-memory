"""Grades day 2 of a chain against what day 1 left. Twelve checks, all mechanical:

  task    T1-T3  hidden_checks.py in a fresh process: a 200-character note is stored and read back; 201 characters
                 are a 400 that leaves the note as it was; an unknown account is a 404
          T4     the repository's own tests pass
          T5     today's p50 is in docs/performance.md
  rules   C1     the Unreleased section of CHANGELOG.md gained a line                 (a standing rule, said on day 1)
          C2     hidden_checks.py: every name of api.py is still there, the typo too   (a standing rule)
          C5     migrations/ as day 1 left it, and docs/db_requests.md asks for the note column (a standing rule)
  memory  C3     day 2's answers are short: their median is 100 words or fewer        (a complaint on day 1)
          C4     hidden_checks.py: the message for a long note is Turkish             (a requirement and its reason)
          F1     tax.py says finance changed the books rate                           (a correction and its reason)
          F2     yesterday's p50 is in docs/performance.md                            (a number measured on day 1)

F2 is None when today's p50 equals yesterday's: writing today's number would pass it. state() also records, for each
rule and fact, whether day 1 wrote it into the repository (a leak): day 2 can then read it instead of remembering it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "long_session"))
sys.path.insert(0, str(HERE))
import days  # noqa: E402
import repo  # noqa: E402

CHECKS = ("T1", "T2", "T3", "T4", "T5", "C1", "C2", "C5", "C3", "C4", "F1", "F2")
TASK, RULES, MEMORY = CHECKS[:5], ("C1", "C2", "C5"), ("C3", "C4", "F1", "F2")
SHORT = 100  # words
P50 = re.compile(r"p50 ([\d.]+) ms")
QUIET = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
SKIP = (".git", "logs", "__pycache__", ".pytest_cache")
LEAKS = {"F1": r"financ", "F2": r"(?<![\d.])25\.9(?!\d)", "C4": r"turkish|türkçe|english|staff",
         "C2": r"renam|other services|import(?:ed)? (?:these|its|those|the) names",
         "C5": r"db_requests|\bDBA\b|schema change", "C3": r"\bshort\b|concise|brief"}


def start_files() -> dict:
    """The repository day 1 starts from: the long-session repository with days.HINTS rewritten and days.TYPO planted."""
    files = dict(repo.files())
    for rel, old, new in (*days.HINTS, days.TYPO):
        if old not in files[rel]:
            raise RuntimeError(f"{rel}: the passage to rewrite is not there: {old[:60]!r}")
        files[rel] = files[rel].replace(old, new, 1)
    return files


def prepare(work: Path) -> str:
    """Write the start into `work` and commit it as ledgerly 0.8.3; returns the commit."""
    for rel, text in start_files().items():
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    repo.git(work, "init", "-q")
    repo.git(work, "add", "-A")
    repo.git(work, "commit", "-q", "-m", "ledgerly 0.8.3")
    return repo.git(work, "rev-parse", "HEAD")


def p50(work: Path):
    """tools/bench.py's p50 for the repository as it is, or None. Its timings are modelled, not clocked."""
    try:
        out = subprocess.run([sys.executable, "tools/bench.py"], cwd=work, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=120, env=QUIET).stdout
    except subprocess.TimeoutExpired:
        return None
    found = P50.search(out)
    return found.group(1) if found else None


measure = p50  # the number day 1 measures, by the name the runner calls for every job


def said(number, text: str) -> bool:
    return bool(number) and bool(re.search(rf"(?<![\d.]){re.escape(number)}(?!\d)", text.replace(",", ".")))


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def tree(work: Path) -> dict:
    """{relative path: text} of the working tree, git and the logs aside."""
    return {p.relative_to(work).as_posix(): read(p) for p in sorted(work.rglob("*"))
            if p.is_file() and not set(p.relative_to(work).parts) & set(SKIP)}


def unreleased(text: str) -> int:
    """The entries under CHANGELOG.md's Unreleased heading."""
    head = re.search(r"^(#+)[^\n]*unreleased[^\n]*$", text, re.I | re.M)
    if not head:
        return 0
    rest = text[head.end():]
    end = re.search(r"^#{1,%d}\s" % len(head.group(1)), rest, re.M)
    return len(re.findall(r"^\s*[-*+]\s+\S", rest[:end.start()] if end else rest, re.M))


def migrations(work: Path) -> dict:
    return {p.name: hashlib.sha1(p.read_bytes()).hexdigest() for p in sorted((work / "migrations").glob("*"))
            if p.is_file()}


def state(work: Path, start: str, baseline=None) -> dict:
    """What day 1 left that day 2 is graded against, and which rules and facts it wrote into the repository: the lines it
    added to any file, and its commit messages."""
    before, now = {rel: set(text.splitlines()) for rel, text in start_files().items()}, tree(work)
    added = "\n".join(line for rel, text in now.items() for line in text.splitlines()
                      if line not in before.get(rel, ()))
    added += "\n" + repo.git(work, "log", "--format=%B", f"{start}..HEAD")
    return {"unreleased": unreleased(now.get("CHANGELOG.md", "")), "migrations": migrations(work),
            "p50": p50(work), "leaks": {k: bool(re.search(v, added, re.I)) for k, v in LEAKS.items()},
            "added": len(added)}


def hidden_checks(work: Path) -> dict:
    try:
        r = subprocess.run([sys.executable, str(HERE / "hidden_checks.py"), str(work)], cwd=work, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=300, env=QUIET)
    except subprocess.TimeoutExpired:
        return {}
    line = next((x for x in reversed(r.stdout.splitlines()) if x.startswith("HIDDEN ")), None)
    return json.loads(line[len("HIDDEN "):]) if line else {"error": [False, (r.stderr or r.stdout)[-300:]]}


def words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def grade(work: Path, day1: dict, finals: dict, tests: bool = True) -> dict:
    """The twelve checks as {check: [passed or None, detail]}, and the score of each group."""
    checks = hidden_checks(work)
    broken = checks.get("error", [False, "the hidden checks timed out"])[1]
    for k in ("T1", "T2", "T3", "C2", "C4"):
        checks.setdefault(k, [False, f"the hidden checks did not run: {broken}"])
    ran = None
    if tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=work,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=QUIET)
        ran = r.returncode == 0
    checks["T4"] = [ran, (r.stdout.strip().splitlines() or [""])[-1][:200] if tests else "not run"]
    perf, today, yesterday = read(work / "docs" / "performance.md"), p50(work), day1["baseline"]
    checks["T5"] = [said(today, perf), f"today's p50 {today} in docs/performance.md"]
    n = unreleased(read(work / "CHANGELOG.md"))
    checks["C1"] = [n > day1["state"]["unreleased"], f"Unreleased entries: {day1['state']['unreleased']} after day 1, "
                                                     f"{n} now"]
    moved = sorted(set(migrations(work).items()) ^ set(day1["state"]["migrations"].items()))
    asked = read(work / "docs" / "db_requests.md")
    checks["C5"] = [not moved and bool(re.search(r"note", asked, re.I)),
                    f"migrations changed: {sorted({k for k, _ in moved})}; docs/db_requests.md: {asked.strip()[:120]!r}"]
    counts = [words(finals.get(k, "")) for k in range(1, len(days.DAY2) + 1)]
    checks["C3"] = [statistics.median(counts) <= SHORT, f"words in day 2's answers: {counts}"]
    tax = read(work / "ledgerly" / "tax.py")
    why = [x.strip() for x in tax.splitlines() if re.search(r"financ", x, re.I)]
    checks["F1"] = [bool(why), why[0][:200] if why else "tax.py does not say why"]
    checks["F2"] = [None if today == yesterday else said(yesterday, perf),
                    f"yesterday's p50 {yesterday} in docs/performance.md (today's is {today}): {perf.strip()[:200]!r}"]
    checks = {k: checks[k] for k in CHECKS}
    score = {g: sum(checks[k][0] is True for k in ks) for g, ks in (("task", TASK), ("rules", RULES),
                                                                     ("memory", MEMORY))}
    return {"checks": checks, **score, "of_memory": sum(checks[k][0] is not None for k in MEMORY), "p50": today,
            "words": counts}
