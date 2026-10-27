"""The working note: what a compaction summary tends to lose, taken from the transcript and put back after it.

One entry point for three Claude Code events:
  PreCompact               writes a trail of the stretch about to be compacted
  PostCompact              adds Claude Code's own summary to that trail
  SessionStart (compact)   puts a short note made from the trail back into the fresh context

A summary keeps the gist and loses what an agent needs to carry on: the user's exact words (a correction becomes a
generic sentence), the open tasks, and the trail of files, commits and test results. The note takes these from the
transcript mechanically. Nothing is rewritten by a model, and the transcript is never copied: the trail points into
it. Never blocks: every failure exits 0 with nothing on stdout (exit 2 from PreCompact would stop the compaction).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import common

TAIL_BYTES = 64 << 20  # the stretch since the last compaction, and the task list from before it; images are large
NOTE_CHARS = 9000  # Claude Code hands at most 10,000 characters of a hook's context to the model
FRESH_S = 3600  # a trail older than this belongs to an earlier compaction, not to the one that just happened
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
COMMIT_OUT = re.compile(r"\[([\w./+-]+) ([0-9a-f]{7,12})\] ([^\n]{1,120})")
ONELINE = re.compile(r"^([0-9a-f]{7,12}) (\S[^\n]{0,119})$", re.M)  # `git log --oneline -1` after a quiet commit
TEST_CMD = re.compile(r"pytest|unittest|\b(?:npm|pnpm|yarn|bun) (?:run )?test|vitest|jest|mocha|node --test|go test|"
                      r"cargo test|dotnet test|mvn test|gradle test|rspec|phpunit", re.I)
TEST_LINE = re.compile(r"\b\d+ (?:passed|failed|passing|failing)\b|\bRan \d+ tests?\b|^(?:OK|FAILED)(?: \(|$)|"
                       r"\btest result: \w+\.|^(?:ok|FAIL)\s+\S+\s+[\d.]+s\b")
PASTED = re.compile(r"<pasted_content[^>]*>.*?</pasted_content[^>]*>", re.S)
SCRATCH = re.compile(r"[\\/]AppData[\\/]Local[\\/]Temp[\\/]|^/tmp/|^/(?:private/)?var/folders/|[\\/]scratchpad[\\/]",
                     re.I)
TEXT = {
    "en": {
        "head": "Working note (lr-memory): taken from the transcript right before the compaction at {at}. The summary "
                "may have shortened or dropped these; what follows is verbatim.",
        "user": "The user's last words (verbatim):",
        "open": "Open tasks (from the task list):",
        "in_progress": "in progress",
        "pending": "next",
        "edited": "Files changed in this stretch: ",
        "commits": "Commits: ",
        "tests": "Latest test results: ",
        "final": "End of the last message: ",
        "pointer": "If you need a detail, don't guess; check the record: transcript {transcript}; trail {trail}. "
                   "Search earlier work first: {cmd} search <words> (every past session, a few sourced hits; open "
                   "one with {cmd} show <ref>).",
        "pasted": "[pasted text, {n} characters]",
    },
    "tr": {
        "head": "Çalışma notu (lr-memory): {at} özetlemesinden hemen önce kayıttan çıkarıldı. Özet bunları kısaltmış "
                "ya da atlamış olabilir; aşağıdakiler birebir kayıttır.",
        "user": "Kullanıcının son sözleri (birebir):",
        "open": "Açık işler (görev listesinden):",
        "in_progress": "sürüyor",
        "pending": "sırada",
        "edited": "Bu dönemde değişen dosyalar: ",
        "commits": "Commit'ler: ",
        "tests": "Son test çıktıları: ",
        "final": "Son mesajın sonu: ",
        "pointer": "Ayrıntı gerekirse tahmin etme, kayda bak: ham kayıt {transcript}; iz kaydı {trail}. Eski bir "
                   "işi önce ara: {cmd} search <sözcükler> (bütün sohbetlerin kaydı, kaynaklı birkaç sonuç; birini "
                   "açmak için {cmd} show <kaynak>).",
        "pasted": "[yapıştırılan metin, {n} karakter]",
    },
}


def _boundary(rows: list) -> int:
    """Where the stretch since the last compaction starts."""
    start = 0
    for i, r in enumerate(rows):
        if r.get("type") == "system" and r.get("subtype") == "compact_boundary":
            start = i + 1
    return start


def _item(content, status) -> dict:
    return {"content": " ".join(str(content or "").split())[:120], "status": str(status or "pending")}


def _plan(items: list, call: dict) -> list:
    """The desktop app's plan tool: a full list replaces, advance/done/start move the statuses."""
    if isinstance(call.get("items"), list):
        return [_item(i.get("content"), i.get("status")) for i in call["items"] if isinstance(i, dict)]
    items = [dict(i) for i in items]
    if call.get("advance"):
        cur = next((i for i in items if i["status"] == "in_progress"), None)
        if cur:
            cur["status"] = "completed"
        nxt = next((i for i in items if i["status"] == "pending"), None)
        if nxt:
            nxt["status"] = "in_progress"
    for n in call.get("done") or []:
        if isinstance(n, int) and 0 < n <= len(items):
            items[n - 1]["status"] = "completed"
    start = call.get("start")
    if isinstance(start, int) and 0 < start <= len(items):
        items[start - 1]["status"] = "in_progress"
    return items


