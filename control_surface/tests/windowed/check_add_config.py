"""Windowed check (task 52). The Add menu's settings and the vanishing-object bug, through a
real Session with fake MIDI ports and the real keyboard (Ctrl+Z):
- an add like Shift+A (registered, undo step), then deck A's add: Blender's last operator
  (its Adjust Last Operation panel) is deck A's, not the first one;
- the settings level opens; IN / platter / IN on deck A change the cylinder's vertices
  and the object is rebuilt, not duplicated; the registered operator gets the value;
- a field changed directly (as the mouse does) rebuilds it too; OUT closes, keeps it;
- Edit Mode: an add inside the mesh, resized, keeps its vertex count;
- Ctrl+Z while the settings are open ends them without a crash.
Writes add_config.json and screenshots.

Run from WSL (a Blender window opens; do not use the PC meanwhile):
    ./run.sh check_add_config.py
"""
import json, os, sys, ctypes
from ctypes import wintypes
import bpy

root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface  # noqa: E402
control_surface.register()
from control_surface import add_config, blender_glue as g, menu_window, oswindow, props_menu  # noqa: E402

u = ctypes.windll.user32


class FakeIn:
    def close(self): pass


class FakeOut:
    def send(self, *m): pass
    def close(self): pass


log, st = [], {}


def press(b0, b1):
    st["s"].queue.put((b0, b1, 0x7F)); st["s"].queue.put((b0, b1, 0x00))


def platter(n):
    for _ in range(abs(n)):
        st["s"].queue.put((0xB1, 0x0F, 0x41 if n > 0 else 0x3F))


def ops():
    return [o.bl_idname for o in bpy.context.window_manager.operators][-2:]


def meshes():
    return sorted(o.name for o in bpy.data.objects if o.type == "MESH")


def shot(n):
    bpy.ops.screen.screenshot(filepath=os.path.join(out, n))


def key(vk, ctrl=False):
    if ctrl: u.keybd_event(0x11, 0, 0, 0)
    u.keybd_event(vk, 0, 0, 0); u.keybd_event(vk, 0, 2, 0)
    if ctrl: u.keybd_event(0x11, 0, 2, 0)


def s0():
    st["main"] = next(iter(oswindow.process_windows()))
    u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0); oswindow.focus(st["main"])
    key(0x1B)                                            # the splash
    pt = wintypes.POINT(0, 0); u.ClientToScreen(st["main"], ctypes.byref(pt))
    win = bpy.context.window_manager.windows[0]
    u.SetCursorPos(pt.x + win.width // 3, pt.y + win.height // 2)
    st["s"] = g.connect(midi_in=FakeIn(), midi_out=FakeOut(), intro=False)
    r = g.run_operator("mesh.primitive_cone_add", {"location": (-3, 0, 0)}, "INVOKE_DEFAULT", undo=True)
    log.append(["like Shift+A: cone", sorted(r), ops()])


def s1():
    bpy.context.scene.cursor.location = (3, 0, 0)
    r = add_config.run("mesh.primitive_cylinder_add", {})  # what deck A's IN runs on an item
    log.append(["deck A cylinder", sorted(r), "last operator (Blender's panel)", ops(), meshes(),
                "settings open", g.read_state("add_config"), "title", props_menu._stack[0]["title"] if props_menu._stack else None,
                "rows", [r["text"] for r in props_menu._stack[0]["items"]][:6] if props_menu._stack else None])


def s2():
    shot("add-config-window.png")
    log.append(["4-Mix window open", menu_window.is_open()])
    press(0x91, 0x02)                                    # IN: edit Vertices (row 0)
    platter(30)                                          # +2 (~14 pulses each)
    press(0x91, 0x02)                                    # IN: keep


def s3():
    cyl = bpy.data.objects.get(add_config._session["objects"][0]) if add_config._session else None
    reg = add_config._registered(add_config._session["pointer"]) if add_config._session else None
    log.append(["after IN/platter/IN", "vertices field", add_config.group().vertices,
                "mesh verts", len(cyl.data.vertices) if cyl else None, "location", list(cyl.location) if cyl else None,
                "meshes", meshes(), "registered op vertices", reg.properties.vertices if reg else None,
                "error", st["s"].engine.last_error])
    add_config.group().radius = 2.0                      # as a mouse edit in the window


def s4():
    cyl = bpy.data.objects.get(add_config._session["objects"][0])
    log.append(["radius 2 by the field", round(cyl.dimensions.x, 3), "meshes", meshes()])
    shot("add-config-edited.png")
    press(0x91, 0x03)                                    # OUT short: close, keep


def s5():
    log.append(["after OUT", "settings open", g.read_state("add_config"), "session", add_config.active(),
                "meshes", meshes(), "window", menu_window.is_open()])
    bpy.ops.object.select_all(action="DESELECT")
    cube = bpy.data.objects["Cube"]; cube.select_set(True); bpy.context.view_layer.objects.active = cube
    g.run_operator("object.mode_set", {"mode": "EDIT"})


def s6():
    n0 = len(bpy.data.objects["Cube"].data.vertices)
    bpy.context.scene.cursor.location = (0, 0, 3)
    r = add_config.run("mesh.primitive_cube_add", {})
    import bmesh
    st["n0"] = n0
    log.append(["Edit Mode add", sorted(r), "verts before", n0,
                "verts now", len(bmesh.from_edit_mesh(bpy.data.objects["Cube"].data).verts), "open", g.read_state("add_config")])
    add_config.group().size = 0.5


def s7():
    import bmesh
    bm = bmesh.from_edit_mesh(bpy.data.objects["Cube"].data)
    zs = sorted({round(v.co.z, 3) for v in bm.verts})
    log.append(["Edit Mode resized", "verts", len(bm.verts), "z levels", zs])
    key(0x5A, ctrl=True)                                 # Ctrl+Z with the settings open


def s8():
    log.append(["after Ctrl+Z", "session", add_config.active(), "settings open", g.read_state("add_config"),
                "mode", bpy.context.mode, "error", st["s"].engine.last_error])


seq = [(1.5, s0), (0.8, s1), (1.0, s2), (1.0, s3), (0.8, s4), (0.8, s5), (0.8, s6), (0.8, s7), (1.0, s8)]


def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "add_config.json"), "w"), default=str)
        g.disconnect(); bpy.ops.wm.quit_blender(); return None
    _, f = seq.pop(0)
    try:
        f()
    except Exception:
        import traceback
        log.append(["error", f.__name__, traceback.format_exc()[-700:]])
    return seq[0][0] if seq else 0.5


bpy.app.timers.register(run, first_interval=1.5)
