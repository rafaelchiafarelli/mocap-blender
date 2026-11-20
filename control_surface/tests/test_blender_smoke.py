"""Runs blender_smoke.py in the pinned Blender (mocap-studio/DEPENDENCIES.md).

Skipped when that Blender is not reachable (e.g. not on WSL with G: mounted).
Override with CONTROL_SURFACE_BLENDER=<path to blender(.exe)>.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

DEFAULT = "/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/blender.exe"
BLENDER = os.environ.get("CONTROL_SURFACE_BLENDER", DEFAULT)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def _win(path):
    """Path as the Windows Blender sees it (via wslpath when under WSL)."""
    if BLENDER.endswith(".exe") and shutil.which("wslpath"):
        return subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()
    return str(path)


@pytest.mark.skipif(not Path(BLENDER).exists(), reason="pinned Blender not found")
def test_addon_in_blender():
    r = subprocess.run(
        [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1",
         "--python", _win(HERE / "blender_smoke.py"), "--", _win(ROOT)],
        capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0 and "SMOKE OK" in r.stdout, r.stdout[-3000:] + r.stderr[-3000:]
