"""Windowed check (task 49). Geometry snapping while the REAL mouse sweeps over a
plane and onto another cube: the cube rests on the plane (FACE), then grabs the
other cube's vertex and edge; it must not jump between corners. Logs the hit kind
and the cube's place per step, screenshots sweep3/5/6/9.png with the snap marker.
Writes snap.json.

Run from WSL (do not use the PC for ~20 s):
    ./run.sh check_snap_sweep.py
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
    bpy.ops.wm.read_homefile(use_splash=False)
    st["c"] = bpy.data.objects["Cube"]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(3, 0, 0))
    win, area, region, rv3d = view()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.view3d.view_all()
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -1))
    c = st["c"]; bpy.ops.object.select_all(action="DESELECT"); c.select_set(True); bpy.context.view_layer.objects.active = c
    snap.cycle(); snap.cycle()  # geometry
    mouse_to(*to_screen(Vector((0, 0, 0))))
def s2():
    log.append(["grab", sorted(g.grab_start("MOVE", "FREE"))])
sweep = [Vector((x, -1.5, -1)) for x in (-2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0)] + [Vector((2.6 + 0.1 * i, -0.4, 0.4)) for i in range(4)]
def mk(p, i):
    def f():
        mouse_to(*to_screen(p))
    def r():
        bpy.context.view_layer.update()
        m = grab._snap_marker or {}; log.append([i, "mouse on", r3(p), "cube at", r3(st["c"].location), "kind", m.get("kind"), "hit", r3(m["hit"]) if m.get("hit") is not None else None])
        if i in (3, 5, 6, 9):
            shot(f"sweep{i}.png")
    return f, r
def shot(name):
    win, area, region, rv3d = view()
    with bpy.context.temp_override(window=win, area=area):
        bpy.ops.screen.screenshot_area(filepath=os.path.join(out, name), check_existing=False)
steps2 = []
for i, p in enumerate(sweep):
    f, r = mk(p, i); steps2 += [f, r]
def s_end():
    grab.request("cancel") if hasattr(grab, "request") else None
seq = [s0, s1, s2] + steps2 + [lambda: grab.request("confirm")]
def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "snap.json"), "w")); bpy.ops.wm.quit_blender(); return None
    f = seq.pop(0)
    try: f()
    except Exception as e:
        import traceback; log.append(["error", f.__name__, traceback.format_exc()[-600:]])
    return 0.7
bpy.app.timers.register(run, first_interval=1.5, persistent=True)
