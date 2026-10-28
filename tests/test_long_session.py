"""The long-session bench's graders, with no model: the job as given fails, a session done right passes all 16 checks,
and each faulty variant fails exactly its own check."""
import subprocess
import sys

from conftest import ROOT


def test_each_long_session_check_catches_its_own_fault():
    r = subprocess.run([sys.executable, str(ROOT / "bench" / "long_session" / "run.py"), "--selftest"],
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "graders: each check passes" in r.stdout
