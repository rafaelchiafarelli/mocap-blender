"""Print a JSON summary of the open .blend (objects, armatures and bones, frame range, fps), for tests."""

import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
import bootstrap  # noqa: E402

bootstrap.args()
import bpy  # noqa: E402

scene = bpy.context.scene
summary = {
    "frame_start": scene.frame_start, "frame_end": scene.frame_end, "fps": scene.render.fps / scene.render.fps_base,
    "objects": {o.name: o.type for o in bpy.data.objects},
    "armatures": {o.name: [b.name for b in o.data.bones] for o in bpy.data.objects if o.type == "ARMATURE"},
    "actions": {a.name: list(a.frame_range) for a in bpy.data.actions},
}
bootstrap.result("summary", json.dumps(summary))
