"""The mind panel reads its numbers from files: these tests write a small layout through the plugins' own log
functions (plus a hand-written transcript) in a temp folder and check that the collected numbers are exactly what was
written, that the blind window leaves no trace, and that the page loads nothing from the network."""
import ast
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plugins" / "mind" / "scripts"))
sys.path.insert(0, str(ROOT / "plugins" / "col" / "scripts"))

sys.path.insert(0, str(ROOT / "docs"))

import make_aims  # noqa: E402
from col import common as col_common  # noqa: E402
from mind import __version__, aims, collect, render  # noqa: E402

SID = "cccc1111-2222-3333-4444-555566667777"


def asst(at, rid, *blocks, side=False, tokens=(10, 100, 5)):
    return {"parentUuid": None, "isSidechain": side, "type": "assistant", "timestamp": at, "requestId": rid,
            "message": {"id": rid, "role": "assistant", "content": list(blocks),
                        "usage": {"input_tokens": tokens[0], "cache_read_input_tokens": tokens[1],
                                  "cache_creation_input_tokens": tokens[2], "output_tokens": 7}}}


def bash(tid, cmd):
    return {"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": cmd}}


def res(at, tid, text, err=False):
    return {"parentUuid": None, "isSidechain": False, "type": "user", "timestamp": at, "message": {
        "role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": err}]}}


def user(at, text):
    return {"parentUuid": None, "isSidechain": False, "type": "user", "timestamp": at,
            "message": {"role": "user", "content": text}}


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def transcript_rows(day="2026-10-20"):
    t = lambda h, m=0: f"{day}T{h:02d}:{m:02d}:00.000Z"  # noqa: E731
    return [
        user(t(10), "run the tests"),
        asst(t(10, 1), "r1", bash("a1", "pytest -q 12")),
        res(t(10, 2), "a1", "1 failed, 3 passed"),
        asst(t(10, 3), "r2", bash("a2", "pytest   -q 13")),
        res(t(10, 4), "a2", "boom", err=True),  # same key: a second failure in a row
        asst(t(10, 5), "r3", bash("a3", "pytest -q 14")),
        res(t(10, 6), "a3", "Traceback (most recent call last):\n  x"),  # third in a row
        asst(t(10, 7), "r4", bash("a4", "pytest -q 15")),
        res(t(10, 8), "a4", "4 passed"),  # success resets the key
        asst(t(10, 9), "r4", {"type": "text", "text": "Hipotez [a]: cache\n  Hypothesis [b]: env\nnot one"}),
        {"parentUuid": None, "isSidechain": False, "type": "user", "timestamp": t(11), "isCompactSummary": True,
         "message": {"role": "user", "content": "This session is being continued..."}},
        asst(t(11, 1), "r5", {"type": "tool_use", "id": "s1", "name": "Skill", "input": {"skill": "scnc"}}),
        asst(t(11, 2), "r6", {"type": "tool_use", "id": "a5", "name": "Bash", "input": {
            "command": "python episodes/archive.py nasıl yapmıştık",
            "description": "Hipotez [x]: 3 sonuç; Hipotez [y]: 0 sonuç"}}),  # one more hypothesis line
        res(t(11, 3), "a5", "found 3"),
        asst(t(11, 4), "r7", bash("a6", "pytest -q 99"), side=True),  # a subagent's row: left out
        res(t(11, 5), "a6", "9 failed"),
    ]


