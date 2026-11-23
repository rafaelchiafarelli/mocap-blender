"""Windowed check (task 42-45). Opens Notepad in front of Blender, opens the Properties menu: the 4-Mix window shows on top and stays open; a click on Notepad closes it. Uses the REAL mouse. Writes other.json.

Run from WSL (a Blender window opens for some seconds; do not use the PC meanwhile):
    ./run.sh check_other_program_in_front.py
or: blender.exe --factory-startup --python <this file> -- <mocap-blender root> <output dir>
"""
import os, sys, json, ctypes, subprocess, bpy
from ctypes import wintypes
root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface; control_surface.register()
from control_surface import menu_window, oswindow, props_menu
u = ctypes.windll.user32
u.GetForegroundWindow.restype = wintypes.HWND
log = []; st = {}
def title(h):
    if not h: return None
    b = ctypes.create_unicode_buffer(256); u.GetWindowTextW(h, b, 256); return b.value
def rec(tag):
    log.append([tag, menu_window.is_open(), title(oswindow.foreground_any()), oswindow.topmost(menu_window._hwnd)])
def s0():
    st["np"] = subprocess.Popen(["notepad.exe"])
def s1():
    fg = oswindow.foreground_any(); st["fg"] = fg
    if fg in oswindow.process_windows():  # make sure another program is in front
        u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0)
    rec("before")
def s2(): props_menu.toggle()
def s3(): rec("1 s after open, other program in front (must stay open)")
def s4(): rec("2 s after open (must stay open)")
def s5():
    fg = oswindow.foreground_any()
    r = oswindow.rect(fg)
    st["click"] = (r[0] + r[2] // 2, r[1] + r[3] // 2)
    m = oswindow.rect(menu_window._hwnd)
    log.append(["click at", st["click"], "on", title(fg), "4mix rect", m])
    u.SetCursorPos(*st["click"]); u.mouse_event(2, 0, 0, 0, 0)
    bpy.app.timers.register(lambda: u.mouse_event(4, 0, 0, 0, 0), first_interval=0.1)
def s6(): rec("after click on the other program (must be closed)")
def s7(): st["np"].kill()
seq = [s0, s1, s2, s3, s4, s5, s6, s7]
def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "other.json"), "w")); bpy.ops.wm.quit_blender(); return None
    f = seq.pop(0)
    try: f()
    except Exception as e: log.append(["error", f.__name__, repr(e)])
    return 1.0
bpy.app.timers.register(run, first_interval=1.5)
