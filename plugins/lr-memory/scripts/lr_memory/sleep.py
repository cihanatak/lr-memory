"""Sleep: once a day, what the user said becomes the memory Claude Code loads in every session.

Claude Code keeps a memory folder per project (~/.claude/projects/<project>/memory/: one file per fact, and MEMORY.md,
the index each session reads). A pass reads what the user said in each project since the last pass, asks Claude once
per project which of it should last, checks every proposal against the record, and writes what holds up there.

- A directive, a standing rule, preference or prohibition the user stated in so many words, is written the same day.
- A lesson inferred from what happened waits as a candidate, which no session sees, until a later pass backs it with
  evidence it did not have. One not backed again within two weeks fades; one the evidence contradicts is withdrawn.
  Replay strengthens a wrong generalisation as readily as a right one: in the runtime this was cut from, one misread
  measurement once became a rule sixty times off.
- Every proposal quotes the user word for word or cites a commit made in these sessions; anything else is dropped.
  An update appends and never rewrites, a retire needs the user's own words, and a changed file is backed up first.

One `claude -p` call per project with new messages: no tools, no MCP servers, no hooks, no session record. Its prompt
is the project's memory index and the new messages, so its cost in tokens follows how much was said.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import common, keys, note

MAX_APPLY = 6  # changes per project and pass
MAX_PROJECTS = 5  # projects per pass, most messages first; the rest keep their window for the next pass
CANDIDATE_DAYS = 14
FIRST_HOURS = 24  # how far back a project's first pass reads
MAX_HOURS = 7 * 24  # and how far back any pass reads
DAILY_S = 20 * 3600  # with LR_MEMORY_SLEEP=daily, a session start runs a pass when the last one began this long ago
RUN_LOCK_S = 2 * 3600
MAX_LINE = 1 << 20
MESSAGE_CHARS = 1500
MESSAGES_CHARS = 100_000  # the newest messages that fit; older ones in a longer window are not read
DESCRIPTION_CHARS = 120
INDEX_LINE_CHARS = 200  # Claude Code asks for index entries under ~200 characters
INDEX_LINES, INDEX_BYTES = 200, 25_000  # past these, sessions read only part of MEMORY.md
BUSY_S = 120  # MEMORY.md written this recently: a session is writing memory now
DREAM_LOCK_S = 3600  # Claude Code's own consolidation (auto-dream) holds .consolidate-lock while it runs
TYPES = ("user", "feedback", "project", "reference")
NAME = re.compile(r"[a-z0-9][a-z0-9-]*\.md")
PASSWORD = re.compile(r"\b(?:password|passwd|parola|şifre)\s*[:=]\s*\S+", re.I)
# what makes a child claude take itself for part of the session that started it
SESSION_VARS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION",
                "CLAUDE_CODE_HOST_SESSION_ID", "CLAUDE_CODE_SSE_PORT", "CLAUDE_PID")
USAGE = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
LOGIN = re.compile(r"not logged in|/login|failed to authenticate|authentication_error|invalid api key|\b401\b", re.I)

SCHEMA = {
    "type": "object",
    "properties": {
        "proposals": {"type": "array", "items": {"type": "object", "properties": {
            "action": {"enum": ["add", "update", "retire"]},
            "file": {"type": "string"},
            "type": {"enum": list(TYPES)},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "body": {"type": "string"},
            "index_line": {"type": "string"},
            "basis": {"enum": ["directive", "lesson"]},
            "scope": {"type": "string"},
            "repeat_of": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "object", "properties": {
                "kind": {"enum": ["user", "commit"]}, "id": {"type": "string"}, "quote": {"type": "string"},
                "hash": {"type": "string"}}, "required": ["kind"]}},
        }, "required": ["action", "file", "basis", "evidence"]}},
        "withdraw": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": ["proposals", "summary"],
}

PROMPT = """You keep the long-term memory of an AI coding assistant (Claude Code) that works with one user. Once a day
you turn what happened in one of their projects into memory that lasts, the way sleep consolidates a day: keep rules,
not events.

