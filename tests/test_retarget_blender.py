from pathlib import Path

import json
import numpy as np
from conftest import FRAMES

from mocap_blender import blender
from mocap_blender.character import make_character
from mocap_blender.performance import retarget_take
from mocap_blender.retarget import normalise

CHARACTER = Path(__file__).parent / "data" / "character.json"
LIMBS = {"upper_arm.L": ("sho.L", "elb.L"), "forearm.R": ("elb.R", "wri.R"),
         "thigh.L": ("hip.L", "knee.L"), "shin.R": ("knee.R", "ank.R")}


def test_limbs_follow_the_actor(take_dir, tmp_path):
    character = tmp_path / "character.blend"
    make_character(CHARACTER, character)

    report = retarget_take(take_dir, character)

    assert report["frames"] == FRAMES and report["fps"] == 30
    blend = take_dir / "blender" / "performance.blend"
    samples = json.loads(blender.results(blender.run("sample_bones", *LIMBS, blend=blend))["samples"])
    data = take_dir / "extract" / "freemocap" / "output_data"
    actor = normalise(np.load(data / "mediapipe_body_3d_xyz.npy"), np.load(data / "mediapipe_left_hand_3d_xyz.npy"),
                      np.load(data / "mediapipe_right_hand_3d_xyz.npy"), ground_plane=False).joints
    for bone, (a, b) in LIMBS.items():
        character_dir = np.array(samples[bone]["tail"]) - np.array(samples[bone]["head"])
        actor_dir = actor[b] - actor[a]
        cos = np.sum(character_dir * actor_dir, axis=1) / (
            np.linalg.norm(character_dir, axis=1) * np.linalg.norm(actor_dir, axis=1))
        assert np.median(cos) > 0.99, bone  # same direction, whatever the proportions
