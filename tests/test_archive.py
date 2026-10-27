"""The search index over past sessions: what goes in, what a search finds, what show prints."""
import os
import sqlite3
import subprocess
import sys

from conftest import SCRIPTS, SID, row, write
from lr_memory import archive, common, keys

FAKE_KEY = "sk-ant-" + "A" * 30  # built here so that this file never holds a key-shaped string


def _rows():
    return [
        row("user", "COL'un karşılaştırıcısı dk ile sn'yi karıştırıyor, düzelt", "2026-10-25T10:00",
            origin={"kind": "human"}),
        row("assistant", [{"type": "text", "text": "Root cause: the comparator matched numbers without their "
                                                   "units; now a duration is only compared with a duration."}],
            "2026-10-25T10:01"),
        row("assistant", [{"type": "tool_use", "id": "t1", "name": "Bash",
                           "input": {"command": "git commit -m 'unit'", "description": "Commit the comparator fix"}}],
            "2026-10-25T10:02"),
        row("user", [{"type": "tool_result", "tool_use_id": "t1", "content": "[master 0426749] Prediction ledger: "
                      "results are compared unit by unit\n 2 files changed"}], "2026-10-25T10:03"),
        row("assistant", [{"type": "tool_use", "id": "t1", "name": "Bash",  # the same call written twice
                           "input": {"command": "git commit -m 'unit'", "description": "Commit the comparator fix"}}],
            "2026-10-25T10:04"),
        row("assistant", [{"type": "tool_use", "id": "t2", "name": "Bash",
                           "input": {"command": 'sh "/x/scripts/run.sh" search comparator',
                                     "description": "Search the archive for the comparator"}}], "2026-10-25T10:05"),
        row("user", "<task-notification><result>Subagent report: the push scan got faster with a pickaxe prefilter."
                    "</result></task-notification>", "2026-10-25T10:06"),
        row("user", "This session is being continued from a previous conversation. listed_commits was added",
            "2026-10-25T10:07", isCompactSummary=True),
        row("user", "You are an INDEPENDENT AUDITOR. Check the comparator.", "2026-10-25T10:08", entrypoint="sdk-cli"),
        row("assistant", [{"type": "text", "text": f"The key was {FAKE_KEY} but this line only tests the masking."}],
            "2026-10-25T10:09"),
    ]


def _docs(kind=None):
    con = sqlite3.connect(common.DATA / "index.db")
    try:
        sql = "select kind, text from docs" + (" where kind = ?" if kind else "")
        return con.execute(sql, (kind,) if kind else ()).fetchall()
    finally:
        con.close()


def _memory(stores, text):
    d = stores / "proj" / "memory"
    d.mkdir(exist_ok=True)
    (d / "rule-x.md").write_text(text, encoding="utf-8")
    return d / "rule-x.md"


def test_query_terms_fold_cut_to_five_and_keep_names_whole():
    assert archive._terms("COL'un dk/sn hatası listed_commits predict.py 58.2 how") == [
        ("col", "col"), ("dk", "dk"), ("sn", "sn"), ("hatas", "hatasi"), ("listed commits", "listed commits"),
        ("predict py", "predict py"), ("58 2", "58 2")]


def test_the_exact_word_outranks_its_stem(transcript):
    """"NotebookLM" was once lost among hundreds of Kaggle "notebook" hits that share its first five letters."""
    rows = [row("assistant", [{"type": "text", "text": "The Kaggle notebook ran; the notebook output went to the "
                                                       "notebook log and the notebook finished."}],
                f"2026-10-25T1{i // 60}:{i % 60:02d}") for i in range(30)]
    rows.append(row("assistant", [{"type": "text", "text": "Connecting NotebookLM through MCP is unofficial; we "
                                                           "advised against it because of the terms of use."}],
                    "2026-10-25T12:00"))
    write(transcript, rows)
    archive.update()
    assert "NotebookLM" in archive.search("NotebookLM")[0]["text"]


