"""Opened on performance.blend. Args: resolved recipe JSON (Windows paths), output shot.blend."""

import json
import math
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
import bootstrap  # noqa: E402

recipe_path, shot_blend = bootstrap.args()
import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

recipe = json.load(open(recipe_path, encoding="utf-8"))
scene = bpy.context.scene
[rig] = [o for o in bpy.data.objects if o.type == "ARMATURE"]


def aim(obj, look_at):
    obj.rotation_euler = (Vector(look_at) - obj.location).to_track_quat("-Z", "Y").to_euler()


def material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1.0)
    return mat


take_first, take_last = scene.frame_start, scene.frame_end
first, last = recipe["frames"] or (take_first, take_last)
if not take_first <= first <= last <= take_last:
    raise SystemExit(f"frames {first}-{last} outside the take ({take_first}-{take_last})")
scene.frame_start, scene.frame_end = first, last

cam = bpy.data.objects.new("ShotCamera", bpy.data.cameras.new("ShotCamera"))
scene.collection.objects.link(cam)
cam.location = recipe["camera"]["location"]
aim(cam, recipe["camera"]["look_at"])
cam.data.lens = recipe["camera"]["lens_mm"]
scene.camera = cam

for i, spec in enumerate(recipe["lights"]):
    light = bpy.data.lights.new(f"Light{i}", spec["type"])
    light.energy, light.color = spec["energy"], spec["rgb"]
    if spec["type"] == "AREA":
        light.size = spec["size"]
    elif spec["type"] in ("POINT", "SPOT"):
        light.shadow_soft_size = spec["size"]
    else:
        light.angle = math.radians(spec["size"])
    obj = bpy.data.objects.new(f"Light{i}", light)
    scene.collection.objects.link(obj)
    obj.location = spec["location"]
    aim(obj, spec["look_at"])

world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
background = world.node_tree.nodes["Background"]
background.inputs["Color"].default_value = (*recipe["world"]["rgb"], 1.0)
background.inputs["Strength"].default_value = recipe["world"]["strength"]

adders = {"cube": bpy.ops.mesh.primitive_cube_add, "cylinder": bpy.ops.mesh.primitive_cylinder_add,
          "sphere": bpy.ops.mesh.primitive_uv_sphere_add, "plane": bpy.ops.mesh.primitive_plane_add,
          "torus": bpy.ops.mesh.primitive_torus_add}
for spec in recipe["objects"]:
    adders[spec["shape"]]()
    obj = bpy.context.active_object
    obj.name = spec["name"]
    obj.dimensions = [max(v, 1e-4) for v in spec["size"]]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler = Euler([math.radians(a) for a in spec["rotation_deg"]])
    obj.data.materials.append(material(spec["name"], spec["rgb"]))
    if spec.get("parent_bone"):
        obj.parent, obj.parent_type, obj.parent_bone = rig, "BONE", spec["parent_bone"]
    obj.location = spec["location"]

if recipe["audio"] is not None:
    editor = scene.sequence_editor or scene.sequence_editor_create()
    strips = editor.strips if hasattr(editor, "strips") else editor.sequences
    start = first + round(recipe["audio"]["offset_s"] * scene.render.fps)
    strips.new_sound("voice", recipe["audio"]["path"], channel=1, frame_start=start)

render = scene.render
render.engine = "BLENDER_EEVEE"
render.resolution_x, render.resolution_y = recipe["resolution"]
render.resolution_percentage = 100
settings = render.image_settings
if hasattr(settings, "media_type"):
    settings.media_type = "VIDEO"
settings.file_format = "FFMPEG"
render.ffmpeg.format = "MPEG4"
render.ffmpeg.codec = "H264"
render.ffmpeg.constant_rate_factor = "HIGH"
render.ffmpeg.audio_codec = "AAC" if recipe["audio"] is not None else "NONE"
render.filepath = recipe["output"]
bpy.ops.wm.save_mainfile(filepath=shot_blend)
bpy.ops.render.render(animation=True)
bootstrap.result("output", recipe["output"])
