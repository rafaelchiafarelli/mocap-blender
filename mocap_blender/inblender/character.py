"""Args: character JSON, output .blend. An MPFB human with a Rigify human metarig, feet on the floor."""

import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
import bootstrap  # noqa: E402

character_json, out = bootstrap.args()
import addon_utils  # noqa: E402
import bpy  # noqa: E402

character = json.load(open(character_json, encoding="utf-8"))
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.entities.objectproperties import HumanObjectProperties  # noqa: E402
from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: E402

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)

macros = {k: character[k] for k in ("gender", "age", "muscle", "weight", "height", "proportions")}
macros.update(cupsize=0.5, firmness=0.5, race=dict(character["race"]))
basemesh = HumanService.create_human(macro_detail_dict=macros)
basemesh.name = character["name"]
rig = HumanService.add_builtin_rig(basemesh, "rigify.human")

skin = bpy.data.materials.new(character["name"] + ".skin")
skin.use_nodes = True
bsdf = skin.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (*character["skin_rgb"], 1.0)
bsdf.inputs["Roughness"].default_value = 0.55
basemesh.data.materials.clear()
basemesh.data.materials.append(skin)

bpy.context.view_layer.update()
bones = rig.data.bones
facing = bones["nose"].head_local.y - bones["spine.006"].head_local.y
for key in macros:
    if key != "race":
        bootstrap.result(f"macro.{key}", round(HumanObjectProperties.get_value(key, entity_reference=basemesh), 4))
bootstrap.result("rig", rig.name)
bootstrap.result("mesh", basemesh.name)
bootstrap.result("facing", "-Y" if facing < 0 else "+Y")
bootstrap.result("height_m", round(max(v.co.z for v in basemesh.data.vertices) * basemesh.matrix_world[2][2], 3))
bpy.ops.wm.save_mainfile(filepath=out)
