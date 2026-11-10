"""What the panel shows, read from the user's own files at the moment the page is made. Nothing here has a default
value that looks like data: a source that is not there is reported as missing, a number that was never measured as
unmeasured, and the rows inside the blind window are dropped before anything is counted."""
from __future__ import annotations

import json
import os
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

CACHE_VERSION = 2
# copied verbatim from LR's col/after.py: what a failed shell command prints
FAIL = re.compile(r"\b[1-9]\d* (?:failed|errors?)\b|Traceback \(most recent call last\)|^\s*(?:FAILED|ERROR)\b|"
                  r"^\w*Error: |npm ERR!|^fatal: |^Exit code [1-9]", re.M)
SHELLS = ("Bash", "PowerShell")
HYPOTHESIS = ("Hipotez [", "Hypothesis [")
PRED_TYPE = ("prediction", "öngörü")
RESULT_TYPE = ("result", "sonuç")
HELD = ("held", "tuttu")
MISSED = ("missed", "tutmadı")
UNCOMPARED = ("not comparable", "karşılaştırılamadı")
TURNED_BACK = ("incomplete", "misread", "violation")  # the intent check holds the stop on these verdicts
DAY_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
STAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})T?(\d{2}):?(\d{2}):?(\d{2})")
TOOL_ID = re.compile(rb'"tool_use_id":"([^"]+)"')
ISO_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?)(\.\d+)?(Z|z|[+-]\d{2}:\d{2}|)$")
REPORT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:_(\d{2})(\d{2}))?")


# ---------------------------------------------------------------------------------------------------------- basics

def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def parse_ts(value) -> float | None:
    """An ISO timestamp (2026-10-27T09:50:37.123Z) as seconds since the epoch, or None."""
    if not isinstance(value, str):
        return None
    m = ISO_RE.match(value.strip())
    if not m:
        return None
    base, frac, zone = m.groups()
    zone = "+00:00" if zone in ("", "Z", "z") else zone
    try:
        t = datetime.fromisoformat(base + ("." + (frac[1:] + "000000")[:6] if frac else "") + zone)
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.timestamp()


