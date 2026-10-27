"""COL's tests run against their own stores: a config dir with its own transcripts, and a data dir for the logs and
the ledger. Nothing reads or writes the real ~/.claude, and COL starts no model."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "col" / "scripts"))

from col import common  # noqa: E402


@pytest.fixture(autouse=True)
def col_data(tmp_path, monkeypatch):
    config = tmp_path / "claude"
    projects = config / "projects"
    (projects / "proj").mkdir(parents=True, exist_ok=True)
    data = tmp_path / "coldata"
    monkeypatch.setattr(common, "CONFIG", config)
    monkeypatch.setattr(common, "PROJECTS", projects)
    monkeypatch.setattr(common, "DATA", data)
    monkeypatch.setattr(common, "system_lang", lambda: "en")
    # git reads no user config either: a global ignore list or hook must not change what a test repository holds
    for name, value in (("CLAUDE_CONFIG_DIR", config), ("COL_TRANSCRIPTS", projects), ("COL_DATA", data),
                        ("COL_LANG", "en"), ("PYTHONIOENCODING", "utf-8"),
                        ("GIT_CONFIG_GLOBAL", tmp_path / "gitconfig")):
        monkeypatch.setenv(name, str(value))
    for name in ("COL_CLAIMS", "COL_PREDICT", "COL_SECRETS", "COL_REPOS", "COL_INQUIRY"):
        monkeypatch.delenv(name, raising=False)
    return data


@pytest.fixture
def repo(tmp_path):
    """A repository with one commit: (folder, short id, a git runner)."""
    r = tmp_path / "repo"
    r.mkdir()

    def git(*args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=r, check=True,
                              capture_output=True, text=True).stdout.strip()

    git("init", "-q")
    git("commit", "-q", "--allow-empty", "-m", "first")
    return r, git("rev-parse", "--short=7", "HEAD"), git
