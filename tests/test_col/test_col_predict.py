"""The prediction ledger: the gate before long jobs and irreversible steps, the reading of numbers, the comparison
like with like, and the record going back to the model."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from col import predict
from .colkit import SESSION, bash, call, hook, logged, result, say, stop, transcript, user


def test_numbers_are_read_in_the_writers_convention():
    assert predict.num("51.713", tr=True) == 51713 and predict.num("51.713") == 51.713
    assert predict.num("1,234") == 1234 and predict.num("1,234", tr=True) == 1.234
    assert predict.num("1.234,5") == 1234.5 and predict.num("1,234.5") == 1234.5
    assert predict.num("49,88") == 49.88 and predict.num("49.88", tr=True) == 49.88
    assert predict.num("1.234.567") == 1234567 and predict.num("-3") == -3


def test_prediction_lines_are_read_as_numbers_not_as_names():
    assert predict.expectation("RL4 average 48–52 (~22:00)") == (48, 52)
    assert predict.expectation("v1.1-3 copy scores 48-52") == (48, 52)  # a version is not a range
    assert predict.expectation("a gap of at least 2") == (2, float("inf"))
    assert predict.expectation("hata en çok 3", tr=True) == (float("-inf"), 3)
    assert predict.expectation("RL4 average ~50") == (45, 55)
    assert predict.expectation("quality will be good") == (None, None)
    assert predict.expectation("41 passed (~1 sec)") == pytest.approx((36.9, 45.1))  # the due time is no value


def test_markers_are_read_in_english_and_turkish():
    said = ("The run is done. Result [t1]: win rate 41; lower than expected.\n"
            "**Prediction [a]:** 5 tests pass. Prediction [b]: 0 errors\n"
            "In short, the result: it went well over 3 rounds.\n"
            "**Result:** the tournament finished\n"
            "Öngörü [c]: 12 dosya değişir. Sonuç [c]: 12 dosya\n"
            "Hypothesis [noise]: a rerun scores 46-50")
    assert predict.marks(said) == [
        ("result", "t1", "win rate 41; lower than expected."), ("prediction", "a", "5 tests pass."),
        ("prediction", "b", "0 errors"), ("result", None, "the tournament finished"),
        ("prediction", "c", "12 dosya değişir."), ("result", "c", "12 dosya"),
        ("hypothesis", "noise", "a rerun scores 46-50")]


def test_results_are_compared_like_with_like():
    """The first night of real use compared "4-9 dk" with "168 sn" as minutes, and a rule 60 times wrong followed.
    That night's lines, and English ones, with the verdict a reader gives them."""
    cases = [
        ("5 görselin 5'i üretilir, duvar saati 4-9 dk (~02:52)", "5/5 görsel, 168 sn.", "missed", True),
        ("2 görselin 2'si üretilir, duvar saati 1-4 dk (~02:55)", "2/2 görsel, 62 sn.", "held", True),
        ("559 test, 0 hata (~03:12)", "559 test, 2 hata (biri dosya yazımıyla çakışma).", "missed", True),
        ("sunucu 1–5 sn içinde hazır, HTTP 200 (~02:40)", "Vite 0,33 sn'de hazırdı, sayfa açıldı.", "missed", True),
        ("1 oturum, 60–150 sn, 1024×1024 PNG (~03:30)",
         "ham görsel 1254×1254, işlenmiş hâli 1208×377 (1024×1024 tahmini tutmadı).", "not comparable", True),
        ("21 oturumun 19–21'i tamam, 35–45 dk (~04:50)",
         "21 oturumun 21'i tamamlandı, duvar saati ~17 dk (35–45 dk öngörüsü tutmadı, daha hızlı).", "missed", True),
        ("4/4 oturum başarılı, toplam 5–9 dk (~06:56)", "4/4 başarılı, ~2,9 dk (ajanın ölçümü).", "missed", True),
        ("toplam 78", "78", "held", True),
        ("41 passed, 0 failed (~2 min)", "41 passed, 0 failed in 2.1 min", "held", False),
        ("41 geçer, 0 düşer (~2 dk)", "41 geçti, 0 düştü, 2,1 dk sürdü", "held", True),
        ("41 geçer, 0 düşer (~2 dk)", "40 geçti, 1 düştü, 2 dk sürdü", "missed", True),
        ("the build takes 3-5 min", "built in 7 min", "missed", False),
        ("at least 90% coverage", "coverage 93%", "held", False),
        ("1,200 rows imported", "imported 1200 rows", "held", False),  # English groups thousands with commas
        ("1.200 satır aktarılır", "1200 satır aktarıldı", "held", True),  # Turkish with dots
    ]
    for prediction, observed, verdict, tr in cases:
        assert predict.compare(prediction, observed, tr)[0] == verdict, prediction
    details = predict.compare(*cases[0][:2], True)[1]
    assert [(d["label"], d["held"], d.get("direction")) for d in details] == [("görs", True, None),
                                                                              ("time", False, "low")]
    assert predict.compare("the build takes 3-5 min", "built in 7 min")[1][0]["direction"] == "high"


