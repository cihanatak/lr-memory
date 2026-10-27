"""What every part of lr-memory shares: where things live, how a transcript row is read, the language, the clock."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
PROJECTS = Path(os.environ.get("LR_MEMORY_TRANSCRIPTS") or CONFIG / "projects")
DATA = Path(os.environ.get("LR_MEMORY_DATA") or CONFIG / "lr-memory")
LANGS = ("en", "tr")
INJECTED = ("<", "Caveat:", "This session is being continued")
# letters only Turkish has, and its commonest small words; case-blind matching is kept to the words, because under
# it ı and İ would match every i in English text
TURKISH = re.compile(r"[ğşıİĞŞ]|\b(?i:ve|bir|bu|için|icin|evet|tamam|değil|degil|neden|nasıl|nasil|devam|yap)\b")


def lang(sample: str = "") -> str:
    """The language lr-memory writes in: LR_MEMORY_LANG (en or tr) when set, otherwise Turkish when the sample
    reads as Turkish and English when it does not."""
    want = os.environ.get("LR_MEMORY_LANG", "").strip().lower()[:2]
    if want in LANGS:
        return want
    return "tr" if len(TURKISH.findall(sample)) >= 3 else "en"


def local(stamp: str, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """A transcript's UTC timestamp (2026-10-27T09:50...) in this machine's time zone."""
    try:
        t = datetime.strptime(stamp[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return "-"
    return t.astimezone().strftime(fmt)


def command() -> str:
    """How to run lr-memory from a shell, with this interpreter and this copy of the plugin."""
    lrm = Path(__file__).resolve().parent.parent / "lrm.py"
    return f'"{Path(sys.executable).as_posix()}" "{lrm.as_posix()}"'


def read_input() -> dict:
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    return data if isinstance(data, dict) else {}


def say(text: str) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    print(text)


def emit(obj: dict) -> None:
    say(json.dumps(obj, ensure_ascii=False))


def log_error(e: BaseException) -> None:
    """A hook never fails loudly; what went wrong goes to a log the user can read."""
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        with open(DATA / "errors.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {type(e).__name__}: {e}\n")
    except OSError:
        pass


def resolve(path: str, session: str) -> Path | None:
    """The session's transcript: the path the hook was given, or the newest file of that session id."""
    p = Path(path) if path else None
    if p and p.is_file() and p.stat().st_size > 2000:
        return p
    found = sorted(PROJECTS.glob(f"*/{session}.jsonl"), key=lambda q: q.stat().st_mtime) if session else []
    return found[-1] if found else (p if p and p.is_file() else None)


def tail_rows(path: Path, max_bytes: int) -> list:
    """The rows in the last max_bytes of a transcript (sessions grow to hundreds of MB)."""
    size = path.stat().st_size
    with open(path, "rb") as f:
        f.seek(max(0, size - max_bytes))
        data = f.read()
    lines = data.split(b"\n")
    if size > max_bytes:
        lines = lines[1:]  # the first line is cut
    rows = []
    for ln in lines:
        try:
            row = json.loads(ln)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def blocks(row: dict) -> list:
    content = (row.get("message") or {}).get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def texts(row: dict) -> list:
    content = (row.get("message") or {}).get("content")
    if isinstance(content, str):
        return [content]
    return [b.get("text", "") for b in blocks(row) if b.get("type") == "text"]


def result_text(block: dict) -> str:
    c = block.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return str(c or "")


def scripted(row: dict) -> bool:
    """A row of a session a script started (claude -p, the Agent SDK): its prompts are not a person's words."""
    return str(row.get("entrypoint", "")).startswith("sdk")


def user_text(row: dict) -> str | None:
    """The user's own words in a transcript row, or None for anything injected, tool-made or a subagent's."""
    if row.get("type") != "user" or row.get("isMeta") or row.get("isSidechain"):
        return None
    origin = row.get("origin") or {}
    if origin and origin.get("kind") != "human":
        return None
    content = (row.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(content, str):
        return None
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", content, flags=re.S).strip()
    # a message that opens with the user's own paste starts with "<" too, yet it is theirs
    pasted = text.startswith("<pasted_content")
    return None if len(text) < 2 or (text.startswith(INJECTED) and not pasted) else text