Below: (1) the project's memory index (MEMORY.md) and each memory file's one-line description, (2) the user's own
messages in this project since the last pass, each with an id and a time, (3) the commits made in these sessions,
(4) the lessons waiting as candidates from earlier passes.

Propose at most {max_apply} changes:
- add: a rule or fact the user stated, or a correction they made, that no existing file covers.
- update: an existing file needs a new fact or a correction; give only the text to append (it goes under a dated
  heading; nothing is rewritten).
- retire: only when the user said in so many words that a rule is wrong or obsolete.
Set repeat_of to an existing file's name when the user had to correct something that file already covers: that rule
did not hold.

Rules:
- Evidence is mandatory: copy the user's words exactly (at least 15 characters) with the message id, or cite a
  commit hash from the list. No evidence, no proposal.
- basis: "directive" when the user states a standing rule, preference or prohibition in so many words (quote it);
  "lesson" when you infer it from what happened (a correction of one piece of work, a failure, the commits). A
  directive is written today. A lesson waits as a candidate and becomes a rule only when a later pass backs it: to
  back a waiting candidate, propose it again with the same file name and evidence from this window. Never back a
  candidate without new evidence.
- withdraw: names of waiting candidates that this window's evidence shows to be wrong.
- One fact per file. Write rules, not diaries: the rule, then a **Why:** line and a **How to apply:** line.
- type: user (who the user is), feedback (how to work with them), project (this project's goals, decisions and
  constraints), reference (where to find things).
- file: lowercase words joined by hyphens, ending in .md, e.g. feedback-short-answers.md.
- description: one line on when the memory matters. index_line: - [Short title](file-name.md) — one-line hook, under
  200 characters.
- scope: "general" for a rule that holds for all work, otherwise what it applies to.
- Write the memory files and the summary in the language of the user's messages above, in the style of the existing
  files. Use they/them for anyone whose pronouns are unknown.
- Never store secrets, tokens, passwords or other people's personal data.
- Routine progress, status updates and one-off task details are not memories. If nothing durable happened, propose
  nothing.
- summary: two or three plain sentences for the user on what you kept and why. A lesson only waits: say it is
  waiting, never that it was added.

Today is {today}.

## Memory index (MEMORY.md)
{index}

## Memory files
{files}

## The user's messages
{messages}

## Commits
{commits}

## Candidate lessons (waiting; no session sees them)
{candidates}
"""

TEXT = {
    "en": {"head": "# LR Memory sleep {at}", "dry": "Dry run: nothing was written.",
           "read": "Read {messages} messages and {commits} commits in {projects} projects. Cost: {tokens} tokens "
                   "(input {inp}, output {out}).",
           "nothing": "No new messages since the last pass.", "since": "since {at}", "model": "Model: {m}.",
           "dropped": "{n} older messages did not fit into one pass and were not read.",
           "written": "Written to memory", "waiting": "Lessons waiting (no session sees them)",
           "rejected": "Rejected", "repeats": "Rules that did not hold (the user had to say it again)",
           "closed": "Closed candidates", "basis": {"directive": "directive", "lesson": "lesson"},
           "state": {"new": "new", "seen": "seen again, no new evidence"}, "nights": "{n} night(s)",
           "withdrawn": "withdrawn", "faded": "faded", "later": "Left for the next pass: {names}",
           "skip": {"off": "Skipped: auto memory is off in Claude Code's settings.",
                    "busy": "Skipped: MEMORY.md changed in the last two minutes; a session is writing memory.",
                    "dream": "Skipped: Claude Code's own memory consolidation is running."},
           "error": "Failed: {e}",
           "login": "Failed: the claude command that sleep starts is not signed in. Sleep cannot use the login of "
                    "the session it runs from, because Claude Code keeps that login out of the shell it gives to "
                    "tools and hooks. Sign in once in a terminal (run `claude`, then `/login`), or set "
                    "LR_MEMORY_CLAUDE to a claude that is signed in.",
           "index": "MEMORY.md has {lines} lines ({kb} KB). Sessions read only part of a long index: move detail "
                    "into topic files.",
           "saved": "Report: {path}", "update": "**Update ({today}, sleep):** {body}\n",
           "why": {"evidence": "no evidence", "quote": "the quote is not word for word in {x}",
                   "commit": "unknown commit {x}", "kind": "unknown kind of evidence", "name": "bad file name {x}",
                   "exists": "an add of a file that exists", "missing": "{x} of a missing file",
                   "words": "needs the user's own words", "body": "empty body",
                   "index": "an add needs a type and an index line under 200 characters that links to its file",
                   "secret": "looks like a secret", "limit": "the limit of {x} changes per pass was reached"}},
    "tr": {"head": "# LR Memory uykusu {at}", "dry": "Deneme: hiçbir şey yazılmadı.",
           "read": "{projects} projede {messages} mesaj ve {commits} commit okundu. Maliyet: {tokens} token "
                   "(girdi {inp}, çıktı {out}).",
           "nothing": "Son geçişten beri yeni mesaj yok.", "since": "{at} sonrası", "model": "Model: {m}.",
           "dropped": "Bir geçişe sığmayan {n} eski mesaj okunmadı.",
           "written": "Hafızaya yazılanlar", "waiting": "Bekleyen dersler (hiçbir oturum görmez)",
           "rejected": "Reddedilenler", "repeats": "Tutmayan kurallar (kullanıcı yeniden söylemek zorunda kaldı)",
           "closed": "Kapanan adaylar", "basis": {"directive": "talimat", "lesson": "ders"},
           "state": {"new": "yeni", "seen": "yine görüldü, yeni kanıt yok"}, "nights": "{n} gece",
           "withdrawn": "geri çekildi", "faded": "söndü", "later": "Sonraki geçişe kalan: {names}",
           "skip": {"off": "Atlandı: Claude Code ayarlarında otomatik hafıza kapalı.",
                    "busy": "Atlandı: MEMORY.md son iki dakikada değişti; bir oturum hafızaya yazıyor.",
                    "dream": "Atlandı: Claude Code'un kendi hafıza birleştirmesi çalışıyor."},
           "error": "Başarısız: {e}",
           "login": "Başarısız: uykunun başlattığı claude komutunda oturum açık değil. Uyku, içinden çalıştığı "
                    "oturumun girişini kullanamaz; Claude Code o girişi araçlara ve kancalara verdiği kabuktan "
                    "çıkarır. Bir kez terminalde giriş yap (`claude`, ardından `/login`) ya da LR_MEMORY_CLAUDE "
                    "değişkenini oturumu açık bir claude'a yönlendir.",
           "index": "MEMORY.md {lines} satır ({kb} KB). Oturumlar uzun bir dizinin yalnız bir kısmını okur: "
                    "ayrıntıyı konu dosyalarına taşı.",
           "saved": "Rapor: {path}", "update": "**Güncelleme ({today}, uyku):** {body}\n",
           "why": {"evidence": "kanıt yok", "quote": "alıntı {x} içinde birebir yok", "commit": "bilinmeyen commit {x}",
                   "kind": "bilinmeyen kanıt türü", "name": "geçersiz dosya adı {x}",
                   "exists": "var olan bir dosyaya ekleme", "missing": "olmayan bir dosyada {x}",
                   "words": "kullanıcının kendi sözlerini ister", "body": "boş metin",
                   "index": "ekleme bir tür ve kendi dosyasına bağlanan, 200 karakterden kısa bir dizin satırı ister",
                   "secret": "gizli anahtara benziyor", "limit": "geçiş başına {x} değişiklik sınırı doldu"}},
}


class LoginError(RuntimeError):
    """The claude that sleep starts is not signed in; every other project would fail the same way."""


def _dir() -> Path:
    return common.DATA / "sleep"


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _at(stamp) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(stamp or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("＠", "@")).strip().lower()  # the model saw @ disarmed


def memory_dir(project: str) -> Path | None:
    """Where Claude Code keeps a project's memory: autoMemoryDirectory when the user set one, otherwise
    <projects>/<project>/memory; None when auto memory is off."""
    settings = _load(common.CONFIG / "settings.json", {})
    settings = settings if isinstance(settings, dict) else {}
    off = os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "").strip().lower() in ("1", "true", "yes")
    if off or settings.get("autoMemoryEnabled") is False:
        return None
    custom = settings.get("autoMemoryDirectory")
    if isinstance(custom, str) and custom.strip():
        return Path(os.path.expanduser(custom.strip()))
    return common.PROJECTS / project / "memory"


def gather(start_of, only: str = "") -> dict:
    """The user's own words and the commits made, per project, each project read from its own start."""
    found = {}
    for path in common.PROJECTS.glob("*/*.jsonl"):
        project = path.parent.name
        if only and project != only and not project.endswith("-" + only.strip("-")):
            continue
        start = start_of(project)
        try:
            if path.stat().st_mtime < start.timestamp():
                continue
            f = open(path, "rb")
        except OSError:
            continue
        x = found.setdefault(project, {"messages": [], "commits": {}})
        with f:
            for raw in f:
                if len(raw) > MAX_LINE or b'"user"' not in raw:
                    continue
                try:
                    row = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(row, dict) or common.scripted(row):
                    continue
                at = _at(row.get("timestamp"))
                if at is None or at < start:
                    continue
                text = common.user_text(row)
                if text:  # a paste is not the user's own words
                    text = keys.mask(note.PASTED.sub("[pasted]", text)).strip()
                    if len(text) > 2:
                        x["messages"].append({"at": at, "session": path.stem[:8], "text": text[:MESSAGE_CHARS]})
                    continue
                for b in common.blocks(row):
                    if b.get("type") == "tool_result":
                        for _, h, subject in note.COMMIT_OUT.findall(common.result_text(b)[:20000]):
                            x["commits"].setdefault(h, subject.strip())
    return found


def _fit(messages: list) -> tuple:
    """The newest messages that fit into one prompt, oldest first, numbered; and how many older ones did not."""
    msgs, keep, total = sorted(messages, key=lambda m: m["at"]), [], 0
    for m in reversed(msgs):
        total += len(m["text"]) + 40
        if total > MESSAGES_CHARS:
            break
        keep.append(m)
    keep.reverse()
    for i, m in enumerate(keep, 1):
        m["id"] = f"m{i}"
    return keep, len(msgs) - len(keep)


def listing(memdir: Path) -> tuple:
    index = memdir / "MEMORY.md"
    text = index.read_text(encoding="utf-8", errors="replace") if index.exists() else ""
    files = []
    for f in sorted(memdir.glob("*.md")):
        if f.name != "MEMORY.md":
            m = re.search(r"^description:\s*(.+)$", f.read_text(encoding="utf-8", errors="replace"), re.M)
            desc = m.group(1).strip().strip('"') if m else ""
            files.append(f"- {f.name}: {desc[:DESCRIPTION_CHARS]}")
    return text, "\n".join(files)


def prompt(memdir: Path, msgs: list, commits: dict, cands: dict, today: str) -> str:
    index, files = listing(memdir)
    waiting = "\n".join(f"- {f} ({c['proposal'].get('title', '')}): backed on {len(c['nights'])} pass(es) since "
                        f"{c['first']}; evidence: {'; '.join(c['evidence'])[:300]}" for f, c in cands.items())
    return PROMPT.format(
        max_apply=MAX_APPLY, today=today, index=index.strip() or "(none)", files=files or "(none)",
        messages="\n".join(f"[{m['id']}] {m['at'].astimezone().strftime('%Y-%m-%d %H:%M')} ({m['session']}): "
                           f"{m['text']}" for m in msgs),
        commits="\n".join(f"{h}: {s}" for h, s in commits.items()) or "(none)", candidates=waiting or "(none)")