@pytest.fixture
def lay(tmp_path, monkeypatch):
    col_dir = tmp_path / "col"
    monkeypatch.setattr(col_common, "DATA", col_dir)
    projects = tmp_path / "projects"
    write_jsonl(projects / "proj" / f"{SID}.jsonl", transcript_rows())
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "MEMORY.md").write_text("# Index\n- a\n", encoding="utf-8")
    (mem / "rule-a-2026-10-01.md").write_text("---\nname: a\ntype: feedback\ncue: pytest\n---\nbody\n",
                                               encoding="utf-8")
    (mem / "rule-b.md").write_text("---\nname: b\nmetadata:\n  type: project\n  cue_words: x\n---\nbody\n",
                                   encoding="utf-8")
    (mem / "rule-c.md").write_text("no frontmatter\n", encoding="utf-8")
    ep = tmp_path / "episodes"
    for s, name in (("s1", "2026-10-26T203220Z"), ("s1", "2026-10-27T095037Z"), ("s2", "2026-10-27T104758Z")):
        (ep / s).mkdir(parents=True, exist_ok=True)
        (ep / s / f"{name}.json").write_text("{}", encoding="utf-8")
    sl = tmp_path / "sleep"
    sl.mkdir()
    for name in ("2026-10-23.json", "2026-10-23.md", "2026-10-24.json"):
        (sl / name).write_text("{}", encoding="utf-8")
    (sl / "candidates.json").write_text(json.dumps({"x.md": {}, "y.md": {}}), encoding="utf-8")
    cfg = {"data": [str(col_dir)], "episodes": str(ep), "sleep": str(sl), "transcripts": str(projects),
           "memory": [str(mem)], "mind": str(tmp_path / "mind")}
    return tmp_path, cfg


def write_logs():
    log = col_common.log
    log("checks", {"session": "s", "calls": 2, "problems": []})
    log("checks", {"session": "s", "calls": 1, "problems": ["no such commit"]})
    log("checks", {"session": "s", "calls": 3, "problems": []})
    log("guard", {"session": "s", "tool": "Write", "rule": "x"})
    log("secrets", {"session": "s", "found": []})
    log("cue", {"session": "s", "tool": "Bash", "rules": ["a", "b"]})
    log("cue", {"session": "s", "tool": "Bash", "rules": ["c"]})
    log("scnc_cue", {"session": "s", "command": "pytest"})
    log("scnc_cue", {"session": "s", "command": "pytest", "again": 3})
    log("intent", {"session": "s", "verdict": "ok", "tokens": 100})
    log("intent", {"session": "s", "verdict": "misread", "tokens": 250})
    log("predictions", {"type": "prediction", "session": "s", "key": "k1", "text": "3 passed"})
    log("predictions", {"type": "prediction", "session": "s", "key": "k2", "text": "2 passed"})
    log("predictions", {"type": "prediction", "session": "s", "key": "k3", "text": "1 passed"})
    log("predictions", {"type": "result", "session": "s", "key": "k1", "verdict": "held"})
    log("predictions", {"type": "result", "session": "s", "key": "k2", "verdict": "missed"})
    log("brevity", {"session": "s"})
    log("mystery", {"session": "s"})


def test_numbers_equal_what_was_written(lay):
    tmp, cfg = lay
    write_logs()
    d = collect.collect(collect.resolve(cfg))
    m = d["metrics"]
    assert d["blind"] == {"active": False}
    assert (m["checks"]["value"], m["claims_caught"]["value"]) == (3, 1)
    assert m["guard_stopped"]["value"] == 1 and m["secrets_stopped"]["value"] == 1
    assert (m["cue_reminders"]["value"], m["cue_rules"]["value"]) == (2, 3)
    assert (m["scnc_reminders"]["value"], m["scnc_third_after"]["value"]) == (1, 1)
    assert (m["intent_looks"]["value"], m["intent_turned_back"]["value"], m["intent_tokens"]["value"]) == (2, 1, 350)
    assert [m[k]["value"] for k in ("pred_recorded", "pred_held", "pred_missed", "pred_open")] == [3, 1, 1, 1]
    assert m["pred_uncompared"]["value"] == 0 and m["pred_hit"]["value"] == 0.5
    assert d["logs"]["mystery"]["value"] == 1 and d["logs"]["brevity"]["value"] == 1  # unknown logs still listed
    assert sum(v for _, v in d["logs"]["checks"]["series"]) == 3
    assert all(m[k]["source"] for k in ("checks", "cue_rules", "pred_held"))
    # the transcript
    assert m["shell_calls"]["value"] == 5  # the side chain's call is left out
    assert m["shell_failures"]["value"] == 3
    assert (m["streak2"]["value"], m["streak3"]["value"]) == (1, 1)
    assert m["calls"]["value"] == 6  # r4 is one request over two rows
    assert m["context_median"]["value"] == 115
    assert m["compactions"]["value"] == 1 and m["compactions"]["series"] == [["2026-10-20", 1]]
    assert m["hypothesis_lines"]["value"] == 3  # two in the text, one in a call's description
    assert m["skill_calls"]["value"] == {"scnc": 1} and m["scnc_skill_calls"]["value"] == 1
    assert m["recall_searches"]["value"] == 1
    assert m["sessions_active"]["value"] == 1 and m["sessions_on_record"]["value"] == 1
    # memory, episodes, sleep
    assert m["rules"]["value"] == 3 and m["rules_with_cue"]["value"] == 2
    assert m["rules_by_type"]["value"] == {"feedback": 1, "project": 1, "-": 1}
    assert ["2026-10-01", 1] in m["rules_added"]["series"]
    assert m["index_lines"]["value"] == 2
    assert (m["episodes"]["value"], m["episode_sessions"]["value"]) == (3, 2)
    assert (m["sleep_passes"]["value"], m["candidates"]["value"]) == (2, 2)
    # the cache is written and a second run reads the same numbers from it
    assert (tmp / "mind" / "cache.json").is_file()
    again = collect.collect(collect.resolve(cfg))
    assert again["metrics"]["streak2"]["value"] == 1 and again["scan"]["scanned_now"] == 0


