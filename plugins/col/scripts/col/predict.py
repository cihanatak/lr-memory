"""Prediction ledger: the expected result is written before a long job or a step that cannot be taken back, and
compared with the result when it comes.

Asked to predict in writing and check itself, a model skips the ritual (in the setup COL comes from, a gate the model
filled in itself was skipped 10,420 times) and rates its own success far too high (agents that succeed 22% of the time
predict 77%: arXiv 2602.06948). So the parts that matter are mechanical:
- a background job, or a command that cannot be taken back, does not start without a measurable prediction in its
  description (gate);
- the comparison is computed here from the numbers, like with like, never taken from the model's word, and a result
  counts as grounded only when its number appears in real tool output;
- the record goes back to the model: a due result is asked for at the next prompt, and a new session in a folder
  starts with that folder's track record.

Lines: "Prediction [key]: <what> <number | range | at least / at most number> (~<time>)" and "Result [key]: <what was
observed>"; the Turkish "Öngörü [anahtar]: …" and "Sonuç [anahtar]: …" read the same. A "Hypothesis [key]: …" is a
rival explanation under test: its miss rules it out and is not counted as a calibration error.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone

from col import common
from col.text import t

LEDGER = "predictions.jsonl"
# not glued to a letter, a digit or @: "RL4" and "v2" are names and "validation@30" a parameter, not values
NUM = r"(?<![\w@])-?\d+(?:[.,]\d+)*"
KIND = {"öngörü": "prediction", "beklenti": "prediction", "prediction": "prediction", "hipotez": "hypothesis",
        "hypothesis": "hypothesis", "sonuç": "result", "result": "result"}
_WORD = "|".join(KIND)
# a marker opens a line ("**Prediction [t1]:** ..."), or, carrying a [key], sits anywhere in it ("The run is done.
# Result [t1]: 41"); an unkeyed one inside a sentence is prose
MARK = re.compile(rf"^[\W_]*(?P<w1>{_WORD})\**\s*(?:\[(?P<k1>[^\]\n]{{1,24}})\])?\s*\**\s*:\s*\**"
                  rf"|(?<=\s)(?P<w2>{_WORD})\s*\[(?P<k2>[^\]\n]{{1,24}})\]\s*:", re.I | re.M)
IN_DESC = re.compile(r"(?:öngörü|beklenti|prediction|expected|expectation)\s*(?:\[([^\]]{1,24})\])?\s*:\s*(.+)",
                     re.I)
CLOCK = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")  # "22:00"; "22.00" would swallow decimals like 1.25
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
# a version or a list ("col 0.1.0", "v2.1.308", "steps 1,2,3") is no quantity, and float() cannot read it; a
# thousands grouping ("1.234.567") is one
SERIES = re.compile(r"(?<![\w@.,])v?\d+([.,])\d+(?:\1\d+)+(?![.,]?\d)", re.I)
# waits, watchers and servers run in the background too, but they have no result to predict
NOT_A_JOB = re.compile(r"\bsleep\b|Start-Sleep|^\s*(?:until|while)\b|tail\s+-f|-Wait\b|http\.server|"
                       r"\b(?:npm|pnpm|yarn|bun)\b[^|;&\n]*?\s(?:run\s+)?(?:dev|preview|start|serve)(?=\s|$)|\bvite\b|"
                       r"expo start|\bserve\b|\b(?:uvicorn|gunicorn|jupyter|tensorboard|ngrok)\b|flask\s+run|"
                       r"docker(?:-compose|\s+compose)\s+up|bek[cç]i|bekle|watch|monitor", re.I)
_GIT = r"\bgit\b(?:\s+-[Cc]\s+\S+|\s+--?[\w.-]+(?:=\S+)?)*\s+"
# steps that cannot be taken back or that reach the outside world; they need a prediction even in the foreground
IRREVERSIBLE = re.compile(
    rf"{_GIT}push\b(?![^|;&\n]*--dry-run)|{_GIT}reset\s+--hard\b|{_GIT}clean\s+-\w*f|"
    r"\bgh\s+(?:release\s+create|pr\s+merge|repo\s+delete)\b|"
    r"\b(?:npm|pnpm|cargo|poetry)\s+publish\b(?![^|;&\n]*--dry-run)|\byarn\s+npm\s+publish\b|\btwine\s+upload\b|"
    r"\bdocker\s+push\b|\bterraform\s+(?:apply|destroy)\b|\bkubectl\s+(?:apply|delete)\b(?![^|;&\n]*--dry-run)|"
    r"\bfirebase\s+deploy\b|\bvercel\b[^|;&\n]*--prod|\bnetlify\s+deploy\b[^|;&\n]*--prod|\bgh-pages\s+-\w*d\b|"
    r"\bkaggle\s+(?:competitions\s+submit|kernels\s+push|datasets\s+(?:create|version))\b", re.I)
STOP = {"sonuç", "öngörü", "beklenti", "ortalama", "için", "ile", "olarak", "kadar", "sonra", "önce", "arası",
        "civarı", "yaklaşık", "result", "prediction", "the", "and", "with", "for", "from", "about", "than", "that",
        "this", "was", "were", "are", "will"}
# a quantity is compared like with like: a time with a time (in seconds), a percentage with a percentage, a count
# with a count of the same thing; "4-9 min" against "168 s" once produced a rule that was 60 times wrong
TIME_UNIT = {"ms": 0.001, "milisaniye": 0.001, "s": 1, "sn": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
             "saniye": 1, "min": 60, "mins": 60, "minute": 60, "minutes": 60, "dk": 60, "dakika": 60, "h": 3600,
             "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600, "sa": 3600, "saat": 3600, "day": 86400,
             "days": 86400, "gün": 86400}
DURATION = re.compile(rf"~\s*({NUM})\s*({'|'.join(sorted(TIME_UNIT, key=len, reverse=True))})\b", re.I)
QTY = re.compile(rf"(?P<p1>%\s*)?(?P<apx>~|≈)?\s*(?P<a>{NUM})(?:\s*(?:–|—|-|ile|ila|to)\s*(?P<b>{NUM}))?"
                 rf"(?:\s*/\s*\d+)?(?P<p2>\s*%)?(?:'[^\W\d_]+)?(?:\s*(?P<word>[^\W\d_]+))?", re.I)
WITHIN = re.compile(r"^\s*(?:'?[^\W\d_]*\s+)?(?:içinde|altında|altı|veya az|en çok|or less|or fewer|at most)\b", re.I)
AT_MOST = re.compile(r"(?:en çok|en fazla|at most|no more than|within|under|≤|<=)\s*$", re.I)
AT_LEAST = re.compile(r"(?:en az|en düşük|at least|no less than|≥|>=)\s*$", re.I)
OR_MORE = re.compile(r"\s*(?:ve üstü|ve üzeri|üstünde|veya fazla|or more|and up|\+)", re.I)
# "(the 35-45 min prediction missed)" repeats the forecast inside a result; it is not an observation
ECHO = re.compile(r"\([^)]*(?:öngörü|tahmin|beklenti|predict|forecast|expected)[^)]*\)", re.I)


def num(s: str, tr: bool = False) -> float:
    """A written number as a value. With both marks the last one is the decimal mark ('1.234,5', '1,234.5'). One mark
    that repeats, or that every group after it follows with exactly three digits, groups thousands in the writer's
    convention: Turkish with dots ('51.713' is 51713), English with commas ('1,234' is 1234); otherwise it is the
    decimal mark ('49,88' and '49.88' are both 49.88)."""
    s = s.strip()
    sign, s = (-1.0, s[1:]) if s.startswith("-") else (1.0, s)
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(",", ".")
    elif "," in s or "." in s:
        mark = "," if "," in s else "."
        parts = s.split(mark)
        grouped = all(len(p) == 3 for p in parts[1:]) and (len(parts) > 2 or mark == ("." if tr else ","))
        s = s.replace(mark, "") if grouped else s.replace(",", ".")
    return sign * float(s)


def _plain(text: str) -> str:
    text = SERIES.sub(lambda m: m.group(0) if all(len(p) == 3 for p in re.split(r"[.,]", m.group(0))[1:]) else " ",
                      text)
    return CLOCK.sub(" ", DATE.sub(" ", text))


def expectation(text: str, tr: bool = False) -> tuple:
    """(low, high) a prediction allows overall, or (None, None) when it names no number. The '(~<time>)' that says
    when the result is due is not the value: '41 passed (~1 sec)' expects 41."""
    s = re.sub(r"\(\s*~[^)]*\)", " ", _plain(text))
    ranges = re.findall(rf"({NUM})\s*(?:–|—|-|ile|ila|to)\s*({NUM})", s)
    if ranges:  # the last one: the subject ("v1.1", "3 runs") comes before the expected value
        a, b = num(ranges[-1][0], tr), num(ranges[-1][1], tr)
        return min(a, b), max(a, b)
    m = re.search(rf"(?:en az|en düşük|at least|≥|>=|>)\s*%?\s*({NUM})"
                  rf"|({NUM})\s*(?:ve üstü|ve üzeri|veya fazla|or more)", s, re.I)
    if m:
        return num(m.group(1) or m.group(2), tr), float("inf")
    m = re.search(rf"(?:en çok|en fazla|at most|≤|<=|<)\s*%?\s*({NUM})|({NUM})\s*(?:ve altı|veya az|or less|or fewer)",
                  s, re.I)
    if m:
        return float("-inf"), num(m.group(1) or m.group(2), tr)
    found = re.findall(NUM, s)
    if found:  # one value: the last number, allowing 10%
        v = num(found[-1], tr)
        return v - abs(v) * 0.1, v + abs(v) * 0.1
    return None, None


def quantities(text: str, expected: bool, tr: bool = False) -> list:
    """The numbers of a line with what they measure: kind 'time' (in seconds), '%', or a count labelled by the word
    after it; `name` is the word before, which pairs percentages and durations ("test-id %40-70")."""
    s = ECHO.sub(" ", _plain(text))
    out = []
    for m in QTY.finditer(s):
        a, b, word = num(m.group("a"), tr), m.group("b"), (m.group("word") or "").lower()
        low, high = (min(a, num(b, tr)), max(a, num(b, tr))) if b else (a, a)
        before = re.findall(r"[^\W\d_]+", s[:m.start()].lower())
        near = re.findall(r"[^\W\d_]+", s[max(0, m.start() - 30):m.start()].lower())
        if word in TIME_UNIT:
            kind, label, low, high = "time", "time", low * TIME_UNIT[word], high * TIME_UNIT[word]
        elif m.group("p1") or m.group("p2"):
            kind, label = "%", "%"
        else:
            kind, label = "count", word or (before[-1] if before else "")
        if expected and not b:
            rest, head = s[m.end():], s[:m.start()]
            if m.group("apx") or re.search(r"(?:yaklaşık|civarı|about|around|roughly)\s*$", head, re.I):
                low, high = low - abs(low) * 0.1, high + abs(high) * 0.1
            elif WITHIN.search(rest) or AT_MOST.search(head):
                low = float("-inf")
            elif AT_LEAST.search(head) or OR_MORE.match(rest):
                high = float("inf")
            elif not float(a).is_integer() or abs(a) > 1000:
                low, high = low - abs(low) * 0.1, high + abs(high) * 0.1
        out.append({"kind": kind, "label": label[:4], "low": low, "high": high, "written": m.group("a"),
                    "name": near[-1] if near else ""})
    return out


def compare(prediction: str, result: str, tr: bool = False) -> tuple:
    """(verdict, details). Every expected quantity that has a like-for-like observation is checked, and the
    prediction held only if all of them held. Percentages and durations pair first by the word before them, then in
    the order written; an observation is used once. Without any such pair: 'not comparable', never a guess."""
    exp, obs = quantities(prediction, True, tr), quantities(result, False, tr)

    def fits(e, o):  # three letters keep the stem across tenses: "geçer" and "geçti", "passes" and "passed"
        return o["kind"] == e["kind"] and (e["kind"] in ("time", "%") or e["label"][:3] == o["label"][:3])

    paired, used = {}, set()
    for named in (True, False):
        for k, e in enumerate(exp):
            # a count is named by its own label already ("227 segments"); the word before is for % and durations
            i = next((i for i, o in enumerate(obs) if k not in paired and i not in used and fits(e, o)
                      and (not named or (e["kind"] != "count" and e["name"] and e["name"] == o["name"]))), None)
            if i is not None:
                paired[k] = i
                used.add(i)
    pairs = [(exp[k], obs[i]) for k, i in sorted(paired.items())]
    if not pairs and len(exp) == 1 and [o for o in obs if o["kind"] == exp[0]["kind"]]:
        pairs = [(exp[0], next(o for o in obs if o["kind"] == exp[0]["kind"]))]  # one number each: compare them
    details = []
    for e, o in pairs:
        v = o["low"]
        held = e["low"] <= v <= e["high"]
        details.append({"label": e["label"], "expected": [e["low"], e["high"]], "observed": v, "written": o["written"],
                        "held": held, **({"name": e["name"]} if e["kind"] == "%" and e["name"] else {}),
                        **({} if held else {"direction": "low" if v < e["low"] else "high"})})
    if not details:
        return "not comparable", []
    return ("held" if all(d["held"] for d in details) else "missed"), details


def _due(text: str, at: datetime) -> str | None:
    """When the result should be in: a clock time in this machine's time zone ("~22:00"), else a duration ("~2 min")
    after the prediction."""
    m = CLOCK.search(text)
    if m:
        local = at.astimezone()
        due = local.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        return common.iso(due if due >= local else due + timedelta(days=1))
    m = DURATION.search(text)
    if m:
        return common.iso(at + timedelta(seconds=num(m.group(1)) * TIME_UNIT[m.group(2).lower()]))
    return None


def rows() -> list:
    return common.read_log(LEDGER[:-6])


def _append(record: dict) -> None:
    common.DATA.mkdir(parents=True, exist_ok=True)
    with open(common.DATA / LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": common.now(), **record}, ensure_ascii=False) + "\n")


def open_predictions(session: str, ledger: list | None = None) -> list:
    ledger = rows() if ledger is None else ledger
    closed = {r.get("key") for r in ledger if r.get("type") == "result" and r.get("session") == session}
    return [r for r in ledger if r.get("type") == "prediction" and r.get("session") == session
            and r.get("key") not in closed]


def _words(text: str) -> set:
    return {w for w in re.findall(r"[^\W\d_]{3,}", text.lower()) if w not in STOP}


def record_prediction(session: str, cwd: str, key: str, body: str, source: str, ledger: list,
                      kind: str = "prediction", lang: str = "en") -> None:
    text = body.strip()[:300]
    mine = [r for r in ledger if r.get("type") == "prediction" and r.get("session") == session]
    waiting = {r.get("key") for r in open_predictions(session, ledger)}
    # a message that names an open prediction restates it ("I retried with `Prediction [check]: 41 passed`")
    if any(r.get("text") == text for r in mine) or (source == "message" and (key or "").strip() in waiting):
        return
    key = (key or "").strip() or f"P{len(mine) + 1}"
    if any(r.get("key") == key for r in mine):  # a reused key starts a new prediction
        key = f"{key}-{len(mine) + 1}"
    low, high = expectation(body, lang == "tr")
    rec = {"type": "prediction", "kind": kind, "session": session, "cwd": cwd, "key": key, "text": text,
           "low": low, "high": high, "due": _due(body, datetime.now(timezone.utc)), "source": source, "lang": lang}
    _append(rec)
    ledger.append(rec)


def record_result(session: str, cwd: str, key: str, body: str, results, ledger: list, lang: str = "en") -> None:
    candidates = open_predictions(session, ledger)
    if not candidates:
        return
    k = (key or "").strip().lower()
    target = next((p for p in candidates if k and str(p.get("key", "")).lower() == k), None)
    if target is None and not k:  # an unkeyed result names its prediction by the words they share
        words = _words(body)
        best = max(candidates, key=lambda p: len(_words(p["text"]) & words))
        target = best if _words(best["text"]) & words else None
    if target is None:
        return
    verdict, details = compare(target["text"], body, (target.get("lang") or lang) == "tr")
    first = next((d for d in details if not d["held"]), details[0] if details else {})
    written = first.get("written")
    seen = results() if callable(results) else results
    grounded = bool(written) and any(v in seen for v in {written, written.replace(",", "."), written.replace(".", ",")})
    rec = {"type": "result", "kind": target.get("kind", "prediction"), "session": session, "cwd": cwd,
           "key": target["key"], "text": body.strip()[:300], "observed": first.get("observed"), "verdict": verdict,
           "grounded": grounded, "expected": first.get("expected", [None, None]), "prediction": target["text"],
           "details": details}
    if verdict == "missed":
        rec["direction"] = {"label": first["label"], "way": first["direction"]}
    _append(rec)
    ledger.append(rec)


def marks(text: str) -> list:
    """(kind, key, body) of every marker; a body runs to the end of its line or to the next marker in it. A marker
    inside inline code is quoted, not written: "I'll write `Result [t1]: <observed>`" closes nothing."""
    found = list(MARK.finditer(text))
    out = []
    for i, m in enumerate(found):
        word = m.start("w1") if m.group("w1") else m.start("w2")
        if text[text.rfind("\n", 0, word) + 1: word].count("`") % 2:
            continue
        end = text.find("\n", m.end())
        end = len(text) if end < 0 else end
        if i + 1 < len(found) and found[i + 1].start() < end:
            end = found[i + 1].start()
        body = text[m.end():end].strip().strip("*").strip()
        if body:
            out.append((KIND[(m.group("w1") or m.group("w2")).lower()], m.group("k1") or m.group("k2"), body))
    return out


def update(session: str, cwd: str, texts: list, results, lang: str = "en") -> None:
    """Record the predictions and the results written in this turn's messages. A turn is read again at every stop,
    so what is already in the ledger is skipped."""
    found = marks("\n".join(x for x in texts if x))
    if not found:
        return
    ledger = rows()
    for kind, key, body in found:
        if kind != "result" and re.search(r"\d", body):
            record_prediction(session, cwd, key, body, "message", ledger, kind, lang)
    # rival hypotheses share one observed value, so a repeat is the same key with the same text, not the text alone
    seen = {(str(r.get("key")).lower(), r.get("text")) for r in ledger
            if r.get("type") == "result" and r.get("session") == session}
    for kind, key, body in found:
        k, text = (key or "").strip().lower(), body.strip()[:300]
        # a plain "Result:" heading is not a result: it needs a number or a key that names the prediction
        if kind != "result" or not (k or re.search(r"\d", text)):
            continue
        if (k, text) in seen or (not k and any(x == text for _, x in seen)):
            continue
        seen.add((k, text))
        record_result(session, cwd, key, body, results, ledger, lang)


def _code_only(cmd: str) -> str:
    """The command without heredoc bodies, here-strings and quoted text: a commit message that mentions "git push"
    does not push."""
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\s*\1\b", " ", cmd, flags=re.S)
    cmd = re.sub(r"@'.*?'@|@\".*?\"@", " ", cmd, flags=re.S)
    return re.sub(r"'[^'\n]*'|\"(?:\\.|[^\"\\\n])*\"", " ", cmd)


def gate(session: str, cwd: str, tool: str, inp: dict, lang: str = "en"):
    """The reason to refuse a background job, or a step that cannot be taken back, started without a measurable
    prediction; None lets it run and records the prediction. The prediction goes in the description, so a subagent
    can meet the rule too."""
    if tool not in ("Bash", "PowerShell"):
        return None
    cmd = str(inp.get("command", ""))
    final = IRREVERSIBLE.search(_code_only(cmd))
    if not final and (not inp.get("run_in_background") or NOT_A_JOB.search(cmd)):
        return None
    m = IN_DESC.search(str(inp.get("description", "")))
    if m and re.search(r"\d", m.group(2)):
        record_prediction(session, cwd, m.group(1), m.group(2), "command", rows(), "prediction", lang)
        return None
    from col.keyscan import redact  # a command line can carry a key; the log keeps only its shape
    common.log("gate", {"session": session, "tool": tool, "kind": "final" if final else "job",
                        "command": redact(cmd)[:120]})
    return t(lang, "gate_final", step=" ".join(final.group(0).split())) if final else t(lang, "gate_job")


def reminder(session: str, state: dict, lang: str = "en") -> str:
    """This session's open predictions whose time has come (their due time passed, or 12 hours went by without one),
    each brought back once."""
    now = datetime.now(timezone.utc)
    cutoff, week, told = common.iso(now - timedelta(hours=12)), common.iso(now - timedelta(days=7)), set(
        state.get("reminded", []))
    late = [p for p in open_predictions(session) if p.get("key") not in told and p.get("at", "") >= week
            and ((p.get("due") or "9") <= common.iso(now) or (not p.get("due") and p.get("at", "") <= cutoff))][:3]
    if not late:
        return ""
    state["reminded"] = sorted(told | {p["key"] for p in late})
    return "\n".join([t(lang, "due_head"), *(f"- [{p['key']}] {p['text'][:140]}" for p in late), t(lang, "due_tail")])


def _folder(path: str) -> str:
    return os.path.normcase(os.path.normpath(path)) if path else ""


def calibration(cwd: str, lang: str = "en", last: int = 50) -> str:
    """One line on how this folder's recent predictions turned out, once there are five to speak of."""
    here = _folder(cwd)
    done = [r for r in rows() if r.get("type") == "result" and r.get("kind") != "hypothesis"
            and r.get("verdict") in ("held", "missed") and here and _folder(r.get("cwd", "")) == here][-last:]
    if len(done) < 5:
        return ""
    held = sum(r["verdict"] == "held" for r in done)
    details = [d for r in done for d in r.get("details", [])]
    misses = [d for d in details if not d.get("held")]
    line = t(lang, "calibration", held=held, n=len(done))
    if misses:
        line += t(lang, "calibration_misses", low=sum(d.get("direction") == "low" for d in misses),
                  high=sum(d.get("direction") == "high" for d in misses))
    timed = [d for d in details if d.get("label") == "time"]
    short = sum(d.get("direction") == "low" for d in timed if not d.get("held"))
    long_ = sum(d.get("direction") == "high" for d in timed if not d.get("held"))
    if short or long_:
        line += t(lang, "calibration_time", short=short, long=long_, timed=len(timed))
    return line