def test_a_search_finds_each_kind_once(transcript):
    write(transcript, _rows())
    archive.update()
    top = archive.search("düzeltmiştik karşılaştırıcı")[0]
    assert top["kind"] == "user" and "karşılaştırıcısı" in top["text"]
    assert [h["text"].split()[0] for h in archive.search("0426749", kinds="commit")] == ["0426749"]
    assert archive.search("pickaxe")[0]["kind"] == "report"
    assert archive.search("listed_commits")[0]["kind"] == "summary"
    # a script's prompt never passes for the user's words
    assert archive.search("AUDITOR")[0]["kind"] == "prompt"
    assert all("AUDITOR" not in h["text"] for h in archive.search("comparator", kinds="user"))
    # the call written twice is one step; the search call is not a step at all
    assert [t for _, t in _docs("step")] == ["Commit the comparator fix\ngit commit -m 'unit'"]


def test_no_key_goes_into_the_index_or_out_of_show(transcript):
    write(transcript, _rows())
    archive.update()
    assert not any(FAKE_KEY in t for _, t in _docs())
    assert keys.MARK in archive.search("masking")[0]["text"]
    shown = archive.show(f"{SID[:8]}:10")
    assert keys.MARK in shown and FAKE_KEY not in shown


def test_only_new_rows_are_indexed_and_a_half_written_line_waits(transcript):
    rows = _rows()
    write(transcript, rows[:2])
    assert archive.update()["new_docs"] == 2
    assert archive.update()["files"] == 0  # nothing changed, nothing read
    half = __import__("json").dumps(rows[8], ensure_ascii=False)
    write(transcript, rows[2:4], mode="a", tail=half[:20])
    assert archive.update()["new_docs"] == 2  # the step and the commit; the half line waits
    with open(transcript, "a", encoding="utf-8", newline="\n") as f:
        f.write(half[20:] + "\n")
    assert archive.update()["new_docs"] == 1
    assert len(_docs("user")) == 1 and len(_docs("prompt")) == 1


def test_a_rewritten_transcript_is_indexed_again_from_the_start(transcript):
    write(transcript, _rows())
    archive.update()
    write(transcript, _rows()[:1])
    archive.update()
    assert [k for k, _ in _docs()] == ["user"]


def test_show_marks_the_hit_and_keeps_the_turn_around_it(transcript, stores):
    write(transcript, _rows())
    _memory(stores, "Rule: a duration is compared only with a duration.")
    archive.update()
    shown = archive.show(f"{SID[:8]}:4")
    assert f">> [commit {common.local('2026-10-25T10:03')}] 0426749" in shown
    assert "[user" in shown and "Root cause" in shown and "[command] Commit the comparator fix" in shown
    assert f"[script {common.local('2026-10-25T10:08')}] You are an INDEPENDENT AUDITOR" in shown
    assert archive.show("memory:proj/rule-x").startswith("Rule:")
    assert archive.show(f"{SID[:8]}:4", lang="tr").count("[kullanıcı") == 1
    for bad in ("nope:1", "memory:../proj/rule-x", "memory:proj/../x", "../../x:1", "*:1"):
        assert archive.show(bad).startswith("not found"), bad


def test_memory_files_are_read_again_only_when_one_changed(stores):
    rule = _memory(stores, "Rule: a duration is compared with a duration.")
    assert archive.update()["memory_files"] == 1
    assert archive.update()["memory_files"] == 0
    rule.write_text("Rule: a duration is compared only with a duration.", encoding="utf-8")
    os.utime(rule, (rule.stat().st_atime, rule.stat().st_mtime + 5))
    assert archive.update()["memory_files"] == 1
    hit = archive.search("rule only")[0]
    assert hit["kind"] == "memory" and hit["ref"] == "memory:proj/rule-x" and len(_docs("memory")) == 1