def test_blind_window_leaves_no_trace(lay):
    tmp, cfg = lay
    col_dir = Path(cfg["data"][0])
    before, after = "2026-05-10T12:00:00Z", "2026-07-15T12:00:00Z"
    write_jsonl(col_dir / "intent.jsonl", [{"at": before, "session": "s", "verdict": "ok", "tokens": 40},
                                           {"at": after, "session": "s", "verdict": "misread", "tokens": 987654321}])
    write_jsonl(col_dir / "checks.jsonl", [{"at": before, "session": "s", "problems": []},
                                           {"at": after, "session": "s", "problems": ["x"]},
                                           {"at": after, "session": "s", "problems": ["y"]}])
    extra = tmp / "shadow.jsonl"
    write_jsonl(extra, [{"at": "2026-09-01T00:00:00Z", "check": "x"}])
    # transcripts: one session before the cut, one after it with a sentinel context size and a compaction
    write_jsonl(Path(cfg["transcripts"]) / "proj" / f"{SID}.jsonl", transcript_rows("2026-05-10"))
    late = transcript_rows("2026-08-20")
    late[1] = asst("2026-08-20T10:01:00.000Z", "r1", bash("a1", "pytest -q 12"), tokens=(987654, 0, 0))
    write_jsonl(Path(cfg["transcripts"]) / "proj" / "dddd.jsonl", late)
    (Path(cfg["episodes"]) / "s3").mkdir()
    (Path(cfg["episodes"]) / "s3" / "2026-08-21T101010Z.json").write_text("{}", encoding="utf-8")
    cfg["blind"] = {"from": "2026-06-01T00:00:00Z", "until": "2099-01-01T00:00:00Z",
                    "note": {"en": "hidden"}, "heartbeat_extra": [str(extra)]}
    d = collect.collect(collect.resolve(cfg))
    m = d["metrics"]
    out = json.dumps(d, ensure_ascii=False)
    html = render.page(d, "en")
    for text in (out, html):
        assert "987654321" not in text and "987654" not in text
        assert "2026-07-15" not in text
    assert m["intent_tokens"]["value"] == 40 and m["intent_tokens"]["blind"] is True
    assert m["checks"]["value"] == 1 and m["claims_caught"]["value"] == 0
    assert m["streak2"]["value"] == 1 and m["shell_calls"]["value"] == 5  # only the session before the cut
    assert m["context_median"]["value"] == 115
    assert all(day < "2026-06-01" for day, _ in m["calls"]["series"])
    # structural numbers keep every row
    assert m["compactions"]["value"] == 2 and m["sessions_active"]["value"] == 2
    assert m["episodes"]["value"] == 4
    assert m["heartbeat"]["as_of"] == "2026-09-01T00:00:00Z"
    # a file read for the heartbeat gives the one heartbeat number; its own newest time is not on the page
    beat = [s for s in d["sources"] if s["kind"] == "heartbeat"]
    assert len(beat) == 1 and beat[0]["newest"] is None and beat[0]["rows"] is None
    assert d["blind"]["active"] and d["blind"]["from"] == "2026-06-01T00:00:00Z"
    tr = [s for s in d["sources"] if s["kind"] == "transcripts"][0]
    assert tr["blind"] and tr["newest"] is None
    # outside the window the same rows count
    cfg["blind"]["until"] = "2026-07-01T00:00:00Z"
    open_ = collect.collect(collect.resolve(cfg))
    assert open_["metrics"]["intent_tokens"]["value"] == 40 + 987654321 and not open_["blind"]["active"]


