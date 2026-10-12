"""The FreeMoCap add-on's own scene of a take (`<take>/blender/freemocap.blend`), to check the capture by eye.

The add-on runs from its pinned release zip (unpacked next to it once), through its own entry point
`ajc27_run_as_main_function`; it isn't installed into Blender. It sets the scene to 24 fps, so the
frame rate is set back to the take's afterwards.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

from mocap_blender import blender, takes

PINNED_ADDON = Path("/mnt/g/mocap-studio-downloads/apps/freemocap-blender-addon/v2026.04.1041/"
                    "freemocap_blender_addon_2026.04.1041.zip")
TAKE_FPS = 30  # mocap-extract resamples every camera to 30 fps (alignment, resample.TARGET_FPS)


def addon_dir() -> Path:
    zip_path = Path(os.environ.get("MOCAP_FREEMOCAP_ADDON", PINNED_ADDON))
    if not zip_path.is_file():
        raise blender.BlenderError(f"FreeMoCap add-on not found at {zip_path} (set MOCAP_FREEMOCAP_ADDON)")
    unpacked = zip_path.parent / "unpacked"
    if not (unpacked / "ajc27_freemocap_blender_addon" / "main.py").is_file():
        zipfile.ZipFile(zip_path).extractall(unpacked)
    return unpacked


def reference_scene(take_dir: Path | str) -> Path:
    take_dir = Path(take_dir)
    recording = takes.freemocap_dir(take_dir)
    out = takes.blender_dir(take_dir) / "freemocap.blend"
    blender.run("freemocap_reference", blender.windows_path(addon_dir()), blender.windows_path(recording),
                blender.windows_path(out), str(TAKE_FPS))
    return out
