"""Every test runs against its own temporary stores: a config dir with its own transcripts and memory files, and a
data dir for the index and the trails. Nothing reads or writes the real ~/.claude, nothing starts claude, and no
test leaves a background process behind."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "lr-memory"
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lr_memory import common  # noqa: E402

SID = "aaaa1111-2222-3333-4444-555566667777"


@pytest.fixture(autouse=True)
def stores(tmp_path, monkeypatch):
    config = tmp_path / "claude"
    projects = config / "projects"
    (projects / "proj").mkdir(parents=True)
    monkeypatch.setattr(common, "CONFIG", config)
    monkeypatch.setattr(common, "PROJECTS", projects)
    monkeypatch.setattr(common, "DATA", tmp_path / "data")
    for name, value in (("CLAUDE_CONFIG_DIR", config), ("LR_MEMORY_DATA", tmp_path / "data"),
                        ("LR_MEMORY_NO_SPAWN", "1"), ("PYTHONIOENCODING", "utf-8")):
        monkeypatch.setenv(name, str(value))
    for name in ("LR_MEMORY_TRANSCRIPTS", "LR_MEMORY_LANG", "CLAUDE_CODE_SESSION_ID", "LR_MEMORY_CLAUDE",
                 "LR_MEMORY_SLEEP", "LR_MEMORY_SLEEP_MODEL", "CLAUDE_CODE_DISABLE_AUTO_MEMORY"):
        monkeypatch.delenv(name, raising=False)
    return projects


@pytest.fixture
def transcript(stores):
    return stores / "proj" / f"{SID}.jsonl"


def row(kind, content, at="2026-10-25T10:00", **extra):
    r = {"type": kind, "timestamp": f"{at}:00.000Z", "message": {"role": kind, "content": content}}
    r.update(extra)
    return r


def write(path, rows, mode="w", tail=""):
    with open(path, mode, encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        f.write(tail)
