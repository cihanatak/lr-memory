"""The cue: before Claude reads a prompt, the turns of this project's earlier sessions that the prompt brings back.

The recall skill is a search the model has to think of, and a model that does not know what it is missing never
thinks of it. On a bench day 2 it wrote "nothing in the repo says why" and asked for a reason the user had given the
day before, with the skill loaded and unused. The cue runs the same search on every prompt instead, the way a cue
brings back a memory: the prompt's words find the earlier turns that share them, and each comes back whole, what the
user said and what was answered, since the answer is where a measured number lives. It spends no model tokens; what it
adds to the context is a few hundred.
"""
from __future__ import annotations

import bisect
import json
import os
import time
from pathlib import Path

from . import archive, common

KINDS = ("user", "assistant", "commit", "summary", "report")
TURNS = 3  # turns per prompt at most
MIN_TERMS = 3  # query terms a prompt must have, and a turn's best hit must carry
FLOOR = 0.35  # a turn that scores under this share of the best one stays out
BUDGET_S = 8.0  # indexing per prompt; a session start indexes the rest in the background
SAID, ANSWER = 600, 260  # characters of each; a longer one shows its part that carries the prompt's words. Five in
# six of the messages a user typed fit whole in SAID, on the machine this was built on.
TEXT = {
    "en": {"head": "LR Memory: turns of this project's earlier sessions that this prompt brings back, verbatim. Where "
                   "they disagree with the code or with what the user says now, those win.",
           "said": "the user said", "answer": "answer", "more": "The whole turn: {cmd} show <ref>"},
    "tr": {"head": "LR Memory: bu projenin önceki oturumlarından, bu isteğin geri getirdiği turlar, birebir. Kodla ya da "
                   "kullanıcının şimdi söylediğiyle çelişirlerse onlar geçerlidir.",
           "said": "kullanıcı", "answer": "yanıt", "more": "Turun tamamı: {cmd} show <ref>"},
}


def off() -> bool:
    return os.environ.get("LR_MEMORY_CUE", "").strip().lower() in ("0", "off", "false", "no")


def _line(ref: str) -> int:
    return int(ref.rpartition(":")[2] or 0)


def _index(project: Path, budget: float = BUDGET_S) -> None:
    """Index what this project's transcripts gained since the last run, newest first, within the budget."""
    start, con = time.time(), archive.connect()
    try:
        known = dict(con.execute("select path, size from files").fetchall())
        for path in sorted(project.glob("*.jsonl"), key=archive._mtime, reverse=True):
            if time.time() - start > budget:
                break
            try:
                if known.get(str(path)) != path.stat().st_size:
                    archive._index_file(con, path)
            except OSError:  # deleted or locked meanwhile; the next prompt takes it
                continue
    finally:
        con.close()


def _reply(path: Path, start: int, end: int) -> str:
    """The last text the assistant wrote in the turn from line start to line end (0: the file's end), the reply the
    user read. Read from the transcript: the index leaves out short texts, and a reply that gives a number often is
    one."""
    last = ""
    try:
        with open(path, "rb") as f:
            for n, raw in enumerate(f, 1):
                if end and n >= end:
                    break
                if n <= start or b'"assistant"' not in raw or len(raw) > archive.MAX_LINE:
                    continue
                try:
                    row = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(row, dict) and row.get("type") == "assistant" and not row.get("isSidechain"):
                    last = next((b["text"] for b in reversed(common.blocks(row))
                                 if b.get("type") == "text" and str(b.get("text", "")).strip()), last)
    except OSError:
        pass
    return " ".join(last.split())


def turns(prompt: str, session: str, project: Path, skip: set = frozenset()) -> list:
    """The best turns of the project's earlier sessions for this prompt, best first: [{ref, at, said, answer}]. A
    turn is a user message and what followed it; it scores as its best hit by BM25, which weighs a match by its
    length, so that a long reply sharing many of a prompt's common words does not outrank a message sharing its rare
    ones."""
    terms = archive._terms(prompt)
    earlier = {p.stem for p in project.glob("*.jsonl")} - {session}
    if len(terms) < MIN_TERMS or not earlier:
        return []
    hits = [h for h in archive.search(prompt, k=200, kinds=",".join(KINDS), within=sorted(earlier))
            if h["hits"] >= MIN_TERMS]
    if not hits:
        return []
    con = archive.connect()
    try:
        starts, best = {}, {}
        for h in hits:
            s = h["session"]
            if s not in starts:
                starts[s] = sorted(_line(r) for (r,) in con.execute(
                    "select ref from docs where session = ? and kind in ('user', 'prompt')", (s,)))
            i = bisect.bisect_right(starts[s], _line(h["ref"])) - 1
            key = f"{s}:{starts[s][i] if i >= 0 else _line(h['ref'])}"
            end = starts[s][i + 1] if i + 1 < len(starts[s]) else 0  # where the next turn starts
            if key not in skip and (key not in best or h["bm25"] < best[key][0]["bm25"]):  # bm25: lower is better
                best[key] = (h, end)
        ranked = sorted(best.items(), key=lambda kv: kv[1][0]["bm25"])
        pats = [archive._pattern(w) for w in archive._words(terms)]
        out = []
        for key, (h, end) in ranked[:TURNS]:
            if h["bm25"] > FLOOR * ranked[0][1][0]["bm25"]:
                break
            s, start = key.rpartition(":")[0], _line(key)
            said = con.execute("select text from docs where session = ? and ref = ? and kind in ('user', 'prompt')",
                               (s, key)).fetchone()
            if h["kind"] == "user" and said:  # found by what the user said: what was answered comes with it
                answer = _reply(project / f"{s}.jsonl", start, end)
                answer = answer if len(answer) <= ANSWER else archive.snippet(answer, pats, ANSWER)
            else:
                answer = archive.snippet(h["text"], pats, ANSWER)
            text = " ".join((said[0] if said else "").split())
            text = text if len(text) <= SAID else archive.snippet(text, pats, SAID)
            out.append({"ref": key, "at": h["at"], "said": text, "answer": answer})
        return out
    finally:
        con.close()


def render(found: list, sample: str) -> str:
    t = TEXT[common.lang(sample)]
    lines = [t["head"]]
    for x in found:
        where = f"{common.local(x['at'])} {x['ref'].rpartition(':')[0][:8]}:{_line(x['ref'])}"
        lines.append(f"- {where}, {t['said']}: {x['said']}" if x["said"] else f"- {where}")
        lines.append(f"  {t['answer']}: {x['answer']}")
    return "\n".join(lines + [t["more"].format(cmd=common.command())])


def prompt(data: dict) -> None:
    """The UserPromptSubmit hook: put the turns the prompt brings back in front of the model, each turn once a
    session."""
    text, session, path = str(data.get("prompt") or ""), str(data.get("session_id") or ""), \
        str(data.get("transcript_path") or "")
    if off() or not text.strip() or not path:
        return
    project = Path(path).parent
    shown_file = common.DATA / "cue" / f"{session or 'none'}.json"
    try:
        shown = set(json.loads(shown_file.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        shown = set()
    _index(project)
    found = turns(text, session, project, shown)
    if not found:
        return
    shown_file.parent.mkdir(parents=True, exist_ok=True)
    shown_file.write_text(json.dumps(sorted(shown | {x["ref"] for x in found})), encoding="utf-8")
    common.emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": render(found, text)}})
