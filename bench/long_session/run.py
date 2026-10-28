"""The long-session bench: one scripted job of ten messages in three arms (DESIGN.md says why and how).

    python bench/long_session/run.py --selftest                     every grader on a scripted session, no model
    python bench/long_session/run.py --pilot --env-module <file>    arms B and C, messages 1-5, once each, and the
                                                                    projected cost of the main runs
    python bench/long_session/run.py --n 3 --env-module <file>      every arm three times, each run followed by a next
                                                                    session with LR Memory and one without
    python bench/long_session/run.py --summary <results folder>     the tables again

Each run gets a fresh copy of the repository (repo.py), its own config folder and git identity, and the messages of
script.py one at a time over stream-json. The login must come in the environment (CLAUDE_CODE_OAUTH_TOKEN or
ANTHROPIC_API_KEY), because each run's config folder starts empty. Real tokens are spent: a full run is several
million, most of them cache reads.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import importlib.util
import json
import queue
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LRM = ROOT / "plugins" / "lr-memory"
sys.path.insert(0, str(HERE))
import grade  # noqa: E402
import repo  # noqa: E402
import script  # noqa: E402

TOOLS = "Bash,Read,Edit,Write,Glob,Grep,Skill,TaskCreate,TaskUpdate,TaskList,TaskGet"  # no TodoWrite under -p
ARMS = {"A": "1M window", "B": "small window", "C": "small window, LR Memory"}
TOKENS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
DESIGN_TOKENS = 79_000_000  # DESIGN.md's estimate for the main runs and the next sessions
NEXT_TOKENS = 250_000  # and for one next session
GITCONFIG = ("[user]\n\tname = ledgerly dev\n\temail = dev@ledgerly.invalid\n[commit]\n\tgpgsign = false\n"
             "[core]\n\tautocrlf = false\n")
LOCK = threading.Lock()


def environment(args) -> tuple:
    """claude and its environment, found as bench/run.py finds them (--env-module, else Claude Code on PATH)."""
    spec = importlib.util.spec_from_file_location("bench_run", ROOT / "bench" / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    claude, env = module.environment(args)
    if not (env.get("CLAUDE_CODE_OAUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")):
        raise SystemExit("each run starts from an empty config folder, so the login must be in the environment: "
                         "pass --env-module")
    return claude, env


def child(env: dict, base: Path, lr: bool) -> dict:
    """The run's own config folder and git identity. LR Memory keeps its data in the run's folder with its background
    passes off: they would start a claude -p of their own, outside the run's count."""
    env = {k: v for k, v in env.items() if not k.startswith(("COL_", "LR_MEMORY_"))}
    (base / "gitconfig").write_text(GITCONFIG, encoding="utf-8")
    env.update(CLAUDE_CONFIG_DIR=str(base / "config"), GIT_CONFIG_GLOBAL=str(base / "gitconfig"),
               GIT_CONFIG_NOSYSTEM="1")
    if lr:
        env.update(LR_MEMORY_DATA=str(base / "lrdata"), LR_MEMORY_LANG="en", LR_MEMORY_NO_SPAWN="1")
    return env


def command(claude: str, args, window: str, lr: bool) -> list:
    cmd = [claude, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
           "--model", args.model, "--autocompact", window, "--setting-sources", "project", "--strict-mcp-config",
           "--tools", TOOLS, "--allowedTools", TOOLS]
    return cmd + ["--plugin-dir", str(LRM)] if lr else cmd


def kill(p) -> None:
    if sys.platform == "win32":  # claude's own children (bash, git, python) go with it
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    else:
        p.kill()


def session(cmd: list, cwd: Path, env: dict, messages, turn_timeout: int, log: Path) -> tuple:
    """Send the messages one at a time, each when the previous turn has ended. Returns every event, tagged with the
    number of the message it answers, and each turn's status: ok, timeout or exited."""
    events, turns = [], []
    with open(log, "w", encoding="utf-8") as err:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
                             text=True, encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
        lines = queue.Queue()

        def pump():
            for line in p.stdout:
                lines.put(line)
            lines.put(None)
        threading.Thread(target=pump, daemon=True).start()
        try:
            for n, text in enumerate(messages, 1):
                start, status = time.time(), "timeout"
                try:
                    p.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": [
                        {"type": "text", "text": text}]}}) + "\n")
                    p.stdin.flush()
                except OSError:
                    turns.append({"n": n, "status": "exited", "seconds": 0})
                    break
                while time.time() - start < turn_timeout:
                    try:
                        line = lines.get(timeout=5)
                    except queue.Empty:
                        continue
                    if line is None:
                        status = "exited"
                        break
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    e["_turn"] = n
                    events.append(e)
                    if e.get("type") == "result":
                        status = "ok"
                        break
                turns.append({"n": n, "status": status, "seconds": round(time.time() - start)})
                if status != "ok":
                    break
            p.stdin.close()
            p.wait(timeout=120)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        finally:
            if p.poll() is None:
                kill(p)
    return events, turns