def test_several_percentages_pair_by_name_then_order_and_are_used_once():
    cases = [
        ("test-id %40–70, test-composition %0–15 (~45 dk)",
         "Train B6 PPO+LSTM, 3 seeds × 3M steps → test-id %62,5, bileşim %0; süre 69 dk.",
         "missed", [("id", 62.5, True), ("composition", 0.0, True), ("", 69 * 60, False)]),
        ("validation@30 %60–75, validation-composition@8 %30–80 (~30 dk)",
         "Train AC-DoF v0, 3 seeds → validation@30 %78, bileşim@8 %22",
         "missed", [("validation", 78.0, False), ("composition", 22.0, False)]),
        ("10–30 dk; segment 120–250", "227 segment, 2.755 avantajlı dal, eşleşmeyen segment 0.",
         "held", [("", 227.0, True)]),
    ]
    for prediction, observed, verdict, want in cases:
        got, details = predict.compare(prediction, observed, True)
        assert got == verdict, prediction
        assert [(d.get("name", ""), d["observed"], d["held"]) for d in details] == want, prediction


def test_a_background_job_starts_only_with_a_measurable_prediction(col_data, tmp_path):
    assert "Prediction [key]" in bash(tmp_path, "python sim.py --games 450", "Run the tournament", True)
    assert bash(tmp_path, "python sim.py --games 450", "Run it. Prediction: it goes well", True)  # nothing to measure
    assert bash(tmp_path, "python sim.py --games 450", "Run it. Prediction [t1]: win rate 48–52 (~03:00)", True) is None
    assert bash(tmp_path, "sleep 600; echo wake", "Wait for the run", True) is None  # a wait has no result
    # a dev server has no result either, wherever the flags sit
    assert bash(tmp_path, "npm --prefix D:/game run dev -- --port 5190 --strictPort", "Start the server", True) is None
    assert bash(tmp_path, "npm --prefix D:/dev/game test 2>&1 | tail -12", "Run the game tests", True)
    assert bash(tmp_path, "python sim.py --games 450", "Run in the foreground") is None
    led = logged(col_data, "predictions")
    assert [(p["key"], p["low"], p["high"], p["source"], p["cwd"]) for p in led] == [
        ("t1", 48, 52, "command", str(tmp_path))]
    assert len(logged(col_data, "gate")) == 3


def test_a_step_that_cannot_be_taken_back_needs_a_prediction_even_in_the_foreground(col_data, tmp_path):
    for step in ("git push origin main", "git -C D:/repo push", "kaggle competitions submit -c arc -f sub.csv -m v2",
                 "npx gh-pages -d dist", "npm publish", "docker push me/app:1", "terraform apply -auto-approve"):
        assert "cannot be taken back" in bash(tmp_path, step, "Ship it"), step
    assert bash(tmp_path, "git push origin main", "Push. Prediction [push]: CI green, live version 60 (~2 min)") is None
    for harmless in ("git push --dry-run origin main", "git log --oneline gh-pages", "git status",
                     "npm publish --dry-run", "kubectl apply --dry-run=client -f x.yaml", "kaggle kernels list"):
        assert bash(tmp_path, harmless, "look") is None, harmless
    # a commit whose message mentions "git push" does not push; text is not a command
    message = "git commit -q -F - <<'MSG'\n- git push and kaggle kernels push now need a prediction\nMSG\ngit log -1"
    assert bash(tmp_path, message, "Commit") is None
    assert bash(tmp_path, 'git commit -m "note: git push later"', "Commit") is None
    assert "cannot be taken back" in bash(tmp_path, "git commit -m x && git push", "Commit and push")
    assert [g["kind"] for g in logged(col_data, "gate")] == ["final"] * 8


def test_the_ledger_compares_results_by_the_numbers_and_grounds_them(col_data, tmp_path):
    path = transcript(col_data.parent / "claude" / "projects", [
        user("run the tournament"),
        say("Prediction [t1]: win rate 48–52\nPrediction [t2]: takes at most 30 min\n"
            "Prediction [t3]: at most 3 errors"),
        call("Bash", command="python sim.py"),
        result("win rate 49.88 / 44 min"),
        say("Result [t1]: average 49.88\nResult [t2]: took 44 minutes\nResult [t3]: 2 errors\n"
            "**Result:** the tournament finished"),
    ])
    assert stop(path, tmp_path) is None
    assert stop(path, tmp_path) is None  # the same turn read again adds nothing
    led = logged(col_data, "predictions")
    assert sum(r["type"] == "prediction" for r in led) == 3
    assert [(r["key"], r["verdict"], r["grounded"], r.get("direction")) for r in led if r["type"] == "result"] == [
        ("t1", "held", True, None), ("t2", "missed", True, {"label": "time", "way": "high"}),
        ("t3", "held", False, None)]  # "2 errors" appears in no tool output


