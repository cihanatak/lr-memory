"""The hooks as Claude Code runs them: a new process each time, the event on stdin, and nothing that can fail the
session."""
import json
import subprocess
import sys

from col import __version__, outcome
from .colkit import CLI, SESSION, bash, call, feedback, hook, logged, result, say, stop, transcript, user

LATER = "2026-10-25T11:00:00.000Z"


def _projects(col_data):
    return col_data.parent / "claude" / "projects"


def _cli(*args):
    r = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0 and not r.stderr.strip(), r.stderr
    return r.stdout


def test_a_false_claim_blocks_the_stop_twice_then_lets_go(col_data, tmp_path):
    path = transcript(_projects(col_data), [user("fix the bug"), say("Done. I fixed the bug and 12 tests passed.")])
    for _ in range(2):
        out = stop(path, tmp_path)
        assert out["decision"] == "block" and "no tool ran in this turn" in out["reason"]
        assert "'12 tests passed' is said" in out["reason"]
    assert stop(path, tmp_path) is None  # twice is enough; the user reads the message
    assert [c["blocked"] for c in logged(col_data, "checks")] == [True, True, False]
    transcript(_projects(col_data), [user("and the docs?", at=LATER), say("Done. I pushed the docs.")], mode="a")
    assert stop(path, tmp_path)["decision"] == "block"  # a new turn, a new count


def test_a_block_is_judged_by_the_answer_to_it(col_data, tmp_path):
    projects = _projects(col_data)
    path = transcript(projects, [user("what changed?"), say("Done. I fixed the bug.")])
    assert stop(path, tmp_path)["decision"] == "block"
    transcript(projects, [feedback("COL: ..."), say("I had already answered that in my previous message.")], mode="a")
    assert stop(path, tmp_path) is None  # the check reads the answer, not the blocked message again
    transcript(projects, [user("next", at=LATER), say("Done. I updated the config.")], mode="a")
    assert stop(path, tmp_path)["decision"] == "block"
    answer = "You're right, I missed that; nothing ran in this turn."
    transcript(projects, [feedback("COL: ..."), say(answer)], mode="a")
    assert stop(path, tmp_path) is None
    labels = [(o["kind"], o["label"]) for o in logged(col_data, "outcomes")]
    assert labels == [("no-tools", "wrong"), ("no-tools", "right")]


def test_taking_the_claim_back_labels_the_block_right():
    answer = ("I'm taking that claim back. I ran no tools and no tests in this session, so I have no evidence that a "
              "parser bug was fixed or that 12 tests passed.")  # a real answer to a right block
    assert outcome.label([answer]) == ("right", "taking that claim back")
    assert outcome.label(["12 test geçti iddiasını geri alıyorum."])[0] == "right"


def test_the_block_speaks_the_users_language(col_data, tmp_path, monkeypatch):
    monkeypatch.delenv("COL_LANG")
    projects = _projects(col_data)
    path = transcript(projects, [user("hatayı düzelt ve testleri çalıştır lütfen"), say("Tamam, hatayı düzelttim.")])
    assert stop(path, tmp_path)["reason"].startswith("COL: son mesajındaki")
    path = transcript(projects, [user("Please fix the failing import in the parser module and tell me what was wrong "
                                      "with it.", at=LATER), say("Done. I fixed the import.")])
    assert stop(path, tmp_path)["reason"].startswith("COL: these claims")


def test_the_language_the_user_writes_in_carries_to_the_gate(col_data, tmp_path, monkeypatch):
    monkeypatch.delenv("COL_LANG")
    assert hook("UserPromptSubmit", prompt="testleri arka planda çalıştır ve sonucu söyle") is None
    # injected text says nothing of the user's language
    hook("UserPromptSubmit", prompt="<task-notification>The job finished: 41 tests passed and the coverage report "
                                    "was written to disk.</task-notification>")
    assert bash(tmp_path, "python sim.py", "run", True).startswith("COL öngörü defteri")


def test_log_mode_records_without_blocking_and_off_does_nothing(col_data, tmp_path, monkeypatch):
    path = transcript(_projects(col_data), [user("fix it"), say("Done. I fixed it.")])
    monkeypatch.setenv("COL_CLAIMS", "log")
    assert stop(path, tmp_path) is None
    assert [(c["blocked"], c["problems"][0]["kind"]) for c in logged(col_data, "checks")] == [(False, "no-tools")]
    monkeypatch.setenv("COL_CLAIMS", "off")
    assert stop(path, tmp_path) is None
    assert len(logged(col_data, "checks")) == 1


def test_a_hook_never_fails_the_session(col_data, tmp_path):
    path = transcript(_projects(col_data), [user("hello there")])
    with open(path, "a", encoding="utf-8") as f:
        f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "cut sho\n')
    for raw in ("", "not json", "[1, 2]", json.dumps({"hook_event_name": "Unknown"}),
                json.dumps({"hook_event_name": "Stop", "session_id": "nobody", "transcript_path": str(tmp_path / "x")}),
                json.dumps({"hook_event_name": "Stop", "session_id": SESSION, "transcript_path": str(path)}),
                json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": "not a dict"})):
        r = subprocess.run([sys.executable, str(CLI), "hook"], input=raw, capture_output=True, text=True,
                           encoding="utf-8", timeout=60)
        assert (r.returncode, r.stdout, r.stderr) == (0, "", ""), raw


def test_the_report_counts_what_was_recorded(col_data, tmp_path):
    assert "Nothing recorded in the last 30 days." in _cli("report")
    projects = _projects(col_data)
    path = transcript(projects, [
        user("run the tests"), say("Prediction [t]: 41 passed (~2 min)"), call("Bash", command="pytest -q"),
        result("41 passed in 3.2s"), say("Result [t]: 41 passed. Done, 41 tests passed.")])
    assert stop(path, tmp_path) is None
    transcript(projects, [user("ship it", at=LATER), say("Done. I updated the docs.")], mode="a")
    assert stop(path, tmp_path)["decision"] == "block"
    assert bash(tmp_path, "python sim.py", "run", True)
    out = _cli("report", "--days", "7")
    for line in ("COL report, the last 7 days", "Claim check: 2 finished turns checked, 1 flagged, 1 blocked.",
                 "Flagged: work claimed with no tool run 1.", "Prediction ledger: 1 predictions, 1 results.",
                 "Compared: 1 held, 0 missed, 0 could not be compared.",
                 "1 of 1 results give a number that appears in real tool output.",
                 "Launches stopped for a missing prediction: 1.", f"Logs: {col_data}"):
        assert line in out, line
    assert _cli("--version").strip() == f"col {__version__}"
