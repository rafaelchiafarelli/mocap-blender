"""Windowed check (task 42-45). Deck A 3D cursor with the REAL mouse: cursor to the mouse on the cube (its surface) and in empty space (view depth); Z axis platter moves; axis off. Writes cursor.json.

Run from WSL (a Blender window opens for some seconds; do not use the PC meanwhile):
    ./run.sh check_cursor_to_mouse.py
or: blender.exe --factory-startup --python <this file> -- <mocap-blender root> <output dir>
"""
import os, sys, json, ctypes, bpy
root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface; control_surface.register()
from control_surface import blender_glue, oswindow
u = ctypes.windll.user32
log = []; st = {}
loc = lambda: [round(v, 3) for v in bpy.context.scene.cursor.location]
def ff(h): u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0); oswindow.focus(h)
def s0():
    st["main"] = next(iter(oswindow.process_windows())); ff(st["main"])
    x, y, w, h = oswindow.rect(st["main"]); st["r"] = (x, y, w, h)
def at(fx, fy):
    def f():
        x, y, w, h = st["r"]; u.SetCursorPos(int(x + w * fx), int(y + h * fy)); u.mouse_event(1, 1, 0, 0, 0); u.mouse_event(1, -1, 0, 0, 0)
    return f
def go(tag):
    def f():
        r = blender_glue.cursor_to_mouse(); log.append([tag, sorted(r), loc()])
    return f
def axis():
    blender_glue.cursor_axis_toggle("Z"); blender_glue.cursor_move(0.05); blender_glue.cursor_move(0.05)
    log.append(["Z +0.1", blender_glue.read_state("cursor_axis"), loc()])
    blender_glue.cursor_axis_toggle("Z"); blender_glue.cursor_move(1.0)
    log.append(["Z off, move ignored", blender_glue.read_state("cursor_axis"), loc()])
seq = [s0, at(0.45, 0.5), go("mouse at the centre (on the cube)"), at(0.25, 0.3), go("mouse up-left (empty space)"), axis]
def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "cursor.json"), "w")); bpy.ops.wm.quit_blender(); return None
    f = seq.pop(0)
    try: f()
    except Exception as e: log.append(["error", repr(e)])
    return 0.8
bpy.app.timers.register(run, first_interval=1.5)
