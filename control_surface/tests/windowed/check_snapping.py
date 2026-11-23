"""Windowed check (task 42-45). Snapping with the REAL mouse: cycle off/grid/geometry/off; grid move on X and grid scale; geometry move (a cube corner onto another cube's vertex); 3D cursor onto a vertex. Writes snap.json.

Run from WSL (a Blender window opens for some seconds; do not use the PC meanwhile):
    ./run.sh check_snapping.py
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
    seq = []
    for _ in range(3):
        snap.cycle(); seq.append(g.read_state("snap_mode"))
    log.append(["cycle", seq])
    snap.cycle()  # grid
    g.grid_set(64)  # S2 VOL: 10 cm, so the mouse moves cross cells
    mouse_to(*to_screen(Vector((0, 0, 0))))
def s2():
    log.append(["grab_start", sorted(g.grab_start("MOVE", "X"))])
def s3():
    x, y = to_screen(Vector((0, 0, 0))); mouse_to(x + 7, y)
def s4():
    x, y = to_screen(Vector((0, 0, 0))); mouse_to(x + 53, y + 4)
def s5():
    loc = st["c"].location
    q = g.grid_size()  # the viewport grid (task 50)
    log.append(["grid move X", r3(loc), "on the viewport grid", q, abs(loc.x / q - round(loc.x / q)) < 1e-6, "y,z kept", abs(loc.y) < 1e-9 and abs(loc.z) < 1e-9])
    grab.request("confirm")
def s6():
    st["c"].location = (0, 0, 0)
    log.append(["grab_start scale", sorted(g.grab_start("SCALE", "FREE"))])
def s7():
    x, y = to_screen(Vector((0, 0, 0))); mouse_to(x + 160, y)
def s8():
    x, y = to_screen(Vector((0, 0, 0))); mouse_to(x + 233, y + 11)
def s9():
    s = st["c"].scale
    log.append(["grid scale", r3(s), "step 0.1", abs(s.x / 0.1 - round(s.x / 0.1)) < 1e-6])
    grab.request("cancel") if False else grab.request("confirm")
def s10():
    st["c"].scale = (1, 1, 1); st["c"].location = (0, 0, 0)
    snap.cycle()  # geometry
    log.append(["mode", g.read_state("snap_mode"), sorted(snap.elements()), snap.snap_target()])
    mouse_to(*to_screen(Vector((0.3, 0, 0))))
def s11():
    log.append(["grab_start geometry", sorted(g.grab_start("MOVE", "FREE"))])
def s12():
    mouse_to(*to_screen(Vector((1.5, 0.2, 0.2))))
def s13():
    st["vt"] = Vector((2.5, -0.5, 0.5))
    mouse_to(*to_screen(st["vt"]))
def s14():
    c = st["c"]; bpy.context.view_layer.update()
    corners = [c.matrix_world @ Vector(k) for k in c.bound_box]
    dmin = min((k - st["vt"]).length for k in corners)
    log.append(["geometry move: a corner on the target vertex", round(dmin, 5), "cube at", r3(c.location)])
    grab.request("confirm")
def s15():
    mouse_to(*to_screen(Vector((3.5, 0.5, 0.5))))
def s16():
    r = g.cursor_to_mouse()
    log.append(["cursor geometry", sorted(r), r3(bpy.context.scene.cursor.location), "expected", [3.5, 0.5, 0.5]])
def s17():
    snap.cycle(); log.append(["after third press", g.read_state("snap_mode")])
seq = [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14, s15, s16, s17]
def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "snap.json"), "w")); bpy.ops.wm.quit_blender(); return None
    f = seq.pop(0)
    try: f()
    except Exception as e:
        import traceback; log.append(["error", f.__name__, traceback.format_exc()[-600:]])
    return 0.7
bpy.app.timers.register(run, first_interval=1.5)
