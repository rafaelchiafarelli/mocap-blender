"""Windowed check (task 50). S2 VOL sets the viewport grid: grid_set values → every 3D View's grid
scale, jitter at a boundary keeps it, the grid-mode move lands on it (REAL mouse), the deck A
cursor walk crosses it with 1 cm platter steps; screenshot with the "grid: …" note. Writes grid.json.

Run from WSL (a Blender window opens for some seconds; do not use the PC meanwhile):
    ./run.sh check_grid_s2_vol.py
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
def scales():
    return [round(a.spaces.active.overlay.grid_scale, 4) for w in bpy.context.window_manager.windows
            for a in w.screen.areas if a.type == "VIEW_3D"]
def to_screen(p):
    win, area, region, rv3d = view()
    xy = view3d_utils.location_3d_to_region_2d(region, rv3d, p)
    pt = wintypes.POINT(0, 0); u.ClientToScreen(st["main"], ctypes.byref(pt))
    return int(pt.x + region.x + xy.x), int(pt.y + win.height - (region.y + xy.y))
def mouse_to(x, y):
    u.SetCursorPos(x - 3, y); u.mouse_event(1, 1, 0, 0, 0); u.SetCursorPos(x, y); u.mouse_event(1, 0, 0, 0, 0)
def s0():
    st["main"] = next(iter(oswindow.process_windows())); ff(st["main"])
    st["c"] = bpy.data.objects["Cube"]
    win, area, region, rv3d = view()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.view3d.view_all()
    log.append(["start", scales(), "grid_size", g.grid_size()])
def s1():
    res = []
    for v in (0, 127, 64, 80):
        g.grid_set(v); res.append([v, scales(), g.grid_size()])
    log.append(["grid_set", res])
    g.grid_set(79); g.grid_set(81); g.grid_set(79)
    log.append(["jitter 79/81 keeps", scales()])
def s2():
    bpy.ops.screen.screenshot(filepath=os.path.join(out, "grid-50cm.png"))
    log.append(["note", g._grid_note[0] if g._grid_note else None])
def s3():
    snap.cycle()  # grid
    mouse_to(*to_screen(Vector((0, 0, 0))))
def s4():
    log.append(["grab_start", sorted(g.grab_start("MOVE", "X"))])
def s5():
    x, y = to_screen(Vector((0, 0, 0))); mouse_to(x + 7, y)
def s6():
    x, y = to_screen(Vector((0, 0, 0))); mouse_to(x + 97, y + 4)
def s7():
    loc = st["c"].location; q = g.grid_size()
    log.append(["grid move X", r3(loc), "grid", q, "on grid", abs(loc.x / q - round(loc.x / q)) < 1e-6, "moved", abs(loc.x) > 1e-6])
    bpy.ops.screen.screenshot(filepath=os.path.join(out, "grid-move.png"))
    grab.request("confirm")
def s8():
    bpy.context.scene.cursor.location = (0, 0, 0)
    g.cursor_axis_toggle("X")
    walk = []
    for n in range(60):
        g.cursor_move(0.01)
        if n in (9, 19, 24, 29, 59):
            walk.append([n + 1, round(bpy.context.scene.cursor.location.x, 4)])
    log.append(["cursor walk, 1 cm steps on the 50 cm grid", walk])
    for _ in range(60):
        g.cursor_move(-0.01)
    log.append(["back", round(bpy.context.scene.cursor.location.x, 4)])
def s9():
    snap.cycle(); snap.cycle()  # off
    bpy.context.scene.cursor.location = (0, 0, 0)
    for _ in range(3):
        g.cursor_move(0.01)
    log.append(["snap off: free", round(bpy.context.scene.cursor.location.x, 4)])
seq = [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9]
def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "grid.json"), "w")); bpy.ops.wm.quit_blender(); return None
    f = seq.pop(0)
    try: f()
    except Exception as e:
        import traceback; log.append(["error", f.__name__, traceback.format_exc()[-600:]])
    return 0.7
bpy.app.timers.register(run, first_interval=1.5)
