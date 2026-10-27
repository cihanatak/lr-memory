"""The same tasks with and without COL's surprise reflex, graded the same way.

Each task (bench/tasks/*.py) is a small repository with a failing test and two causes: a real bug where the user
points, and a second one that makes the fix the user asks for fail again the same way. A hidden check passes only when
both are fixed. Every run starts from a fresh copy in a temp folder and runs `claude -p` with your Claude Code login;
the reflex arm loads plugins/col with only the reflex on. Real tokens are spent: a run is roughly 50-300k, most of it
cache reads.

    python bench/run.py --model sonnet --n 3             every task, both arms, three runs each
    python bench/run.py --summary <results folder>       the table again
    python bench/run.py --selftest                       each grader against the task's real fix and a symptom patch
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
COL = ROOT / "plugins" / "col"
sys.path.insert(0, str(COL / "scripts"))
from col import inquiry  # noqa: E402  the reflex's own reading of a check, to count fixes the same way in both arms

TOOLS = "Bash,Read,Glob,Grep,Edit,Write"
TASKS = sorted(p.stem for p in (BENCH / "tasks").glob("*.py") if not p.stem.startswith("_"))
ARMS = ("bare", "reflex")
TOKENS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
LOCK = threading.Lock()


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"bench_task_{name}", BENCH / "tasks" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def remove(path: Path) -> None:
    def retry(func, p, _):  # git keeps its objects read-only on Windows
        os.chmod(p, 0o666)
        func(p)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)


def materialize(t, work: Path, git: bool = True) -> None:
    for rel, text in t.FILES.items():
        f = work / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    if git:
        g = ["git", "-c", "user.name=bench", "-c", "user.email=bench@example.invalid", "-c", "commit.gpgsign=false"]
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "start"]):
            subprocess.run([*g, *args], cwd=work, check=True, capture_output=True)


def digest(work: Path, rels: list) -> dict:
    return {r: hashlib.sha256((work / r).read_bytes()).hexdigest() if (work / r).exists() else None for r in rels}


def grade(t, name: str, work: Path, before: dict) -> dict:
    """Visible: the check the user named passes. Hidden: the task's own check of the cause. Kept: the tests the user
    gave are unchanged. Solved needs all three; a visible pass without the other two is a symptom patch."""
    check = f'"{sys.executable}" {t.CHECK[7:]}' if t.CHECK.startswith("python ") else t.CHECK
    visible = subprocess.run(check, cwd=work, shell=True, capture_output=True, text=True, timeout=300)
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}  # a grader run under pytest
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--hidden", name, str(work)], cwd=work,
                       env=env, capture_output=True, text=True, timeout=300)
    try:
        problems = json.loads(r.stdout) if r.returncode == 0 else [f"hidden check crashed: {r.stderr[-300:]}"]
    except ValueError:
        problems = [f"hidden check printed no verdict: {r.stdout[-200:]}"]
    passed, kept = visible.returncode == 0, digest(work, t.PROTECTED) == before
    return {"visible": passed, "hidden": not problems, "tests_kept": kept, "solved": passed and not problems and kept,
            "symptom_patch": passed and (bool(problems) or not kept), "problems": problems[:5],
            "failure": inquiry.failure(visible.stdout + visible.stderr)}


def _text(content) -> str:
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return str(content or "")


def counts(msgs: list) -> dict:
    """From the run's own record: tool calls, edits, check runs, and fixes that did not hold, read by the reflex's own
    rules (inquiry.step), so both arms are counted alike. asked_at_call is the tool call after which the reflex asked,
    or would have asked in the bare arm."""
    uses, mem, asked_at = {}, {"edits": 0, "checks": {}}, None
    n = {"check_runs": 0, "failed_checks": 0, "failed_fixes": 0, "same_failures": 0}
    for m in msgs:
        content = (m.get("message") or {}).get("content")
        for b in content if isinstance(content, list) else []:
            if not isinstance(b, dict):
                continue
            if m.get("type") == "assistant" and b.get("type") == "tool_use":
                uses[b.get("id")] = (b.get("name", ""), b.get("input") or {})
                continue
            if m.get("type") != "user" or b.get("type") != "tool_result":
                continue
            tool, inp = uses.get(b.get("tool_use_id"), ("", {}))
            err, out = bool(b.get("is_error")), _text(b.get("content"))
            if tool in inquiry.EDIT_TOOLS:
                mem["edits"] += not err
                continue
            command = str(inp.get("command", "")) if tool in ("Bash", "PowerShell") else ""
            if command and inquiry.SHELL_EDIT.search(command) and not err:
                mem["edits"] += 1
            k = inquiry.key(command)
            if not k or (err and not out.startswith("Exit code") and inquiry.NOT_RUN.search(out[:200])):
                continue
            failed = err or bool(inquiry.FAILED.search(out))
            n["check_runs"] += 1
            n["failed_checks"] += failed
            for e in inquiry.step(mem, k, failed, out):
                if e["event"] == "fix_failed":
                    n["failed_fixes"] += 1
                    n["same_failures"] += e["same"]
                    if e["nudge"] and asked_at is None:
                        asked_at = len(uses)
    return {"tool_calls": len(uses), "edits": mem["edits"], **n, "asked_at_call": asked_at}


def environment(args) -> tuple:
    """The command and the environment for claude -p: from --env-module when given (a file with claude_bin() and
    child_env()), else Claude Code on PATH with this environment, unlinked from a parent session."""
    if args.env_module:
        spec = importlib.util.spec_from_file_location("bench_env", args.env_module)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return args.claude or module.claude_bin(), module.child_env()
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE" and not k.startswith("COL_")}
    return args.claude or shutil.which("claude") or "claude", env


def run_one(name: str, arm: str, i: int, args, out: Path) -> dict:
    t = load(name)
    base = Path(tempfile.mkdtemp(prefix=f"lrbench-{name}-{arm}-{i}-"))
    work = base / "repo"
    work.mkdir()
    materialize(t, work)
    before = digest(work, t.PROTECTED)
    claude, env = environment(args)
    env = {k: v for k, v in env.items() if not k.startswith("COL_")}
    if env.get("CLAUDE_CODE_OAUTH_TOKEN") or env.get("ANTHROPIC_API_KEY"):
        env["CLAUDE_CONFIG_DIR"] = str(base / "config")  # the login is in the environment: no plugin of yours loads
    cmd = [claude, "-p", t.PROMPT, "--setting-sources", "project", "--tools", TOOLS, "--allowedTools", TOOLS,
           "--output-format", "stream-json", "--verbose", "--strict-mcp-config", "--no-session-persistence",
           "--max-turns", str(args.max_turns), "--model", args.model]
    if arm == "reflex":  # the reflex alone: COL's other checks stay off, so the arms differ in one thing
        cmd += ["--plugin-dir", str(COL)]
        env.update(COL_DATA=str(base / "col"), COL_CLAIMS="off", COL_PREDICT="off", COL_SECRETS="off",
                   COL_LANG="en", COL_INQUIRY="on")
    start, timed_out = time.time(), False
    try:
        stdout = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=args.timeout).stdout
    except subprocess.TimeoutExpired as e:
        stdout, timed_out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else e.stdout or "", True
    seconds = round(time.time() - start)
    msgs = []
    for line in stdout.splitlines():
        try:
            msgs.append(json.loads(line))
        except ValueError:
            pass
    result = next((m for m in reversed(msgs) if m.get("type") == "result"), {})
    usage = result.get("usage") or {}
    asked = [json.loads(x) for x in (base / "col" / "inquiry.jsonl").read_text(encoding="utf-8").splitlines()] if (
        base / "col" / "inquiry.jsonl").exists() else []
    row = {"task": name, "arm": arm, "model": args.model, "i": i, **grade(t, name, work, before), **counts(msgs),
           "nudges": sum(r.get("event") == "nudge" for r in asked),
           "loosen_notes": sum(r.get("event") == "loosen" for r in asked),
           "turns": result.get("num_turns"), "seconds": seconds, "timed_out": timed_out,
           "tokens": sum(usage.get(k) or 0 for k in TOKENS),
           "new_tokens": sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                                         "output_tokens")),
           "usage": {k: usage.get(k) for k in TOKENS}, "cost_usd": result.get("total_cost_usd"),
           "models": sorted((result.get("modelUsage") or {}).keys()), "final": str(result.get("result", ""))[:600]}
    with LOCK:
        (out / "streams").mkdir(parents=True, exist_ok=True)
        (out / "streams" / f"{name}-{arm}-{i}.jsonl").write_text(stdout, encoding="utf-8")
        with open(out / "results.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if args.keep:
        row["kept"] = str(base)
    else:
        remove(base)
    return row


def summary(rows: list) -> str:
    med = lambda xs: statistics.median(xs) if xs else 0  # noqa: E731
    head = ("| model | task | arm | runs | solved | symptom patch | runs where a fix did not hold | fixes that did not "
            "hold | reflex asked | tokens (median) | new tokens (median) | turns (median) |")
    lines = [head, "|" + "---|" * 12]
    groups = sorted({(r["model"], r["task"]) for r in rows}) + sorted({(r["model"], "all") for r in rows})
    for model, name in groups:
        for arm in ARMS:
            rs = [r for r in rows if r["model"] == model and r["arm"] == arm and name in ("all", r["task"])]
            if not rs:
                continue
            lines.append(f"| {model} | {name} | {arm} | {len(rs)} | {sum(r['solved'] for r in rs)} | "
                         f"{sum(r['symptom_patch'] for r in rs)} | {sum(r['failed_fixes'] > 0 for r in rs)} | "
                         f"{sum(r['failed_fixes'] for r in rs)} | "
                         f"{sum(r['nudges'] for r in rs)} | {med([r['tokens'] for r in rs]):,.0f} | "
                         f"{med([r['new_tokens'] for r in rs]):,.0f} | {med([r['turns'] or 0 for r in rs]):.0f} |")
    return "\n".join(lines)


def selftest() -> int:
    """Each task fails as given; its obvious fix, the one the user asks for, fails again the same way; its real fix
    solves it; a symptom patch passes the visible check and is caught."""
    bad = []
    for name in TASKS:
        t, given = load(name), ""
        for label, change, visible, solved in (("as given", None, False, False), ("obvious fix", t.first, False, False),
                                               ("real fix", t.fix, True, True), ("symptom patch", t.patch, True, False)):
            base = Path(tempfile.mkdtemp(prefix=f"lrbench-self-{name}-"))
            work = base / "repo"
            work.mkdir()
            materialize(t, work, git=False)
            before = digest(work, t.PROTECTED)
            if change:
                change(work)
            g = grade(t, name, work, before)
            given = g["failure"] if label == "as given" else given
            if (g["visible"] != visible or g["solved"] != solved or (label == "symptom patch" and not g["symptom_patch"])
                    or (label == "obvious fix" and not (given and g["failure"] == given))):
                bad.append(f"{name}, {label}: visible {g['visible']}, solved {g['solved']}, {g['problems']}, "
                           f"failure {g['failure'][:120]!r} (as given {given[:120]!r})")
            remove(base)
    print("\n".join(bad) or f"{len(TASKS)} tasks: each fails as given, the obvious fix fails again the same way, the "
                            f"real fix solves it, a symptom patch is caught")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tasks", default=",".join(TASKS))
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=1200, help="seconds per run")
    ap.add_argument("--out", help="results folder (default: a new one in the temp folder)")
    ap.add_argument("--claude", help="the claude command")
    ap.add_argument("--env-module", help="a .py file with claude_bin() and child_env() for the child's login")
    ap.add_argument("--keep", action="store_true", help="keep each run's folder, to look at what it did")
    ap.add_argument("--summary", metavar="FOLDER")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--hidden", nargs=2, metavar=("TASK", "WORK"), help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.hidden:  # a fresh process, so the grader imports the run's code and nothing else
        name, work = args.hidden
        sys.path.insert(0, work)
        print(json.dumps(load(name).hidden(Path(work))))
        return 0
    if args.selftest:
        return selftest()
    if args.summary:
        rows = [json.loads(x) for x in (Path(args.summary) / "results.jsonl").read_text(encoding="utf-8").splitlines()]
        print(summary(rows))
        return 0
    out = Path(args.out or Path(tempfile.gettempdir()) / "lrbench-results" / time.strftime("%Y%m%d-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    plan = [(name, arm, i) for i in range(1, args.n + 1) for name in args.tasks.split(",") for arm in
            args.arms.split(",")]
    print(f"{len(plan)} runs, results in {out}", flush=True)
    with cf.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {pool.submit(run_one, name, arm, i, args, out): (name, arm, i) for name, arm, i in plan}
        for f in cf.as_completed(futures):
            try:
                r = f.result()
                print(f"{r['task']} {r['arm']} #{r['i']}: solved {r['solved']}, fixes not held {r['failed_fixes']}, "
                      f"asked {r['nudges']}, {r['tokens']:,} tokens, {r['seconds']} s {r.get('kept', '')}", flush=True)
            except Exception as e:  # one broken run must not lose the others
                print(f"{futures[f]}: {type(e).__name__}: {e}", flush=True)
    rows = [json.loads(x) for x in (out / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    text = summary(rows)
    (out / "summary.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
