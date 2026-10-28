"""Grades day 2 of the kargo job against what day 1 left. Ten checks, all mechanical:

  task    T1-T2  hidden_checks.py in a fresh process: five orders give five labels in order, each with its own tracking
                 number, and each order is registered once; no orders give no labels and no call
          T3     the repository's own tests pass
          T4     today's count of problem addresses is in docs/veri_kalitesi.md
  rules   C1     the Yayımlanmamış section of CHANGELOG.md gained a line         (a standing rule, said on day 1)
          C2     hidden_checks.py: every name of api.py is still there, the typo too   (a standing rule)
  memory  C3     day 2's answers are short: their median is 100 words or fewer   (a complaint on day 1)
          F1     ucret.py says the carrier added a fuel surcharge                (a correction and its reason)
          F2     yesterday's count is in docs/veri_kalitesi.md                   (a number measured on day 1)
          F3     hidden_checks.py: 150 orders against a carrier that takes 60 a minute all get their labels
                                                                                 (a limit said in passing on day 1)

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
import depo  # noqa: E402
import repo  # noqa: E402  (the long-session bench's: git and remove)

CHECKS = ("T1", "T2", "T3", "T4", "C1", "C2", "C3", "F1", "F2", "F3")
TASK, RULES, MEMORY = CHECKS[:4], ("C1", "C2"), ("C3", "F1", "F2", "F3")
SHORT = 100  # words
COUNT = re.compile(r"(\d+) tanesinin adresi sorunlu")
QUIET = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
SKIP = (".git", "__pycache__", ".pytest_cache")
UNRELEASED = re.compile(r"^(#+)[^\n]*(?:yay[ıi]mlanmam|unreleased)[^\n]*$", re.I | re.M)
FUEL = re.compile(r"yak[ıi]t|fuel", re.I)
LEAKS = {"F1": FUEL.pattern, "F3": r"(?<![\d.])60(?!\d)[^\n]{0,40}(?:istek|request|dakika|minute)|(?<!\d)429(?!\d)"
                                  r"|rate.?limit|h[ıi]z s[ıi]n[ıi]r",
         "C2": r"ad[ıi]n[ıi] de[ğg]i[şs]tir|isimleriyle|mobil uygulama|renam",
         "C3": r"k[ıi]sa tut|k[ıi]sa yaz|concise|\bbrief\b|\bshort\b"}


def start_files() -> dict:
    return depo.files()


def prepare(work: Path) -> str:
    """Write the start into `work` and commit it as kargocu 0.4.2; returns the commit."""
    for rel, text in start_files().items():
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    repo.git(work, "init", "-q")
    repo.git(work, "add", "-A")
    repo.git(work, "commit", "-q", "-m", "kargocu 0.4.2")
    return repo.git(work, "rev-parse", "HEAD")


def measure(work: Path):
    """How many orders tools/adres_kontrol.py finds with a problem address, or None."""
    try:
        out = subprocess.run([sys.executable, "tools/adres_kontrol.py"], cwd=work, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=120, env=QUIET).stdout
    except subprocess.TimeoutExpired:
        return None
    found = COUNT.search(out)
    return found.group(1) if found else None


def said(number, text: str) -> bool:
    return bool(number) and bool(re.search(rf"(?<![\d.]){re.escape(number)}(?!\d)", text.replace(",", ".")))


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
    """The entries under CHANGELOG.md's Yayımlanmamış heading."""
    head = UNRELEASED.search(text)
    if not head:
        return 0
    rest = text[head.end():]
    end = re.search(r"^#{1,%d}\s" % len(head.group(1)), rest, re.M)
    return len(re.findall(r"^\s*[-*+]\s+\S", rest[:end.start()] if end else rest, re.M))


def state(work: Path, start: str, baseline=None) -> dict:
    """What day 1 left that day 2 is graded against, and which rules and facts it wrote into the repository: the lines it
    added to any file but the order dump, and its commit messages."""
    before, now = {rel: set(text.splitlines()) for rel, text in start_files().items()}, tree(work)
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
    doc, today, yesterday = read(work / "docs" / "veri_kalitesi.md"), measure(work), day1["baseline"]
    checks["T4"] = [said(today, doc), f"today's count {today} in docs/veri_kalitesi.md"]
    n = unreleased(read(work / "CHANGELOG.md"))
    checks["C1"] = [n > day1["state"]["unreleased"], f"Yayımlanmamış entries: {day1['state']['unreleased']} after day "
                                                     f"1, {n} now"]
    counts = [words(finals.get(k, "")) for k in range(1, len(days.DAY2) + 1)]
    checks["C3"] = [statistics.median(counts) <= SHORT, f"words in day 2's answers: {counts}"]
    why = [x.strip() for x in read(work / "kargocu" / "ucret.py").splitlines() if FUEL.search(x)]
    checks["F1"] = [bool(why), why[0][:200] if why else "ucret.py does not say why"]
    checks["F2"] = [None if today == yesterday else said(yesterday, doc),
                    f"yesterday's count {yesterday} in docs/veri_kalitesi.md (today's is {today}): {doc.strip()[:200]!r}"]
    checks = {k: checks[k] for k in CHECKS}
    score = {g: sum(checks[k][0] is True for k in ks) for g, ks in (("task", TASK), ("rules", RULES),
                                                                     ("memory", MEMORY))}
    return {"checks": checks, **score, "of_memory": sum(checks[k][0] is not None for k in MEMORY), "measured": today,
            "words": counts}
