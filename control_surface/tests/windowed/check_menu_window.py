"""Windowed check (task 42-45). The 4-Mix window follows the Properties and Add menus: opens, resizes per level (Render > Motion Blur > Shutter Curve through menu_pick), a click outside (focus moved to the main window) closes both menus; screenshots 01-04.png. Writes result.json.

Run from WSL (a Blender window opens for some seconds; do not use the PC meanwhile):
    ./run.sh check_menu_window.py
or: blender.exe --factory-startup --python <this file> -- <mocap-blender root> <output dir>
"""
"""Windowed check for task 42: blender.exe --factory-startup --python check_window.py -- <repo root> <out dir>"""
import json
import os
import sys

import bpy

root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface  # noqa: E402

control_surface.register()
from control_surface import add_menu, menu_window, oswindow, props_menu  # noqa: E402

log = {}


def win4():
    return menu_window.window()


def shot(name):
    w = win4()
    if w is None:
        return
    a = w.screen.areas[0]
    with bpy.context.temp_override(window=w, area=a):
        bpy.ops.screen.screenshot(filepath=os.path.join(out, name), check_existing=False)


def pick(text):
    lv = props_menu._stack[-1]
    i = next(i for i, it in enumerate(lv["items"]) if it["text"] == text)
    w = win4()
    with bpy.context.temp_override(window=w, area=w.screen.areas[0]):
        return bpy.ops.control_surface.menu_pick(menu="PROPS", index=i)


def state(tag):
    log[tag] = {
        "windows": len(bpy.context.window_manager.windows),
        "open": menu_window.is_open(),
        "hwnd": bool(menu_window._hwnd),
        "rect": oswindow.rect(menu_window._hwnd),
        "size": menu_window._size,
        "units": menu_window._units,
        "fg_is_4mix": oswindow.foreground_any() == menu_window._hwnd if menu_window._hwnd else None,
        "props": [lv["title"] for lv in props_menu._stack],
        "add": [lv["title"] for lv in add_menu._stack],
        "ui_scale": bpy.context.preferences.system.ui_scale,
    }


main_hwnd = []


def force_focus(h):
    """Test only: Blender started from WSL is not the foreground program, and Windows
    refuses SetForegroundWindow then; a synthetic Alt press lifts that lock."""
    import ctypes
    u = ctypes.windll.user32
    u.keybd_event(0x12, 0, 0, 0)
    u.keybd_event(0x12, 0, 2, 0)
    oswindow.focus(h)
steps = [
    (1.0, lambda: (main_hwnd.append(next(iter(oswindow.process_windows()))), force_focus(main_hwnd[0]))),
    (1.0, lambda: props_menu.toggle()),
    (2.0, lambda: (state("opened"), shot("01-opened.png"))),
    (0.3, lambda: pick("Render")),
    (0.8, lambda: pick("Motion Blur")),
    (1.2, lambda: (state("motion_blur"), shot("02-motion-blur.png"))),
    (0.3, lambda: pick("Shutter Curve")),
    (1.2, lambda: (state("curve"), shot("03-curve.png"))),
    (0.3, lambda: force_focus(main_hwnd[0])),  # a click outside
    (1.0, lambda: state("clicked_outside")),
    (0.5, lambda: add_menu.toggle()),
    (2.0, lambda: (state("add_opened"), shot("04-add.png"))),
    (0.3, lambda: menu_window.close_menus()),
    (1.0, lambda: state("add_closed")),
]


def run():
    if not steps:
        with open(os.path.join(out, "result.json"), "w") as f:
            json.dump(log, f, indent=1, default=str)
        bpy.ops.wm.quit_blender()
        return None
    delay, fn = steps.pop(0)
    try:
        fn()
    except Exception as e:
        import traceback
        log.setdefault("errors", []).append(traceback.format_exc())
    return steps[0][0] if steps else 0.5


bpy.app.timers.register(run, first_interval=steps[0][0])
