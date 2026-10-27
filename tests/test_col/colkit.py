"""Helpers for COL's tests: transcript rows the way Claude Code writes them, and a hook run the way Claude Code runs
it (a new process, the event on stdin)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COL = ROOT / "plugins" / "col"
CLI = COL / "scripts" / "cli.py"
SESSION = "bbbb1111-2222-3333-4444-555566667777"


def user(text, at="2026-10-25T10:00:00.000Z"):
    return {"type": "user", "timestamp": at, "message": {"role": "user", "content": text}}


def say(*texts):
    return {"type": "assistant", "message": {"role": "assistant",
                                             "content": [{"type": "text", "text": x} for x in texts]}}


def call(name, **inp):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "t1", "name": name, "input": inp}]}}


def result(text):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": text}]}}


def feedback(text):
    return {"type": "user", "isMeta": True, "message": {"role": "user", "content": "Stop hook feedback:\n" + text}}


def transcript(projects, rows, mode="w"):
    path = projects / "proj" / f"{SESSION}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    return path


def hook(event, **payload):
    payload = {"hook_event_name": event, "session_id": SESSION, **payload}
    r = subprocess.run([sys.executable, str(CLI), "hook"], input=json.dumps(payload), capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    assert not r.stderr.strip(), r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def stop(path, cwd):
    return hook("Stop", transcript_path=str(path), cwd=str(cwd))


def bash(cwd, command, description="x", background=False):
    out = hook("PreToolUse", tool_name="Bash", cwd=str(cwd),
               tool_input={"command": command, "description": description, "run_in_background": background})
    return (out or {}).get("hookSpecificOutput", {}).get("permissionDecisionReason")


def turn(calls=None, final=""):
    return {"user": "x", "user_at": "t", "calls": calls or [], "final": final, "said": [final], "after_hook": []}


def logged(data, name):
    f = data / f"{name}.jsonl"
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []
