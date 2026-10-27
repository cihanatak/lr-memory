"""A search index over every past Claude Code session: find how something was done, decided or said.

The transcripts Claude Code keeps (~/.claude/projects/<project>/<session>.jsonl) stay the record; this is an index
into them, not a copy. What goes in is what a person would search for, never bulk tool output:
  user       the user's own words                   assistant  what the assistant wrote (notes and answers)
  commit     hash and subject from git's output     step       a command's description and its first line
  summary    Claude Code's compaction summary       report     a subagent's report as it came back
  memory     Claude Code's memory files              prompt     a script's prompt (claude -p, the Agent SDK)
Long texts go in as parts of about 1,500 characters, so a summary cannot outrank a precise hit by sheer length.
Matching is lexical (SQLite FTS5) over case- and accent-folded text. A query word is cut to its first five letters,
which for Turkish works about as well as a full stemmer (Can et al., JASIST 2008): "düzeltmiştik" finds
"düzeltme", and "comparator" finds "compare". The whole word, when a hit has it, outranks the cut one. A name made
of parts (listed_commits, predict.py, 58.2) is matched whole, as a phrase. Local, no model tokens: every search
first indexes what was appended since the last one.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import common, keys

FOLD = str.maketrans({"ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c",
                      "ö": "o", "Ö": "o", "ü": "u", "Ü": "u", "â": "a", "Â": "a", "î": "i", "Î": "i", "û": "u",
                      "Û": "u", "’": "'"})
MAX_LINE = 1 << 20  # rows larger than this carry images or bulk tool output, never indexed
CHUNK = 1500
BUDGET_S = 40.0  # a search indexes at most this long, newest sessions first; the rest waits for the next run
STALE_LOCK_S = 3600
COMMIT_OUT = re.compile(r"\[([\w./+-]+) ([0-9a-f]{7,12})\] ([^\n]{1,160})")
WEIGHT = {"memory": 1.3, "commit": 1.3, "user": 1.1, "summary": 0.9, "report": 0.9, "step": 0.6, "prompt": 0.6}
# a search is not work; indexed, it would find itself
SEARCH_CALL = re.compile(r"(?:lrm\.py|run\.sh)[\"']?\s+(?:search|show)\b")
NAME = re.compile(r"[^\\/:*?\"<>|]+")
STOP = {"bir", "ve", "ile", "icin", "bu", "su", "da", "de", "ki", "mi", "mu", "ne", "nasil", "neden", "niye", "ben",
        "biz", "sen", "siz", "peki", "evet", "yani", "ama", "gibi", "daha", "once", "sonra", "gecen", "sefer", "hani",
        "neydi", "nedir", "olan", "oldu", "olmustu", "yaptik", "yapmistik", "yaptin", "yapmistin", "yaptim",
        "yapmistim", "ettik", "etmistik", "dedik", "demistik", "dedim", "demistim", "hatirliyor", "musun", "misin",
        "the", "and", "for", "how", "what", "did", "was", "were", "with", "that", "this", "have", "has", "had", "you",
        "we", "our", "us", "is", "it", "its", "of", "to", "in", "on", "at", "by", "as", "be", "an", "or", "do", "does",
        "are", "from", "when", "where", "which", "who", "why", "remember", "py", "md", "js", "ts", "json", "jsonl",
        "txt", "html"}
TEXT = {
    "en": {"terms": "terms: ",
           "pending": "(the index is still being built: {n} older session files are not in it yet; search again to "
                      "cover them)",
           "none": "Nothing found. Search again with other words: a synonym, the other language, a file, function "
                   "or error name. Do not guess.",
           "more": "open one: {cmd} show <ref>",
           "fts": "lr-memory needs SQLite with FTS5, and this Python's SQLite lacks it."},
    "tr": {"terms": "terimler: ",
           "pending": "(dizin hâlâ kuruluyor: eski {n} oturum dosyası henüz içinde değil; onları da kapsamak için "
                      "yeniden ara)",
           "none": "Bulunamadı. Başka sözcüklerle ara: eş anlamlısı, öbür dildeki karşılığı, dosya, işlev ya da hata "
                   "adı. Tahmin etme.",
           "more": "birini aç: {cmd} show <kaynak>",
           "fts": "lr-memory FTS5'li SQLite ister; bu Python'un SQLite'ında yok."},
}
LABELS = {
    "en": {"user": "user", "prompt": "script", "assistant": "assistant", "command": "command", "file": "file",
           "missing": "not found: a ref is <session>:<row> or memory:<project>/<name>, as a hit prints it, and its "
                      "file must still exist",
           "empty": "no text in these rows"},
    "tr": {"user": "kullanıcı", "prompt": "betik", "assistant": "asistan", "command": "komut", "file": "dosya",
           "missing": "bulunamadı: kaynak, bir sonucun yazdığı gibi <oturum>:<satır> ya da memory:<proje>/<ad> "
                      "olmalı ve dosyası durmalı",
           "empty": "bu satırlarda metin yok"},
}


def fold(text: str) -> str:
    return text.translate(FOLD).lower()  # one character for one, so positions in the fold match the text


def connect() -> sqlite3.Connection:
    common.DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(common.DATA / "index.db", timeout=60, isolation_level=None)  # transactions are explicit
    con.execute("pragma journal_mode=wal")
    con.execute("create table if not exists files (path text primary key, offset integer, line integer, size integer)")
    con.execute("create table if not exists meta (key text primary key, value text)")
    con.execute("create table if not exists seen (hash text primary key)")
    con.execute("create virtual table if not exists docs using fts5(norm, text unindexed, kind unindexed, "
                "session unindexed, at unindexed, ref unindexed, tokenize='unicode61 remove_diacritics 2')")
    return con


def _fresh() -> dict:
    return {"seen": set(), "agents": set(), "commits": set()}


def _docs(row: dict, state: dict) -> list:
    """(kind, text) pairs worth finding later in one transcript row."""
    if row.get("isSidechain"):  # a subagent's own turns; its report arrives in the main line
        return []
    if row.get("isCompactSummary"):
        return [("summary", "\n".join(common.texts(row)))]
    said = common.user_text(row)
    if said:
        return [("prompt" if common.scripted(row) else "user", said)]
    if row.get("type") == "user":
        joined = "\n".join(common.texts(row)).lstrip()
        if joined.startswith("<task-notification>"):
            m = re.search(r"<result>(.*?)</result>", joined, re.S)
            return [("report", m.group(1))] if m else []
    out = []
    for b in common.blocks(row):
        if b.get("type") == "text" and row.get("type") == "assistant" and len(b.get("text", "")) >= 80:
            out.append(("assistant", b["text"]))
        elif b.get("type") == "tool_use" and b.get("id") not in state["seen"]:  # a call can be written twice
            state["seen"].add(b.get("id"))
            inp = b.get("input") or {}
            cmd = str(inp.get("command", ""))
            if b.get("name") in ("Bash", "PowerShell") and inp.get("description") and not SEARCH_CALL.search(cmd):
                out.append(("step", f"{inp['description']}\n{cmd.splitlines()[0][:300]}" if cmd.strip()
                            else inp["description"]))
            elif b.get("name") in ("Agent", "Task"):
                state["agents"].add(b.get("id"))
        elif b.get("type") == "tool_result":
            text = common.result_text(b)
            if b.get("tool_use_id") in state["agents"] and len(text) >= 300:  # not the "started in background" stub
                out.append(("report", text))
            for branch, h, subject in COMMIT_OUT.findall(text[:20000]):
                if h not in state["commits"]:
                    state["commits"].add(h)
                    out.append(("commit", f"{h} {subject} ({branch})"))
    return out


def _chunks(text: str) -> list:
    """A long text in parts of about CHUNK characters, cut at blank lines where it can be."""
    out, cur = [], ""
    for para in re.split(r"\n\s*\n", text):
        for piece in [para[i:i + CHUNK] for i in range(0, len(para), CHUNK)] or [""]:
            if cur and len(cur) + len(piece) > CHUNK:
                out.append(cur)
                cur = ""
            cur = f"{cur}\n\n{piece}" if cur else piece
    if cur.strip():
        out.append(cur)
    return out


def _rows(path: Path, offset: int, line_no: int):
    """(line number, offset after it, row or None) for each whole line from offset on; a half-written last line
    waits for the next run."""
    with open(path, "rb") as f:
        f.seek(offset)
        for raw in iter(f.readline, b""):
            if not raw.endswith(b"\n"):
                return
            offset += len(raw)
            line_no += 1
            row = None
            if len(raw) <= MAX_LINE:
                try:
                    row = json.loads(raw)
                except ValueError:
                    pass
            yield line_no, offset, row if isinstance(row, dict) else None


def _key(kind: str, text: str, at: str) -> str:
    return hashlib.sha1(f"{kind}\0{'' if kind == 'prompt' else at}\0{text}".encode("utf-8")).hexdigest()[:20]


def _first(con: sqlite3.Connection, kind: str, text: str, at: str) -> bool:
    """True the first time a text is seen. A forked or resumed session copies its parent's rows, and a script can
    send the same prompt hundreds of times (measured: 17% of all parts were exact repeats, 70% of the prompts); the
    same words at another time are kept, because when something was said matters."""
    return con.execute("insert or ignore into seen (hash) values (?)", (_key(kind, text, at),)).rowcount == 1


def _index_file(con: sqlite3.Connection, path: Path) -> int:
    """Index the rows appended since the last run; rows already indexed are never read again."""
    con.execute("begin immediate")  # one writer at a time: two searches at once must not index a row twice
    try:
        size = path.stat().st_size
        got = con.execute("select offset, line from files where path = ?", (str(path),)).fetchone()
        offset, line_no = got or (0, 0)
        if offset > size:  # the file was rewritten: index it again from the start
            gone = con.execute("select kind, text, at from docs where session = ?", (path.stem,)).fetchall()
            con.executemany("delete from seen where hash = ?", [(_key(k, t, a),) for k, t, a in gone])
            con.execute("delete from docs where session = ?", (path.stem,))
            offset, line_no = 0, 0
        state, docs, boundary = _fresh(), [], ""
        for line_no, offset, row in _rows(path, offset, line_no):
            if row is None:
                continue
            at = str(row.get("timestamp", ""))[:16]
            if row.get("subtype") == "compact_boundary":
                boundary = at
            try:
                found = _docs(row, state)
            except Exception:  # a row of an unexpected shape must not stop the index
                continue
            for kind, text in found:
                for part in _chunks(keys.mask(text.strip())):
                    if part.strip() and _first(con, kind, part, at):
                        docs.append((fold(part), part, kind, path.stem, at, f"{path.stem}:{line_no}"))
        con.executemany("insert into docs (norm, text, kind, session, at, ref) values (?, ?, ?, ?, ?, ?)", docs)
        if boundary:  # where this session's last compaction is, so a search from it can skip what is in context
            con.execute("insert or replace into meta (key, value) values (?, ?)", (f"boundary:{path.stem}", boundary))
        con.execute("insert or replace into files (path, offset, line, size) values (?, ?, ?, ?)",
                    (str(path), offset, line_no, size))
        con.execute("commit")
        return len(docs)
    except BaseException:
        con.execute("rollback")
        raise


def _index_memory(con: sqlite3.Connection) -> int:
    """Claude Code's memory files (~/.claude/projects/<project>/memory/*.md), read again only when one changed."""
    files = sorted(common.PROJECTS.glob("*/memory/*.md"))
    sig = f"{len(files)}:{max((p.stat().st_mtime_ns for p in files), default=0)}"
    if con.execute("select value from meta where key = 'memory'").fetchone() == (sig,):
        return 0
    docs = []
    for p in files:
        at = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M")
        for part in _chunks(keys.mask(p.read_text(encoding="utf-8", errors="replace"))):
            docs.append((fold(f"{p.stem}\n{part}"), part, "memory", "", at, f"memory:{p.parent.parent.name}/{p.stem}"))
    con.execute("begin immediate")
    con.execute("delete from docs where kind = 'memory'")
    con.executemany("insert into docs (norm, text, kind, session, at, ref) values (?, ?, ?, ?, ?, ?)", docs)
    con.execute("insert or replace into meta (key, value) values ('memory', ?)", (sig,))
    con.execute("commit")
    return len(files)


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def update(budget: float | None = None, clock=time.time) -> dict:
    """Index what was appended since the last run, newest sessions first. With a budget in seconds, the files left
    when it runs out wait for the next run."""
    t, con, n, files, left = clock(), connect(), 0, 0, 0
    try:
        known = dict(con.execute("select path, size from files").fetchall())
        for path in sorted(common.PROJECTS.glob("*/*.jsonl"), key=_mtime, reverse=True):
            try:
                if known.get(str(path)) == path.stat().st_size:
                    continue
                if budget is not None and clock() - t > budget:
                    left += 1
                    continue
                n += _index_file(con, path)
                files += 1
            except OSError:  # deleted or locked meanwhile; the next run takes it
                continue
        memory = _index_memory(con)
    finally:
        con.close()
    return {"new_docs": n, "files": files, "pending_files": left, "memory_files": memory,
            "seconds": round(clock() - t, 1)}


def background_update() -> dict | None:
    """An update that runs once at a time across sessions: a lock file marks the running one, and a lock older than
    an hour is taken for a run that died."""
    common.DATA.mkdir(parents=True, exist_ok=True)
    lock = common.DATA / "update.lock"
    try:
        if time.time() - lock.stat().st_mtime > STALE_LOCK_S:
            lock.unlink()
    except OSError:
        pass
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError:
        return None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return update()
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def spawn_update() -> None:
    """Start `lrm.py update --background` detached, so that a session's first search finds the index ready."""
    if os.environ.get("LR_MEMORY_NO_SPAWN"):
        return
    cmd = [sys.executable, str(Path(__file__).resolve().parent.parent / "lrm.py"), "update", "--background"]
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "close_fds": True}
    if os.name != "nt":
        subprocess.Popen(cmd, start_new_session=True, **kw)
        return
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:  # outlive the hook even when Claude Code closes the job it ran the hook in
        subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kw)
    except OSError:  # the job does not allow breaking away
        subprocess.Popen(cmd, creationflags=flags, **kw)


def _terms(query: str) -> list:
    """A query's index terms as (term, whole word) pairs. A name made of parts joined by _ . - is a phrase of its
    whole parts; any other word is folded, its suffix after an apostrophe dropped and cut to five letters, with the
    whole word kept beside it so that the exact form can outrank its stem ("notebooklm" was once lost among
    hundreds of "notebook" hits). A slash separates alternatives."""
    out = []
    for w in re.findall(r"[^\W_]+(?:[_.-][^\W_]+)*", re.sub(r"'[^\W_]+", "", fold(query))):
        parts = re.split(r"[_.-]", w)
        if len(parts) > 1:
            out.append((" ".join(parts),) * 2)
        elif len(w) >= 2 and w not in STOP:
            out.append((w[:5], w))
    return list(dict.fromkeys(out))


def _words(terms: list) -> list:
    return list(dict.fromkeys(w for pair in terms for w in pair))


def _exact(term: str) -> bool:
    return " " in term or len(term) == 2  # a phrase, or a two-letter word (db, ui, js): whole words only


def _fts(term: str) -> str:
    return f'"{term}"' if _exact(term) else f'"{term}"*'


def _pattern(term: str) -> re.Pattern:
    return re.compile(r"(?<![^\W_])" + r"[\W_]+".join(map(re.escape, term.split()))
                      + (r"(?![^\W_])" if _exact(term) else ""))


def search(query: str, k: int = 8, kinds: str = "", since: str = "", session: str = "") -> list:
    """The best k hits. A hit scores the rarity (IDF) of each query term it carries, the whole word's when it has
    that and the stem's otherwise, so one exact name outweighs several common words; BM25 weighted by kind breaks
    ties."""
    terms = _terms(query)
    if not terms:
        return []
    con, words = connect(), _words(terms)
    try:
        total = max(1, con.execute("select max(rowid) from docs").fetchone()[0] or 1)  # near enough, and instant
        idf = {w: math.log(1 + (total - df + 0.5) / (df + 0.5)) for w, (df,) in
               ((w, con.execute("select count(*) from docs where docs match ?", (_fts(w),)).fetchone()) for w in words)}
        sql, args = "select text, kind, session, at, ref, bm25(docs) from docs where docs match ?", \
            [" OR ".join(map(_fts, words))]
        kind_list = [x.strip() for x in kinds.split(",") if x.strip()]
        if kind_list:
            sql += f" and kind in ({','.join('?' * len(kind_list))})"
            args += kind_list
        if since:
            sql += " and at >= ?"
            args.append(since)
        if session:
            sql += " and session like ?"
            args.append(session + "%")
        current = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
        if current and not session:
            # what this session said since its last compaction is in context already; as a hit (the question
            # just asked, above all) it would only repeat itself
            got = con.execute("select value from meta where key = ?", (f"boundary:{current}",)).fetchone()
            sql += " and not (session = ? and at >= ?)"
            args += [current, got[0] if got else ""]
        rows = con.execute(sql + " order by bm25(docs) limit 200", args).fetchall()
    finally:
        con.close()
    pats = {w: _pattern(w) for w in words}
    ranked = []
    for t, kd, s, a, r, b in rows:
        folded = fold(t)
        found = [idf[full] if pats[full].search(folded) else idf[stem] if pats[stem].search(folded) else 0.0
                 for stem, full in terms]
        ranked.append({"text": t, "kind": kd, "session": s, "at": a, "ref": r, "hits": sum(1 for f in found if f),
                       "score": round(sum(found), 2), "bm25": b * WEIGHT.get(kd, 1.0)})
    ranked.sort(key=lambda h: (-h["score"], h["bm25"]))  # bm25 is negative: lower is better
    seen, best = set(), []
    for h in ranked:
        hit_keys = {h["text"].split()[0] if h["kind"] == "commit" else h["ref"]}
        if h["session"]:
            hit_keys.add((h["session"], h["at"], h["kind"]))  # one minute of one session often says a thing twice
        if hit_keys & seen:
            continue
        seen |= hit_keys
        best.append(h)
        if len(best) == k:
            break
    return best


def snippet(text: str, pats: list, width: int = 240) -> str:
    """The window of the text that carries the most query terms."""
    folded = fold(text)
    found = sorted((m.start(), i) for i, p in enumerate(pats) for m in p.finditer(folded))[:200]
    best, start = -1, 0
    for pos, _ in found:
        s = max(0, pos - width // 4)
        n = len({i for q, i in found if s <= q < s + width})
        if n > best:
            best, start = n, s
    piece = " ".join(text[start:start + width].split())
    return ("…" if start else "") + piece + ("…" if start + width < len(text) else "")


def report(query: str, k: int = 8, kinds: str = "", since: str = "", session: str = "") -> str:
    """What a search prints: the terms as matched, then each hit with its kind, local time, ref and snippet."""
    t = TEXT[common.lang(query)]
    stats = update(budget=BUDGET_S)
    terms = _terms(query)
    hits = search(query, k, kinds, since, session)
    out = [t["terms"] + ", ".join(f'"{s}"' if " " in s else s if _exact(s) else s + "*" for s, _ in terms)]
    if stats["pending_files"]:
        out.append(t["pending"].format(n=stats["pending_files"]))
    if not hits:
        return "\n".join(out + [t["none"]])
    pats = [_pattern(w) for w in _words(terms)]
    out += [f"{i}. [{h['kind']}] {common.local(h['at'])} {where(h)} — {snippet(h['text'], pats)}"
            for i, h in enumerate(hits, 1)]
    return "\n".join(out + [t["more"].format(cmd=common.command())])


def where(hit: dict) -> str:
    """How a hit is named for show(): memory:<project>/<name>, or the session's first 8 characters and the row."""
    return hit["ref"] if hit["kind"] == "memory" else f"{hit['session'][:8]}:{hit['ref'].rpartition(':')[2]}"


def show(ref: str, around: int = 40, budget: int = 7000, lang: str = "en") -> str:
    """The turn around a hit: what the user and the assistant wrote within `around` rows, and the commands run and
    files changed right next to it, without tool output. Over budget, the rows nearest the hit are kept."""
    lab = LABELS.get(lang, LABELS["en"])
    if ref.startswith("memory:"):
        project, _, name = ref[7:].rpartition("/")
        p = common.PROJECTS / project / "memory" / f"{name}.md"
        ok = NAME.fullmatch(project) and NAME.fullmatch(name) and ".." not in ref and p.is_file()
        return keys.mask(p.read_text(encoding="utf-8", errors="replace"))[:8000] if ok else lab["missing"]
    session, _, line = ref.rpartition(":")
    ok = re.fullmatch(r"[0-9A-Za-z-]+", session) and line.isdigit()
    paths = sorted(common.PROJECTS.glob(f"*/{session}*.jsonl")) if ok else []
    if not paths:
        return lab["missing"]
    want, entries = int(line), []
    with open(paths[0], "rb") as f:
        for n, raw in enumerate(f, 1):
            if n > want + around:
                break
            if n < want - around or len(raw) > MAX_LINE:
                continue
            try:
                row = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(row, dict) or row.get("isSidechain"):
                continue
            when, near, lines = common.local(str(row.get("timestamp", ""))), abs(n - want) <= 6, []
            said = common.user_text(row)
            if said:
                lines.append(f"[{lab['prompt'] if common.scripted(row) else lab['user']} {when}] {said[:1200]}")
            for b in common.blocks(row) if not said else []:
                inp = b.get("input") or {}
                if b.get("type") == "text" and row.get("type") == "assistant" and b.get("text", "").strip():
                    lines.append(f"[{lab['assistant']} {when}] {b['text'].strip()[:1200]}")
                elif near and b.get("type") == "tool_use" and b.get("name") in ("Bash", "PowerShell"):
                    lines.append(f"[{lab['command']}] {inp.get('description') or str(inp.get('command', ''))[:160]}")
                elif near and b.get("type") == "tool_use" and b.get("name") in ("Edit", "Write", "NotebookEdit"):
                    lines.append(f"[{lab['file']}] {inp.get('file_path') or inp.get('notebook_path', '')}")
            if n == want and not lines:
                lines = [f"[{kind} {when}] {text.strip()[:1200]}" for kind, text in _docs(row, _fresh())]
            entries += [(abs(n - want), n, f"{'>>' if n == want else '  '} {keys.mask(x)}") for x in lines]
    keep, used = set(), 0
    for dist, n, x in sorted(entries, key=lambda e: e[0]):
        if used + len(x) > budget:
            break
        keep.add((n, x))
        used += len(x) + 1
    out = []
    for _, n, x in entries:
        if (n, x) in keep and (not out or out[-1] != x):  # the same command or file twice in a row reads once
            out.append(x)
    return "\n".join(out) or lab["empty"]
