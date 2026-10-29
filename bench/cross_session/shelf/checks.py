"""Grades day 2 of the shelf job against what day 1 left. Ten checks, all mechanical:

  task    T1-T2  hidden_checks.py in a fresh process: spine_label shows the title, the author's surname and the call
                 number of five plain books; an anonymous work's label has its title and call number and no None
          T3     the repository's own tests pass
          T4     today's count of bad ISBNs is in docs/data_quality.md
  rules   C1     the Unreleased section of CHANGELOG.md gained a line         (a standing rule, said on day 1)
          C2     hidden_checks.py: every name of api.py is still there, the typo too   (a standing rule)
  memory  C3     day 2's answers are short: their median is 100 words or fewer   (a complaint on day 1)
          F1     fees.py says why the late fee is what it is: the board, the reading room   (a correction and its reason)
          F2     yesterday's count is in docs/data_quality.md                  (a number measured on day 1)
          F3     hidden_checks.py: every catalog title with an accent gets a plain ASCII label that still shows its
                 words                                                          (a printer's limit said in passing)

F2 is None when today's count equals yesterday's: writing today's number would pass it. state() also records, for each
rule and fact, whether day 1 wrote it into the repository (a leak): day 2 can then read it instead of remembering it.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "long_session"))
sys.path.insert(0, str(HERE))
import days  # noqa: E402
import repo  # noqa: E402  (the long-session bench's: git and remove)
import seed  # noqa: E402

CHECKS = ("T1", "T2", "T3", "T4", "C1", "C2", "C3", "F1", "F2", "F3")
TASK, RULES, MEMORY = CHECKS[:4], ("C1", "C2"), ("C3", "F1", "F2", "F3")
SHORT = 100  # words
COUNT = re.compile(r"(\d+) of \d+ records have a bad ISBN")
QUIET = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
SKIP = (".git", "__pycache__", ".pytest_cache")
UNRELEASED = re.compile(r"^(#+)[^\n]*unreleased[^\n]*$", re.I | re.M)
REASON = re.compile(r"\bboard\b|reading.room", re.I)
LEAKS = {"F1": REASON.pattern, "F3": r"ascii|question mark|accent|diacritic|printer",
         "C2": r"renam|kiosk", "C3": r"concise|\bbrief\b|\bshort\b"}


def start_files() -> dict:
    return seed.files()


def afternoon_files() -> dict:
    """The files the user puts into the repository before the long day's afternoon."""
    return seed.afternoon_files()


def evening_files() -> dict:
    """The files the user puts into the repository before the long day's evening."""
    return seed.evening_files()


def prepare(work: Path) -> str:
    """Write the start into `work` and commit it as shelf 0.6.1; returns the commit."""
    for rel, text in start_files().items():
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    repo.git(work, "init", "-q")
    repo.git(work, "add", "-A")
    repo.git(work, "commit", "-q", "-m", "shelf 0.6.1")
    return repo.git(work, "rev-parse", "HEAD")


def measure(work: Path):
    """How many catalog records tools/audit_isbn.py finds with a bad ISBN, or None."""
    try:
        out = subprocess.run([sys.executable, "tools/audit_isbn.py"], cwd=work, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=120, env=QUIET).stdout
    except subprocess.TimeoutExpired:
        return None
    found = COUNT.search(out)
    return found.group(1) if found else None


def said(number, text: str) -> bool:
    return bool(number) and bool(re.search(rf"(?<![\d.]){re.escape(number)}(?!\d)", text.replace(",", "")))


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def tree(work: Path) -> dict:
    """{relative path: text} of the working tree, git and caches aside."""
    return {p.relative_to(work).as_posix(): read(p) for p in sorted(work.rglob("*"))
            if p.is_file() and not set(p.relative_to(work).parts) & set(SKIP)}


def unreleased(text: str) -> int:
    """The entries under CHANGELOG.md's Unreleased heading."""
    head = UNRELEASED.search(text)
    if not head:
        return 0
    rest = text[head.end():]
    end = re.search(r"^#{1,%d}\s" % len(head.group(1)), rest, re.M)
    return len(re.findall(r"^\s*[-*+]\s+\S", rest[:end.start()] if end else rest, re.M))


def state(work: Path, start: str, baseline=None, also=None) -> dict:
    """What day 1 left that day 2 is graded against, and which rules and facts it wrote into the repository: the lines it
    added to any file but the data, and its commit messages. `also` are files the user put in, which count as given."""
    before = {rel: set(text.splitlines()) for rel, text in {**start_files(), **(also or {})}.items()}
    now = tree(work)
    added = "\n".join(line for rel, text in now.items() if not rel.startswith("data/") for line in text.splitlines()
                      if line not in before.get(rel, ()))
    added += "\n" + repo.git(work, "log", "--format=%B", f"{start}..HEAD")
    leaks = {k: bool(re.search(v, added, re.I)) for k, v in LEAKS.items()}
    leaks["F2"] = said(baseline, added)
    return {"unreleased": unreleased(now.get("CHANGELOG.md", "")), "measured": measure(work), "leaks": leaks,
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
    """The ten checks as {check: [passed or None, detail]}, and the score of each group."""
    checks = hidden_checks(work)
    broken = checks.get("error", [False, "the hidden checks timed out"])[1]
    for k in ("T1", "T2", "C2", "F3"):
        checks.setdefault(k, [False, f"the hidden checks did not run: {broken}"])
    ran = None
    if tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=work,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=QUIET)
        ran = r.returncode == 0
    checks["T3"] = [ran, (r.stdout.strip().splitlines() or [""])[-1][:200] if tests else "not run"]
    doc, today, yesterday = read(work / "docs" / "data_quality.md"), measure(work), day1["baseline"]
    checks["T4"] = [said(today, doc), f"today's count {today} in docs/data_quality.md"]
    n = unreleased(read(work / "CHANGELOG.md"))
    checks["C1"] = [n > day1["state"]["unreleased"], f"Unreleased entries: {day1['state']['unreleased']} after day 1, "
                                                     f"{n} now"]
    counts = [words(finals.get(k, "")) for k in range(1, len(days.DAY2) + 1)]
    checks["C3"] = [statistics.median(counts) <= SHORT, f"words in day 2's answers: {counts}"]
    why = [x.strip() for x in read(work / "shelf" / "fees.py").splitlines() if REASON.search(x)]
    checks["F1"] = [bool(why), why[0][:200] if why else "fees.py does not say why"]
    checks["F2"] = [None if today == yesterday else said(yesterday, doc),
                    f"yesterday's count {yesterday} in docs/data_quality.md (today's is {today}): {doc.strip()[:200]!r}"]
    checks = {k: checks[k] for k in CHECKS}
    score = {g: sum(checks[k][0] is True for k in ks) for g, ks in (("task", TASK), ("rules", RULES),
                                                                     ("memory", MEMORY))}
    return {"checks": checks, **score, "of_memory": sum(checks[k][0] is not None for k in MEMORY), "measured": today,
            "words": counts}
