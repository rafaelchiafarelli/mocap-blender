"""Windowed check (task 52 fix). The real deck A path: IN opens the Add menu (the 4-Mix window
opens), Mesh › Circle and Mesh › Cube are picked with IN, which closes that window and adds;
Blender crashed here in 0.1.54 (HUD laid out from the timer with no GPU context). Then a
settings change and a redo: Blender's panel must belong to the last add. Writes add_menu.json.

Run from WSL:
    ./run.sh check_add_from_menu.py
"""
import json, os, sys
import bpy

root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface  # noqa: E402
control_surface.register()
from control_surface import add_config, add_menu, blender_glue as g, menu_window  # noqa: E402

log, st = [], {}


def pick(text):
    level = add_menu._stack[-1]
    level["index"] = next(i for i, it in enumerate(level["items"]) if it["text"] == text)
    return g.add_menu_toggle()


def ops():
    return [o.bl_idname for o in bpy.context.window_manager.operators][-2:]


def s_open():
    g.add_menu_toggle()


def s_mesh():
    log.append(["4-Mix window", menu_window.is_open()]); pick("Mesh")


def make_pick(text):
    def f():
        r = pick(text)
        log.append([f"added {text}", sorted(r), ops(), "settings", g.read_state("add_config"),
                    "window", menu_window.is_open()])
    return f


def s_close():
    add_config.end()
    log.append(["closed", g.read_state("add_config"), sorted(o.name for o in bpy.data.objects if o.type == "MESH")])


seq = []
for name in ("Circle", "Cube", "Circle"):
    seq += [(1.0, s_open), (0.8, s_mesh), (1.0, make_pick(name)), (1.2, s_close)]


def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "add_menu.json"), "w"), default=str)
        bpy.ops.wm.quit_blender(); return None
    _, f = seq.pop(0)
    try:
        f()
    except Exception:
        import traceback
        log.append(["error", f.__name__, traceback.format_exc()[-700:]])
    return seq[0][0] if seq else 0.5


bpy.app.timers.register(run, first_interval=2.0)
