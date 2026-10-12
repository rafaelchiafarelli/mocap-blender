"""A placeholder character: an MPFB human skinned to a Rigify human metarig, from a character JSON.

The JSON (film material, in the film root) holds `name`, the MPFB macro values in 0..1 (`gender`,
`age`, `muscle`, `weight`, `height`, `proportions`, and `race` with `african`, `asian`, `caucasian`)
and `skin_rgb` (linear, 0..1). Every key is required, so nothing about the character is decided here.
"""

from __future__ import annotations

import json
from pathlib import Path

from mocap_blender import blender

MACROS = ("gender", "age", "muscle", "weight", "height", "proportions")
RACES = ("african", "asian", "caucasian")


class CharacterError(ValueError):
    """A character JSON that can't be used."""


def read_character(path: Path | str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = {"name", "race", "skin_rgb", *MACROS}
    if set(data) != expected:
        raise CharacterError(f"{path}: keys must be exactly {sorted(expected)}, got {sorted(data)}")
    for key in MACROS:
        _unit(path, key, data[key])
    if not isinstance(data["race"], dict) or set(data["race"]) != set(RACES):
        raise CharacterError(f"{path}: race must have exactly {list(RACES)}")
    for key in RACES:
        _unit(path, f"race.{key}", data["race"][key])
    if not (isinstance(data["skin_rgb"], list) and len(data["skin_rgb"]) == 3):
        raise CharacterError(f"{path}: skin_rgb must be [r, g, b]")
    for i, v in enumerate(data["skin_rgb"]):
        _unit(path, f"skin_rgb[{i}]", v)
    if not isinstance(data["name"], str) or not data["name"]:
        raise CharacterError(f"{path}: name must be a non-empty string")
    return data


def make_character(character_json: Path | str, out_blend: Path | str) -> dict[str, str]:
    read_character(character_json)
    out = blender.run("character", blender.windows_path(character_json), blender.windows_path(out_blend))
    return blender.results(out)


def _unit(path, key: str, value) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise CharacterError(f"{path}: {key} must be a number in 0..1, got {value!r}")