def test_a_quoted_marker_neither_opens_nor_closes_a_prediction(col_data, tmp_path):
    """What a real session wrote after the gate took its prediction; the quote once opened a second one."""
    assert bash(tmp_path, "python check.py", "run the check Prediction [check]: 41 passed (~1 sec)", True) is None
    projects = col_data.parent / "claude" / "projects"
    path = transcript(projects, [
        user("run the check"), call("Bash", command="python check.py"), result("41 passed"),
        say("I retried with the description `run the check Prediction [check]: 41 passed (~1 sec)`. This adds to the "
            "exact `run the check` text you asked for.\nI'll write `Result [check]: <observed>` when it is in."),
    ])
    stop(path, tmp_path)
    assert [(r["type"], r["key"]) for r in logged(col_data, "predictions")] == [("prediction", "check")]
    transcript(projects, [say("Prediction [check]: 41 passed\nResult [check]: 41 passed")], mode="a")
    stop(path, tmp_path)  # a message that names the open prediction restates it
    assert [(r["type"], r["key"], r.get("verdict")) for r in logged(col_data, "predictions")] == [
        ("prediction", "check", None), ("result", "check", "held")]


def test_a_hypothesis_that_fails_is_ruled_out(col_data, tmp_path):
    path = transcript(col_data.parent / "claude" / "projects", [
        user("why did the score drop"),
        say("Hypothesis [noise]: a rerun scores 46–50\nHypothesis [config]: the old config scores 46–50\n"
            "Hypothesis [code]: the old code scores 40–42"),
        call("Bash", command="python score.py"),
        result("score 41"),
        say("Result [noise]: 41\nResult [config]: 41\nResult [code]: 41"),
    ])
    stop(path, tmp_path)
    led = logged(col_data, "predictions")
    assert {r["kind"] for r in led} == {"hypothesis"}
    assert [(r["key"], r["verdict"]) for r in led if r["type"] == "result"] == [
        ("noise", "missed"), ("config", "missed"), ("code", "held")]


def _ago(hours):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_a_due_prediction_comes_back_once_at_the_next_prompt(col_data):
    col_data.mkdir(parents=True, exist_ok=True)
    rec = {"at": _ago(2), "type": "prediction", "session": SESSION, "key": "rl4", "text": "average 48–52",
           "low": 48, "high": 52, "due": _ago(1), "source": "command"}
    (col_data / "predictions.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
    out = hook("UserPromptSubmit", prompt="how is it going")["hookSpecificOutput"]
    assert out["hookEventName"] == "UserPromptSubmit" and "[rl4]" in out["additionalContext"]
    assert hook("UserPromptSubmit", prompt="and now?") is None  # once is enough
    assert hook("UserPromptSubmit", session_id="other", prompt="how is it going") is None  # not its business


def test_a_duration_sets_when_the_result_is_due():
    at = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
    assert predict._due("3 files change (~2 min)", at) == "2026-10-27T12:02:00Z"
    assert predict._due("ortalama 48–52 (~1,5 saat)", at) == "2026-10-27T13:30:00Z"
    assert predict._due("quality is good", at) is None


def test_a_new_session_hears_the_rules_and_this_folders_record(col_data, tmp_path, monkeypatch):
    here, there = tmp_path / "here", tmp_path / "there"
    text = hook("SessionStart", cwd=str(here))["hookSpecificOutput"]["additionalContext"]
    assert "Prediction [key]" in text and "a commit you name must exist" in text and "record" not in text
    col_data.mkdir(parents=True, exist_ok=True)
    rows = [{"at": _ago(1), "type": "result", "kind": "prediction", "cwd": str(here), "verdict": v,
             "details": [{"label": "time", "held": v == "held", **({} if v == "held" else {"direction": w})}]}
            for v, w in (("held", ""), ("held", ""), ("missed", "low"), ("missed", "low"), ("missed", "low"),
                         ("missed", "high"))]
    (col_data / "predictions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    text = hook("SessionStart", cwd=str(here))["hookSpecificOutput"]["additionalContext"]
    assert "2 of the last 6 compared predictions held" in text
    assert "3 below the range and 1 above" in text.replace("came in ", "")
    assert "3 of 6 took less time than predicted, 1 more" in text
    assert "record" not in hook("SessionStart", cwd=str(there))["hookSpecificOutput"]["additionalContext"]
    monkeypatch.setenv("COL_PREDICT", "off")
    assert "Prediction [key]" not in hook("SessionStart", cwd=str(here))["hookSpecificOutput"]["additionalContext"]
    monkeypatch.setenv("COL_CLAIMS", "off")
    assert hook("SessionStart", cwd=str(here)) is None
