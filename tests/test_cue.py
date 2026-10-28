"""The cue: the turns of a project's earlier sessions that a prompt brings back, put in front of the model by the
UserPromptSubmit hook."""
import json
import subprocess
import sys

from conftest import SCRIPTS, SID, row, write
from lr_memory import cue

OLD = "bbbb1111-2222-3333-4444-555566667777"
PROMPT = "Run tools/bench.py and add today's p50 to docs/performance.md, next to yesterday's baseline."


def _yesterday(stores, project="proj", session=OLD):
    write(stores / project / f"{session}.jsonl", [
        row("user", "Run tools/bench.py and tell me the p50. That's our baseline before the currency work.",
            "2026-10-27T10:00", origin={"kind": "human"}),
        row("assistant", [{"type": "text", "text": "Baseline p50 is 25.9 ms (p95 38.8 ms) over 120 invoices."}],
            "2026-10-27T10:01"),
        row("user", "Correction: finance changed the books rate last week, it's 7%, not 8%.", "2026-10-27T10:05",
            origin={"kind": "human"}),
        row("assistant", [{"type": "text", "text": "Changed the books rate in ledgerly/tax.py from 8% to 7% and updated "
                                                   "tests/test_tax.py; the CHANGELOG line under Unreleased says 7%."}],
            "2026-10-27T10:06"),
    ])


def _hook(stores, prompt, session=SID, project="proj"):
    data = {"hook_event_name": "UserPromptSubmit", "prompt": prompt, "session_id": session,
            "transcript_path": str(stores / project / f"{session}.jsonl")}
    r = subprocess.run([sys.executable, str(SCRIPTS / "lrm.py"), "hook"], input=json.dumps(data), capture_output=True,
                       text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout.strip() else ""


def test_a_prompt_brings_back_the_turn_whole_with_the_number_in_its_answer(stores):
    _yesterday(stores)
    said = _hook(stores, PROMPT)
    assert "That's our baseline before the currency work" in said
    assert "Baseline p50 is 25.9 ms" in said  # the answer, where the number is, comes with the user's words
    assert "finance" not in said  # a turn that shares too little with the prompt stays out


def test_each_turn_is_brought_back_once_a_session(stores):
    _yesterday(stores)
    assert "25.9" in _hook(stores, PROMPT)
    assert _hook(stores, PROMPT) == ""
    assert "25.9" in _hook(stores, PROMPT, session="cccc1111-2222-3333-4444-555566667777")


def test_the_reason_comes_back_for_a_question_about_it(stores):
    _yesterday(stores)
    said = _hook(stores, "People keep asking why books are at 7%. Add a short comment above that rate in "
                         "ledgerly/tax.py that explains it.")
    assert "finance changed the books rate last week" in said  # found by the answer, it brings the user's words


def test_only_earlier_sessions_of_the_same_project(stores):
    (stores / "other").mkdir()
    _yesterday(stores, project="other")
    assert _hook(stores, PROMPT) == ""  # another project's session
    _yesterday(stores, session=SID)
    assert _hook(stores, PROMPT) == ""  # the session's own turns are in its context already


def test_other_projects_do_not_crowd_this_one_out(stores):
    (stores / "other").mkdir()
    for n in range(60):  # sessions of another project that share every word of the prompt
        write(stores / "other" / f"dddd{n:04d}-2222-3333-4444-555566667777.jsonl",
              [row("user", f"{PROMPT} Variant {n}.", "2026-10-26T10:00", origin={"kind": "human"})])
    cue._index(stores / "other")
    _yesterday(stores)
    assert "Baseline p50 is 25.9 ms" in _hook(stores, PROMPT)


def test_long_replies_of_common_words_do_not_push_out_the_turn_of_rare_ones(stores):
    reply = ("I went through the importer line by line: it now reads each row only once, detects the CSV dialect "
             "before anything else, and skips a malformed row with a warning instead of an exception. You can already "
             "see the skipped rows in the import log, with their line numbers. I did not touch the exporter or any of "
             "the tools, and the earlier session's changes to the tax classes stand. The full suite passes, with six "
             "new tests. One question: should a file with more than ten malformed rows be refused as a whole? Reply "
             "when you can; nothing else is pending.")
    rows = []
    for n in range(4):  # replies as long as replies are, each sharing many of the prompt's common words once
        rows += [row("user", f"Item {n}: tidy up the importer.", f"2026-10-27T09:0{n}", origin={"kind": "human"}),
                 row("assistant", [{"type": "text", "text": f"Item {n} is done. {reply}"}], f"2026-10-27T09:0{n}")]
    write(stores / "proj" / "eeee1111-2222-3333-4444-555566667777.jsonl", rows)
    _yesterday(stores)
    said = _hook(stores, f"{PROMPT} Before anything else, reply with one line only: the baseline p50 you can already "
                         "see in your context from an earlier session, or 'none'. Do not run any tools.")
    assert "Baseline p50 is 25.9 ms" in said


def test_a_short_or_unrelated_prompt_brings_nothing(stores):
    _yesterday(stores)
    assert _hook(stores, "Thanks, go on.") == ""
    assert _hook(stores, "Write a section in README.md on how to install ledgerly with pip.") == ""


def test_the_cue_can_be_turned_off(stores, monkeypatch):
    _yesterday(stores)
    monkeypatch.setenv("LR_MEMORY_CUE", "off")
    assert _hook(stores, PROMPT) == ""


def test_turns_finds_the_same_turns_in_process(stores):
    _yesterday(stores)
    cue._index(stores / "proj")
    found = cue.turns(PROMPT, SID, stores / "proj")
    assert [x["ref"] for x in found] == [f"{OLD}:1"]
    assert found[0]["answer"].startswith("Baseline p50 is 25.9 ms")
