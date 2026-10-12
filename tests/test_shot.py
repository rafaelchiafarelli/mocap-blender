import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mocap_blender.character import make_character
from mocap_blender.performance import retarget_take
from mocap_blender.shot import ShotError, read_recipe, render_shot

DATA = Path(__file__).parent / "data"


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return {s["codec_type"]: s for s in json.loads(out)["streams"]}


@pytest.fixture
def recipe(tmp_path: Path) -> Path:
    shutil.copy(DATA / "shot.json", tmp_path / "shot.json")
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    str(tmp_path / "tone.wav")], check=True)
    return tmp_path / "shot.json"


def test_shot_renders_frames_and_voice(take_dir, tmp_path, recipe):
    character = tmp_path / "character.blend"
    make_character(DATA / "character.json", character)
    retarget_take(take_dir, character)

    mp4 = render_shot(take_dir, recipe)

    assert mp4 == tmp_path / "out" / "shot.mp4"
    streams = probe(mp4)
    assert int(streams["video"]["nb_read_frames"]) == 10
    assert (streams["video"]["width"], streams["video"]["height"]) == (320, 180)
    assert "audio" in streams
    assert (take_dir / "blender" / "shot.blend").is_file()


def test_recipe_keys_are_all_required(tmp_path, recipe):
    data = json.loads(recipe.read_text())
    del data["world"]
    recipe.write_text(json.dumps(data))
    with pytest.raises(ShotError, match="keys must be exactly"):
        read_recipe(recipe)


def test_missing_audio_is_refused(tmp_path, recipe):
    (tmp_path / "tone.wav").unlink()
    with pytest.raises(ShotError, match="audio .* not found"):
        read_recipe(recipe)