def iso(ep: float | None) -> str | None:
    if ep is None:
        return None
    return datetime.fromtimestamp(ep, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day(ep: float) -> str:
    """The local day of a moment: logs keep UTC, the page counts the user's days."""
    return datetime.fromtimestamp(ep).strftime("%Y-%m-%d")


def series(eps, values=None, how: str = "count") -> list:
    """[[day, value], ...] sorted by day: a count of moments per day, or the sum or median of their values."""
    by = {}
    for i, ep in enumerate(eps):
        by.setdefault(day(ep), []).append(1 if values is None else values[i])
    out = []
    for d in sorted(by):
        v = by[d]
        out.append([d, statistics.median(v) if how == "median" else sum(v)])
    return out


def tilde(p) -> str:
    """A path with the home folder written as ~: a page or a screenshot of it does not carry the user's name."""
    s, home = str(p), str(Path.home())
    if os.path.normcase(s).startswith(os.path.normcase(home)) and s[len(home):len(home) + 1] in ("", "\\", "/"):
        return "~" + s[len(home):].replace("\\", "/")
    return s


def metric(value, unit: str, source, how: dict, status: str = "ok", window=None, as_of=None, series_=None,
           blind: bool = False, recent: bool = False) -> dict:
    m = {"value": value, "unit": unit, "source": [tilde(s) for s in source], "window": window, "as_of": as_of,
         "status": status, "how": how, "blind": blind, "active_24h": bool(recent) and not blind}
    if series_ is not None:
        m["series"] = series_
    return m


def missing(unit: str, source, how: dict) -> dict:
    return metric(None, unit, source, how, status="missing")


def unmeasured(unit: str, source, how: dict) -> dict:
    return metric(None, unit, source, how, status="unmeasured")


# ---------------------------------------------------------------------------------------------------------- config

def load_config(path: str | None = None, mind_dir: str | None = None) -> dict:
    """The layout: the public plugins' folders, overridden by <mind folder>/config.json or --config."""
    cfg_file = Path(path) if path else Path(mind_dir or os.environ.get("MIND_DATA") or config_dir() / "mind") / \
        "config.json"
    cfg = {}
    if cfg_file.is_file():
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    cfg["_config_file"] = str(cfg_file) if cfg_file.is_file() else None
    return resolve(cfg)


def resolve(cfg: dict) -> dict:
    """Fills in every folder the config leaves out with the public plugins' defaults."""
    conf = config_dir()
    col = Path(os.environ.get("COL_DATA") or conf / "col")
    lrm = Path(os.environ.get("LR_MEMORY_DATA") or conf / "lr-memory")
    out = dict(cfg)
    for key in ("episodes", "sleep", "transcripts", "mind", "outside", "scorecard"):  # a path may start with ~
        if isinstance(out.get(key), str):
            out[key] = cfg[key] = os.path.expanduser(out[key])
    for key in ("data", "memory"):
        if isinstance(out.get(key), list):
            out[key] = cfg[key] = [os.path.expanduser(str(p)) for p in out[key]]
    if isinstance(out.get("blind"), dict) and isinstance(out["blind"].get("heartbeat_extra"), list):
        out["blind"] = dict(out["blind"], heartbeat_extra=[os.path.expanduser(str(p))
                                                           for p in out["blind"]["heartbeat_extra"]])
    out["data"] = [str(p) for p in (cfg.get("data") or [col, lrm])]
    out["episodes"] = str(cfg.get("episodes") or lrm / "episodes")
    out["sleep"] = str(cfg.get("sleep") or lrm / "sleep")
    out["transcripts"] = str(cfg.get("transcripts") or os.environ.get("LR_MEMORY_TRANSCRIPTS") or conf / "projects")
    if cfg.get("memory"):
        out["memory"] = [str(p) for p in cfg["memory"]]
    else:
        out["memory"] = [str(p) for p in sorted(Path(out["transcripts"]).glob("*/memory")) if p.is_dir()]
        out.setdefault("_memory_glob", str(Path(out["transcripts"]) / "*" / "memory"))
    out["mind"] = str(cfg.get("mind") or os.environ.get("MIND_DATA") or conf / "mind")
    if not cfg.get("outside"):
        guess = Path(out["data"][0]) / "outside.json"
        out["outside"] = str(guess) if guess.is_file() else None
    if not cfg.get("scorecard"):
        guess = Path(out["mind"]) / "scorecard.json"
        out["scorecard"] = str(guess) if guess.is_file() else None
    out["exclude_logs"] = list(cfg.get("exclude_logs") or [])
    out["lang"] = cfg.get("lang") if cfg.get("lang") in ("en", "tr") else None
    return out


def blind_window(cfg: dict, now: float) -> dict | None:
    """The blind window when it is configured and now lies inside [from, until)."""
    b = cfg.get("blind") or {}
    start, until = parse_ts(b.get("from")), parse_ts(b.get("until"))
    if start is None:
        return None
    if now < start or (until is not None and now >= until):
        return None
    return {"from": start, "until": until, "note": b.get("note") or {}}


# ---------------------------------------------------------------------------------------------------------- logs

def read_rows(path: Path) -> list:
    rows = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        pass
    return rows


def newest_stamp(path: Path, tail: int = 1 << 16) -> float | None:
    """The newest timestamp in the last part of a file, read for that one value only; no row leaves this function."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - tail))
            data = f.read()
    except OSError:
        return None
    best = None
    for line in data.split(b"\n"):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            ep = parse_ts(row.get("at") or row.get("timestamp"))
            if ep is not None and (best is None or ep > best):
                best = ep
    return best


def H(tr: str, en: str) -> dict:
    return {"tr": tr, "en": en}


def collect_logs(cfg: dict, blind: dict | None, now: float, sources: list, missing_paths: list) -> tuple:
    """Every *.jsonl log in the data folders: rows per day, and the numbers its fields allow. Returns
    (logs, metrics, newest moment over every row read)."""
    cut = blind["from"] if blind else None
    by_name, files = {}, {}
    for d in cfg["data"]:
        folder = Path(d)
        if not folder.is_dir():
            missing_paths.append(str(folder))
            continue
        for f in sorted(folder.glob("*.jsonl")):
            if f.stem in cfg["exclude_logs"]:
                continue
            by_name.setdefault(f.stem, []).extend(read_rows(f))
            files.setdefault(f.stem, []).append(str(f))
    newest_all = None
    logs, kept = {}, {}
    for name, rows in sorted(by_name.items()):
        timed = []
        for r in rows:
            ep = parse_ts(r.get("at"))
            if ep is not None and (newest_all is None or ep > newest_all):
                newest_all = ep
            if cut is not None and (ep is None or ep >= cut):
                continue  # the blind window: dropped before anything is counted
            timed.append((ep, r))
        kept[name] = timed
        eps = [ep for ep, _ in timed if ep is not None]
        newest = max(eps) if eps else None
        logs[name] = metric(len(timed), "rows", files[name], H("satır sayısı", "number of rows"),
                            status="blind" if cut is not None else "ok",
                            window=window(eps, cut), as_of=iso(newest), series_=series(eps), blind=cut is not None,
                            recent=bool(eps) and max(eps) > now - 86400)
        for p in files[name]:
            sources.append({"path": p, "kind": "log", "rows": len(timed), "newest": iso(newest),
                            "blind": cut is not None})
    return logs, derived(kept, files, cut, now), newest_all


def window(eps: list, cut: float | None) -> dict | None:
    if not eps:
        return {"from": None, "to": iso(cut)} if cut is not None else None
    return {"from": iso(min(eps)), "to": iso(cut) if cut is not None else iso(max(eps))}


def derived(kept: dict, files: dict, cut: float | None, now: float) -> dict:
    """The numbers named by the aims, from the logs whose fields allow them."""
    out = {}
    is_blind = cut is not None
    status = "blind" if is_blind else "ok"

    def put(key, name, pick, unit, how, value_of=None):
        if name not in kept:
            out[key] = missing(unit, [f"{name}.jsonl"], how)
            return
        sel = [(ep, r) for ep, r in kept[name] if pick(r)]
        if value_of is not None and not any(value_of(r) is not None for _, r in kept[name]):
            out[key] = unmeasured(unit, files[name], how)
            return
        eps = [ep for ep, _ in sel if ep is not None]
        vals = [(value_of(r) or 0) if value_of else 1 for ep, r in sel if ep is not None]
        total = sum((value_of(r) or 0) for _, r in sel) if value_of else len(sel)
        out[key] = metric(total, unit, files[name], how, status=status, window=window(eps, cut),
                          as_of=iso(max(eps)) if eps else None, series_=series(eps, vals), blind=is_blind,
                          recent=bool(eps) and max(eps) > now - 86400)

    put("checks", "checks", lambda r: True, "turns", H("checks.jsonl satırları", "rows of checks.jsonl"))
    put("claims_caught", "checks", lambda r: bool(r.get("problems")), "turns",
        H("problems alanı boş olmayan checks satırları", "checks rows whose problems is not empty"))
    put("guard_stopped", "guard", lambda r: True, "writes", H("guard.jsonl satırları", "rows of guard.jsonl"))
    put("secrets_stopped", "secrets", lambda r: True, "commits", H("secrets.jsonl satırları",
                                                                    "rows of secrets.jsonl"))
    put("gate", "gate", lambda r: True, "rows", H("gate.jsonl satırları", "rows of gate.jsonl"))
    put("cue_reminders", "cue", lambda r: True, "reminders", H("cue.jsonl satırları", "rows of cue.jsonl"))
    put("cue_rules", "cue", lambda r: isinstance(r.get("rules"), list), "rules",
        H("cue satırlarında len(rules) toplamı", "sum of len(rules) over cue rows"),
        value_of=lambda r: len(r["rules"]) if isinstance(r.get("rules"), list) else None)
    put("scnc_reminders", "scnc_cue", lambda r: "again" not in r, "reminders",
        H("again alanı olmayan scnc_cue satırları", "scnc_cue rows without again"))
    put("scnc_third_after", "scnc_cue", lambda r: "again" in r, "streaks",
        H("again alanı olan scnc_cue satırları (hatırlatmadan sonra üçüncü başarısızlık)",
          "scnc_cue rows with again (a third failure after a reminder)"))
    put("intent_looks", "intent", lambda r: True, "looks", H("intent.jsonl satırları", "rows of intent.jsonl"))
    put("intent_turned_back", "intent", lambda r: r.get("verdict") in TURNED_BACK, "turns",
        H("verdict alanı incomplete, misread ya da violation olan intent satırları",
          "intent rows whose verdict is incomplete, misread or violation"))
    put("intent_tokens", "intent", lambda r: isinstance(r.get("tokens"), (int, float)), "tokens",
        H("intent satırlarında tokens toplamı", "sum of tokens over intent rows"),
        value_of=lambda r: r["tokens"] if isinstance(r.get("tokens"), (int, float)) else None)
    put("inquiry", "inquiry", lambda r: True, "rows", H("inquiry.jsonl satırları", "rows of inquiry.jsonl"))
    # the prediction ledger: COL (public and LR's own) keeps it in predictions.jsonl
    if "predictions" in kept:
        rows = kept["predictions"]
        preds = [(ep, r) for ep, r in rows if r.get("type") in PRED_TYPE]
        results = [(ep, r) for ep, r in rows if r.get("type") in RESULT_TYPE]
        closed = {(r.get("session"), r.get("key")) for _, r in results}
        for key, sel, how in (
                ("pred_recorded", preds, H("type öngörü/prediction satırları", "rows of type prediction")),
                ("pred_held", [x for x in results if x[1].get("verdict") in HELD],
                 H("verdict tuttu/held olan sonuç satırları", "result rows whose verdict is held")),
                ("pred_missed", [x for x in results if x[1].get("verdict") in MISSED],
                 H("verdict tutmadı/missed olan sonuç satırları", "result rows whose verdict is missed")),
                ("pred_uncompared", [x for x in results if x[1].get("verdict") in UNCOMPARED],
                 H("verdict karşılaştırılamadı/not comparable olan sonuç satırları",
                   "result rows whose verdict is not comparable")),
                ("pred_open", [x for x in preds if (x[1].get("session"), x[1].get("key")) not in closed],
                 H("aynı oturum ve anahtarla sonucu olmayan öngörüler",
                   "predictions with no result of the same session and key"))):
            eps = [ep for ep, _ in sel if ep is not None]
            out[key] = metric(len(sel), "predictions", files["predictions"], how, status=status,
                              window=window(eps, cut), as_of=iso(max(eps)) if eps else None, series_=series(eps),
                              blind=is_blind, recent=bool(eps) and max(eps) > now - 86400)
        held, missed = out["pred_held"]["value"], out["pred_missed"]["value"]
        out["pred_hit"] = metric(round(held / (held + missed), 4) if held + missed else None, "share",
                                 files["predictions"], H("tuttu / (tuttu + tutmadı)", "held / (held + missed)"),
                                 status=status if held + missed else "unmeasured", blind=is_blind)
    else:
        for key in ("pred_recorded", "pred_held", "pred_missed", "pred_uncompared", "pred_open", "pred_hit"):
            out[key] = missing("predictions", ["predictions.jsonl"], H("öngörü defteri", "the prediction ledger"))
    return out


# ---------------------------------------------------------------------------------------------------------- episodes, sleep, memory

def collect_episodes(cfg: dict, now: float, sources: list, missing_paths: list) -> dict:
    root = Path(cfg["episodes"])
    how = H("özetlemeden hemen önce kaydedilen iz dosyaları (<oturum>/*.json)",
            "trace files saved right before a compaction (<session>/*.json)")
    if not root.is_dir():
        missing_paths.append(str(root))
        return {"episodes": missing("files", [root], how), "episode_sessions": missing("sessions", [root], how)}
    eps, sessions = [], set()
    for f in root.glob("*/*.json"):
        m = STAMP_RE.match(f.stem)
        ep = None
        if m:
            ep = parse_ts(f"{m.group(1)}T{m.group(2)}:{m.group(3)}:{m.group(4)}Z")
        if ep is None:
            try:
                ep = f.stat().st_mtime
            except OSError:
                continue
        eps.append(ep)
        sessions.add(f.parent.name)
    sources.append({"path": str(root), "kind": "episodes", "rows": len(eps), "newest": iso(max(eps)) if eps else None,
                    "blind": False})
    recent = bool(eps) and max(eps) > now - 86400
    return {"episodes": metric(len(eps), "files", [root], how, window=window(eps, None),
                               as_of=iso(max(eps)) if eps else None, series_=series(eps), recent=recent),
            "episode_sessions": metric(len(sessions), "sessions", [root], H("iz dosyası olan oturumlar",
                                                                            "sessions with trace files"),
                                       as_of=iso(max(eps)) if eps else None)}


def collect_sleep(cfg: dict, now: float, sources: list, missing_paths: list) -> dict:
    """The nightly pass: how many dated reports exist and when the last pass ran. No report body is read."""
    root = Path(cfg["sleep"])
    how_n = H("tarihli rapor sayısı (yalnız dosya adları okunur)", "dated reports (only file names are read)")
    if not root.is_dir():
        missing_paths.append(str(root))
        return {"sleep_passes": missing("passes", [root], how_n),
                "sleep_last": missing("time", [root], H("son geçiş", "the last pass")),
                "candidates": missing("candidates", [root / "candidates.json"], H("bekleyen adaylar",
                                                                                  "candidates waiting"))}
    stems = {}
    for folder in (root, root / "reports"):
        if folder.is_dir():
            for f in folder.iterdir():
                if f.suffix in (".json", ".md") and DAY_RE.match(f.name) and "_dry" not in f.stem:
                    stems[f.stem] = f.stem
    eps = []
    for s in stems:
        # a report is named by its local day (and time, in the public plugin); a bare day counts as its noon
        m = REPORT_RE.match(s)
        try:
            ep = datetime.strptime(f"{m.group(1)} {m.group(2) or '12'}{m.group(3) or '00'}",
                                   "%Y-%m-%d %H%M").timestamp()
        except (ValueError, AttributeError):
            continue
        eps.append(ep)
    last, last_src = None, root
    state = root / "state.json"
    if state.is_file():
        try:
            last = parse_ts(json.loads(state.read_text(encoding="utf-8")).get("last_run"))
            last_src = state
        except (OSError, ValueError, AttributeError):
            last = None
    if last is None and (root / "last-run.log").is_file():
        last, last_src = (root / "last-run.log").stat().st_mtime, root / "last-run.log"
    if last is None and eps:
        last = max(eps)
    out = {"sleep_passes": metric(len(stems), "passes", [root], how_n, window=window(eps, None),
                                  as_of=iso(max(eps)) if eps else None, series_=series(eps),
                                  recent=last is not None and last > now - 86400)}
    out["sleep_last"] = metric(iso(last), "time", [last_src],
                               H("state.json last_run, yoksa last-run.log değişme zamanı, yoksa en yeni rapor adı",
                                 "state.json last_run, else last-run.log's modification time, else the newest "
                                 "report name"), status="ok" if last else "missing", as_of=iso(last))
    cand = root / "candidates.json"
    if cand.is_file():
        try:
            data = json.loads(cand.read_text(encoding="utf-8"))
            n = len(data) if isinstance(data, (dict, list)) else None
        except (OSError, ValueError):
            n = None
        out["candidates"] = metric(n, "candidates", [cand], H("candidates.json içindeki kayıt sayısı",
                                                              "entries in candidates.json"),
                                   status="ok" if n is not None else "unmeasured")
    else:
        out["candidates"] = missing("candidates", [cand], H("bekleyen adaylar", "candidates waiting"))
    sources.append({"path": str(root), "kind": "sleep", "rows": len(stems), "newest": iso(last), "blind": False})
    return out


def frontmatter(text: str) -> dict:
    """The keys of a memory file's frontmatter; keys under metadata: are lifted to the top as well."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out, nested = {}, {}
    for line in text[3:end].splitlines():
        m = re.match(r"^(\s*)([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        indent, k, v = m.groups()
        (nested if indent else out)[k] = v.strip().strip("'\"")
    for k, v in nested.items():
        out.setdefault(k, v)
    out["_keys"] = list(out) + list(nested)
    return out


def collect_memory(cfg: dict, now: float, sources: list, missing_paths: list) -> dict:
    folders = [Path(p) for p in cfg["memory"]]
    how = H("MEMORY.md dışındaki *.md kural dosyaları", "the *.md rule files except MEMORY.md")
    found = [p for p in folders if p.is_dir()]
    for p in folders:
        if not p.is_dir():
            missing_paths.append(str(p))
    if not found:
        src = folders or [cfg.get("_memory_glob") or "memory"]
        if not folders:
            missing_paths.append(str(src[0]))
        return {"rules": missing("files", src, how), "rules_added": missing("files", src, how),
                "rules_with_cue": missing("files", src, how), "index_lines": missing("lines", src, how)}
    eps, types, cued, n = [], {}, 0, 0
    lines = size = 0
    have_index = False
    for folder in found:
        for f in folder.glob("*.md"):
            if f.name == "MEMORY.md":
                try:
                    raw = f.read_bytes()
                    size += len(raw)
                    lines += raw.decode("utf-8", "replace").count("\n") + (0 if raw.endswith(b"\n") or not raw
                                                                            else 1)
                    have_index = True
                except OSError:
                    pass
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                st = f.stat()
            except OSError:
                continue
            n += 1
            fm = frontmatter(text)
            t = fm.get("type") or "-"
            types[t] = types.get(t, 0) + 1
            if any(k.lower().startswith("cue") for k in fm.get("_keys", [])):
                cued += 1
            m = re.search(r"(\d{4}-\d{2}-\d{2})$", f.stem)
            ep = None
            if m:
                try:
                    ep = datetime.strptime(m.group(1), "%Y-%m-%d").replace(hour=12).timestamp()
                except ValueError:
                    ep = None
            if ep is None:
                ep = getattr(st, "st_birthtime", None) or st.st_ctime
            eps.append(ep)
        sources.append({"path": str(folder), "kind": "memory", "rows": n, "newest": None, "blind": False})
    out = {"rules": metric(n, "files", found, how, as_of=iso(max(eps)) if eps else None),
           "rules_added": metric(n, "files", found, H("dosya adının sonundaki tarih, yoksa dosyanın oluşturulma zamanı",
                                                     "the date at the end of the file name, else the file's creation "
                                                     "time"), window=window(eps, None), series_=series(eps),
                                 recent=bool(eps) and max(eps) > now - 86400),
           "rules_with_cue": metric(cued, "files", found, H("frontmatter'da cue ile başlayan anahtarı olan kurallar",
                                                           "rules with a frontmatter key starting with cue")),
           "rules_by_type": metric(types, "files", found, H("frontmatter type (metadata altında da olabilir)",
                                                           "frontmatter type (it may sit under metadata)"))}
    if have_index:
        out["index_lines"] = metric(lines, "lines", [p / "MEMORY.md" for p in found], H("MEMORY.md satırları",
                                                                                         "lines of MEMORY.md"))
        out["index_bytes"] = metric(size, "bytes", [p / "MEMORY.md" for p in found], H("MEMORY.md baytı",
                                                                                        "bytes of MEMORY.md"))
    else:
        out["index_lines"] = missing("lines", [p / "MEMORY.md" for p in found], H("dizin", "the index"))
    return out


# ---------------------------------------------------------------------------------------------------------- transcripts

def outside_list(cfg: dict) -> tuple:
    """(project folder names, session ids) the user keeps out of every reader."""
    path = cfg.get("outside")
    if not path or not Path(path).is_file():
        return set(), set()
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set(), set()
    if not isinstance(data, dict):
        return set(), set()
    folders = {re.sub(r"[^A-Za-z0-9]", "-", str(f).rstrip("\\/")) for f in data.get("folders") or []}
    sessions = {str(s) for s in data.get("sessions") or [] if s}
    return folders, sessions


def is_outside(path: Path, root: Path, folders: set, sessions: set) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    if parts and any(parts[0] == f or parts[0].startswith(f + "-") for f in folders):
        return True
    return any(p.startswith(s) for p in parts for s in sessions)


def command_key(cmd: str) -> str:
    """The same key LR's scnc hook uses: whitespace collapsed, every run of digits a #, the first 90 characters."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", cmd)).strip()[:90]


def result_text(block: dict) -> str:
    c = block.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return str(c or "")


def scan_transcript(path: Path) -> dict:
    """Every moment the panel counts in one session file, with its time; the blind cut is applied later, so the
    cache stays the same whatever the window."""
    ev = {"rows": 0, "active": [], "compact": [], "calls": [], "shell": [], "fail": [], "s2": [], "s3": [],
          "hyp": [], "skills": [], "recall": []}
    active, requests, shell_ids, streak = set(), set(), {}, {}
    with open(path, "rb") as f:
        for line in f:
            if b'"isSidechain":true' in line[:400]:
                continue
            is_assistant = b'"type":"assistant"' in line
            if not is_assistant and b'"tool_result"' in line and b"isCompactSummary" not in line:
                ids = TOOL_ID.findall(line)
                if not any(i.decode("utf-8", "replace") in shell_ids for i in ids):
                    if len(line) > 50000:
                        continue
            elif not is_assistant and len(line) > 50000 and b"isCompactSummary" not in line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict) or row.get("isSidechain"):
                continue
            ep = parse_ts(row.get("timestamp"))
            if ep is None:
                continue
            ev["rows"] += 1
            kind = row.get("type")
            if kind in ("user", "assistant"):
                active.add(int(ep // 900) * 900)
            if row.get("isCompactSummary"):
                ev["compact"].append(ep)
            msg = row.get("message") if isinstance(row.get("message"), dict) else {}
            content = msg.get("content") if isinstance(msg.get("content"), list) else []
            if kind == "assistant":
                rid = row.get("requestId") or msg.get("id")
                usage = msg.get("usage") if isinstance(msg.get("usage"), dict) else None
                if usage is not None and rid not in requests:
                    if rid:
                        requests.add(rid)
                    ctx = sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens",
                                                                "cache_creation_input_tokens"))
                    ev["calls"].append([ep, ctx])
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use":
                        name, inp = b.get("name"), b.get("input") if isinstance(b.get("input"), dict) else {}
                        # a hypothesis line is also written into a call's description, where COL's ledger reads it
                        for ln in str(inp.get("description") or "").splitlines():
                            if ln.strip().lstrip("*_>#- ").startswith(HYPOTHESIS):
                                ev["hyp"].append(ep)
                        if name in SHELLS:
                            cmd = str(inp.get("command", ""))
                            shell_ids[b.get("id")] = command_key(cmd)
                            ev["shell"].append(ep)
                            if "archive.py" in cmd or "run.sh search" in cmd:
                                ev["recall"].append(ep)
                        elif name == "Skill":
                            ev["skills"].append([ep, str(inp.get("skill", ""))])
                    elif b.get("type") == "text":
                        for ln in str(b.get("text", "")).splitlines():
                            if ln.strip().lstrip("*_>#- ").startswith(HYPOTHESIS):
                                ev["hyp"].append(ep)
            elif kind == "user":
                for b in content:
                    if not isinstance(b, dict) or b.get("type") != "tool_result":
                        continue
                    k = shell_ids.get(b.get("tool_use_id"))
                    if k is None:
                        continue
                    bad = bool(b.get("is_error")) or bool(FAIL.search(result_text(b)[-4000:]))
                    if not bad:
                        streak.pop(k, None)
                        continue
                    ev["fail"].append(ep)
                    streak[k] = streak.get(k, 0) + 1
                    if len(streak) > 50:  # the hook keeps the last 50 keys
                        streak = dict(list(streak.items())[-50:])
                    if streak[k] == 2:
                        ev["s2"].append(ep)
                    elif streak[k] == 3:
                        ev["s3"].append(ep)
    ev["active"] = sorted(active)
    return ev


def load_cache(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get("version") != CACHE_VERSION:
        return {}
    return data.get("files") or {}


def save_cache(path: Path, files: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": CACHE_VERSION, "files": files}), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def collect_transcripts(cfg: dict, blind: dict | None, now: float, sources: list, missing_paths: list,
                        skip: bool = False) -> tuple:
    """Returns (metrics, scan facts)."""
    root = Path(cfg["transcripts"])
    names = ("sessions_active", "sessions_on_record", "compactions", "calls", "context_median", "shell_calls",
             "shell_failures", "streak2", "streak3", "streak_share", "hypothesis_lines", "skill_calls",
             "scnc_skill_calls", "recall_searches")
    if skip:
        how = H("transkript taraması --no-transcripts ile kapatıldı", "the transcript scan was turned off with "
                                                                       "--no-transcripts")
        return {n: unmeasured("-", [root], how) for n in names}, {"skipped": True}
    if not root.is_dir():
        missing_paths.append(str(root))
        how = H("transkript klasörü yok", "the transcripts folder is not there")
        return {n: missing("-", [root], how) for n in names}, {"files": 0}
    folders, sessions = outside_list(cfg)
    cache_path = Path(cfg["mind"]) / "cache.json"
    cache = load_cache(cache_path)
    fresh, started, scanned, skipped_outside = {}, time.time(), 0, 0
    for f in sorted(root.rglob("*.jsonl")):
        if is_outside(f, root, folders, sessions):
            skipped_outside += 1
            continue
        try:
            st = f.stat()
        except OSError:
            continue
        key = str(f)
        old = cache.get(key)
        if old and old.get("size") == st.st_size and old.get("mtime") == st.st_mtime:
            fresh[key] = old
            continue
        try:
            fresh[key] = {"size": st.st_size, "mtime": st.st_mtime, "ev": scan_transcript(f)}
            scanned += 1
        except OSError:
            continue
    save_cache(cache_path, fresh)
    cut = blind["from"] if blind else None

    def keep(ep):
        return cut is None or ep < cut

    def gather(name, blind_ok=True):
        out = []
        for v in fresh.values():
            for x in v["ev"][name]:
                ep = x[0] if isinstance(x, list) else x
                if blind_ok or keep(ep):
                    out.append(x)
        return out

    src = [root]
    is_blind = cut is not None
    st_b = "blind" if is_blind else "ok"

    def m_count(eps, unit, how, blinded):
        eps = sorted(eps)
        return metric(len(eps), unit, src, how, status=st_b if blinded else "ok",
                      window=window(eps, cut if blinded else None), as_of=iso(eps[-1]) if eps else None,
                      series_=series(eps), blind=blinded and is_blind,
                      recent=bool(eps) and eps[-1] > now - 86400)

    # structural: sessions active per day and compactions per day keep every row
    per_day = {}
    for key, v in fresh.items():
        for ep in v["ev"]["active"]:
            per_day.setdefault(day(ep), set()).add(key)
    active_all = [ep for v in fresh.values() for ep in v["ev"]["active"]]
    out = {"sessions_active": metric(len([k for k, v in fresh.items() if v["ev"]["active"]]), "sessions", src,
                                     H("o gün satırı olan oturum dosyaları (yan zincir hariç)",
                                       "session files with a row that day (side chains left out)"),
                                     window=window(active_all, None),
                                     as_of=iso(max(active_all)) if active_all else None,
                                     series_=[[d, len(s)] for d, s in sorted(per_day.items())],
                                     recent=bool(active_all) and max(active_all) > now - 86400)}
    out["sessions_on_record"] = metric(len([1 for v in fresh.values() if v["ev"]["rows"]]), "sessions", src,
                                       H("satırı olan transkript dosyaları", "transcript files with rows"))
    out["compactions"] = m_count(gather("compact"), "compactions",
                                 H("isCompactSummary true olan satırlar", "rows whose isCompactSummary is true"), False)
    calls = sorted(gather("calls", False))
    ceps = [c[0] for c in calls]
    out["calls"] = m_count(ceps, "calls", H("requestId başına bir asistan çağrısı",
                                            "one assistant call per requestId"), True)
    ctx_how = H("çağrı başına input + cache read + cache creation tokenlarının günlük ortancası",
                "daily median of input + cache read + cache creation tokens per call")
    out["context_median"] = metric(statistics.median([c[1] for c in calls]) if calls else None, "tokens", src,
                                   ctx_how, status=st_b if calls else "unmeasured", window=window(ceps, cut),
                                   as_of=iso(ceps[-1]) if ceps else None,
                                   series_=series(ceps, [c[1] for c in calls], "median"), blind=is_blind,
                                   recent=bool(ceps) and ceps[-1] > now - 86400)
    out["shell_calls"] = m_count(gather("shell", False), "calls", H("Bash ve PowerShell çağrıları",
                                                                    "Bash and PowerShell calls"), True)
    out["shell_failures"] = m_count(gather("fail", False), "failures",
                                    H("is_error ya da son 4000 karakterde FAIL deseni",
                                      "is_error, or the FAIL pattern in the last 4000 characters"), True)
    s2, s3 = gather("s2", False), gather("s3", False)
    out["streak2"] = m_count(s2, "streaks", H("aynı komut anahtarı art arda ikinci kez başarısız",
                                              "the same command key failing a second time in a row"), True)
    out["streak3"] = m_count(s3, "streaks", H("aynı komut anahtarı art arda üçüncü kez başarısız",
                                              "the same command key failing a third time in a row"), True)
    out["streak_share"] = metric(round(len(s3) / len(s2), 4) if s2 else None, "share", src,
                                 H("üçüncü başarısızlık / ikinci başarısızlık", "third failures / second failures"),
                                 status=st_b if s2 else "unmeasured", window=window(sorted(s2), cut),
                                 blind=is_blind)
    out["hypothesis_lines"] = m_count(gather("hyp", False), "lines",
                                      H("'Hipotez [' ya da 'Hypothesis [' ile başlayan satırlar (asistan metni ve "
                                        "araç çağrısı açıklamaları)",
                                        "lines starting with 'Hipotez [' or 'Hypothesis [' (assistant text and "
                                        "tool call descriptions)"), True)
    skills = gather("skills", False)
    by_skill = {}
    for ep, name in skills:
        by_skill[name] = by_skill.get(name, 0) + 1
    out["skill_calls"] = metric(by_skill, "calls", src, H("Skill aracı çağrıları, beceri adına göre",
                                                          "Skill tool calls by skill name"), status=st_b,
                                window=window([s[0] for s in skills], cut), blind=is_blind)
    out["scnc_skill_calls"] = m_count([ep for ep, name in skills if name.split(":")[-1] == "scnc"], "calls",
                                      H("adı scnc olan Skill çağrıları", "Skill calls named scnc"), True)
    out["recall_searches"] = m_count(gather("recall", False), "searches",
                                     H("archive.py ya da 'run.sh search' içeren kabuk komutları",
                                       "shell commands containing archive.py or 'run.sh search'"), True)
    newest = max(active_all) if active_all else None
    sources.append({"path": str(root), "kind": "transcripts", "rows": len(fresh),
                    "newest": None if is_blind else iso(newest), "blind": is_blind,
                    "skipped_outside": skipped_outside})
    return out, {"files": len(fresh), "scanned_now": scanned, "skipped_outside": skipped_outside,
                 "seconds": round(time.time() - started, 1)}


# ---------------------------------------------------------------------------------------------------------- heartbeat, health

def heartbeat(newest_log: float | None, cfg: dict, now: float, sources: list, missing_paths: list) -> dict:
    best, src = newest_log, [p for p in cfg["data"]]
    for extra in (cfg.get("blind") or {}).get("heartbeat_extra") or []:
        p = Path(extra)
        if not p.is_file():
            missing_paths.append(str(p))
            continue
        ep = newest_stamp(p)
        src.append(str(p))
        # this file's own newest time stays out of the page: only the newest over everything is shown
        sources.append({"path": str(p), "kind": "heartbeat", "rows": None, "newest": None, "blind": False,
                        "only_newest": True})
        if ep is not None and (best is None or ep > best):
            best = ep
    how = H("bütün okunan günlüklerdeki en yeni at (tek sayı; dosya dosya gösterilmez)",
            "the newest at over every log read (one number; not shown file by file)")
    if best is None:
        return missing("minutes", src, how)
    return metric(round((now - best) / 60, 1), "minutes", src, how, as_of=iso(best), recent=now - best < 86400)


def health(cfg: dict) -> dict | None:
    url = cfg.get("health_url")
    if not url:
        return None
    host = urlparse(url).hostname or ""
    how = H("health_url'e 2 saniyelik tek GET", "one GET to health_url with a 2 second timeout")
    if host not in ("127.0.0.1", "localhost", "::1"):
        return metric(None, "state", [url], H("yalnız localhost adresi okunur", "only a localhost address is read"),
                      status="unmeasured")
    from urllib.request import urlopen
    try:
        with urlopen(url, timeout=2) as r:  # noqa: S310 (a localhost address, checked above)
            up = 200 <= r.status < 300
    except Exception:
        up = False
    return metric("up" if up else "down", "state", [url], how, as_of=iso(time.time()))


# ---------------------------------------------------------------------------------------------------------- all

def collect(cfg: dict, now: float | None = None, transcripts: bool = True) -> dict:
    """Everything the page shows, as one dict that can be printed as JSON or embedded in the page."""
    from . import aims as aims_mod
    now = time.time() if now is None else now
    blind = blind_window(cfg, now)
    sources, missing_paths = [], []
    logs, metrics, newest_log = collect_logs(cfg, blind, now, sources, missing_paths)
    metrics.update(collect_episodes(cfg, now, sources, missing_paths))
    metrics.update(collect_sleep(cfg, now, sources, missing_paths))
    metrics.update(collect_memory(cfg, now, sources, missing_paths))
    tmetrics, scan = collect_transcripts(cfg, blind, now, sources, missing_paths, skip=not transcripts)
    metrics.update(tmetrics)
    metrics["heartbeat"] = heartbeat(newest_log, cfg, now, sources, missing_paths)
    hl = health(cfg)
    if hl is not None:
        metrics["health"] = hl
    card, card_src = aims_mod.load_scorecard(cfg.get("scorecard"), missing_paths)
    if card_src:
        card_src["path"] = tilde(card_src["path"])
    for s in sources:
        s["path"] = tilde(s["path"])
    return {
        "generated": iso(now),
        "lang": cfg.get("lang") or "en",
        "blind": ({"active": True, "from": iso(blind["from"]), "until": iso(blind["until"]), "note": blind["note"]}
                  if blind else {"active": False}),
        "config": tilde(cfg["_config_file"]) if cfg.get("_config_file") else None,
        "metrics": metrics,
        "logs": logs,
        "aims": aims_mod.build(card, metrics),
        "scorecard": card_src,
        "scan": scan,
        "sources": sources,
        "missing": sorted({tilde(p) for p in missing_paths}),
    }
