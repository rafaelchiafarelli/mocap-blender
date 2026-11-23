"""Windowed check (task 42-45). Geometry snapping in Edit Mode with the REAL mouse: a selected vertex moved onto another cube's vertex. Writes snap.json.

Run from WSL (a Blender window opens for some seconds; do not use the PC meanwhile):
    ./run.sh check_snapping_edit_mode.py
or: blender.exe --factory-startup --python <this file> -- <mocap-blender root> <output dir>
"""
import os, sys, json, ctypes, bpy
from ctypes import wintypes
from bpy_extras import view3d_utils
from mathutils import Vector
root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface; control_surface.register()
from control_surface import blender_glue as g, grab, oswindow, snap
u = ctypes.windll.user32
log = []; st = {}
r3 = lambda v: [round(c, 4) for c in v]
def ff(h): u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0); oswindow.focus(h)
def view():
    win = bpy.context.window_manager.windows[0]
    area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
    region = next(r for r in area.regions if r.type == "WINDOW")
    return win, area, region, area.spaces.active.region_3d
def to_screen(p):
    win, area, region, rv3d = view()
    xy = view3d_utils.location_3d_to_region_2d(region, rv3d, p)
    pt = wintypes.POINT(0, 0); u.ClientToScreen(st["main"], ctypes.byref(pt))
    return int(pt.x + region.x + xy.x), int(pt.y + win.height - (region.y + xy.y))
def mouse_to(x, y):
    u.SetCursorPos(x - 3, y); u.mouse_event(1, 1, 0, 0, 0); u.SetCursorPos(x, y); u.mouse_event(1, 0, 0, 0, 0)
def s0():
    st["main"] = next(iter(oswindow.process_windows())); ff(st["main"])
    bpy.ops.mesh.primitive_cube_add(size=1, location=(3, 0, 0)); st["t"] = bpy.context.active_object
    cube = bpy.data.objects["Cube"]; st["c"] = cube
    bpy.ops.object.select_all(action="DESELECT"); cube.select_set(True); bpy.context.view_layer.objects.active = cube
    win, area, region, rv3d = view()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.view3d.view_all()
def s1():
    import bmesh
    snap.cycle(); snap.cycle()  # geometry
    c = st["c"]
    win, area, region, rv3d = view()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(c.data)
    v = max(bm.verts, key=lambda v: (v.co.x, -v.co.y, v.co.z)); v.select = True
    bm.select_flush(True); bmesh.update_edit_mesh(c.data)
    st["v0"] = c.matrix_world @ v.co.copy(); st["vi"] = v.index
    log.append(["edit: moving vertex", r3(st["v0"]), "mode", g.read_state("snap_mode")])
    mouse_to(*to_screen(st["v0"]))
def s2():
    log.append(["grab_start edit", sorted(g.grab_start("MOVE", "FREE"))])
def s3():
    mouse_to(*to_screen(Vector((1.8, 0.1, 0.4))))
def s4():
    mouse_to(*to_screen(Vector((2.5, -0.5, 0.5))))
def s5():
    import bmesh
    c = st["c"]; bm = bmesh.from_edit_mesh(c.data); bm.verts.ensure_lookup_table()
    log.append(["edit: vertex now", r3(c.matrix_world @ bm.verts[st["vi"]].co), "expected", [2.5, -0.5, 0.5]])
    grab.request("confirm")
seq = [s0, s1, s2, s3, s4, s5]
def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "snap.json"), "w")); bpy.ops.wm.quit_blender(); return None
    f = seq.pop(0)
    try: f()
    except Exception as e:
        import traceback; log.append(["error", f.__name__, traceback.format_exc()[-600:]])
    return 0.7
bpy.app.timers.register(run, first_interval=1.5)
