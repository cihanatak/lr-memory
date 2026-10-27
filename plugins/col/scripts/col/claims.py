"""Claim check at Stop: what the final message says against what exists and what ran. Zero model tokens.

A model closing a task often says more than it did, and a second model reading the transcript catches that barely
better than chance (AUROC at most 0.65 where it was measured); checks against the disk and the tool output do the
work. So the final message's checkable claims are checked: a commit it names must exist, a file it cites must be on
disk, a test count it gives must appear in real test output, "done, I fixed it" needs a tool run in the turn, and
"committed" needs a commit. What cannot be checked is left alone: no commit is looked up when no repository is in
reach, and a path the message says is gone is not looked for.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from glob import escape, glob
from pathlib import Path

# git ids; one counts only when it holds a digit and a letter and sits near the word commit
HEX = re.compile(r"(?<![\w#/.-])([0-9a-f]{7,40})(?![\w-])")
# an absolute path cited in backticks: a drive (C:\ or D:/), the home folder (~/), a Git Bash drive (/c/) or a Unix
# folder that holds files; "/api/v1/health" and slash commands are not paths
CODE_PATH = re.compile(r"`((?:[A-Za-z]:[\\/]|~[\\/]|/(?:home|Users|tmp|var|opt|etc|usr|srv|mnt|workspace|[A-Za-z])/)"
                       r"[^`<>|*?\n]+)`")
MD_LINK = re.compile(r"\]\(<?([^)\s>]+)>?\)")
GONE_AFTER = re.compile(r"\b(?:yok|silindi|silinmiş|kaldırıldı|bulunamadı|bulunmuyor|oluşmadı|yazılmadı|olmayan|"
                        r"değil|not found|missing|deleted|removed|no longer|does not exist|doesn't exist|was moved|"
                        r"is gone|not created|not written)", re.I)
GONE_BEFORE = re.compile(r"\b(?:deleted|removed|dropped|deleting|removing|sildim|kaldırdım|silinen|kaldırılan)\b"
                         r"[^`\n]{0,20}$", re.I)
TEST_CLAIM = re.compile(
    r"\b(\d{1,5})\s+(?:yeni\s+)?test\w*\s+(?:geçti|geçiyor|geçer|başarılı)"
    r"|\b\d{1,5}\s+test\w*\s+(\d{1,5})'\w+\s+(?:geçti|geçiyor|başarılı)"
    r"|\b(\d{1,5})\s+(?:of|out of)\s+\d{1,5}\s+(?:tests?|specs?)\s+(?:passed|pass)"
    r"|\b(\d{1,5})(?:\s*/\s*\d{1,5})?\s+(?:new\s+|unit\s+|integration\s+|e2e\s+)?(?:tests?|specs?)\s+"
    r"(?:passed|pass|passing|are\s+passing|succeeded|green)\b"
    r"|\ball\s+(\d{1,5})\s+(?:tests?|specs?)\s+(?:passed|pass|passing)\b"
    r"|\b(\d{1,5})\s+passed\b", re.I)
# a count that is quoted, denied or only asked about is no claim. A real answer to a block read "I have no evidence
# that ... 12 tests passed", then "I'm withdrawing the claim that 12 tests passed", and both were blocked again.
DENIED_BEFORE = re.compile(r"\b(?:claim(?:ed|ing)?|saying|said|statement|line|wrote)\s+that\s+$"
                           r"|\bno (?:evidence|proof|test output|record)\b"
                           r"|\b(?:can(?:not|'t)|could(?: not|n't)|did(?: not|n't)|ha(?:ve|s)(?: not|n't)|never)\s+"
                           r"(?:\w+\s+){0,2}?(?:confirm|verif|show|run|ran|check|see|seen|measur)\w*"
                           r"|\b(?:whether|if|unless)\b[^,;]*$|\bnot\s+$", re.I)
DENIED_AFTER = re.compile(r"^[\s\"'`)*]*(?:\?|(?:is|was|were)\s+(?:not|false|wrong|untrue)\b|iddia\w*|ifade\w*|"
                          r"diyemem|doğru değil)", re.I)
# how runners print N passing tests: "6 passed" (pytest, vitest, jest, playwright, cargo), "6 passing" (mocha),
# "pass 6" (node --test, TAP), "Passed: 6" (dotnet), "Ran 6 tests in 0.1s / OK" (unittest)
PASSED = (r"(?<![\d.]){n} (?:passed|passing|pass)\b", r"\bpass(?:ed)?:?\s+{n}(?!\d)",
          r"\bRan {n} tests? in [\d.]+s\s+OK\b")
DONE_HEAD = re.compile(r"\b(?:tamam|tamamlandı|bitti|hazır|yaptım|done|finished|completed|all set)\b", re.I)
DID_WORK = re.compile(r"\b(?:düzelttim|ekledim|kurdum|yazdım|güncelledim|kaldırdım|değiştirdim|commit'?ledim|"
                      r"oluşturdum|sildim|gönderdim|yayınladım|yükledim|"
                      r"fixed|added|implemented|committed|updated|removed|created|wrote|changed|deleted|installed|"
                      r"refactored|pushed|deployed|published|shipped|released|merged|uploaded)\b", re.I)
# work done before this turn: "it was already committed", "önceki turda düzelttim"
EARLIER = re.compile(r"\b(?:earlier|previous(?:ly)?|already|last turn|önceki|zaten|daha önce|az önce|demin)\b", re.I)
COMMIT_CLAIM = re.compile(r"commit'?le(?:n)?di|commit'?ledim|\bcommitted\b", re.I)
NOT_YET = re.compile(r"\b(?:not|nothing|never|yet|will|to be|ready|once|if|after|before|should|can|could|would)\b"
                     r"|n't", re.I)
GIT_PLACE = re.compile(r"(?:\bcd\s+|\bgit\s+-C\s+|\bSet-Location\s+(?:-Path\s+)?)[\"']?([^\s\"';&|)]+)", re.I)
COMMIT_RUN = re.compile(r"\bgit\b[^|;&\n]*\bcommit\b")


def tests_passed(n: str, results: str) -> bool:
    return any(re.search(p.format(n=n), results, re.I) for p in PASSED)


def _local(p: str) -> str:
    p = os.path.expanduser(p.strip().strip("'\""))
    if os.name == "nt":  # Git Bash writes /c/Users for C:/Users
        p = re.sub(r"^/([A-Za-z])/", lambda m: f"{m.group(1).upper()}:/", p)
    return p


def _toplevel(p: str, cwd: str) -> str | None:
    path = Path(_local(p))
    if not path.is_absolute():
        if not cwd:
            return None
        path = Path(cwd) / path
    for d in (path, *path.parents):
        if (d / ".git").exists():
            return str(d)
    return None


def repos(cwd: str, calls: list, paths: list) -> list:
    """Where a commit the message names may live: the working folder's repository and the ones right under it, any
    repository a tool call of the turn worked in, any the message cites, and the folders COL_REPOS names."""
    if not shutil.which("git"):
        return []
    places = [cwd] if cwd else []
    for c in calls:
        inp = c.get("input") or {}
        places += [str(inp[k]) for k in ("file_path", "notebook_path") if inp.get(k)]
        places += GIT_PLACE.findall(str(inp.get("command", "")))
    found = {top for top in (_toplevel(p, cwd) for p in [*places, *paths]) if top}
    if cwd:
        found.update(str(Path(g).parent) for g in glob(os.path.join(escape(cwd), "*", ".git")))
    for pattern in os.environ.get("COL_REPOS", "").split(os.pathsep):
        if pattern.strip():
            found.update(p for p in glob(os.path.expanduser(pattern.strip())) if (Path(p) / ".git").exists())
    return sorted(found)


def commit_exists(h: str, where: list) -> bool:
    for r in where:
        try:
            if subprocess.run(["git", "-C", r, "rev-parse", "--verify", "--quiet", f"{h}^{{commit}}"],
                              capture_output=True, timeout=5).returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            continue
    return False


def cited_commits(final: str) -> set:
    """Ids the message itself calls a commit ("commit 7b6c5df", "7b6c5df commit'i")."""
    out = set()
    for m in HEX.finditer(final):
        tok = m.group(1)
        if not (re.search(r"\d", tok) and re.search(r"[a-f]", tok)):
            continue
        near = final[max(0, m.start() - 25): m.start()] + " " + final[m.end(): m.end() + 12]
        if "commit" in near.lower():
            out.add(tok)
    return out


def listed_commits(final: str, where: list) -> set:
    """Any id in the message that resolves to a real commit. The id behind "committed" can sit in a list after the
    word ("committed (0426749, b4738b6)"), and a short id can be all digits; only a real commit counts, so a plain
    number cannot pass for one."""
    return {m.group(1) for m in list(HEX.finditer(final))[:8] if commit_exists(m.group(1), where)}


def commit_claim(final: str) -> str:
    """The words that say something was committed, unless they say it was not, or not yet."""
    for m in COMMIT_CLAIM.finditer(final):
        if not NOT_YET.search(final[max(0, m.start() - 25): m.start()]):
            return m.group(0)
    return ""


def cited_paths(final: str, cwd: str, memory: str, calls: list) -> dict:
    """Paths the message cites in backticks or as link targets: each with where it was found, or "" when it was not.

    A relative link counts as present when it resolves under the working folder, one of its parents or the
    project's memory folder (links are written relative to whichever pane opens them), or names a file a tool of
    this turn wrote."""
    touched = [str((c.get("input") or {}).get(k, "")).replace("\\", "/") for c in calls
               for k in ("file_path", "notebook_path") if (c.get("input") or {}).get(k)]
    roots = ([Path(cwd), *Path(cwd).parents] if cwd else []) + ([Path(memory)] if memory else [])
    out = {}
    for m in [*CODE_PATH.finditer(final), *MD_LINK.finditer(final)]:
        raw = m.group(1).strip().rstrip(".,;:'\"")
        if (raw.startswith(("http:", "https:", "#", "mailto:", "file:", "data:")) or "..." in raw
                or any(ch in raw for ch in "<>{}*…$")):
            continue
        if (GONE_AFTER.search(final[m.end(): m.end() + 45])
                or GONE_BEFORE.search(final[max(0, m.start() - 40): m.start()])):
            continue
        path = _local(re.sub(r"(?::\d+(?:-\d+)?|#L?\d+(?:-L?\d+)?)$", "", raw).replace("%20", " "))
        if os.path.isabs(path) or re.match(r"^[A-Za-z]:[\\/]", path):
            out[raw] = path if os.path.exists(path) else ""
            continue
        hit = next((str(r / path) for r in roots if (r / path).exists()), "")
        tail = "/" + path.replace("\\", "/").lstrip("./")
        out[raw] = hit or (path if any(t.endswith(tail) for t in touched) else "")
    return out


def check(final: str, turn: dict, results, cwd: str, memory: str = "") -> list:
    """What a reader of `final` would be misled by, as {kind, what[, n]}; empty when every checkable claim holds.
    `results` returns the session's recent tool output; it is read only when a test count needs it."""
    problems = []
    calls = turn["calls"]
    cited = cited_paths(final, cwd, memory, calls)
    problems += [{"kind": "path", "what": raw} for raw, found in sorted(cited.items()) if not found]
    found_paths = [p for p in cited.values() if p]
    hashes, where = cited_commits(final), None
    if hashes:
        where = repos(cwd, calls, found_paths)
        problems += [{"kind": "commit", "what": h} for h in sorted(hashes) if where and not commit_exists(h, where)]
    for m in TEST_CLAIM.finditer(final):
        before = re.split(r"[.!?\n]", final[max(0, m.start() - 160): m.start()])[-1]
        if DENIED_BEFORE.search(before) or DENIED_AFTER.match(final[m.end(): m.end() + 30]):
            continue
        n = next(g for g in m.groups() if g)
        if not tests_passed(n, results() if callable(results) else results):
            problems.append({"kind": "tests", "what": m.group(0).strip(), "n": n})
    earlier = EARLIER.search(final)
    if not calls and not earlier and DONE_HEAD.search(final[:200]) and DID_WORK.search(final):
        problems.append({"kind": "no-tools", "what": ""})
    claim = commit_claim(final)
    ran = any(COMMIT_RUN.search(str((c.get("input") or {}).get("command", ""))) for c in calls)
    if claim and not hashes and not earlier and not ran:
        where = repos(cwd, calls, found_paths) if where is None else where
        if not (where and listed_commits(final, where)):
            problems.append({"kind": "commit-claim", "what": claim})
    return problems
