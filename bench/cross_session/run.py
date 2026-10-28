"""The cross-session bench: say a thing once on day 1, and see whether a fresh session on day 2 still knows it
(DESIGN.md says why and how).

    python bench/cross_session/run.py --selftest                     every grader on scripted days, no model
    python bench/cross_session/run.py --scan --env-module <file>     one chain: day 1, then day 2 with Claude Code alone
    python bench/cross_session/run.py --n 3 --env-module <file>      three chains: day 1, then day 2 with Claude Code
                                                                     alone (N) and with LR Memory (L), each from the
                                                                     same copy of day 1
    python bench/cross_session/run.py --summary <results folder>     the tables again

--job kargo runs the second job instead of ledgerly's: a Turkish shop's shipping module, in kargo/.

Day 2 runs in day 1's folder with day 1's config folder, so Claude Code's own memory carries over as it does on a
user's machine; the arms of a chain take turns, each from a fresh copy of what day 1 left. A second run with the same
--out skips what is already there, so --n 3 after --scan reuses the scan's chain. Real tokens are spent, most of them
cache reads.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import importlib.util
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

JOBS = ("ledgerly", "kargo")  # each with its own days, checks and selftest; ledgerly's sit beside this file
LRM = HERE.parents[1] / "plugins" / "lr-memory"
ARMS = {"N": "Claude Code alone", "L": "with LR Memory"}
RECALL = re.compile(r"(?:run\.sh|lrm\.py)\\?\"? (?:search|show)")  # a recall command inside a tool call's JSON
BUSY_S = 120  # LR Memory's sleep.BUSY_S: a MEMORY.md written this recently means a session is writing memory
LOCK = threading.Lock()


def _long_run():
    """The long-session bench's runner, for its environment, session and metrics; loaded under its own name, since
    its modules (grade, hidden, repo, script) share names with nothing here."""
    spec = importlib.util.spec_from_file_location("long_run", HERE.parent / "long_session" / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lr_run = _long_run()


def use(job: str) -> None:
    """Load a job's days, checks and selftest; a run does one job."""
    global checks, days, selfcheck
    sys.path.insert(0, str(HERE if job == "ledgerly" else HERE / job))
    import checks
    import days
    import selfcheck


