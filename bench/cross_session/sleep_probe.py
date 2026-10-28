"""LR Memory's sleep pass alone, run the bench's way on the day-1 snapshots a finished run kept: does it write into
memory the facts the user stated on day 1? A pass costs about 5,000 tokens and no day-2 session runs.

    python bench/cross_session/sleep_probe.py --job kargo --results <run folder> --out <folder> --runs 3 \
        --env-module <file> --plugins <plugin dir>[,<plugin dir>...]

Each pass starts from a fresh copy of a chain's day-1 config folder, with day 1 marked as typed (run.py's typed()).
A fact counts as written when a memory file the pass wrote matches the job's own leak pattern for it: F1 for the
reason, F3 for the fact said in passing; as held back when only a waiting candidate does.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402

FACTS = ("F1", "F3")


def one(plugin: Path, chain: Path, k: int, args, claude: str, env: dict) -> dict:
    version = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    base = Path(tempfile.mkdtemp(prefix=f"{version}-{chain.name}-{k}-", dir=args.out))
    shutil.copytree(chain / "day1" / "config", base / "config")
    run.typed(base / "config" / "projects")
    e = run.lr_run.child(env, base, True)
    e.update(LR_MEMORY_LANG=getattr(run.days, "LANG", "en"), LR_MEMORY_CLAUDE=claude,
             LR_MEMORY_SLEEP_MODEL=args.sleep_model)
    r = subprocess.run([sys.executable, str(plugin / "scripts" / "lrm.py"), "sleep"], cwd=base, env=e,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                       creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    report = (r.stdout + "\n" + r.stderr).strip()
    records = sorted((base / "lrdata" / "sleep" / "reports").glob("*.json"))
    projects = json.loads(records[-1].read_text(encoding="utf-8"))["projects"] if records else []
    p = projects[0] if projects else {}
    written = " ".join(t for t in (f.read_text(encoding="utf-8") for f in
                                   (base / "config" / "projects").glob("*/memory/*.md"))
                       if "source: lr-memory sleep" in t)
    cands = base / "lrdata" / "sleep" / "candidates.json"
    waiting = cands.read_text(encoding="utf-8") if cands.exists() else ""
    row = {"version": version, "chain": chain.name, "run": k, "tokens": run.tokens_of(report),
           "written": {f: bool(re.search(run.checks.LEAKS[f], written, re.I)) for f in FACTS},
           "waiting": {f: bool(re.search(run.checks.LEAKS[f], waiting, re.I)) for f in FACTS},
           "applied": [[a["file"], a.get("basis")] for a in p.get("applied", [])],
           "candidates": [c["file"] for c in p.get("candidates", [])], "error": p.get("error", "")}
    with run.LOCK:
        with open(Path(args.out) / "probe.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{version} {chain.name} run {k}: written {row['written']}, waiting {row['waiting']}, "
              f"{row['tokens']:,} tokens, files {row['applied']}{', error ' + row['error'] if row['error'] else ''}",
              flush=True)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="the sleep pass alone on a run's day-1 snapshots")
    ap.add_argument("--job", default="ledgerly", choices=run.JOBS)
    ap.add_argument("--results", required=True, help="a finished run's folder, whose chains kept their day 1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=3, help="passes per chain and plugin")
    ap.add_argument("--plugins", default=str(run.LRM), help="plugin folders, comma-separated")
    ap.add_argument("--env-module", default="", help="a file with claude_bin() and child_env()")
    ap.add_argument("--claude", default="")
    ap.add_argument("--sleep-model", default="claude-sonnet-5-5")
    ap.add_argument("--parallel", type=int, default=3)
    args = ap.parse_args()
    run.use(args.job)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    claude, env = run.lr_run.environment(args)
    chains = sorted(c for c in (Path(args.results) / "chains").glob("c*") if (c / "day1" / "config").is_dir())
    plugins = [Path(p) for p in args.plugins.split(",")]
    jobs = [(p, c, k) for k in range(1, args.runs + 1) for c in chains for p in plugins]
    with cf.ThreadPoolExecutor(args.parallel) as pool:
        rows = list(pool.map(lambda j: one(*j, args, claude, env), jobs))
    for v in sorted({r["version"] for r in rows}):
        rs = [r for r in rows if r["version"] == v]
        print(f"{v}: " + ", ".join(f"{f} written {sum(r['written'][f] for r in rs)}/{len(rs)}, held back "
                                   f"{sum(r['waiting'][f] and not r['written'][f] for r in rs)}" for f in FACTS)
              + f"; files per pass {[len(r['applied']) for r in rs]}; {sum(r['tokens'] for r in rs):,} tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
