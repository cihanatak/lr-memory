"""The surprise reflex: a fix that does not hold is named once, from the tool results alone; a rerun with nothing
changed, a refused command and a passing check are no surprise."""
from col import inquiry, report
from .colkit import hook, logged

CMD = "python -m pytest -q tests/test_cart.py"
FAIL = ("Exit code 1\nFAILED tests/test_cart.py::test_total - AssertionError: assert 98.5 == 85.0\n"
        "1 failed, 2 passed in 0.10s")


def run(command, out, failed=False, **extra):
    if failed:
        return hook("PostToolUseFailure", tool_name="Bash", tool_input={"command": command}, error=out, **extra)
    return hook("PostToolUse", tool_name="Bash", tool_input={"command": command},
                tool_response={"stdout": out, "stderr": "", "interrupted": False})


def edit(path="shop/cart.py", old="a", new="b"):
    return hook("PostToolUse", tool_name="Edit", tool_input={"file_path": path, "old_string": old, "new_string": new},
                tool_response={"filePath": path})


def note(out):
    return ((out or {}).get("hookSpecificOutput") or {}).get("additionalContext", "")


def test_the_same_failure_after_an_edit_asks_for_rival_explanations_once(col_data):
    assert note(run(CMD, FAIL, failed=True)) == ""
    assert note(edit()) == ""
    out = run(CMD, FAIL, failed=True)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure"
    said = note(out)
    assert "failed again the same way" in said and "test_cart.py::test_total" in said
    assert "stale copy or cache" in said and "single cheap command" in said
    edit()
    assert note(run(CMD, FAIL, failed=True)) == ""  # once per failing check
    assert [r["event"] for r in logged(col_data, "inquiry")] == ["nudge"]
    assert note(run(CMD, "3 passed in 0.10s")) == ""
    passed = logged(col_data, "inquiry")[-1]
    assert passed["event"] == "passed" and passed["nudged"] and passed["edits_after_nudge"] == 1


def test_a_rerun_with_nothing_changed_is_no_failed_fix(col_data):
    for _ in range(3):
        assert note(run(CMD, FAIL, failed=True)) == ""
    assert logged(col_data, "inquiry") == []


def test_a_failure_that_changes_is_named_after_the_second_fix(col_data):
    fails = [FAIL.replace("98.5", x) for x in ("98.5", "97.0", "96.0")]
    run(CMD, fails[0], failed=True)
    edit()
    assert note(run(CMD, fails[1], failed=True)) == ""  # the edit changed something: not yet a surprise
    edit()
    assert "still fails after 2 edits" in note(run(CMD, fails[2], failed=True))


def test_flags_and_pipes_do_not_hide_a_rerun():
    assert inquiry.key(CMD) == inquiry.key("cd shop && python -m pytest -x tests/test_cart.py 2>&1 | tail -5")
    assert inquiry.key("pytest tests/test_a.py") != inquiry.key("pytest tests/test_b.py")
    assert inquiry.key("npx vitest run src/cart.test.ts") == "vitest src/cart.test.ts"
    for other in ("git status", "ls tests", "cat README.md"):
        assert inquiry.key(other) == "", other


def test_a_piped_run_that_exits_0_still_counts_as_failed(col_data):
    piped = CMD + " 2>&1 | tail -3"
    out = FAIL.split("\n", 1)[1]  # tail exits 0, so the tool call succeeds
    run(piped, out)
    edit()
    assert "failed again the same way" in note(run(piped, out))


def test_how_much_of_the_output_was_shown_does_not_change_the_failure(col_data):
    long = FAIL.replace("FAILED", "E       assert 98.5 == 85.0\ntests/test_cart.py:5: AssertionError\nFAILED", 1)
    run(CMD + " 2>&1 | tail -40", long.split("\n", 1)[1])
    edit()
    assert "failed again the same way" in note(run(CMD + " 2>&1 | tail -3", FAIL.split("\n", 1)[1]))


def test_a_narrower_rerun_after_an_edit_is_the_same_check(col_data):
    run("python -m pytest -q", FAIL, failed=True)
    edit()
    assert "failed again the same way" in note(run(CMD + "::test_total", FAIL, failed=True))


def test_other_tests_failing_under_the_same_tool_are_a_check_of_their_own(col_data):
    other = FAIL.replace("test_cart.py::test_total", "test_tax.py::test_vat")
    run(CMD, FAIL, failed=True)
    edit()
    assert note(run("python -m pytest -q", other, failed=True)) == ""
    edit()
    assert "test_tax.py::test_vat" in note(run("python -m pytest -q", other, failed=True))


def test_a_whole_suite_pass_closes_the_narrower_checks(col_data):
    run(CMD, FAIL, failed=True)
    edit()
    run(CMD, FAIL, failed=True)
    edit()
    assert note(run("python -m pytest -q", "5 passed in 0.20s")) == ""
    passed = logged(col_data, "inquiry")[-1]
    assert passed["event"] == "passed" and passed["check"] == inquiry.key(CMD) and passed["edits_after_nudge"] == 1


def test_a_refused_or_interrupted_command_is_no_failure(col_data):
    run(CMD, "PreToolUse:Bash hook error: COL prediction ledger: write the expected result", failed=True)
    run(CMD, FAIL, failed=True, is_interrupt=True)
    edit()
    assert note(run(CMD, FAIL, failed=True)) == ""  # the first real failure starts the count
    edit()
    assert note(run(CMD, FAIL, failed=True))


def test_a_shell_edit_counts_as_an_edit(col_data):
    run(CMD, FAIL, failed=True)
    run("sed -i 's/0.015/0.15/' shop/settings.py", "")
    assert note(run(CMD, FAIL, failed=True))


def test_a_test_made_quiet_while_failing_is_named(col_data):
    assert note(edit("tests/test_cart.py", "def test_total():", "@pytest.mark.skip\ndef test_total():")) == ""
    run(CMD, FAIL, failed=True)
    assert note(edit("shop/cart.py", "x = 1", "x = 2  # noqa")) == ""  # not a test
    said = note(edit("tests/test_cart.py", "def test_total():", "@pytest.mark.skip\ndef test_total():"))
    assert "'pytest.mark.skip'" in said and CMD.split()[2] in said
    assert note(edit("tests/test_cart.py", "a", "b  # noqa")) == ""  # once


def test_off_is_silent(col_data, monkeypatch):
    monkeypatch.setenv("COL_INQUIRY", "off")
    run(CMD, FAIL, failed=True)
    edit()
    assert run(CMD, FAIL, failed=True) is None
    assert logged(col_data, "inquiry") == []


def test_the_reflex_speaks_the_users_language(col_data, monkeypatch):
    monkeypatch.setenv("COL_LANG", "tr")
    run(CMD, FAIL, failed=True)
    edit()
    assert "yine aynı şekilde düştü" in note(run(CMD, FAIL, failed=True))


def test_the_report_counts_the_questions(col_data):
    run(CMD, FAIL, failed=True)
    edit()
    run(CMD, FAIL, failed=True)
    edit()
    run(CMD, "3 passed in 0.10s")
    text = report.report(30, "en")
    assert "where COL asked for rival explanations: 1; 1 of those checks passed later" in text
