"""The bench's graders, with no model: each task fails as given, the fix the user asks for fails again the same way,
the real fix solves it, and a symptom patch is caught."""
import subprocess
import sys

from conftest import ROOT


def test_the_graders_tell_the_real_fix_from_a_symptom_patch():
    r = subprocess.run([sys.executable, str(ROOT / "bench" / "run.py"), "--selftest"], capture_output=True, text=True,
                       timeout=600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "tasks: each fails as given" in r.stdout
