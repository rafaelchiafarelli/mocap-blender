"""A shot: the take's performance plus a blockout set, camera, lights and voice, rendered with EEVEE to MP4.

The recipe is a JSON file (film material, in the film root); its relative paths are relative to it.
Keys: `resolution` [w, h]; `frames` [first, last] (take frames, from 1) or null for the whole take;
`camera` {location, look_at, lens_mm}; `lights` [{type (SUN, AREA, POINT, SPOT), location, look_at,
energy, rgb, size}]; `world` {rgb, strength}; `objects` [{name, shape (cube, cylinder, sphere, plane,
torus), size [x, y, z] in m, location, rotation_deg, rgb, and optionally parent_bone to follow a
character bone, its location then relative to that bone}]; `audio` {path, offset_s} or null; `output`
(an .mp4 path). Every key is required: nothing about the shot is decided here.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from mocap_blender import blender, takes

KEYS = {"resolution", "frames", "camera", "lights", "world", "objects", "audio", "output"}
SHAPES = {"cube", "cylinder", "sphere", "plane", "torus"}
LIGHTS = {"SUN", "AREA", "POINT", "SPOT"}


class ShotError(ValueError):
    """A recipe that can't be used."""


def read_recipe(path: Path | str) -> dict:
    path = Path(path)
    recipe = json.loads(path.read_text(encoding="utf-8"))
    if set(recipe) != KEYS:
        raise ShotError(f"{path}: keys must be exactly {sorted(KEYS)}, got {sorted(recipe)}")
    for obj in recipe["objects"]:
        if obj.get("shape") not in SHAPES:
            raise ShotError(f"{path}: object {obj.get('name')!r}: shape must be one of {sorted(SHAPES)}")
    for light in recipe["lights"]:
        if light.get("type") not in LIGHTS:
            raise ShotError(f"{path}: light type must be one of {sorted(LIGHTS)}")
    if not str(recipe["output"]).endswith(".mp4"):
        raise ShotError(f"{path}: output must be an .mp4")
    base = path.parent
    recipe["output"] = str((base / recipe["output"]).resolve())
    if recipe["audio"] is not None:
        audio = (base / recipe["audio"]["path"]).resolve()
        if not audio.is_file():
            raise ShotError(f"{path}: audio {audio} not found")
        recipe["audio"]["path"] = str(audio)
    return recipe


def render_shot(take_dir: Path | str, recipe_path: Path | str) -> Path:
    """Render the recipe on `<take>/blender/performance.blend`; save `<take>/blender/shot.blend`; return the mp4."""
    take_dir = Path(take_dir)
    recipe = read_recipe(recipe_path)
    performance = takes.blender_dir(take_dir) / "performance.blend"
    if not performance.is_file():
        raise ShotError(f"{performance} not found: retarget the take first")
    output = Path(recipe["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    recipe["output"] = blender.windows_path(output)
    if recipe["audio"] is not None:
        recipe["audio"]["path"] = blender.windows_path(recipe["audio"]["path"])
    with tempfile.TemporaryDirectory(dir=takes.blender_dir(take_dir)) as tmp:
        resolved = Path(tmp) / "recipe.json"
        resolved.write_text(json.dumps(recipe), encoding="utf-8")
        blender.run("shot", blender.windows_path(resolved), blender.windows_path(takes.blender_dir(take_dir) / "shot.blend"),
                    blend=performance)
    return output
