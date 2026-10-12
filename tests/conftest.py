import json
import os
import tarfile
from pathlib import Path

import pytest

from mocap_blender import blender

FIXTURES = Path(os.environ.get("MOCAP_FIXTURES", "/mnt/g/mocap-studio-downloads/fixtures"))
FREEMOCAP_OUTPUT = FIXTURES / "freemocap-test-output-60f" / "freemocap-test-output-60f.tar.gz"
FRAMES = 60


@pytest.fixture
def take_dir(tmp_path: Path) -> Path:
    """A take with `extract/freemocap/` from the 60-frame FreeMoCap fixture (short names: Windows path limit)."""
    if not FREEMOCAP_OUTPUT.is_file():
        pytest.fail(f"{FREEMOCAP_OUTPUT} not found (see its README in mocap-studio-downloads/fixtures)")
    take = tmp_path / "s" / "takes" / "t"
    (take / "extract").mkdir(parents=True)
    with tarfile.open(FREEMOCAP_OUTPUT) as tar:
        tar.extractall(take / "extract", filter="data")
    return take


def inspect(blend: Path) -> dict:
    return json.loads(blender.results(blender.run("inspect_blend", blend=blend))["summary"])
