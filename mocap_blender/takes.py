"""Where a take's files are, for the MVP path (the session layout of `mocap-contracts`, read by path only)."""

from __future__ import annotations

from pathlib import Path

from mocap_blender.blender import BlenderError, windows_path


def freemocap_dir(take_dir: Path) -> Path:
    """`extract/freemocap/`, the FreeMoCap recording folder `mocap-extract body` writes."""
    path = Path(take_dir) / "extract" / "freemocap"
    if not (path / "output_data" / "mediapipe_body_3d_xyz.npy").is_file():
        raise BlenderError(f"{path} has no FreeMoCap 3D: run mocap-extract body first")
    longest = max((p for p in path.rglob("*") if p.is_file()), key=lambda p: len(str(p)))
    windows_path(longest)  # refuses paths Windows can't open
    return path


def blender_dir(take_dir: Path) -> Path:
    path = Path(take_dir) / "blender"
    path.mkdir(parents=True, exist_ok=True)
    return path
