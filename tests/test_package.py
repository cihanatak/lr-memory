"""The package as Claude Code loads it: the manifests, the hooks, the skill, and nothing personal inside."""
import json
import re

from conftest import PLUGIN, ROOT
from lr_memory import __version__


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_manifests_agree():
    plugin = _json(PLUGIN / ".claude-plugin" / "plugin.json")
    market = _json(ROOT / ".claude-plugin" / "marketplace.json")
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", plugin["name"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"]) and plugin["version"] == __version__
    entry = next(p for p in market["plugins"] if p["name"] == plugin["name"])
    assert (ROOT / entry["source"]).resolve() == PLUGIN.resolve()


def test_every_hook_runs_the_launcher():
    hooks = _json(PLUGIN / "hooks" / "hooks.json")["hooks"]
    assert set(hooks) == {"PreCompact", "PostCompact", "SessionStart"}
    for groups in hooks.values():
        for group in groups:
            for h in group["hooks"]:
                assert h["type"] == "command" and h["command"] == 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" hook'
    assert b"\r" not in (PLUGIN / "scripts" / "run.sh").read_bytes()  # sh stops at a CRLF line end


def test_the_skill_names_itself_and_its_launcher():
    text = (PLUGIN / "skills" / "recall" / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---")[1]
    assert re.search(r"^name: recall$", front, re.M)
    description = re.search(r"^description: (.+)$", front, re.M).group(1)
    assert 200 < len(description) <= 1024
    assert 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" search' in text


def test_nothing_personal_ships():
    """The package was cut out of a personal setup: no path, user name, port or session of it may remain."""
    banned = re.compile(r"F:[\\/]|ClaudeWorkspace|atakc|\.living-runtime|\b8766\b|TSİ|e7528c41", re.I)
    for p in ROOT.rglob("*"):
        if p.is_file() and p.name != "test_package.py" and not {".git", "__pycache__", ".pytest_cache"} & set(p.parts):
            assert not banned.search(p.read_text(encoding="utf-8", errors="replace")), p
