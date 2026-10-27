"""The surprise reflex: a fix that does not hold is named at once. A check (tests, a build, a type check, a linter)
fails, a file is edited, and the same check fails again the same way: the edit rested on a wrong idea of the cause.
COL then asks for two explanations that both fit, one of them that nothing in the edited code is wrong (a stale copy
or cache, the environment, another file being run, a wrong test), and for one command that tells them apart. Once per
failing check, from the tool results alone; no model is asked."""
from __future__ import annotations

import re
import statistics

from col import common
from col.text import t

# a command that checks the code; its key keeps the tool and the files it names, so "-x" or "| tail" hide no rerun
CHECK = re.compile(r"\b(pytest|unittest|vitest|jest|mocha|tsc|playwright test|node --test|"
                   r"cargo (?:test|build|check|clippy)|go (?:test|build|vet)|"
                   r"(?:npm|pnpm|yarn) (?:run )?(?:test|build|lint|typecheck|check)\b|dotnet (?:test|build)|"
                   r"mvn|gradle|ruff|mypy|eslint|flake8|pyright)\b")
TARGET = re.compile(r"[\w./\\-]*(?:test|spec)[\w./\\-]*|[\w./\\-]+\.(?:py|tsx?|jsx?|go|rs)\b")
# a command piped into tail exits 0 even when its tests fail, so the output is read too
FAILED = re.compile(r"\b[1-9]\d* (?:failed|errors?)\b|^FAILED\b|\berror TS\d+|npm ERR!|Tests?:\s+[1-9]\d* failed|"
                    r"Traceback \(most recent call last\)|Build failed|error\[E\d+\]|test result: FAILED|"
                    r"^Exit code [1-9]", re.M)
# what names a failure: the failing tests and the error lines, whole; the same text after an edit is the same failure
FAILURE = re.compile(r"^(?:(?:FAILED|ERROR) \S+.*|E {3}.+|.*error TS\d+.*|\s*[✗×] .+|\s*\w+Error: .+)", re.M)
NAMED = re.compile(r"(?:FAILED|ERROR) \S")  # pytest's short summary names each failing test, whatever was cut away
NOISE = re.compile(r"\x1b\[[0-9;]*m|\s*\(?\d+(?:\.\d+)?\s?m?s\)?\s*$|\s*\[\s*\d+%\]\s*$")  # colour, timings, progress
NOT_RUN = re.compile(r"hook|denied|permission|interrupted|rejected", re.I)  # a refusal: nothing ran
SHELL_EDIT = re.compile(r"\bsed -i\b|\bgit (?:apply|checkout|restore|stash|reset)\b|\bapply_patch\b|write_text\(|"
                        r"open\([^)]*['\"]w|\bcat\s*>|\btee\s|Set-Content|Out-File|"
                        r">\s*[\w./\\-]+\.(?:py|tsx?|jsx?|json|toml|ya?ml|cfg|ini|env)\b")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
TEST_FILE = re.compile(r"(?:^|/)(?:tests?|__tests__|spec)/|(?:^|/)test_[^/]*\.py$|_test\.(?:py|go)$|"
                       r"\.(?:test|spec)\.[jt]sx?$|(?:^|/)conftest\.py$")
# ways to quiet a failing test without making the code right
LOOSEN = ("pytest.mark.skip", "pytest.skip(", "xfail", "unittest.skip", ".skip(", "approx(", "abs_tol", "rel_tol",
          "except Exception", "except:", "# noqa", "# type: ignore", "@ts-ignore", "@ts-expect-error",
          "eslint-disable")
OPEN_CHECKS = 20


def key(command: str) -> str:
    """The check a command runs, or '' when it runs none."""
    m = CHECK.search(command)
    if not m:
        return ""
    targets = sorted(set(TARGET.findall(command[m.end():])))
    return " ".join([m.group(1), *targets])[:160]


def failure_lines(output: str) -> list:
    """What names a failure, the same however much of the output was shown (`| tail -3` or `| tail -40`): the failing
    tests when the runner names them, else every error line."""
    text = NOISE.sub("", output) if "\x1b" in output else output
    found = {x for x in (NOISE.sub("", y).strip()[:120] for y in FAILURE.findall(text)) if x}
    return sorted({x for x in found if NAMED.match(x)} or found)[:30]


def failure(output: str) -> str:
    return " | ".join(failure_lines(output))[:400]


def _targets(k: str) -> set:
    return set(k.split(" ")[1:])


def _open(checks: dict, k: str, failed: bool) -> str:
    """The open check a run belongs to. A failing run continues the same command, or the same tool run on every file
    or on some of the same files; a passing run closes the same command, the checks whose files it ran, or, naming no
    file, every open check of its tool."""
    if k in checks:
        return k
    tool, mine = k.split(" ")[0], _targets(k)
    for other in reversed(list(checks)):
        theirs = _targets(other)
        if other.split(" ")[0] == tool and (not mine or (theirs and theirs <= mine) or
                                            (failed and (not theirs or mine & theirs))):
            return other
    return ""


