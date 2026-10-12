"""Run the pinned Windows Blender headless from WSL.

Blender is `MOCAP_BLENDER` or the pinned portable 5.2.2 (`mocap-studio/DEPENDENCIES.md`). It runs in
portable mode, so its add-ons (MPFB) live next to it. Paths handed to it are Windows paths
(`wslpath -w`); a path Windows can't open whole (260 characters and more) is refused here, because
Python inside Blender would otherwise just report the file as missing.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

PINNED = Path("/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/blender.exe")
MAX_PATH = 259
INBLENDER = Path(__file__).parent / "inblender"


class BlenderError(RuntimeError):
    """Blender is missing, or a script run in it failed."""


def executable() -> Path:
    exe = Path(os.environ.get("MOCAP_BLENDER", PINNED))
    if not exe.is_file():
        raise BlenderError(f"Blender not found at {exe} (set MOCAP_BLENDER)")
    return exe


def windows_path(path: Path | str) -> str:
    path = Path(path).absolute()
    existing, rest = path, []
    while not existing.exists():  # wslpath only converts paths that exist; outputs often don't yet
        existing, rest = existing.parent, [existing.name, *rest]
    out = subprocess.run(["wslpath", "-w", str(existing)], capture_output=True, text=True, check=True).stdout.strip()
    out = "\\".join([out.rstrip("\\"), *rest]) if rest else out
    if len(out) > MAX_PATH:
        raise BlenderError(f"{out} is {len(out)} characters; Windows needs under {MAX_PATH + 1}: use a shorter path")
    return out


def run(script: str, *args: str, blend: Path | None = None, timeout: float = 3600) -> str:
    """Run `inblender/<script>.py -- args` (args already converted) and return Blender's output."""
    cmd = [str(executable()), "-b"]
    if blend is not None:
        cmd.append(windows_path(blend))
    cmd += ["--python-exit-code", "1", "--python", windows_path(INBLENDER / f"{script}.py"), "--", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout,
                          cwd=executable().parent)
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-40:])
        raise BlenderError(f"{script} failed in Blender (exit {proc.returncode}):\n{tail}")
    return proc.stdout


def results(output: str) -> dict[str, str]:
    """The `RESULT key=value` lines an inblender script printed."""
    found = {}
    for line in output.splitlines():
        if line.startswith("RESULT "):
            key, _, value = line[len("RESULT "):].partition("=")
            found[key] = value
    return found