def test_a_forked_copy_is_indexed_once_but_a_later_repeat_is_kept(transcript):
    """Forked sessions copy their parent's rows, and one script sent the same prompt 476 times."""
    rows = _rows()
    write(transcript, rows)
    fork = transcript.parent / "bbbb2222-0000-0000-0000-000000000000.jsonl"
    later = dict(rows[0], timestamp="2026-10-26T09:00:00.000Z")  # the same words on another day
    prompt_again = dict(rows[8], timestamp="2026-10-26T09:05:00.000Z")
    write(fork, rows[:2] + [later, prompt_again])
    archive.update()
    said = [h["at"] for h in archive.search("karşılaştırıcısı karıştırıyor", kinds="user")]
    assert sorted(said) == ["2026-10-25T10:00", "2026-10-26T09:00"]
    assert len(archive.search("Root cause", kinds="assistant")) == 1
    assert len(archive.search("AUDITOR", kinds="prompt")) == 1


def test_what_this_session_holds_in_context_is_left_out(transcript, stores, monkeypatch):
    """The question just asked, and all this session said since its last compaction, is in context already: as a
    hit it only repeats itself. What came before the compaction is not in context, so it is searched."""
    write(transcript, [
        row("user", "the cache key moved to the request hash", "2026-10-25T09:00", origin={"kind": "human"}),
        {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-10-25T09:30:00.000Z"},
        row("user", "how did we change the cache key?", "2026-10-25T10:00", origin={"kind": "human"}),
    ])
    other = "bbbb2222-0000-0000-0000-000000000000"  # never compacted: all of it is in context
    write(stores / "proj" / f"{other}.jsonl", [row("user", "cache key again?", origin={"kind": "human"})])
    archive.update()
    assert len(archive.search("cache key")) == 3
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", SID)
    assert sorted(h["at"] for h in archive.search("cache key")) == ["2026-10-25T09:00", "2026-10-25T10:00"]
    assert len(archive.search("cache key", session=SID[:8])) == 2  # this session asked for by name: all of it
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", other)
    assert len(archive.search("cache key")) == 2


def test_a_budget_indexes_the_newest_sessions_first_and_counts_the_rest(stores):
    for i, name in enumerate(["old", "mid", "new"]):
        p = stores / "proj" / f"{name}.jsonl"
        write(p, [row("user", f"word{name} is here", origin={"kind": "human"})])
        os.utime(p, (1_000_000 + i * 100, 1_000_000 + i * 100))
    clock = iter(range(100))
    stats = archive.update(budget=1.5, clock=lambda: next(clock))
    assert (stats["files"], stats["pending_files"]) == (1, 2)
    assert archive.search("wordnew") and not archive.search("wordold")
    assert archive.update()["files"] == 2 and archive.search("wordold")


def test_one_background_update_runs_at_a_time(transcript):
    write(transcript, _rows())
    common.DATA.mkdir(parents=True)
    lock = common.DATA / "update.lock"
    lock.write_text("123")
    assert archive.background_update() is None  # another run holds the lock
    os.utime(lock, (1_000_000, 1_000_000))  # a lock this old belongs to a run that died
    assert archive.background_update()["files"] == 1 and not lock.exists()


def test_the_command_line_searches_and_shows(transcript):
    write(transcript, _rows())
    run = [sys.executable, str(SCRIPTS / "lrm.py")]
    out = subprocess.run(run + ["search", "karşılaştırıcı", "düzeltmiştik", "-k", "2"], capture_output=True,
                         text=True, encoding="utf-8", timeout=60).stdout
    assert out.startswith("terimler: karsi*, duzel*")
    assert f"1. [user] {common.local('2026-10-25T10:00')} {SID[:8]}:1 — " in out and "show <kaynak>" in out
    out = subprocess.run(run + ["search", "pickaxe", "prefilter"], capture_output=True, text=True,
                         encoding="utf-8", timeout=60).stdout
    assert out.startswith("terms: picka*, prefi*") and "1. [report]" in out and "show <ref>" in out
    shown = subprocess.run(run + ["show", f"{SID[:8]}:4"], capture_output=True, text=True, encoding="utf-8",
                           timeout=60).stdout
    assert f">> [commit {common.local('2026-10-25T10:03')}] 0426749" in shown