def step(mem: dict, k: str, failed: bool, out: str) -> list:
    """One check run against the open checks, with nothing logged or said; the bench counts with it too. Returns the
    events it ends in: "passed" for a check that passes now, "fix_failed" for one that still fails after an edit,
    with "nudge" set when the reflex asks."""
    checks, edits, events = mem["checks"], mem["edits"], []
    if not failed:
        while o := _open(checks, k, False):
            c = checks.pop(o)
            events.append({"event": "passed", "check": o, "fixes_failed": c["fixes_failed"], "nudged": c["nudged"],
                           "quiet": edits == c["edits_at"],
                           "edits_after_nudge": edits - c["nudge_at"] if c["nudged"] else None})
        return events
    lines, o = failure_lines(out), _open(checks, k, True)
    c = checks.get(o)
    if c and o != k and lines and c.get("lines") and not set(lines) & set(c["lines"]):
        c = None  # the same tool, but other tests fail: a check of its own
    if c is None:
        checks[k] = {"lines": lines, "edits_at": edits, "fixes_failed": 0, "nudged": False, "nudge_at": 0}
        for old in list(checks)[:-OPEN_CHECKS]:
            del checks[old]
        return events
    if edits == c["edits_at"]:  # run again with nothing changed: no fix was tried
        c["lines"] = sorted(set(c.get("lines") or []) | set(lines))[:30]
        return events
    c["fixes_failed"] += 1
    same = bool(lines) and set(lines) <= set(c.get("lines") or [])
    c.update(lines=lines, edits_at=edits)
    nudge = not c["nudged"] and (same or c["fixes_failed"] >= 2)
    if nudge:
        c.update(nudged=True, nudge_at=edits)
    events.append({"event": "fix_failed", "check": o, "same": same, "nudge": nudge,
                   "fixes_failed": c["fixes_failed"], "failure": " | ".join(lines)[:400]})
    return events


def _output(response) -> str:
    if isinstance(response, dict):
        return "\n".join(str(response.get(k) or "") for k in ("stdout", "stderr", "output", "error"))
    return str(response or "")


def _texts(tool: str, inp: dict) -> tuple:
    """What an edit removed and what it put in; a Write's old text is not known, so it adds nothing here."""
    if tool == "Edit":
        return str(inp.get("old_string", "")), str(inp.get("new_string", ""))
    if tool == "MultiEdit":
        edits = [e for e in inp.get("edits") or [] if isinstance(e, dict)]
        return (" ".join(str(e.get("old_string", "")) for e in edits),
                " ".join(str(e.get("new_string", "")) for e in edits))
    return "", ""


def _loosening(sid: str, mem: dict, tool: str, inp: dict, lang: str) -> str:
    path = str(inp.get("file_path") or inp.get("notebook_path") or "").replace("\\", "/")
    failing = [k for k, c in mem["checks"].items() if not c.get("loosen")]
    if not failing or not TEST_FILE.search(path):
        return ""
    old, new = _texts(tool, inp)
    added = [m for m in LOOSEN if m in new and m not in old]
    if not added:
        return ""
    for k in failing:
        mem["checks"][k]["loosen"] = True
    common.log("inquiry", {"session": sid, "event": "loosen", "check": failing[0], "file": path[-120:],
                           "added": added[:5]})
    return t(lang, "inq_loosen", what=", ".join(f"'{m}'" for m in added[:3]), check=failing[0])


def _check(sid: str, mem: dict, k: str, failed: bool, out: str, lang: str) -> str:
    note = ""
    for e in step(mem, k, failed, out):
        if e["event"] == "passed":
            common.log("inquiry", {"session": sid, **e})
        elif e["nudge"]:
            common.log("inquiry", {"session": sid, "event": "nudge", "check": e["check"],
                                   "why": "same" if e["same"] else "again", "fixes_failed": e["fixes_failed"],
                                   "failure": e["failure"][:200]})
            head = (t(lang, "inq_same", check=k, failure=e["failure"][:160]) if e["same"]
                    else t(lang, "inq_again", check=k, n=e["fixes_failed"]))
            note = head + " " + t(lang, "inq_ask")
    return note


def after_tool(data: dict, failed_call: bool) -> str:
    """Called after a tool call (PostToolUse) and after a failed one (PostToolUseFailure); returns what to tell the
    model, or ''."""
    tool, inp, sid = data.get("tool_name", ""), data.get("tool_input") or {}, data.get("session_id", "")
    if not sid or not isinstance(inp, dict) or tool not in (*EDIT_TOOLS, "Bash", "PowerShell"):
        return ""
    state = common.load_state(sid)
    mem = state.setdefault("inquiry", {"edits": 0, "checks": {}})
    lang = common.lang(stored=state.get("lang", ""))
    note = ""
    if tool in EDIT_TOOLS:
        if not failed_call:
            mem["edits"] += 1
            note = _loosening(sid, mem, tool, inp, lang)
    else:
        command = str(inp.get("command", ""))
        out = str(data.get("error") or "") if failed_call else _output(data.get("tool_response"))
        refused = failed_call and (data.get("is_interrupt") or (not out.startswith("Exit code")
                                                                 and NOT_RUN.search(out[:200])))
        if SHELL_EDIT.search(command) and not failed_call:
            mem["edits"] += 1
        k = key(command)
        if k and not refused:
            note = _check(sid, mem, k, failed_call or bool(FAILED.search(out)), out, lang)
    common.save_state(sid, state)
    return note


def summary(rows: list) -> dict:
    """For the report: how often a fix did not hold, and what came of the question."""
    nudges = [r for r in rows if r.get("event") == "nudge"]
    passed = [r for r in rows if r.get("event") == "passed" and r.get("nudged")]
    after = [r["edits_after_nudge"] for r in passed if isinstance(r.get("edits_after_nudge"), int)]
    return {"nudges": len(nudges), "passed": len(passed), "edits": statistics.median(after) if after else 0,
            "loosen": sum(r.get("event") == "loosen" for r in rows),
            "quiet": sum(r.get("event") == "passed" and bool(r.get("quiet")) for r in rows)}
