"""lr-memory from a shell, and the entry point of its Claude Code hooks.

  lrm.py search <words> [-k 8] [--kind user,commit] [--since 2026-10-20] [--session 3f2a9c1e]
  lrm.py show <ref>          the turn around a hit; ref as a hit prints it (3f2a9c1e:1234, memory:<project>/<name>)
  lrm.py update [--background]
  lrm.py sleep [--dry-run] [--hours 48] [--project <name>] [--background]
                             turn what the user said since the last pass into memory files (one claude -p per project)
  lrm.py hook                PreCompact, PostCompact, SessionStart and UserPromptSubmit, each reading its event as
                             JSON on stdin
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lr_memory import archive, common, cue, note, sleep  # noqa: E402


def hook() -> int:
    """Every hook exits 0: a failing hook must never stop a compaction or a session start."""
    try:
        data = common.read_input()
        event = data.get("hook_event_name", "")
        if event == "PreCompact":
            note.precompact(data)
        elif event == "PostCompact":
            note.postcompact(data)
        elif event == "UserPromptSubmit":
            cue.prompt(data)
        elif event == "SessionStart":
            note.sessionstart(data)
            archive.spawn_update()
            if sleep.due():
                common.spawn("sleep", "--background")
    except Exception as e:
        common.log_error(e)
    return 0


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lrm", description="lr-memory: search every past Claude Code session")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="find how something was done, decided or said")
    s.add_argument("words", nargs="+")
    s.add_argument("-k", type=int, default=8, help="how many hits (default 8)")
    s.add_argument("--kind", default="", help="user,assistant,commit,step,summary,report,memory,prompt")
    s.add_argument("--since", default="", help="YYYY-MM-DD")
    s.add_argument("--session", default="", help="a session id or its first characters")
    sub.add_parser("show", help="the turn around a hit").add_argument("ref")
    sub.add_parser("update", help="index what is new").add_argument("--background", action="store_true")
    z = sub.add_parser("sleep", help="turn what the user said since the last pass into memory files")
    z.add_argument("--dry-run", action="store_true", help="show what would be written, write nothing")
    z.add_argument("--hours", type=float, help="read this many hours back instead of since the last pass")
    z.add_argument("--project", default="", help="only this project (its folder name under projects/)")
    z.add_argument("--background", action="store_true", help="once at a time; errors go to errors.log")
    sub.add_parser("hook", help="entry point of the Claude Code hooks; reads the event on stdin")
    a = ap.parse_args(argv)
    if a.cmd == "hook":
        return hook()
    if a.cmd == "sleep":
        if not a.background:
            common.say(sleep.run(a.hours, a.dry_run, a.project)["text"])
            return 0
        try:
            sleep.background()
        except Exception as e:
            common.log_error(e)
        return 0
    try:
        if a.cmd == "search":
            common.say(archive.report(" ".join(a.words), a.k, a.kind, a.since, a.session))
        elif a.cmd == "show":
            common.say(archive.show(a.ref, lang=common.lang()))
        elif a.background:
            archive.background_update()
        else:
            common.say(json.dumps(archive.update()))
    except sqlite3.OperationalError as e:
        if "fts5" not in str(e):
            raise
        common.say(archive.TEXT[common.lang()]["fts"])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
