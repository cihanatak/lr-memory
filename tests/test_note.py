"""The working note: what the trail keeps from the transcript, and the note the hooks put back."""
import json
import shutil
import subprocess
import sys

import pytest

from conftest import SCRIPTS, SID, row, write
from lr_memory import common, note


def _tool(name, inp, id_, at="2026-10-25T10:00"):
    return row("assistant", [{"type": "tool_use", "id": id_, "name": name, "input": inp}], at)


def _result(id_, text, at="2026-10-25T10:00"):
    return row("user", [{"type": "tool_result", "tool_use_id": id_, "content": text}], at)


def _hook(event) -> subprocess.CompletedProcess:
    data = event if isinstance(event, str) else json.dumps(event)
    return subprocess.run([sys.executable, str(SCRIPTS / "lrm.py"), "hook"], input=data, capture_output=True,
                          text=True, encoding="utf-8", timeout=60)


def test_the_trail_keeps_the_users_own_words_and_only_theirs(transcript):
    paste = '<pasted_content id="1">' + "x" * 5000 + "</pasted_content>"
    write(transcript, [
        row("user", "said before the last compaction", "2026-10-25T09:00", origin={"kind": "human"}),
        {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-10-25T09:30:00.000Z"},
        row("user", "This session is being continued from a previous conversation.", "2026-10-25T09:31",
            isCompactSummary=True),
        row("user", "Don't touch the old migration; only fix the parser.", "2026-10-25T10:00",
            origin={"kind": "human"}),
        row("user", f"{paste} look at this log", "2026-10-25T10:01", origin={"kind": "human"}),
        row("user", "<command-name>/model</command-name>", "2026-10-25T10:02"),
        row("user", "a subagent's prompt", "2026-10-25T10:03", isSidechain=True),
        row("user", "You are a judge. Reply with exactly PASS.", "2026-10-25T10:04", entrypoint="sdk-cli"),
        row("user", [{"type": "text", "text": "a background task finished"}], "2026-10-25T10:05",
            origin={"kind": "task-notification"}),
    ])
    tr = note.trail(transcript)
    assert [w["text"] for w in tr["user"]] == ["Don't touch the old migration; only fix the parser.",
                                               f"[pasted text, {len(paste)} characters] look at this log"]
    assert tr["lang"] == "en" and tr["rows"] == 7  # the rows after the boundary


def test_the_trail_keeps_files_commits_and_test_results(transcript):
    write(transcript, [
        _tool("Edit", {"file_path": "/repo/src/parser.py"}, "e1"),
        _tool("Edit", {"file_path": "/repo/src/parser.py"}, "e2"),
        _tool("Edit", {"file_path": "/repo/src/parser.py"}, "e2"),  # written twice: one edit
        _tool("Write", {"file_path": "/tmp/scratch.txt"}, "e3"),  # a temp file is not the work
        _tool("Bash", {"command": "git commit -m 'Parser: keep quotes'"}, "c1"),
        _result("c1", "[main 1a2b3c4] Parser: keep quotes\n 1 file changed"),
        _tool("Bash", {"command": "git commit -q -m x && git log --oneline -1"}, "c2"),
        _result("c2", "5d6e7f8 Parser: a quiet commit"),
        _tool("Bash", {"command": "python -m pytest tests/test_parser.py"}, "t1"),
        _result("t1", "....F\n=== 1 failed, 13 passed in 4.06s ==="),
        _tool("Bash", {"command": "cat notes.txt"}, "n1"),
        _result("n1", "we had 3 passed checks"),  # not a test run
        row("assistant", [{"type": "text", "text": "Fixed the parser; one test still fails."}]),
    ])
    tr = note.trail(transcript)
    assert [tuple(e) for e in tr["edited"]] == [("/repo/src/parser.py", 2)]
    assert [c["hash"] for c in tr["commits"]] == ["1a2b3c4", "5d6e7f8"]
    assert tr["tests"] == ["=== 1 failed, 13 passed in 4.06s ==="]
    assert tr["final"] == "Fixed the parser; one test still fails."


def test_the_task_list_is_replayed_from_whichever_tool_was_used_last(transcript):
    plan = [_tool("mcp__ccd_turn__update_plan", {"items": [{"content": "Read the code", "status": "in_progress"},
                                                            {"content": "Fix it", "status": "pending"},
                                                            {"content": "Test it", "status": "pending"}]}, "p1"),
            {"type": "system", "subtype": "compact_boundary"},  # a list set before the last compaction still counts
            _tool("mcp__ccd_turn__update_plan", {"advance": True}, "p2"),
            _tool("mcp__ccd_turn__update_plan", {"advance": True}, "p2")]  # written twice: one step
    write(transcript, plan)
    assert [(i["content"], i["status"]) for i in note.trail(transcript)["plan"]] == [
        ("Read the code", "completed"), ("Fix it", "in_progress"), ("Test it", "pending")]
    todo = _tool("TodoWrite", {"todos": [{"content": "Ship", "status": "pending", "activeForm": "Shipping"}]}, "w1")
    write(transcript, plan + [todo])
    assert note.trail(transcript)["plan"] == [{"content": "Ship", "status": "pending"}]
    tasks = [_tool("TaskCreate", {"subject": "Write the docs", "description": "README"}, "k1"),
             _result("k1", "Task #1 created successfully: Write the docs"),
             _tool("TaskCreate", {"subject": "Tag the release"}, "k2"),
             _result("k2", "Task #2 created successfully: Tag the release"),
             _tool("TaskCreate", {"subject": "Drop this"}, "k3"),
             _result("k3", "Task #3 created successfully: Drop this"),
             _tool("TaskUpdate", {"taskId": "1", "status": "completed"}, "k4"),
             _tool("TaskUpdate", {"taskId": "3", "status": "deleted"}, "k5"),
             _tool("TaskUpdate", {"taskId": "9", "status": "completed"}, "k6")]  # not one of ours: ignored
    write(transcript, plan + [todo] + tasks)
    assert [(i["content"], i["status"]) for i in note.trail(transcript)["plan"]] == [
        ("Write the docs", "completed"), ("Tag the release", "pending")]


def test_the_language_follows_the_user_unless_it_is_set(monkeypatch):
    assert common.lang("şunu düzelt ve testleri koş") == "tr"
    assert common.lang("fix this and run the tests") == "en"
    assert common.lang("Is it this initial list I edit in Vim? It is.") == "en"  # i and I are not ı and İ
    monkeypatch.setenv("LR_MEMORY_LANG", "tr")
    assert common.lang("fix this") == "tr"


def test_the_note_keeps_the_pointer_when_the_rest_is_too_long():
    ep = {"lang": "tr", "at": "2026-10-25T10:00:00Z", "transcript": "/t.jsonl",
          "user": [{"at": "2026-10-25T09:59", "text": "eski göçe dokunma"}],
          "plan": [{"content": "Ayrıştırıcıyı düzelt", "status": "in_progress"}, {"content": "x", "status": "completed"}],
          "edited": [["a.py", 3]], "commits": [{"hash": "1a2b3c4", "subject": "Parser"}], "tests": ["1 passed"],
          "final": "son söz"}
    text = note.note(ep, "/data/trail.json")
    assert text.startswith("Çalışma notu (lr-memory)") and '"eski göçe dokunma"' in text
    assert "[sürüyor] Ayrıştırıcıyı düzelt" in text and "] x" not in text  # done items are not open work
    assert "a.py (×3)" in text and "1a2b3c4 Parser" in text and "show <kaynak>" in text
    ep.update(lang="en", user=[{"at": "2026-10-25T09:59", "text": "y" * 600}] * 20)
    text = note.note(ep, "/data/trail.json")
    assert len(text) <= note.NOTE_CHARS and text.endswith("show <ref>).") and "/t.jsonl" in text


def test_the_hooks_write_the_trail_add_the_summary_and_put_the_note_back(transcript):
    write(transcript, [row("user", "Keep the old API; add the flag only.", origin={"kind": "human"}),
                       row("assistant", [{"type": "text", "text": "Adding the flag now."}])])
    base = {"session_id": SID, "transcript_path": str(transcript)}
    assert _hook({**base, "hook_event_name": "PreCompact", "trigger": "auto"}).stdout == ""
    assert _hook({**base, "hook_event_name": "PostCompact", "compact_summary": "Summary: flag work."}).stdout == ""
    trail = json.loads(next((common.DATA / "episodes" / SID).glob("*.json")).read_text(encoding="utf-8"))
    assert trail["summary"] == "Summary: flag work." and trail["trigger"] == "auto"
    ctx = json.loads(_hook({**base, "hook_event_name": "SessionStart", "source": "compact"}).stdout)
    ctx = ctx["hookSpecificOutput"]
    assert ctx["hookEventName"] == "SessionStart"
    assert '"Keep the old API; add the flag only."' in ctx["additionalContext"]
    assert _hook({**base, "hook_event_name": "SessionStart", "source": "startup"}).stdout == ""


def test_a_stale_trail_is_not_put_back():
    folder = common.DATA / "episodes" / SID
    folder.mkdir(parents=True)
    (folder / "2026-01-01T000000Z.json").write_text(json.dumps({"at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    assert _hook({"session_id": SID, "hook_event_name": "SessionStart", "source": "compact"}).stdout == ""


def test_a_broken_event_exits_zero_silently_and_is_logged():
    p = _hook("{not json")
    assert p.returncode == 0 and p.stdout == ""
    assert "JSONDecodeError" in (common.DATA / "errors.log").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs sh")
def test_the_launcher_finds_a_python_and_passes_the_arguments(transcript):
    write(transcript, [row("user", "the flag work is done", origin={"kind": "human"})])
    out = subprocess.run(["sh", (SCRIPTS / "run.sh").as_posix(), "search", "flag"], capture_output=True, text=True,
                         encoding="utf-8", timeout=60)
    assert out.returncode == 0 and "1. [user]" in out.stdout, out.stderr