def ask(text: str) -> dict:
    """One `claude -p` call that answers in SCHEMA. The user's settings are read, so that their login, provider and
    model apply, but hooks are off, MCP servers are not started, there are no tools and no session is recorded.
    LR_MEMORY_CLAUDE names another claude: a path, or a JSON list of command words."""
    raw = os.environ.get("LR_MEMORY_CLAUDE", "").strip()
    if not raw and os.environ.get("PYTEST_CURRENT_TEST"):
        raise RuntimeError("refusing to start a real claude under pytest; set LR_MEMORY_CLAUDE")
    cmd = json.loads(raw) if raw.startswith("[") else [raw or shutil.which("claude") or "claude"]
    cmd += ["-p", "Follow the instructions you receive on standard input.",
            "--system-prompt", "You curate an AI assistant's long-term memory. Answer only in the requested structure.",
            "--setting-sources", "user", "--settings", json.dumps({"disableAllHooks": True}), "--strict-mcp-config",
            "--tools", "", "--no-session-persistence", "--output-format", "json", "--json-schema", json.dumps(SCHEMA)]
    if os.environ.get("LR_MEMORY_SLEEP_MODEL", "").strip():
        cmd += ["--model", os.environ["LR_MEMORY_SLEEP_MODEL"].strip()]
    env = {k: v for k, v in os.environ.items() if k not in SESSION_VARS}
    env["LR_MEMORY_NO_SPAWN"] = "1"  # should a hook run after all, it starts nothing
    work = _dir() / "work"  # an empty folder: no project settings, CLAUDE.md or memory of any project
    work.mkdir(parents=True, exist_ok=True)
    # the prompt goes on stdin (a day of messages overflows a Windows command line); an @path in it would make the
    # CLI attach that file, and a full-width at sign reads the same without doing so
    r = subprocess.run(cmd, cwd=work, env=env, input=text.replace("@", "＠"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    try:
        payload = json.loads(r.stdout)
    except ValueError:
        said = (r.stderr or r.stdout).strip()[-300:]
        raise (LoginError if LOGIN.search(said) else RuntimeError)(f"claude exited {r.returncode}: {said}") from None
    if payload.get("is_error"):
        said = str(payload.get("result"))[:300]
        raise (LoginError if LOGIN.search(said) else RuntimeError)(f"claude: {said}")
    data = payload.get("structured_output")
    if not isinstance(data, dict):
        result = str(payload.get("result") or "")
        data = json.loads(result[result.index("{"): result.rindex("}") + 1])
    usage = payload.get("usage") or {}
    data["_usage"] = {k: int(usage.get(k) or 0) for k in USAGE}
    data["_model"] = ", ".join(sorted(payload.get("modelUsage") or {}))
    return data


def verify(p: dict, msgs: list, commits: dict, memdir: Path) -> str:
    """Empty when the proposal may be applied; otherwise why not, as a key of TEXT[...]["why"] (key:detail)."""
    by_id = {m["id"]: _norm(m["text"]) for m in msgs}
    ev = [e for e in p.get("evidence") or [] if isinstance(e, dict)]
    if not ev:
        return "evidence"
    for e in ev:
        if e.get("kind") == "user":
            q = _norm(e.get("quote", ""))
            if len(q) < 15 or q not in by_id.get(e.get("id", ""), ""):
                return f"quote:{e.get('id')}"
        elif e.get("kind") == "commit":
            if e.get("hash") not in commits:
                return f"commit:{e.get('hash')}"
        else:
            return "kind"
    name, action = str(p.get("file", "")), p.get("action")
    if not NAME.fullmatch(name):
        return f"name:{name}"
    exists = (memdir / name).exists()
    if action == "add" and exists:
        return "exists"
    if action in ("update", "retire") and not exists:
        return f"missing:{action}"
    if (action == "retire" or p.get("basis") == "directive") and not any(e.get("kind") == "user" for e in ev):
        return "words"
    if action in ("add", "update") and not str(p.get("body") or "").strip():
        return "body"
    line = str(p.get("index_line") or "").strip()
    if action == "add" and (p.get("type") not in TYPES or not line.startswith("- [") or f"]({name})" not in line
                            or len(line) > INDEX_LINE_CHARS or "\n" in line):
        return "index"
    blob = json.dumps(p, ensure_ascii=False)
    if keys.mask(blob) != blob or PASSWORD.search(blob):
        return "secret"
    return ""


def apply(p: dict, memdir: Path, backup: Path, today: str, lang: str) -> None:
    index, target = memdir / "MEMORY.md", memdir / p["file"]
    backup.mkdir(parents=True, exist_ok=True)
    for f in (index, target):
        if f.exists() and not (backup / f.name).exists():
            shutil.copy2(f, backup / f.name)
    memdir.mkdir(parents=True, exist_ok=True)
    lines = index.read_text(encoding="utf-8").splitlines(keepends=True) if index.exists() else []
    if p["action"] == "add":
        desc = re.sub(r"\s+", " ", str(p.get("description") or p.get("title") or "")).replace('"', "'").strip()
        target.write_text(f"---\nname: {target.stem}\ndescription: \"{desc}\"\nmetadata:\n  type: {p['type']}\n"
                          f"  basis: {p.get('basis')}\n  scope: {p.get('scope') or 'general'}\n"
                          f"  source: lr-memory sleep {today}\n---\n\n{str(p['body']).strip()}\n",
                          encoding="utf-8", newline="\n")
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        header = "## " + p["type"]
        # under the matching section ("## Feedback", "## Feedback (general)"); an index with sections but none for
        # this type gets one, and an index without sections stays a plain list
        at = next((i + 1 for i, ln in enumerate(lines) if ln.strip().lower() == header
                   or ln.lower().startswith(header + " ")), None)
        if at is None:
            if any(ln.startswith("## ") for ln in lines):
                lines += (["\n"] if lines[-1].strip() else []) + [f"## {p['type'].capitalize()}\n"]
            at = len(lines)
        lines.insert(at, p["index_line"].strip() + "\n")
        index.write_text("".join(lines), encoding="utf-8", newline="\n")
    elif p["action"] == "update":
        gap = "\n" if target.read_text(encoding="utf-8", errors="replace").endswith("\n") else "\n\n"
        with target.open("a", encoding="utf-8", newline="\n") as f:
            f.write(gap + TEXT[lang]["update"].format(today=today, body=str(p["body"]).strip()))
    else:
        (memdir / "_retired").mkdir(exist_ok=True)
        shutil.move(str(target), str(memdir / "_retired" / target.name))
        if lines:
            index.write_text("".join(ln for ln in lines if f"]({target.name})" not in ln), encoding="utf-8",
                             newline="\n")


def _evidence(p: dict) -> set:
    """Evidence as it stays from pass to pass: message ids are renumbered each time, the quoted words are not."""
    return {f"user:{_norm(e.get('quote', ''))[:120]}" if e.get("kind") == "user" else f"commit:{e.get('hash')}"
            for e in p.get("evidence") or [] if isinstance(e, dict)}


def back(cands: dict, p: dict, today: str) -> str:
    """Tonight's proposal of a lesson: "new", "seen" (again today, or with no evidence it did not have) or
    "promoted" (backed on a later day by new evidence)."""
    ids, c = _evidence(p), cands.get(p["file"])
    if c is None:
        cands[p["file"]] = {"proposal": p, "first": today, "nights": [today], "evidence": sorted(ids)}
        return "new"
    fresh = ids - set(c["evidence"])
    c["evidence"] = sorted(set(c["evidence"]) | ids)
    if today in c["nights"] or not fresh:
        return "seen"
    c["nights"].append(today)
    c["proposal"] = p  # the newer wording, with the newer evidence
    return "promoted"


def _blank(project: str, start: datetime) -> dict:
    return {"project": project, "since": start.isoformat(), "messages": 0, "dropped": 0, "commits": 0,
            "applied": [], "candidates": [], "rejected": [], "repeats": [], "closed": [], "summary": "", "usage": {},
            "model": "", "skipped": "", "error": "", "index": None}


def _project(out: dict, found: dict, cands: dict, today: str, dry_run: bool, log: list) -> None:
    memdir = memory_dir(out["project"])
    index = memdir / "MEMORY.md" if memdir else None
    if memdir is None:
        out["skipped"] = "off"
    elif index.exists() and time.time() - index.stat().st_mtime < BUSY_S:
        out["skipped"] = "busy"
    elif (memdir / ".consolidate-lock").exists() and \
            time.time() - (memdir / ".consolidate-lock").stat().st_mtime < DREAM_LOCK_S:
        out["skipped"] = "dream"
    if out["skipped"]:
        return
    msgs, out["dropped"] = _fit(found["messages"])
    out["messages"], out["commits"] = len(msgs), len(found["commits"])
    data = ask(prompt(memdir, msgs, found["commits"], cands, today))
    out["usage"], out["model"] = data.get("_usage", {}), data.get("_model", "")
    out["summary"] = str(data.get("summary") or "").strip()
    lang = common.lang(" ".join(m["text"] for m in msgs[-50:]))
    backup = _dir() / "backup" / today / out["project"]
    for p in data.get("proposals") or []:
        if not isinstance(p, dict):
            continue
        if isinstance(p.get("repeat_of"), str) and NAME.fullmatch(p["repeat_of"]) and (memdir / p["repeat_of"]).exists():
            out["repeats"].append(p["repeat_of"])
        reason = verify(p, msgs, found["commits"], memdir)
        if not reason and len(out["applied"]) >= MAX_APPLY:
            reason = f"limit:{MAX_APPLY}"  # a lesson that would have been promoted waits for the next pass
        if reason:
            out["rejected"].append({"action": p.get("action"), "file": p.get("file"), "reason": reason})
            continue
        if p["action"] != "retire" and p.get("basis") != "directive":
            state = back(cands, p, today)
            if state != "promoted":
                out["candidates"].append({"file": p["file"], "state": state, "nights": len(cands[p["file"]]["nights"])})
                continue
            cands.pop(p["file"])
        if not dry_run:
            apply(p, memdir, backup, today, lang)
        out["applied"].append({"action": p["action"], "file": p["file"], "title": str(p.get("title") or ""),
                               "basis": p.get("basis")})
    for f in data.get("withdraw") or []:
        if isinstance(f, str) and f in cands:
            log.append({"at": today, "why": "withdrawn", "project": out["project"], "file": f, **cands.pop(f)})
            out["closed"].append({"file": f, "why": "withdrawn"})
    if index.exists():
        size, lines = index.stat().st_size, index.read_text(encoding="utf-8", errors="replace").count("\n")
        if size > INDEX_BYTES or lines > INDEX_LINES:
            out["index"] = {"lines": lines, "kb": size // 1000}


def run(hours: float | None = None, dry_run: bool = False, only: str = "", now: datetime | None = None) -> dict:
    """One pass over every project with new messages; the report is saved under DATA/sleep/reports."""
    now = now or datetime.now(timezone.utc)
    today, d = now.astimezone().strftime("%Y-%m-%d"), _dir()
    state = _load(d / "state.json", {})
    last = state.setdefault("projects", {})
    if not dry_run:  # a pass that fails still counts as today's try
        state["last_run"] = now.isoformat()
        _save(d / "state.json", state)

    def start_of(project: str) -> datetime:
        if hours is not None:
            return now - timedelta(hours=hours)
        return max(_at(last.get(project)) or now - timedelta(hours=FIRST_HOURS), now - timedelta(hours=MAX_HOURS))

    found = gather(start_of, only)
    active = sorted((p for p in found if found[p]["messages"]), key=lambda p: -len(found[p]["messages"]))
    cands = _load(d / "candidates.json", {})
    log, record = [], {"at": now.isoformat(), "dry_run": dry_run, "projects": [], "later": active[MAX_PROJECTS:],
                       "faded": []}
    for i, project in enumerate(active[:MAX_PROJECTS]):
        out = _blank(project, start_of(project))
        try:
            _project(out, found[project], cands.setdefault(project, {}), today, dry_run, log)
        except LoginError:
            out["error"] = "login"
        except Exception as e:  # one project's failure must not cost the others their pass
            out["error"] = f"{type(e).__name__}: {e}"[:300]
        record["projects"].append(out)
        if not dry_run and not out["error"] and not out["skipped"]:
            last[project] = now.isoformat()
        if out["error"] == "login":  # the rest would fail the same way; they keep their window
            record["later"] = active[i + 1:]
            break
    if not dry_run:
        oldest = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=CANDIDATE_DAYS)).strftime("%Y-%m-%d")
        for project, waiting in cands.items():
            for f in [f for f, c in waiting.items() if c["nights"][-1] < oldest]:
                log.append({"at": today, "why": "faded", "project": project, "file": f, **waiting.pop(f)})
                record["faded"].append({"project": project, "file": f})
        _save(d / "candidates.json", {p: w for p, w in cands.items() if w})
        _save(d / "state.json", state)
        if log:
            with open(d / "candidates-closed.jsonl", "a", encoding="utf-8") as f:
                f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in log)
    stamp = now.astimezone().strftime("%Y-%m-%d_%H%M") + ("_dry" if dry_run else "")
    record["report"] = str(d / "reports" / f"{stamp}.md")
    lang = common.lang(" ".join(m["text"] for x in found.values() for m in x["messages"][-30:]))
    _save(d / "reports" / f"{stamp}.json", record)
    record["text"] = report(record, lang)
    Path(record["report"]).write_text(record["text"], encoding="utf-8", newline="\n")
    return record


def report(record: dict, lang: str) -> str:
    t = TEXT[lang]

    def num(v: int) -> str:
        return f"{v:,}".replace(",", "." if lang == "tr" else ",")

    def why(reason: str) -> str:
        key, _, x = str(reason).partition(":")
        return t["why"].get(key, key).format(x=x)

    ps = record["projects"]
    inp = sum(p["usage"].get(k, 0) for p in ps for k in USAGE[:3])
    out = sum(p["usage"].get("output_tokens", 0) for p in ps)
    lines = [t["head"].format(at=_at(record["at"]).astimezone().strftime("%Y-%m-%d %H:%M")), ""]
    if record["dry_run"]:
        lines += [t["dry"], ""]
    lines.append(t["read"].format(messages=sum(p["messages"] for p in ps), commits=sum(p["commits"] for p in ps),
                                  projects=len(ps), tokens=num(inp + out), inp=num(inp), out=num(out))
                 if ps else t["nothing"])
    models = sorted({p["model"] for p in ps if p["model"]})
    if models:
        lines[-1] += " " + t["model"].format(m=", ".join(models))
    for p in ps:
        since = _at(p["since"]).astimezone().strftime("%Y-%m-%d %H:%M")
        lines += ["", f"## {p['project']} ({t['since'].format(at=since)})"]
        if p["skipped"]:
            lines.append(t["skip"][p["skipped"]])
            continue
        error = t["login"] if p["error"] == "login" else p["error"] and t["error"].format(e=p["error"])
        lines += [x for x in (p["summary"], p["dropped"] and t["dropped"].format(n=p["dropped"]), error) if x]
        for title, items in (
                (t["written"], [f"- {a['action']} `{a['file']}`{' ' + a['title'] if a['title'] else ''} "
                                f"({t['basis'].get(a['basis'], t['basis']['lesson'])})" for a in p["applied"]]),
                (t["waiting"], [f"- {t['state'][c['state']]}: `{c['file']}` ({t['nights'].format(n=c['nights'])})"
                                for c in p["candidates"]]),
                (t["rejected"], [f"- {r['action']} `{r['file']}`: {why(r['reason'])}" for r in p["rejected"]]),
                (t["repeats"], [f"- `{f}`" for f in p["repeats"]]),
                (t["closed"], [f"- {t[c['why']]}: `{c['file']}`" for c in p["closed"]])):
            if items:
                lines += ["", f"{title}:"] + items
        if p["index"]:
            lines += ["", t["index"].format(**p["index"])]
    if record["faded"]:
        lines += ["", f"{t['closed']}:"] + [f"- {t['faded']}: `{x['file']}` ({x['project']})" for x in record["faded"]]
    if record["later"]:
        lines += ["", t["later"].format(names=", ".join(record["later"]))]
    lines += ["", t["saved"].format(path=record["report"])]
    return "\n".join(lines) + "\n"


def due(clock=time.time) -> bool:
    """With LR_MEMORY_SLEEP=daily, whether this session start should run a pass: the last one began DAILY_S ago."""
    if os.environ.get("LR_MEMORY_SLEEP", "").strip().lower() != "daily":
        return False
    last = _at(_load(_dir() / "state.json", {}).get("last_run"))
    return last is None or clock() - last.timestamp() > DAILY_S


def background() -> dict | None:
    """A pass that runs once at a time across sessions; None when another one is running."""
    return common.once("sleep.lock", RUN_LOCK_S, run)
