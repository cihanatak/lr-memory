"""What every part of COL shares: where things live, the language, how a turn is read from a transcript, the logs."""
from __future__ import annotations

import json
import locale
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
PROJECTS = Path(os.environ.get("COL_TRANSCRIPTS") or CONFIG / "projects")
DATA = Path(os.environ.get("COL_DATA") or CONFIG / "col")
LANGS = ("en", "tr")
INJECTED = ("<", "Caveat:", "This session is being continued", "Stop hook feedback:")
# letters only Turkish has, and its commonest small words; case-blind matching is kept to the words, because under
# it ı and İ would match every i in English text
TR_LETTERS = re.compile(r"[ğşıİĞŞ]")
TR_WORDS = re.compile(r"\b(?i:ve|bir|bu|için|icin|evet|tamam|değil|degil|neden|nasıl|nasil|devam|yap)\b")
STATE_DAYS = 30


def setting(name: str, default: str = "on") -> str:
    """COL_<NAME>: on or off; the claim check also takes log (check and record, never block)."""
    value = os.environ.get(f"COL_{name.upper()}", "").strip().lower()
    return value if value in ("on", "off", "log") else default


def system_lang() -> str:
    try:
        name = locale.getlocale()[0] or ""
    except (ValueError, TypeError):
        name = ""
    name = (name or os.environ.get("LC_ALL") or os.environ.get("LANG") or "").lower()
    return "tr" if name.startswith(("tr", "turkish")) else "en"


def lang(sample: str = "", stored: str = "") -> str:
    """The language COL writes in: COL_LANG (en or tr) when set; else the sample's, when it is long enough to tell;
    else the one this session showed last; else the machine's."""
    want = os.environ.get("COL_LANG", "").strip().lower()[:2]
    if want in LANGS:
        return want
    letters, words = len(TR_LETTERS.findall(sample)), len(TR_WORDS.findall(sample))
    if letters + words >= 3 or (len(sample) < 80 and (letters or words >= 2)):
        return "tr"
    if len(sample) >= 80:
        return "en"
    return stored if stored in LANGS else system_lang()


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now() -> str:
    return iso(datetime.now(timezone.utc))


def read_input() -> dict:
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def say(text: str) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    print(text)


def emit(obj: dict) -> None:
    say(json.dumps(obj, ensure_ascii=False))


def log(name: str, record: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / f"{name}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now(), **record}, ensure_ascii=False) + "\n")


def read_log(name: str) -> list:
    try:
        lines = (DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def log_error(e: BaseException) -> None:
    """A hook never fails loudly; what went wrong goes to a log the user can read."""
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        with open(DATA / "errors.log", "a", encoding="utf-8") as f:
            f.write(f"{now()} {type(e).__name__}: {e}\n")
    except OSError:
        pass


def _state(session: str) -> Path:
    name = re.sub(r"[^\w-]", "_", session)[:100] or "none"
    return DATA / "state" / f"{name}.json"


def load_state(session: str) -> dict:
    try:
        data = json.loads(_state(session).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(session: str, state: dict) -> None:
    f = _state(session)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def prune_state(days: float = STATE_DAYS) -> None:
    cutoff = time.time() - days * 86400
    for f in (DATA / "state").glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass


def resolve(path: str, session: str) -> Path | None:
    """The session's transcript: the path the hook was given, or the newest file of that session id."""
    p = Path(path) if path else None
    if p and p.is_file() and p.stat().st_size > 2000:
        return p
    found = sorted(PROJECTS.glob(f"*/{session}.jsonl"), key=lambda q: q.stat().st_mtime) if session else []
    return found[-1] if found else (p if p and p.is_file() else None)


def tail_rows(path: Path, max_bytes: int, must: bytes = b"") -> list:
    """The rows in the last max_bytes of a transcript (sessions grow to hundreds of MB); with `must`, only the lines
    that hold it are parsed."""
    size = path.stat().st_size
    with open(path, "rb") as f:
        f.seek(max(0, size - max_bytes))
        data = f.read()
    lines = data.split(b"\n")
    if size > max_bytes:
        lines = lines[1:]  # the first line is cut
    rows = []
    for ln in lines:
        if must and must not in ln:
            continue
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


def plain(row: dict) -> str:
    content = (row.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in blocks(row) if b.get("type") == "text")


def result_text(block: dict) -> str:
    c = block.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return str(c or "")


def user_text(row: dict) -> str | None:
    """The user's own words in a transcript row, or None for anything injected, tool-made or a subagent's."""
    if row.get("type") != "user" or row.get("isMeta") or row.get("isSidechain"):
        return None
    origin = row.get("origin") or {}
    if origin and origin.get("kind") != "human":
        return None
    if any(b.get("type") == "tool_result" for b in blocks(row)):
        return None
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", plain(row), flags=re.S).strip()
    # a message that opens with the user's own paste starts with "<" too, yet it is theirs
    pasted = text.startswith("<pasted_content")
    return None if len(text) < 2 or (text.startswith(INJECTED) and not pasted) else text


def turn(path: Path) -> dict:
    """The user's last message and everything the assistant did after it: the tool calls, every text, the final
    message (the text after the last tool call) and what was said after the last block of a Stop hook."""
    rows = []
    for max_bytes in (2 << 20, 16 << 20, 1 << 40):
        rows = tail_rows(path, max_bytes)
        if any(user_text(r) for r in rows):
            break
    start, words, at = len(rows), "", ""
    for i in range(len(rows) - 1, -1, -1):
        text = user_text(rows[i])
        if text:
            start, words, at = i, text, str(rows[i].get("timestamp", ""))
            break
    calls, final, said, after_hook = [], [], [], None
    for r in rows[start + 1:]:
        if r.get("isSidechain"):
            continue
        if r.get("type") == "user" and plain(r).lstrip().startswith("Stop hook feedback:"):
            # what the assistant says next is its answer to the block, and the message the next check reads
            after_hook, final = [], []
            continue
        for b in blocks(r):
            if r.get("type") == "assistant" and b.get("type") == "tool_use":
                calls.append({"name": b.get("name", ""), "input": b.get("input") or {}})
                final = []
            elif r.get("type") == "assistant" and b.get("type") == "text":
                final.append(b.get("text", ""))
                said.append(b.get("text", ""))
                if after_hook is not None:
                    after_hook.append(b.get("text", ""))
            elif b.get("type") == "tool_result":
                final = []
    return {"user": words, "user_at": at, "calls": calls, "final": "\n".join(final).strip(), "said": said,
            "after_hook": after_hook or []}


def results_text(path: Path, max_bytes: int = 16 << 20) -> str:
    """The tool outputs of the recent part of the session: the evidence a final message may restate."""
    return "\n".join(result_text(b) for r in tail_rows(path, max_bytes, b'"tool_result"') for b in blocks(r)
                     if b.get("type") == "tool_result")
