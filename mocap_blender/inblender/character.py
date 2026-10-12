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

# MPFB's weights name a few bones of the generated Rigify rig (DEF-forearm.L.001, DEF-eye_master.L, ...),
# which the metarig doesn't have: their vertices wouldn't move. Merge each into the metarig bone it stands for.
bones = {b.name for b in rig.data.bones}


def metarig_bone(name):
    name = name.removeprefix("DEF-").replace("_master", "")
    while name not in bones and name[-4:-3] == "." and name[-3:].isdigit():
        name = name[:-4]
    return name if name in bones else None


merged = 0
for group in [g for g in basemesh.vertex_groups if g.name not in bones and g.name.startswith("DEF-")]:
    target_name = metarig_bone(group.name)
    if target_name is None:
        continue
    target = basemesh.vertex_groups.get(target_name) or basemesh.vertex_groups.new(name=target_name)
    for v in basemesh.data.vertices:
        for g in v.groups:
            if g.group == group.index and g.weight > 0:
                target.add([v.index], g.weight, "ADD")
    basemesh.vertex_groups.remove(group)
    merged += 1
deforming = {g.index for g in basemesh.vertex_groups if g.name in bones}
body = basemesh.vertex_groups["body"].index
unweighted = sum(1 for v in basemesh.data.vertices
                 if any(g.group == body and g.weight > 0 for g in v.groups)
                 and not any(g.group in deforming and g.weight > 0 for g in v.groups))
bootstrap.result("merged_groups", merged)
bootstrap.result("unweighted", unweighted)

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