def answers(events: list) -> dict:
    """What the model wrote in answer to each message: its text blocks and the turn's result."""
    out = {}
    for e in events:
        n = e.get("_turn")
        if e.get("type") == "assistant":
            out[n] = out.get(n, "") + "".join(b.get("text", "") + "\n" for b in (e.get("message") or {}).get(
                "content") or [] if isinstance(b, dict) and b.get("type") == "text")
        elif e.get("type") == "result":
            out[n] = out.get(n, "") + str(e.get("result") or "")
    return out


def metrics(events: list) -> dict:
    """Tokens and the shape of a session, from its own events. Each model call counts once (by message id): its input,
    cache writes, cache reads and output. A compaction's own call is in none of those; it counts as the context it
    read and the context it left (pre_tokens and post_tokens of compact_metadata)."""
    usage, order, compactions, read_in, rereads, seen = {}, [], [], {}, 0, set()
    for e in events:
        if e.get("type") == "system" and e.get("subtype") == "compact_boundary":
            meta = e.get("compact_metadata") or {}
            compactions.append({"call": len(order), "turn": e.get("_turn"), "trigger": meta.get("trigger"),
                                "pre": meta.get("pre_tokens") or 0, "post": meta.get("post_tokens") or 0})
        if e.get("type") != "assistant" or e.get("parent_tool_use_id"):
            continue
        m = e.get("message") or {}
        mid = m.get("id") or f"call-{len(order)}"
        if mid not in usage:
            order.append(mid)
        usage[mid] = m.get("usage") or {}
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Read" and b.get(
                    "id") not in seen:
                seen.add(b.get("id"))
                path = str((b.get("input") or {}).get("file_path", ""))
                rereads += path in read_in and read_in[path] < len(compactions)
                read_in[path] = len(compactions)
    context = [sum(usage[m].get(k) or 0 for k in TOKENS[:3]) for m in order]
    output = [usage[m].get("output_tokens") or 0 for m in order]
    by_kind = {k: sum(usage[m].get(k) or 0 for m in order) for k in TOKENS}
    by_kind["compaction"] = sum(c["pre"] + c["post"] for c in compactions)
    after = [sum(context[i] + output[i] for i in range(c["call"], min(c["call"] + 10, len(order))))
             for c in compactions]
    results = [e.get("usage") or {} for e in events if e.get("type") == "result"]
    return {"tokens": sum(by_kind.values()), "by_kind": by_kind, "calls": len(order), "compactions": compactions,
            "peak_context": max(context, default=0),
            "floors": [context[c["call"]] for c in compactions if c["call"] < len(context)], "rereads": rereads,
            "after_compaction": after, "context": context, "output": output,
            "result_tokens": sum(sum(u.get(k) or 0 for k in TOKENS) for u in results)}


