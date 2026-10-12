"""A take's performance on a character: `<take>/blender/performance.blend` (and `retarget.json`)."""

from __future__ import annotations

import json
from pathlib import Path

from mocap_blender import blender, takes

TAKE_FPS = 30  # mocap-extract resamples every camera to 30 fps


def retarget_take(take_dir: Path | str, character_blend: Path | str) -> dict:
    take_dir = Path(take_dir)
    recording = takes.freemocap_dir(take_dir)
    out_dir = takes.blender_dir(take_dir)
    out, report = out_dir / "performance.blend", out_dir / "retarget.json"
    blender.run("retarget_take", blender.windows_path(recording), blender.windows_path(out),
                blender.windows_path(report), str(TAKE_FPS), blend=Path(character_blend))
    return json.loads(report.read_text(encoding="utf-8"))
