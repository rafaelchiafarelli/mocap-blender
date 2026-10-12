"""Print world head and tail of the armature's bones on every frame, as JSON (for tests)."""

import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
import bootstrap  # noqa: E402

names = bootstrap.args()
import bpy  # noqa: E402

scene = bpy.context.scene
[rig] = [o for o in bpy.data.objects if o.type == "ARMATURE"]
samples = {n: {"head": [], "tail": []} for n in names}
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    for n in names:
        pb = rig.pose.bones[n]
        samples[n]["head"].append(list(rig.matrix_world @ pb.head))
        samples[n]["tail"].append(list(rig.matrix_world @ pb.tail))
bootstrap.result("samples", json.dumps(samples))
