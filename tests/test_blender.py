import pytest

from mocap_blender.blender import BlenderError, results, run, windows_path


def test_pinned_blender_with_mpfb():
    found = results(run("info"))
    assert found["blender"].startswith("5.2.2")
    assert found["python"].startswith("3.13.")
    assert found["mpfb"] == "True"


def test_windows_paths(tmp_path):
    assert windows_path(tmp_path).startswith("\\\\wsl")
    with pytest.raises(BlenderError, match="use a shorter path"):
        windows_path(tmp_path.joinpath(*["deep-folder-name"] * 20))


def test_failures_are_reported():
    with pytest.raises(BlenderError, match="failed in Blender"):
        run("no_such_script")
