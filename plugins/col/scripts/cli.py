#!/usr/bin/env python3
"""COL's entry point: the Claude Code hooks, and the report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from col import __version__, common, hooks, report  # noqa: E402


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="col", description="COL: claims against evidence, a prediction ledger, a key "
                                                         "scan before commits and pushes")
    ap.add_argument("--version", action="version", version=f"col {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hook", help="entry point of the Claude Code hooks; reads the event on stdin")
    r = sub.add_parser("report", help="what COL checked, blocked and compared")
    r.add_argument("--days", type=float, default=30, help="how far back to look (default 30)")
    a = ap.parse_args(argv)
    if a.cmd == "hook":
        return hooks.run()
    common.say(report.report(a.days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
