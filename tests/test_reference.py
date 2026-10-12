from conftest import FRAMES, inspect

from mocap_blender.reference import reference_scene


def test_reference_scene(take_dir):
    blend = reference_scene(take_dir)

    assert blend == take_dir / "blender" / "freemocap.blend"
    summary = inspect(blend)
    assert "hand.L" in summary["armatures"]["freemocap_rig"]
    assert summary["fps"] == 30
    assert summary["frame_end"] - summary["frame_start"] + 1 >= FRAMES