def version() -> str:
    """The LR Memory version this run loads."""
    return json.loads((LRM / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def column(row: dict) -> str:
    """A day-2 row's column in the tables: the arm, and for LR Memory its version, and whether its nightly pass ran."""
    if row["arm"] != "L":
        return row["arm"]
    return f"L {row['version']}" + (" no sleep" if row.get("no_sleep") else "")


def tag(row: dict) -> str:
    """The same, as part of a file name."""
    return column(row).replace(" no sleep", "-nosleep").replace(" ", "")


def cued(base: Path) -> list:
    """The turns LR Memory's cue put in front of the model on day 2, as refs."""
    return sorted(ref for p in (base / "lrdata" / "cue").glob("*.json") for ref in json.loads(checks.read(p) or "[]"))


def finals(events: list) -> dict:
    """The answer that ended each turn: the result text."""
    return {e.get("_turn"): str(e.get("result") or "") for e in events if e.get("type") == "result"}


def recalls(events: list) -> int:
    """How often the session searched or opened the record with LR Memory's recall."""
    n = 0
    for e in events:
        for b in (e.get("message") or {}).get("content") or [] if e.get("type") == "assistant" else []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                text = json.dumps(b.get("input") or {})
                n += b.get("name") == "Skill" and "recall" in text or bool(RECALL.search(text))
    return n


def memory(base: Path) -> dict:
    """Claude Code's memory files for the project: {name: text}."""
    return {p.name: checks.read(p)[:3000] for p in sorted((base / "config" / "projects").glob("*/memory/*.md"))}


def typed(projects: Path) -> int:
    """Mark day 1's transcript as typed by a person, and return how many rows changed. The bench sends its messages
    through claude -p, which records them with entrypoint sdk-cli; LR Memory's sleep pass rightly skips those as a
    script's prompts, while on a user's machine day 1 is typed in a terminal. Claude Code's own memory never reads
    these files, so only arm L sees the change."""
    changed = 0
    for path in projects.glob("*/*.jsonl"):
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                rows.append(line)
                continue
            if isinstance(row, dict) and str(row.get("entrypoint", "")).startswith("sdk"):
                row["entrypoint"] = "cli"
                origin = row.get("origin")
                if isinstance(origin, dict) and origin.get("kind") != "human" and row.get("type") == "user":
                    content = (row.get("message") or {}).get("content")
                    text = content if isinstance(content, str) else "".join(
                        b.get("text", "") for b in content or [] if isinstance(b, dict))
                    if text.strip() in days.DAY1:
                        origin["kind"] = "human"
                changed += 1
            rows.append(json.dumps(row, ensure_ascii=False))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(rows) + "\n")
    return changed


def sleep_pass(base: Path, env: dict, claude: str, args) -> dict:
    """LR Memory's nightly pass over day 1, as `lrm.py sleep` runs it, with the run's claude; its tokens count towards
    arm L. It skips a project whose MEMORY.md changed in the last two minutes, so that wait comes first."""
    index = list((base / "config" / "projects").glob("*/memory/MEMORY.md"))
    wait = BUSY_S + 5 - (time.time() - max((p.stat().st_mtime for p in index), default=0))
    if wait > 0:
        time.sleep(wait)
    e = dict(env, LR_MEMORY_CLAUDE=claude, LR_MEMORY_SLEEP_MODEL=args.sleep_model)
    r = subprocess.run([sys.executable, str(LRM / "scripts" / "lrm.py"), "sleep"], cwd=base, env=e, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=1800,
                       creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    report = (r.stdout + "\n" + r.stderr).strip()
    return {"code": r.returncode, "tokens": tokens_of(report), "read": messages_read(report), "report": report[-3000:]}


def tokens_of(report: str) -> int:
    """The sleep report's cost, in English or in Turkish."""
    found = re.search(r"(?:Cost|Maliyet): ([\d,. ]+) token", report)
    return int(re.sub(r"\D", "", found.group(1))) if found else 0


def messages_read(report: str):
    found = re.search(r"Read (\d+) messages|(\d+) mesaj ve", report)
    return int(found.group(1) or found.group(2)) if found else None


def slept(row: dict) -> int:
    """The tokens of a row's sleep pass, read again from its report: runs before the Turkish reading counted 0."""
    sleep = row.get("sleep") or {}
    return sleep.get("tokens") or tokens_of(sleep.get("report", ""))


def write(out: Path, name: str, row: dict) -> None:
    with LOCK:
        with open(out / name, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(progress(row), flush=True)


def rows_of(out: Path, name: str) -> list:
    path = out / name
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []


def day_one(i: int, base: Path, args, claude: str, env: dict, out: Path) -> dict:
    """Day 1 in a fresh folder, with Claude Code alone; when every turn ended, the folders it left are kept for day 2."""
    if base.exists():
        lr_run.repo.remove(base)
    work = base / "work"
    work.mkdir(parents=True)
    start = checks.prepare(work)
    row = {"chain": i, "day": 1, "start": start, "baseline": checks.measure(work)}
    began = time.time()
    events, turns = lr_run.session(lr_run.command(claude, args, "1M", False), work, lr_run.child(env, base, False),
                                   days.DAY1, args.turn_timeout, out / "streams" / f"c{i}-day1.stderr")
    lr_run.save(out, f"c{i}-day1", events)
    m = lr_run.metrics(events)
    row.update(turns=turns, seconds=round(time.time() - began), tokens=m["tokens"], calls=m["calls"],
               words=[checks.words(t) for _, t in sorted(finals(events).items())], memory=memory(base),
               state=checks.state(work, start, row["baseline"]))
    row["ok"] = len(turns) == len(days.DAY1) and all(t["status"] == "ok" for t in turns)
    if row["ok"]:
        for name in ("work", "config"):
            shutil.copytree(base / name, base / "day1" / name)
    write(out, "day1.jsonl", row)
    return row


def day_two(i: int, arm: str, base: Path, day1: dict, args, claude: str, env: dict, out: Path) -> dict:
    """Day 2 from a fresh copy of what day 1 left: with Claude Code alone (N), or with LR Memory (L), whose nightly
    pass runs first unless --no-sleep."""
    lr = arm == "L"
    for name in ("work", "config", "lrdata"):
        if (base / name).exists():
            lr_run.repo.remove(base / name)
    for name in ("work", "config"):
        shutil.copytree(base / "day1" / name, base / name)
    e = lr_run.child(env, base, lr)
    if lr:
        e["LR_MEMORY_LANG"] = getattr(days, "LANG", "en")
    row = {"chain": i, "day": 2, "arm": arm}
    try:
        if lr:
            row["version"] = version()
            row["typed"] = typed(base / "config" / "projects")
            if args.no_sleep:
                row["no_sleep"] = True
            else:
                row["sleep"] = sleep_pass(base, e, claude, args)
        row["memory_before"] = memory(base)
        began = time.time()
        events, turns = lr_run.session(lr_run.command(claude, args, "1M", lr), base / "work", e, days.DAY2,
                                       args.turn_timeout, out / "streams" / f"c{i}-{tag(row)}.stderr")
        lr_run.save(out, f"c{i}-{tag(row)}", events)
        m = lr_run.metrics(events)
        said = finals(events)
        row.update(turns=turns, seconds=round(time.time() - began), tokens=m["tokens"], calls=m["calls"],
                   recalls=recalls(events), **checks.grade(base / "work", day1, said),
                   answers={k: v[-1500:] for k, v in said.items()})
        row["all_tokens"] = row["tokens"] + (row.get("sleep") or {}).get("tokens", 0)
        if lr:
            row["cued"] = cued(base)
    except Exception as x:
        row["error"] = f"{type(x).__name__}: {x}"
    write(out, "results.jsonl", row)
    return row


def chain(i: int, arms: list, args, out: Path) -> None:
    base = out / "chains" / f"c{i}"
    done = {column(r) for r in rows_of(out, "results.jsonl") if r.get("chain") == i and "error" not in r and "arm" in r}
    arms = [a for a in arms if column({"arm": a, "version": version(), "no_sleep": args.no_sleep}) not in done]
    if not arms:
        return
    try:
        claude, env = lr_run.environment(args)
        day1 = next((r for r in reversed(rows_of(out, "day1.jsonl")) if r["chain"] == i and r.get("ok")), None)
        if day1 is None or not (base / "day1").is_dir():
            day1 = day_one(i, base, args, claude, env, out)
            if not day1["ok"]:
                return
        for arm in arms if i % 2 else arms[::-1]:  # the arms take turns going first
            day_two(i, arm, base, day1, args, claude, env, out)
    except Exception as x:
        write(out, "results.jsonl", {"chain": i, "error": f"{type(x).__name__}: {x}"})
    finally:
        if not args.keep:
            for name in ("work", "config", "lrdata"):
                if (base / name).exists():
                    lr_run.repo.remove(base / name)


def progress(row: dict) -> str:
    if "error" in row:
        return f"c{row['chain']}{'-' + row['arm'] if row.get('arm') else ''}: {row['error']}"
    if row.get("day") == 1:
        return (f"c{row['chain']} day 1: {'ok' if row['ok'] else 'turns ' + str(row['turns'])}, {row['tokens']:,} "
                f"tokens, {row['seconds']} s, memory files {sorted(row['memory'])}, leaks "
                f"{[k for k, v in row['state']['leaks'].items() if v]}")
    sleep = row.get("sleep") or {}
    return (f"c{row['chain']} day 2 {column(row)}: memory {row['memory']}/{row['of_memory']}, rules {row['rules']}/"
            f"{len(checks.RULES)}, task {row['task']}/{len(checks.TASK)}, {row['tokens']:,} tokens" + (f" + sleep {sleep.get('tokens', 0):,} (read "
                                                                    f"{sleep.get('read')})" if sleep else "")
            + f", recalls {row['recalls']}" + (f", cued {len(row['cued'])}" if "cued" in row else "")
            + f", {row['seconds']} s; failed "
            + str([k for k, v in row["checks"].items() if v[0] is False]))


def sign_test(wins: int, losses: int) -> float:
    """Two-sided exact sign test on discordant pairs."""
    n = wins + losses
    if not n:
        return 1.0
    tail = sum(comb(n, k) for k in range(min(wins, losses) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summary(rows: list, day1: list) -> str:
    rows = [r for r in rows if "error" not in r and r.get("day") == 2]
    arms = sorted({column(r) for r in rows}, key=lambda c: (c != "N", c))  # N, then each LR Memory version
    med = lambda xs: statistics.median(xs) if xs else 0  # noqa: E731
    by = {a: [r for r in rows if column(r) == a] for a in arms}
    head = ["| | " + " | ".join(f"{a}: {ARMS[a[0]]}{a[1:]}" for a in arms) + " |", "| --- |" + " --- |" * len(arms)]
    lines = [("Chains", [str(len(by[a])) for a in arms])]
    for k in checks.CHECKS:
        lines.append((k, [f"{sum(r['checks'][k][0] is True for r in by[a])} of "
                          f"{sum(r['checks'][k][0] is not None for r in by[a])}" for a in arms]))
    lines += [(f"Memory checks passed ({' '.join(checks.MEMORY)})", [f"{sum(r['memory'] for r in by[a])} of "
                                                                    f"{sum(r['of_memory'] for r in by[a])}"
                                                                    for a in arms]),
              (f"Rules kept ({' '.join(checks.RULES)})", [f"{sum(r['rules'] for r in by[a])} of "
                                                          f"{len(checks.RULES) * len(by[a])}" for a in arms]),
              (f"Task checks ({checks.TASK[0]}-{checks.TASK[-1]})", [f"{sum(r['task'] for r in by[a])} of "
                                                                     f"{len(checks.TASK) * len(by[a])}" for a in arms]),
              ("Day 2 tokens, median", [f"{med([r['tokens'] for r in by[a]]):,.0f}" for a in arms]),
              ("Day 2 tokens with the sleep pass, median", [f"{med([r['tokens'] + slept(r) for r in by[a]]):,.0f}"
                                                            for a in arms]),
              ("Words per answer, median", [f"{med([w for r in by[a] for w in r['words']]):g}" for a in arms]),
              ("Recall searches, median", [f"{med([r['recalls'] for r in by[a]]):g}" for a in arms]),
              ("Turns the cue showed, median", [f"{med([len(r['cued']) for r in by[a]]):g}"
                                                if all("cued" in r for r in by[a]) else "-" for a in arms])]
    out = head + [f"| {label} | " + " | ".join(cells) + " |" for label, cells in lines]
    pairs = {(r["chain"], k): {} for r in rows for k in checks.MEMORY + checks.RULES}
    for r in rows:
        for k in checks.MEMORY + checks.RULES:
            pairs[(r["chain"], k)][column(r)] = r["checks"][k][0]
    for a in arms if "N" in arms else []:
        both = [v for v in pairs.values() if a != "N" and v.get("N") is not None and v.get(a) is not None]
        if both:
            wins = sum(not v["N"] and v[a] for v in both)
            losses = sum(v["N"] and not v[a] for v in both)
            out += ["", f"Paired over chains and the {len(checks.MEMORY + checks.RULES)} memory and rule checks: {a} "
                        f"passed where N failed {wins} "
                        f"times, and the other way round {losses} times; two-sided sign test "
                        f"p = {sign_test(wins, losses):.3f}."]
    for r in day1:
        out.append(f"Day 1 of chain {r['chain']}: {r['tokens']:,} tokens, words per answer {r['words']}, memory files "
                   f"{sorted(r['memory'])}, written into the repository: "
                   f"{[k for k, v in r['state']['leaks'].items() if v] or 'none'}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="LR Memory's cross-session bench")
    ap.add_argument("--job", default="ledgerly", choices=JOBS)
    ap.add_argument("--selftest", action="store_true", help="every grader on scripted days, no model")
    ap.add_argument("--scan", action="store_true", help="one chain, day 2 with Claude Code alone")
    ap.add_argument("--n", type=int, default=3, help="chains")
    ap.add_argument("--chains", default="", help="these chains only, such as 2,3,5")
    ap.add_argument("--no-sleep", action="store_true", help="arm L without LR Memory's nightly pass")
    ap.add_argument("--arms", default="N,L")
    ap.add_argument("--model", default="claude-sonnet-5-5[1m]")
    ap.add_argument("--sleep-model", default="claude-sonnet-5-5")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--turn-timeout", type=int, default=1500, help="seconds one turn may take")
    ap.add_argument("--out", default="", help="the results folder (default: a new temp folder)")
    ap.add_argument("--env-module", default="", help="a file with claude_bin() and child_env()")
    ap.add_argument("--claude", default="", help="the claude binary")
    ap.add_argument("--keep", action="store_true", help="keep each chain's folders after day 2")
    ap.add_argument("--summary", default="", help="print the tables of a results folder")
    args = ap.parse_args()
    use(args.job)
    if args.selftest:
        return selfcheck.selftest(sys.modules[__name__])
    if args.summary:
        print(summary(rows_of(Path(args.summary), "results.jsonl"), rows_of(Path(args.summary), "day1.jsonl")))
        return 0
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="lrcross-results-"))
    (out / "streams").mkdir(parents=True, exist_ok=True)
    arms, n = (["N"], 1) if args.scan else (args.arms.split(","), args.n)
    chains = [int(x) for x in args.chains.split(",")] if args.chains else list(range(1, n + 1))
    args.keep = args.keep or args.scan  # the scan's chain is reused by the full run
    print(f"{args.job}: chains {chains}, arms {arms}{' without the sleep pass' if args.no_sleep else ''}, "
          f"{args.parallel} at a time; results in {out}", flush=True)
    with cf.ThreadPoolExecutor(args.parallel) as pool:
        list(pool.map(lambda i: chain(i, arms, args, out), chains))
    text = summary(rows_of(out, "results.jsonl"), rows_of(out, "day1.jsonl"))
    (out / "summary.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