def tasks(rows: list) -> list:
    """The task list as it stands at the end of the rows, from whichever task tool was used last: TodoWrite (the
    whole list each time), TaskCreate and TaskUpdate (one task at a time, its number in the result), or the desktop
    app's plan tool. The whole tail is read, not only the stretch since the last compaction: a list set before it is
    still the list."""
    plan, made, numbered, seen, last = [], {}, {}, set(), "plan"
    for r in rows:
        if r.get("isSidechain"):  # a subagent's own list
            continue
        for b in common.blocks(r):
            key = (b.get("type"), b.get("id") or b.get("tool_use_id"))
            if key[1] and key in seen:  # a call can be written twice; replaying both would move a step too far
                continue
            seen.add(key)
            if b.get("type") == "tool_use":
                name, inp = b.get("name", ""), b.get("input") or {}
                if name == "TodoWrite" and isinstance(inp.get("todos"), list):
                    plan = [_item(t.get("content"), t.get("status")) for t in inp["todos"] if isinstance(t, dict)]
                    last = "plan"
                elif name.endswith("update_plan"):
                    plan, last = _plan(plan, inp), "plan"
                elif name == "TaskCreate":
                    made[b.get("id")] = inp.get("subject") or inp.get("description")
                elif name == "TaskUpdate" and str(inp.get("taskId", "")) in numbered:
                    number, last = str(inp["taskId"]), "tasks"
                    if inp.get("status") == "deleted":
                        numbered.pop(number)
                    elif inp.get("status"):
                        numbered[number]["status"] = str(inp["status"])
                    if inp.get("subject") and number in numbered:
                        numbered[number]["content"] = _item(inp["subject"], "")["content"]
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in made:
                subject = made.pop(b["tool_use_id"])
                m = re.search(r"Task #(\w+) created", common.result_text(b))
                if m:
                    numbered[m.group(1)], last = _item(subject, "pending"), "tasks"
    return list(numbered.values()) if last == "tasks" else plan


def trail(transcript: Path) -> dict:
    rows = common.tail_rows(transcript, TAIL_BYTES)
    window = rows[_boundary(rows):]
    words, edited, commits, tests, final = [], Counter(), [], [], ""
    seen, commit_calls, test_calls = set(), set(), set()
    for r in window:
        if r.get("isCompactSummary"):
            continue
        said = common.user_text(r)
        if said:
            if not common.scripted(r):
                words.append({"at": str(r.get("timestamp", ""))[:16], "text": said})
            continue
        for b in common.blocks(r):
            key = (b.get("type"), b.get("id") or b.get("tool_use_id"))
            if key[1] and key in seen:
                continue
            seen.add(key)
            if b.get("type") == "tool_use":
                name, inp = b.get("name", ""), b.get("input") or {}
                if name in EDIT_TOOLS:
                    path = str(inp.get("file_path") or inp.get("notebook_path") or "?")
                    if not SCRATCH.search(path):
                        edited[path] += 1
                elif name in ("Bash", "PowerShell"):
                    cmd = str(inp.get("command", ""))
                    if re.search(r"\bgit\b[^\n]*\bcommit\b", cmd):
                        commit_calls.add(b.get("id"))
                    if TEST_CMD.search(cmd):
                        test_calls.add(b.get("id"))
            elif b.get("type") == "tool_result":
                text = common.result_text(b)
                found = [{"hash": h, "subject": s.strip()} for _, h, s in COMMIT_OUT.findall(text)]
                if not found and b.get("tool_use_id") in commit_calls:
                    found = [{"hash": h, "subject": s.strip()} for h, s in ONELINE.findall(text)][-1:]
                commits.extend(c for c in found if all(c["hash"] != x["hash"] for x in commits))
                if b.get("tool_use_id") in test_calls:  # only a test run's own summary lines
                    tests.extend(ln.strip()[:160] for ln in text.splitlines() if TEST_LINE.search(ln.strip()))
            elif (b.get("type") == "text" and r.get("type") == "assistant" and not r.get("isSidechain")
                  and b.get("text", "").strip()):
                final = b["text"].strip()
    lang = common.lang(" ".join(PASTED.sub(" ", w["text"]) for w in words))
    words = words[-8:]
    for w in words:
        w["text"] = PASTED.sub(lambda m: TEXT[lang]["pasted"].format(n=len(m.group(0))), w["text"])[:600]
    return {"lang": lang, "user": words, "edited": edited.most_common(15), "commits": commits[-12:],
            "tests": list(dict.fromkeys(tests))[-4:], "plan": tasks(rows), "final": final[-1500:],
            "rows": len(window)}


