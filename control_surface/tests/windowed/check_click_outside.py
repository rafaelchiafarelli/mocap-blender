"""Windowed check (task 42-45). With the REAL mouse: hovering over the viewport keeps the 4-Mix window open, a click inside keeps it, an instant click and a 0.12 s click outside close it. Writes click.json.

Run from WSL (a Blender window opens for some seconds; do not use the PC meanwhile):
    ./run.sh check_click_outside.py
or: blender.exe --factory-startup --python <this file> -- <mocap-blender root> <output dir>
"""
import os, sys, json, ctypes, bpy
root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface; control_surface.register()
from control_surface import menu_window, oswindow, props_menu
u = ctypes.windll.user32
log = []
st = {}
def ff(h):
    u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0); oswindow.focus(h)
def click(x, y):
    u.SetCursorPos(x, y); u.mouse_event(0x0002, 0, 0, 0, 0); u.mouse_event(0x0004, 0, 0, 0, 0)
def desc(h):
    if not h: return None
    b = ctypes.create_unicode_buffer(256); u.GetWindowTextW(h, b, 256)
    return [h, b.value, h in oswindow.process_windows()]
def rec(tag):
    log.append((tag, "open", menu_window.is_open(), "props", [l["title"] for l in props_menu._stack], "fg", desc(oswindow.foreground_any()), "down", oswindow.mouse_down()))
def s0():
    st["main"] = next(iter(oswindow.process_windows())); ff(st["main"])
    x, y, w, h = oswindow.rect(st["main"]); st["c"] = (x + w // 2, y + h // 2)
    u.SetCursorPos(*st["c"])
def s1(): props_menu.toggle()
def s2(): rec("opened")
def s3(): u.SetCursorPos(st["c"][0] + 40, st["c"][1] + 20)   # hover over the main window
def s4(): u.SetCursorPos(st["c"][0] + 80, st["c"][1] + 40)
def s5(): rec("after hover (must stay open)")
def s6():
    x, y, w, h = oswindow.rect(menu_window._hwnd); click(x + w // 2, y + h - 15)  # inside, empty bottom
def s7(): rec("after click inside (must stay open)")
def s8(): click(*st["c"])  # outside: the main viewport, instant click
def s9(): rec("after quick click outside (must be closed)")
def s10(): props_menu.toggle()
def s11(): rec("reopened")
def s12():
    u.SetCursorPos(*st["c"]); u.mouse_event(0x0002, 0, 0, 0, 0)
    bpy.app.timers.register(lambda: u.mouse_event(0x0004, 0, 0, 0, 0), first_interval=0.12)
def s13(): rec("after normal click outside (must be closed)")
seq = [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13]
def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "click.json"), "w"), indent=0); bpy.ops.wm.quit_blender(); return None
    f = seq.pop(0)
    try: f()
    except Exception as e: log.append(("error", f.__name__, repr(e)))
    return 1.0
bpy.app.timers.register(run, first_interval=1.5)