def save(out: Path, name: str, events: list) -> None:
    with open(out / "streams" / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def next_session(arm: str, i: int, base: Path, args, claude: str, env: dict, revert, out: Path, lr: bool) -> dict:
    """A fresh session the next day, in a copy of the run's config folder and repository, asked three questions about
    the long session."""
    tag = "lr" if lr else "bare"
    folder = base / f"next-{tag}"
    shutil.copytree(base / "config", folder / "config")
    shutil.copytree(base / "work", folder / "work")
    events, turns = session(command(claude, args, "1M", lr), folder / "work", child(env, folder, lr),
                            [script.NEXT_SESSION], args.turn_timeout, out / "streams" / f"{arm}-{i}-next-{tag}.stderr")
    save(out, f"{arm}-{i}-next-{tag}", events)
    text = answers(events).get(1, "")
    right = grade.grade_next(text, revert)
    m = metrics(events)
    return {"answers": right, "right": sum(v is True for v in right.values()),
            "of": sum(v is not None for v in right.values()), "tokens": m["tokens"], "calls": m["calls"],
            "status": turns[-1]["status"] if turns else "none", "text": text[-800:]}


def run_one(arm: str, i: int, args, out: Path, messages, next_sessions: bool) -> dict:
    base = Path(tempfile.mkdtemp(prefix=f"lrlong-{arm}-{i}-"))
    try:
        work = base / "work"
        work.mkdir()
        start = repo.materialize(work)
        claude, env = environment(args)
        window = "1M" if arm == "A" else args.window
        began = time.time()
        events, turns = session(command(claude, args, window, arm == "C"), work, child(env, base, arm == "C"),
                                messages, args.turn_timeout, out / "streams" / f"{arm}-{i}.stderr")
        seconds = round(time.time() - began)
        save(out, f"{arm}-{i}", events)
        g = grade.grade(work, start, answers(events))
        row = {"arm": arm, "i": i, "model": args.model, "window": window, "messages": len(messages), "turns": turns,
               "seconds": seconds, "score": g["score"], "checks": {k: v[0] for k, v in g["checks"].items()},
               "detail": {k: v[1] for k, v in g["checks"].items()}, "tests": g["tests"], "revert": g["revert"],
               "history": g["history"], **metrics(events)}
        if next_sessions:
            row["next"] = {("lr" if lr else "bare"): next_session(arm, i, base, args, claude, env, g["revert"], out, lr)
                           for lr in (True, False)}
    except Exception as e:
        row = {"arm": arm, "i": i, "error": f"{type(e).__name__}: {e}"}
    if args.keep:
        row["kept"] = str(base)
    else:
        repo.remove(base)
    with LOCK:
        with open(out / "results.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(progress(row), flush=True)
    return row


def progress(row: dict) -> str:
    if "error" in row:
        return f"{row['arm']}-{row['i']}: {row['error']}"
    return (f"{row['arm']}-{row['i']}: {row['score']}/16, {row['tokens']:,} tokens, {row['calls']} calls, "
            f"{len(row['compactions'])} compactions, peak context {row['peak_context']:,}, {row['seconds']} s"
            + "".join(f"; next session {k}: {v['right']} of {v['of']}" for k, v in (row.get("next") or {}).items()))


def project(rows: list, args) -> str:
    """What the pilot says: the compactions, the context they left, and the projected cost of the main runs and the
    next sessions. B and C scale with the number of messages. A is B's calls replayed with no compaction: the
    context grows by B's mean step, for as many calls as B would make."""
    by = {r["arm"]: r for r in rows if "error" not in r}
    if set(by) != {"B", "C"}:
        return "The pilot did not finish: " + "; ".join(str(r.get("error") or r.get("turns")) for r in rows)
    b = by["B"]
    scale = len(script.MESSAGES) / b["messages"]
    per_run = {arm: by[arm]["tokens"] * scale for arm in ("B", "C")}
    cuts = {c["call"] for c in b["compactions"]}
    steps = [b["context"][k] - b["context"][k - 1] for k in range(1, len(b["context"])) if k not in cuts]
    step = statistics.mean(steps) if steps else 0.0
    calls = round(len(b["context"]) * scale)
    per_run["A"] = sum(b["context"][0] + step * k for k in range(calls)) + statistics.mean(b["output"] or [0]) * calls
    main = args.n * sum(per_run.values())
    later = 2 * args.n * len(ARMS) * NEXT_TOKENS
    ratio = (main + later) / DESIGN_TOKENS
    floors = [x for r in by.values() for x in r["floors"]]
    lines = [f"Pilot: messages 1-{b['messages']} in arms B and C, window {args.window}: "
             f"{sum(r['tokens'] for r in by.values()):,} tokens in all (the design said about 5M)."]
    for arm, r in sorted(by.items()):
        lines.append(f"- {arm}: {r['tokens']:,} tokens ({r['by_kind']}), {r['calls']} calls, compactions at "
                     f"{[c['pre'] for c in r['compactions']]} leaving {r['floors']}, peak context "
                     f"{r['peak_context']:,}, score {r['score']}/16, turns {[(t['status'], t['seconds']) for t in r['turns']]}")
    lines += [f"- Context growth per call in B, compactions aside: {step:,.0f} tokens on average; A would peak near "
              f"{b['context'][0] + step * (calls - 1):,.0f} over {calls} calls.",
              f"Projected per run: A {per_run['A']:,.0f}, B {per_run['B']:,.0f}, C {per_run['C']:,.0f}.",
              f"Projected main runs ({args.n} per arm) and next sessions: {main + later:,.0f} tokens against the "
              f"design's {DESIGN_TOKENS:,}, a ratio of {ratio:.2f}.",
              f"Verdict: {'go' if 0.5 <= ratio <= 1.5 else 'stop'} (stop when off by more than half).",
              f"Context right after a compaction: median {statistics.median(floors):,.0f} against the window of "
              f"{args.window}." if floors else "No compaction happened in the pilot."]
    return "\n".join(lines)


def summary(rows: list) -> str:
    rows = [r for r in rows if "error" not in r]
    arms = [a for a in ARMS if any(r["arm"] == a for r in rows)]
    med = lambda xs: statistics.median(xs) if xs else 0  # noqa: E731

    def each(arm, f):
        return [f(r) for r in rows if r["arm"] == arm]

    def table(head, lines):
        return ([f"| {head} | " + " | ".join(f"{a}: {ARMS[a]}" for a in arms) + " |", "| --- |" + " --- |" * len(arms)]
                + [f"| {label} | " + " | ".join(cells) + " |" for label, cells in lines])

    n = {a: len(each(a, lambda r: 1)) for a in arms}
    main = [("Runs", [str(n[a]) for a in arms]),
            ("Checks passed, median of 16", [f"{med(each(a, lambda r: r['score'])):g}" for a in arms]),
            ("Tokens per run, median", [f"{med(each(a, lambda r: r['tokens'])):,.0f}" for a in arms]),
            ("Tokens, all runs", [f"{sum(each(a, lambda r: r['tokens'])):,}" for a in arms]),
            ("Model calls per run, median", [f"{med(each(a, lambda r: r['calls'])):g}" for a in arms]),
            ("Compactions per run, median", [f"{med(each(a, lambda r: len(r['compactions']))):g}" for a in arms]),
            ("Peak context, median", [f"{med(each(a, lambda r: r['peak_context'])):,.0f}" for a in arms]),
            ("Context right after a compaction, median",
             [f"{med([x for r in rows if r['arm'] == a for x in r['floors']]):,.0f}" for a in arms]),
            ("Files read again after a compaction, median", [f"{med(each(a, lambda r: r['rereads'])):g}" for a in arms]),
            ("The repository's own tests pass at the end", [f"{sum(each(a, lambda r: bool(r['tests'])))} of {n[a]}"
                                                            for a in arms]),
            ("Turns that did not end", [str(sum(each(a, lambda r: sum(t["status"] != "ok" for t in r["turns"]))))
                                        for a in arms])]
    checks = [(k, [f"{sum(each(a, lambda r: r['checks'][k]))} of {n[a]}" for a in arms]) for k in grade.CHECKS]
    later = []
    for tag, label in (("lr", "with LR Memory"), ("bare", "without")):
        got = {a: [r["next"][tag] for r in rows if r["arm"] == a and tag in (r.get("next") or {})] for a in arms}
        if not any(got.values()):
            continue
        for q in ("p50", "reason", "revert"):
            later.append((f"Next session {label}: {q} right", [
                f"{sum(x['answers'][q] is True for x in got[a])} of {sum(x['answers'][q] is not None for x in got[a])}"
                for a in arms]))
        later.append((f"Next session {label}: tokens, median", [f"{med([x['tokens'] for x in got[a]]):,.0f}"
                                                                 for a in arms]))
    out = table("", main) + [""] + table("Check", checks)
    return "\n".join(out + ([""] + table("", later) if later else []))


def main() -> int:
    ap = argparse.ArgumentParser(description="LR Memory's long-session bench")
    ap.add_argument("--selftest", action="store_true", help="every grader on a scripted session, no model")
    ap.add_argument("--pilot", action="store_true", help="arms B and C, messages 1-5, once each, and the projection")
    ap.add_argument("--arms", default="A,B,C")
    ap.add_argument("--n", type=int, default=3, help="runs per arm")
    ap.add_argument("--window", default="100k", help="the auto-compact window of arms B and C")
    ap.add_argument("--model", default="claude-sonnet-5-5[1m]")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--turn-timeout", type=int, default=1500, help="seconds one turn may take")
    ap.add_argument("--no-next", action="store_true", help="skip the next sessions")
    ap.add_argument("--out", default="", help="the results folder (default: a new temp folder)")
    ap.add_argument("--env-module", default="", help="a file with claude_bin() and child_env()")
    ap.add_argument("--claude", default="", help="the claude binary")
    ap.add_argument("--keep", action="store_true", help="keep each run's folder")
    ap.add_argument("--summary", default="", help="print the tables of a results folder")
    args = ap.parse_args()
    if args.selftest:
        import selftest
        return selftest.selftest()
    if args.summary:
        rows = [json.loads(x) for x in (Path(args.summary) / "results.jsonl").read_text(encoding="utf-8").splitlines()
                if x.strip()]
        print(summary(rows))
        return 0
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="lrlong-results-"))
    (out / "streams").mkdir(parents=True, exist_ok=True)
    arms = ["B", "C"] if args.pilot else args.arms.split(",")
    messages = script.MESSAGES[:5] if args.pilot else script.MESSAGES
    jobs = [(arm, i) for i in range(1 if args.pilot else args.n) for arm in arms]
    grade.baseline()  # once, before the threads
    print(f"{len(jobs)} runs, {args.parallel} at a time; results in {out}", flush=True)
    with cf.ThreadPoolExecutor(args.parallel) as pool:
        rows = list(pool.map(lambda job: run_one(*job, args, out, messages, not (args.pilot or args.no_next)), jobs))
    text = project(rows, args) if args.pilot else summary(rows)
    (out / ("pilot.md" if args.pilot else "summary.md")).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
