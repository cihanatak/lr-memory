"""The package as Claude Code loads it: the manifests, the hooks, the skill, and nothing personal inside."""
import json
import re
import struct

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


def test_each_skill_names_itself_and_its_launcher():
    for name, command in (("recall", "search"), ("sleep", "sleep")):
        text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---")[1]
        assert re.search(rf"^name: {name}$", front, re.M)
        description = re.search(r"^description: (.+)$", front, re.M).group(1)
        assert 200 < len(description) <= 1024
        assert f'sh "${{CLAUDE_PLUGIN_ROOT}}/scripts/run.sh" {command}' in text
    # a pass costs model tokens, so only the user starts it
    assert re.search(r"^disable-model-invocation: true$", (PLUGIN / "skills" / "sleep" / "SKILL.md").read_text(
        encoding="utf-8").split("---")[1], re.M)


def test_nothing_personal_ships():
    """The package was cut out of a personal setup: no path, user name, port or session of it may remain."""
    # the time zone note is matched as written: blind to case it would find "tsi" in "outside"
    banned = re.compile(r"F:[\\/]|ClaudeWorkspace|atakc|\.living-runtime|\b8766\b|(?-i:\bTSİ\b)|e7528c41", re.I)
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.name == "test_package.py" or {".git", "__pycache__", ".pytest_cache"} & set(p.parts):
            continue
        if p.suffix in {".png", ".jpg"}:  # image bytes are not text: three random ones can spell "F:/"
            continue
        assert not banned.search(p.read_text(encoding="utf-8", errors="replace")), p


def test_each_plugin_has_an_icon_the_catalog_takes():
    """The plugin directory takes a square PNG of 512 to 2048 px under 2 MB."""
    for plugin in (ROOT / "plugins").iterdir():
        data = (plugin / ".claude-plugin" / "icon.png").read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", plugin.name
        width, height = struct.unpack(">II", data[16:24])  # the IHDR chunk comes first
        assert width == height and 512 <= width <= 2048 and len(data) < 2 * 1024 * 1024, plugin.name