def _trails(session: str) -> list:
    return sorted((common.DATA / "episodes" / session).glob("*.json")) if session else []


def precompact(data: dict) -> None:
    session = str(data.get("session_id", ""))
    transcript = common.resolve(str(data.get("transcript_path", "")), session)
    if not transcript or not session:
        return
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ep = {"session": session, "at": at, "trigger": data.get("trigger", ""), "transcript": str(transcript),
          **trail(transcript)}
    out = common.DATA / "episodes" / session
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{at.replace(':', '')}.json").write_text(json.dumps(ep, ensure_ascii=False, indent=1), encoding="utf-8")


def postcompact(data: dict) -> None:
    files = _trails(str(data.get("session_id", "")))
    summary = data.get("compact_summary")
    if files and isinstance(summary, str) and summary.strip():
        ep = json.loads(files[-1].read_text(encoding="utf-8"))
        ep["summary"] = summary[:40000]
        files[-1].write_text(json.dumps(ep, ensure_ascii=False, indent=1), encoding="utf-8")


def note(ep: dict, trail_file: Path) -> str:
    """The note put back after compaction: what the summary is likely to have lost, most important first, and
    where to look for the rest."""
    t = TEXT.get(ep.get("lang"), TEXT["en"])
    parts = [t["head"].format(at=common.local(ep.get("at", ""), "%H:%M"))]
    if ep.get("user"):
        parts.append(t["user"] + "\n" + "\n".join(
            f'- [{common.local(w["at"], "%H:%M")}] "{w["text"]}"' for w in ep["user"]))
    open_items = [i for i in ep.get("plan", []) if i.get("status") not in ("completed", "deleted")]
    if open_items:
        parts.append(t["open"] + "\n" + "\n".join(
            f'- [{t.get(i["status"], i["status"])}] {i["content"]}' for i in open_items))
    if ep.get("edited"):
        parts.append(t["edited"] + ", ".join(p + (f" (×{n})" if n > 1 else "") for p, n in ep["edited"]))
    if ep.get("commits"):
        parts.append(t["commits"] + "; ".join(f'{c["hash"]} {c["subject"]}' for c in ep["commits"]))
    if ep.get("tests"):
        parts.append(t["tests"] + " | ".join(ep["tests"]))
    if ep.get("final"):
        parts.append(t["final"] + '"' + ep["final"][-700:] + '"')
    pointer = t["pointer"].format(transcript=ep.get("transcript", "?"), trail=Path(trail_file).as_posix(),
                                  cmd=common.command())
    body = "\n\n".join(parts)
    room = NOTE_CHARS - len(pointer) - 2
    if len(body) > room:  # the pointer is what lets the rest be found again, so the body gives way
        body = body[:room - 1] + "…"
    return body + "\n\n" + pointer


def sessionstart(data: dict) -> None:
    if data.get("source") != "compact":
        return
    files = _trails(str(data.get("session_id", "")))
    if not files:
        return
    ep = json.loads(files[-1].read_text(encoding="utf-8"))
    try:
        age = (datetime.now(timezone.utc) - datetime.strptime(ep["at"], "%Y-%m-%dT%H:%M:%SZ")
               .replace(tzinfo=timezone.utc)).total_seconds()
    except (KeyError, ValueError):
        return
    if age <= FRESH_S:  # an older trail means this compaction left none; its note would be stale
        common.emit({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                            "additionalContext": note(ep, files[-1])}})
