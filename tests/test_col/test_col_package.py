"""COL as Claude Code loads it: the manifests, the hooks and the skill."""
import json
import re

from col import __version__
from .colkit import COL, ROOT


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_manifests_agree():
    plugin = _json(COL / ".claude-plugin" / "plugin.json")
    market = _json(ROOT / ".claude-plugin" / "marketplace.json")
    assert plugin["name"] == "col" and plugin["version"] == __version__
    entry = next(p for p in market["plugins"] if p["name"] == "col")
    assert (ROOT / entry["source"]).resolve() == COL.resolve()
    assert len({p["name"] for p in market["plugins"]}) == len(market["plugins"])


def test_every_hook_runs_the_launcher():
    hooks = _json(COL / "hooks" / "hooks.json")["hooks"]
    assert set(hooks) == {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop"}
    for groups in hooks.values():
        for group in groups:
            for h in group["hooks"]:
                assert h["type"] == "command" and h["command"] == 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" hook'
    assert [g.get("matcher") for g in hooks["PreToolUse"]] == ["Bash|PowerShell"]
    assert [g.get("matcher") for g in hooks["PostToolUseFailure"]] == ["Bash|PowerShell"]
    # the reflex counts edits, so every tool that edits a file reaches it
    assert set(hooks["PostToolUse"][0]["matcher"].split("|")) == {"Bash", "PowerShell", "Edit", "Write", "MultiEdit",
                                                                  "NotebookEdit"}
    assert b"\r" not in (COL / "scripts" / "run.sh").read_bytes()  # sh stops at a CRLF line end


def test_the_report_skill_names_itself_and_its_launcher():
    text = (COL / "skills" / "report" / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---")[1]
    assert re.search(r"^name: report$", front, re.M)
    description = re.search(r"^description: (.+)$", front, re.M).group(1)
    assert 200 < len(description) <= 1024
    assert 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" report' in text
