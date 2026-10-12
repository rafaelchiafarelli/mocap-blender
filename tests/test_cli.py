import json
import shutil
from pathlib import Path

from mocap_blender.cli import main

DATA = Path(__file__).parent / "data"


def test_character_command(tmp_path, capsys):
    out = tmp_path / "c.blend"
    assert main(["character", str(DATA / "character.json"), str(out)]) == 0
    assert out.is_file() and "rig test_person.metarig" in capsys.readouterr().out


def test_bad_recipe_exits_1(take_dir, tmp_path, capsys):
    recipe = json.loads((DATA / "shot.json").read_text())
    recipe["objects"][0]["shape"] = "teapot"
    path = tmp_path / "shot.json"
    path.write_text(json.dumps(recipe))
    shutil.copy(DATA / "shot.json", tmp_path / "unused.json")
    assert main(["shot", str(take_dir), str(path)]) == 1
    assert "shape must be one of" in capsys.readouterr().err
