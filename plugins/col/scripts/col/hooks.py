"""COL's four hooks: what it does when a session starts, when the user writes, before a shell command and when the
assistant stops."""
from __future__ import annotations

import re

from col import claims, common, keyscan, outcome, predict
from col.text import t


def _deny(reason: str) -> None:
    common.emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                        "permissionDecisionReason": reason}})


def session_start(data: dict) -> None:
    """The rules, so the model can meet them before a block teaches them, and this folder's track record."""
    common.prune_state()
    sid, cwd = data.get("session_id", ""), data.get("cwd", "")
    lang = common.lang(stored=common.load_state(sid).get("lang", ""))
    lines = []
    if common.setting("predict") != "off":
        lines.append(t(lang, "rule_predict"))
        lines.append(predict.calibration(cwd, lang))
    if common.setting("claims") == "on":
        lines.append(t(lang, "rule_claims"))
    text = "\n".join(x for x in lines if x)
    if text:
        common.emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}})


def prompt(data: dict) -> None:
    """The language the user writes in, for the blocks of this session; and the predictions whose result is due."""
    sid = data.get("session_id", "")
    if not sid:
        return
    state = common.load_state(sid)
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", str(data.get("prompt", "")), flags=re.S).strip()
    if text and not text.startswith(common.INJECTED):
        state["lang"] = common.lang(text, state.get("lang", ""))
    due = predict.reminder(sid, state, state.get("lang") or common.lang()) if common.setting("predict") != "off" else ""
    common.save_state(sid, state)
    if due:
        common.emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": due}})


def pre_tool(data: dict) -> None:
    """A commit or a push that would carry a key is refused; so is a long job or an irreversible step that starts
    without a measurable prediction."""
    tool, inp = data.get("tool_name", ""), data.get("tool_input") or {}
    if tool not in ("Bash", "PowerShell") or not isinstance(inp, dict):
        return
    sid, cwd = data.get("session_id", ""), data.get("cwd", "")
    lang = common.lang(stored=common.load_state(sid).get("lang", ""))
    if common.setting("secrets") != "off":
        try:
            reason = keyscan.gate(sid, tool, inp, cwd, lang)
        except Exception as e:  # a broken scan must not stop the user's work
            common.log_error(e)
            reason = None
        if reason:
            _deny(reason)
            return
    if common.setting("predict") != "off":
        reason = predict.gate(sid, cwd, tool, inp, lang)
        if reason:
            _deny(reason)


def stop(data: dict) -> None:
    """The turn's predictions and results go to the ledger; the final message's claims are checked, and a false one
    blocks the stop, at most twice a turn. A block is labelled right or wrong at the next stop, from the answer."""
    sid, cwd = data.get("session_id", ""), data.get("cwd", "")
    path = common.resolve(data.get("transcript_path", ""), sid)
    if not path:
        return
    turn = common.turn(path)
    if not turn["final"]:
        return
    state = common.load_state(sid)
    lang = common.lang(turn["user"], state.get("lang", ""))
    pending = state.pop("pending", None)
    if pending:  # the previous block, judged by what the assistant said in answer to it
        label, cue = outcome.label(turn["after_hook"] if state.get("turn") == turn["user_at"] else [])
        common.log("outcomes", {"session": sid, **pending, "label": label, "cue": cue[:120]})
    if state.get("turn") != turn["user_at"]:
        state.update({"turn": turn["user_at"], "blocks": 0})
    cache = {}

    def results() -> str:  # read once, and only when a claim or a result needs it
        if "text" not in cache:
            cache["text"] = common.results_text(path)
        return cache["text"]

    try:
        predict.update(sid, cwd, turn["said"], results, lang)
    except Exception as e:  # the ledger failing must not trap the session
        common.log_error(e)
    mode = common.setting("claims")
    problems = claims.check(turn["final"], turn, results, cwd, str(path.parent / "memory")) if mode != "off" else []
    block = bool(problems) and mode == "on" and state.get("blocks", 0) < 2
    if mode != "off":
        common.log("checks", {"session": sid, "calls": len(turn["calls"]), "problems": problems, "blocked": block})
    if block:
        state["blocks"] = state.get("blocks", 0) + 1
        state["pending"] = {"kind": problems[0]["kind"], "blocked_at": common.now(), "what": problems[0]["what"][:160]}
    common.save_state(sid, state)
    if block:
        found = ("- " + t(lang, p["kind"], what=p["what"], n=p.get("n", "")) for p in problems)
        lines = [t(lang, "claims_head"), *found, t(lang, "claims_tail")]
        common.emit({"decision": "block", "reason": "\n".join(lines)})


HANDLERS = {"SessionStart": session_start, "UserPromptSubmit": prompt, "PreToolUse": pre_tool, "Stop": stop}


def run() -> int:
    """Entry point of every COL hook. It never fails the session: an error goes to errors.log and the hook exits 0."""
    try:
        data = common.read_input()
        handler = HANDLERS.get(str(data.get("hook_event_name", "")))
        if handler:
            handler(data)
    except Exception as e:
        common.log_error(e)
    return 0