def test_outside_list_and_exclude_logs(lay):
    tmp, cfg = lay
    write_logs()
    projects = Path(cfg["transcripts"])
    write_jsonl(projects / "C--Work-secret" / "eeee.jsonl", transcript_rows())
    write_jsonl(projects / "proj" / "deadbeef-0000.jsonl", transcript_rows())
    outside = tmp / "outside.json"
    outside.write_text(json.dumps({"folders": ["C:\\Work\\secret"], "sessions": ["deadbeef"]}), encoding="utf-8")
    cfg.update({"outside": str(outside), "exclude_logs": ["brevity"]})
    d = collect.collect(collect.resolve(cfg))
    assert d["metrics"]["shell_calls"]["value"] == 5 and d["metrics"]["sessions_on_record"]["value"] == 1
    assert [s for s in d["sources"] if s["kind"] == "transcripts"][0]["skipped_outside"] == 2
    assert "brevity" not in d["logs"]
    assert not any("brevity" in s["path"] for s in d["sources"])
    cache = (tmp / "mind" / "cache.json").read_text(encoding="utf-8")
    assert "secret" not in cache and "deadbeef" not in cache


def test_missing_sources_and_no_scorecard(tmp_path):
    nowhere = tmp_path / "nowhere"
    cfg = collect.resolve({"data": [str(nowhere / "col")], "episodes": str(nowhere / "ep"),
                           "sleep": str(nowhere / "sleep"), "transcripts": str(nowhere / "projects"),
                           "memory": [str(nowhere / "memory")], "mind": str(tmp_path / "mind")})
    d = collect.collect(cfg)
    m = d["metrics"]
    for k in ("checks", "pred_held", "episodes", "sleep_passes", "rules", "compactions", "streak2", "heartbeat"):
        assert m[k]["status"] == "missing" and m[k]["value"] is None, k
    assert collect.tilde(nowhere / "projects") in d["missing"]
    assert all(a["status"] == "unmeasured" and not a["on_card"] for a in d["aims"])
    html = render.page(d, "en")
    assert "not measured on this machine" in html and "</html>" in html
    assert "bu makinede ölçülmedi" in render.page(d, "tr")


def test_scorecard_language_fallback(lay):
    tmp, cfg = lay
    card = tmp / "card.json"
    card.write_text(json.dumps({"as_of": "2026-11-11", "aims": [
        {"id": 3, "status": "works", "measured": {"tr": "74 düzeltmenin 24'ü"}, "measured_on": "2026-11-11"},
        {"id": 5, "status": "bogus"}]}), encoding="utf-8")
    cfg["scorecard"] = str(card)
    got = {a["id"]: a for a in collect.collect(collect.resolve(cfg), transcripts=False)["aims"]}
    assert got[3]["status"] == "works" and got[3]["measured"] == {"tr": "74 düzeltmenin 24'ü",
                                                                 "en": "74 düzeltmenin 24'ü"}
    assert got[5]["status"] == "unmeasured" and got[1]["status"] == "unmeasured" and not got[1]["on_card"]
    assert len(got) == 13


def test_page_loads_nothing_from_the_network(lay):
    tmp, cfg = lay
    write_logs()
    for served in (False, True):
        html = render.page(collect.collect(collect.resolve(cfg)), "tr", served=served)
        assert not re.search(r"""(?:src|href)\s*=\s*["']?\s*(?:https?:)?//""", html, re.I)
        assert not re.search(r"""fetch\(\s*["'](?:https?:)?//""", html, re.I)
        assert "@import" not in html and "url(http" not in html


