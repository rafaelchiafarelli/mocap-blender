"""Windowed check (task 42-45). The eight Shift+S operators of deck A through run_operator, on a cube and a sphere. Writes snapmenu.json.

Run from WSL (a Blender window opens for some seconds; do not use the PC meanwhile):
    ./run.sh check_snap_menu.py
or: blender.exe --factory-startup --python <this file> -- <mocap-blender root> <output dir>
"""
import os, sys, json, bpy
root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface; control_surface.register()
from control_surface import blender_glue as g
log = []
def run():
    cube = bpy.data.objects["Cube"]
    bpy.ops.mesh.primitive_uv_sphere_add(location=(3.3, 1.2, 0.7))
    sph = bpy.context.active_object
    cur = bpy.context.scene.cursor
    v = lambda x: [round(c, 2) for c in x]
    def do(op, **a):
        r = g.run_operator(op, a)
        log.append([op, a, sorted(r), "cursor", v(cur.location), "cube", v(cube.location), "sphere", v(sph.location)])
    # sphere active and selected, cube selected too
    cube.select_set(True); sph.select_set(True); bpy.context.view_layer.objects.active = sph
    do("view3d.snap_cursor_to_selected")
    do("view3d.snap_cursor_to_active")
    cur.location = (0.37, 0.88, 0.12); do("view3d.snap_cursor_to_grid")
    do("view3d.snap_cursor_to_center")
    cur.location = (1, 1, 1)
    sph.select_set(False); bpy.context.view_layer.objects.active = cube
    do("view3d.snap_selected_to_cursor", use_offset=False)
    cube.location = (0.4, 0.3, 0.2); do("view3d.snap_selected_to_grid")
    cube.select_set(True); sph.select_set(True); bpy.context.view_layer.objects.active = sph
    do("view3d.snap_selected_to_active")
    do("view3d.snap_selected_to_cursor", use_offset=True)
    json.dump(log, open(os.path.join(out, "snapmenu.json"), "w"), indent=0)
    bpy.ops.wm.quit_blender()
bpy.app.timers.register(run, first_interval=1.5)
