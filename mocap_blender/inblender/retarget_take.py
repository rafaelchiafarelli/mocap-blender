"""Opened on character.blend. Args: FreeMoCap recording folder, output .blend, report .json, fps."""

import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, __import__("os").path.dirname(__file__))
import bootstrap  # noqa: E402

recording, out, report_path, fps = bootstrap.args()
import bpy  # noqa: E402
import numpy as np  # noqa: E402

from mocap_blender import retarget  # noqa: E402

data = Path(recording) / "output_data"
body = np.load(data / "mediapipe_body_3d_xyz.npy")
left = np.load(data / "mediapipe_left_hand_3d_xyz.npy")
right = np.load(data / "mediapipe_right_hand_3d_xyz.npy")
[toml_path] = list(Path(recording).glob("*_camera_calibration.toml"))
ground_plane = bool(tomllib.loads(toml_path.read_text()).get("metadata", {}).get("groundplane_calibration", False))
source = retarget.normalise(body, left, right, ground_plane=ground_plane)
frames = body.shape[0]

[rig] = [o for o in bpy.data.objects if o.type == "ARMATURE"]
bones = sorted(rig.data.bones, key=lambda b: len(b.parent_recursive))
rest = [retarget.RestBone(b.name, b.parent.name if b.parent else None, np.array(b.matrix_local), np.array(b.tail_local))
        for b in bones]
basis, scale = retarget.solve(rest, source.joints, frames)

scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = int(fps), 1.0
scene.frame_start, scene.frame_end = 1, frames
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions.new(f"{rig.name}.take")
for name, matrices in basis.items():
    pb = rig.pose.bones[name]
    pb.rotation_mode = "QUATERNION"
    quats = retarget.quaternions(matrices[:, :3, :3])
    for f in range(frames):
        pb.rotation_quaternion = quats[f]
        pb.keyframe_insert("rotation_quaternion", frame=f + 1)
        if name == retarget.ROOT:
            pb.location = matrices[f, :3, 3]
            pb.keyframe_insert("location", frame=f + 1)

Path(report_path).write_text(json.dumps({
    "frames": frames, "fps": int(fps), "scale": scale, "ground_plane": ground_plane,
    "filled_samples": source.filled, "bones": sorted(basis),
}, indent=2), encoding="utf-8")
bpy.ops.wm.save_mainfile(filepath=out)
bootstrap.result("frames", frames)
bootstrap.result("scale", round(scale, 4))
