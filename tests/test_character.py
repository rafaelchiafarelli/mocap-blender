import json
from pathlib import Path

import pytest
from conftest import inspect

from mocap_blender.character import CharacterError, make_character, read_character

CHARACTER = Path(__file__).parent / "data" / "character.json"


def test_character_with_metarig(tmp_path):
    out = tmp_path / "character.blend"
    found = make_character(CHARACTER, out)

    asked = json.loads(CHARACTER.read_text())
    for key in ("gender", "age", "muscle", "weight", "height", "proportions"):
        assert float(found[f"macro.{key}"]) == pytest.approx(asked[key], abs=1e-3)
    assert found["facing"] == "-Y"
    assert found["unweighted"] == "0"  # every body vertex follows a metarig bone
    assert 1.5 < float(found["height_m"]) < 2.0
    bones = inspect(out)["armatures"][found["rig"]]
    for name in ("upper_arm.L", "hand.R", "spine.006", "thigh.L", "f_index.01.L"):
        assert name in bones


@pytest.mark.parametrize("change, message", [
    (dict(age=1.5), "age must be a number in 0..1"),
    (dict(race={"asian": 1.0}), "race must have exactly"),
    (dict(hair="grey"), "keys must be exactly"),
])
def test_invalid_character(tmp_path, change, message):
    data = {**json.loads(CHARACTER.read_text()), **change}
    path = tmp_path / "c.json"
    path.write_text(json.dumps(data))
    with pytest.raises(CharacterError, match=message):
        read_character(path)