def test_painted_brain_is_embedded_and_falls_back(tmp_path):
    d = collect.collect(collect.resolve({"data": [str(tmp_path / "none")], "transcripts": str(tmp_path / "none"),
                                         "memory": [str(tmp_path / "none")], "mind": str(tmp_path / "mind")}))
    if render.BRAIN.is_file():
        assert "data:image/jpeg;base64," in render.page(d, "en")
    html = render.page(d, "en", brain=tmp_path / "no-such.jpg")
    assert "data:image/jpeg" not in html and '"brain": ""' in html and 'class="cortex"' in html


def test_paths_are_shown_from_the_home_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(collect.Path, "home", classmethod(lambda cls: tmp_path))
    assert collect.tilde(tmp_path / "col" / "cue.jsonl") == "~/col/cue.jsonl"
    assert collect.tilde(tmp_path) == "~"
    other = str(tmp_path) + "x"  # a folder whose name only starts like the home folder is left alone
    assert collect.tilde(other) == other
    m = collect.metric(1, "rows", [tmp_path / "a.jsonl"], {})
    assert m["source"] == ["~/a.jsonl"]


def test_config_paths_may_start_from_the_home_folder(monkeypatch, tmp_path):
    for name in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(name, str(tmp_path))
    cfg = collect.resolve({"data": ["~/col"], "episodes": "~/ep", "memory": ["~/mem"], "scorecard": "~/card.json",
                           "blind": {"heartbeat_extra": ["~/shadow.jsonl"]}})
    assert Path(cfg["data"][0]) == tmp_path / "col" and Path(cfg["episodes"]) == tmp_path / "ep"
    assert Path(cfg["memory"][0]) == tmp_path / "mem" and Path(cfg["scorecard"]) == tmp_path / "card.json"
    assert Path(cfg["blind"]["heartbeat_extra"][0]) == tmp_path / "shadow.jsonl"


def test_the_package_as_claude_code_loads_it():
    plugin = ROOT / "plugins" / "mind"
    manifest = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "mind" and manifest["version"] == __version__
    entry = next(p for p in market["plugins"] if p["name"] == "mind")
    assert (ROOT / entry["source"]).resolve() == plugin.resolve()
    assert b"\r" not in (plugin / "scripts" / "run.sh").read_bytes()  # sh stops at a CRLF line end
    skill = (plugin / "skills" / "panel" / "SKILL.md").read_text(encoding="utf-8")
    front = skill.split("---")[1]
    assert re.search(r"^name: panel$", front, re.M)
    assert 200 < len(re.search(r"^description: (.+)$", front, re.M).group(1)) <= 1024
    assert 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" --open' in skill
    assert render.BRAIN.is_file() and render.BRAIN.stat().st_size < 400 * 1024  # it travels inside every page


def test_the_aims_pages_and_the_readmes_say_what_the_scorecard_says():
    """docs/AIMS*.md are written by docs/make_aims.py from aims.py and docs/scorecard.json; the READMEs carry its
    short table. A change in either source without running it again fails here."""
    card = json.loads((ROOT / "docs" / "scorecard.json").read_text(encoding="utf-8"))
    assert sorted(a["id"] for a in card["aims"]) == list(range(1, 14))
    assert all(a["status"] in aims.STATUSES for a in card["aims"])
    for lang, page, readme in (("en", "AIMS.md", "README.md"), ("tr", "AIMS.tr.md", "README.tr.md")):
        assert (ROOT / "docs" / page).read_text(encoding="utf-8") == make_aims.render(lang)
        text = (ROOT / readme).read_text(encoding="utf-8")
        assert make_aims.table(lang) in text and make_aims.counts(lang) in text


def test_modules_compile_as_python_39():
    files = list((ROOT / "plugins" / "mind" / "scripts").rglob("*.py"))
    assert len(files) >= 5  # panel.py and the mind package's four modules
    for f in files:
        src = f.read_text(encoding="utf-8")
        ast.parse(src, filename=str(f), feature_version=(3, 9))
        assert "from __future__ import annotations" in src, f


def test_aims_are_complete_in_both_languages():
    assert [a["id"] for a in aims.AIMS] == list(range(1, 14))
    for a in aims.AIMS:
        for field in ("aim", "analogy", "yardstick"):
            assert a[field]["tr"] and a[field]["en"]
    assert set(render.TEXT["tr"]) == set(render.TEXT["en"])
