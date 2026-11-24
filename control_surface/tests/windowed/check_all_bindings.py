"""Validation round (task 53): every binding of the bundled mapping, one by one, in a windowed
Blender through a real Session with fake MIDI ports.

For each binding, in mapping order:
1. reset: tools, grabs, menus, settings, delete, vertex pick off; Object Mode; perspective;
   snapping off; the scene back to the Cube (selected, active) plus a camera;
2. reach its `when`: each state not yet right gets its recipe — controller presses where a
   control leads there (e.g. grab_axis X = deck C 2; cursor_pick = CUP, CUP), the API only
   where none does (Edit Mode, a view);
3. check the `when` states really hold (else: "not reached");
4. send the control's bytes (press = press + release; cw/ccw = one pulse; value = a value);
5. record which binding(s) fired (`Engine._fire` wrapped), `Engine.last_error`, and whether
   the target fired.
Progress goes to all_bindings.progress.json after every binding, so a crash shows where.
The result: all_bindings.json and all_bindings.md (a table, in Portuguese, for Rafael).

Run from WSL (about 4 minutes; a Blender window opens; do not use the PC meanwhile):
    CHECK_TIMEOUT=600 ./run.sh check_all_bindings.py
"""
import ctypes
import json
import os
import sys
import time
from ctypes import wintypes

import bpy

root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface  # noqa: E402

control_surface.register()
from control_surface import add_config, add_menu, adjust, blender_glue as g, grab, oswindow, props_menu  # noqa: E402

u = ctypes.windll.user32
MAPPING = json.load(open(os.path.join(root, "control_surface", "mappings", "blender_modes.json")))
PROFILE = json.load(open(os.path.join(root, "control_surface", "devices", "dj_tech_4mix.json")))["controls"]
TICK = 0.15  # seconds between steps (the session ticks every 20 ms)


class FakeIn:
    def close(self): pass


class FakeOut:
    def send(self, *m): pass
    def close(self): pass


st = {"fired": [], "results": []}


def send(cid, event="press"):
    """The bytes the 4-Mix sends for this control event."""
    c = PROFILE[cid]
    q = st["s"].queue
    if c["type"] == "button":
        if event in ("press", "release"):
            q.put(tuple(c["press"]))
            q.put(tuple(c["release"]))
    elif c["type"] == "relative":
        b0, b1 = c["cc"]
        q.put((b0, b1, c.get("center", 64) + (1 if event == "cw" else -1)))
    elif c["type"] == "absolute":
        b0, b1 = c["cc"]
        if c.get("center_tap") is not None and cid not in st["s"].engine.armed:
            q.put((b0, b1, c["center_tap"]))  # a centre-tap knob counts once it passed the centre
        q.put((b0, b1, 80))


def api_mode(mode):
    return lambda: g.run_operator("object.mode_set", {"mode": mode})


EDIT = [api_mode("EDIT"), lambda: g.run_operator("mesh.select_all", {"action": "SELECT"})]


# state -> value -> recipe: ("send", control) or a callable; applied only if the state is not yet right
RECIPES = {
    "object_mode": {"EDIT": EDIT,
                    "OBJECT": [api_mode("OBJECT")]},
    "view_perspective": {"CAMERA": [("send", "CUE D")], "ORTHO": [lambda: g.ACTIONS["view_projection"](type="ORTHO")]},
    "view_axis": {"RIGHT": [("send", "CUE C")], "FRONT": [("send", "CUE A")], "TOP": [("send", "CUE B")]},
    "sync_mode": {"on": [("send", "SYNC L/C")], "blink": [("send", "SYNC L/C"), ("send", "SYNC L/C")]},
    "scale_mode": {"ARMED": [("send", "RE L/C"), ("send", "1 L/C")]},
    # IN starts a free rotation; the 1st press of 1 turns the 90° mode on, the 2nd confirms
    "rotate_mode": {"ARMED": [("send", "IN L/C"), ("send", "1 L/C"), ("send", "1 L/C")], "RUNNING": [("send", "IN L/C")]},
    "cage": {True: [("send", "RE L/C"), ("send", "RE L/C")]},
    # a grab on another axis than the button tested: on its own axis (or free, for 1) it confirms
    "grabbing": {True: [lambda: send("3 L/C" if st["cur"]["control"].startswith("2 ") else "2 L/C")]},
    "grab_axis": {"FREE": [("send", "1 L/C")], "X": [("send", "2 L/C")], "Y": [("send", "3 L/C")],
                  "Z": [("send", "4 L/C")], "NORMAL": EDIT + [("send", "CUP L/C")]},  # the extrusion: Edit Mode only
    "grab_snap": {True: [("send", "IN L/C"), ("send", "1 L/C")]},
    "adjusting": {"mesh.inset": EDIT + [("send", "CUE L/C")], "mesh.bevel": EDIT + [("send", "PLAY/PAUSE L/C")],
                  "mesh.loopcut": EDIT + [("send", "CUP L/C+SHIFT")]},  # Edit Mode only
    "adjust_active": {True: EDIT + [("send", "CUE L/C")]},
    "add_menu": {True: [("send", "IN L/A")]},
    "props_menu": {True: [("send", "IN R/B")]},
    "add_config": {True: [lambda: add_config.run("mesh.primitive_cube_add", {"size": 0.5, "location": (4, 0, 0)})]},
    "delete_armed": {True: [("send", "OUT L/C")]},
    "cursor_pick": {True: [("send", "CUP L/A"), ("send", "CUP L/A")]},
}
ORDER = ["object_mode", "view_perspective", "view_axis", "sync_mode", "scale_mode", "rotate_mode", "cage",
         "grabbing", "grab_axis", "grab_snap", "adjusting", "adjust_active", "add_menu", "props_menu",
         "add_config", "delete_armed", "cursor_pick"]


def reset():
    """Everything off, Object Mode, perspective, the scene back to Cube + Camera + Light."""
    for f in (grab.end_tools, adjust.end, add_config.end, add_menu.close, props_menu.close, g._delete_disarm):
        try:
            f()
        except Exception:
            pass
    g._pick = None
    g._cup_at = None
    g._cursor_axis = "NONE"
    bpy.context.scene.tool_settings.use_snap = False
    if bpy.context.mode != "OBJECT":
        g.run_operator("object.mode_set", {"mode": "OBJECT"})
    if g.read_state("view_perspective") == "CAMERA":
        g.run_operator("view3d.view_camera", {})
    if g.read_state("view_perspective") != "PERSP":
        g.ACTIONS["view_projection"](type="PERSP")
    for o in list(bpy.data.objects):
        if o.name not in st["keep"]:
            bpy.data.objects.remove(o)
    cube = bpy.data.objects.get("Cube")
    if cube is None:
        g.run_operator("mesh.primitive_cube_add", {})
        cube = bpy.context.active_object
        cube.name = "Cube"
    cube.location, cube.rotation_euler, cube.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
    for o in bpy.data.objects:
        o.select_set(o == cube)
    bpy.context.view_layer.objects.active = cube
    st["s"].engine.last_error = ""


def when_holds(when):
    return {k: g.read_state(k) for k in when}


def label(b):
    what = b.get("action") or b.get("operator")
    args = b.get("args")
    return f"{what} {json.dumps(args, ensure_ascii=False)}" if args else what


def run_binding(i, b):
    """Generator: yields seconds to wait between its steps; an exception is recorded, not raised."""
    try:
        yield from _run_binding(i, b)
    except Exception:
        import traceback
        st["results"].append({"i": i, "control": b["control"], "event": b["event"], "when": b.get("when", {}),
                              "does": label(b), "reached": False, "states": {}, "fired": list(st["fired"]),
                              "result": "error", "error": "check: " + traceback.format_exc()[-500:]})


def _run_binding(i, b):
    st["cur"] = b
    reset()
    yield TICK
    when = b.get("when", {})
    for k in ORDER:
        if k in when and g.read_state(k) != when[k]:
            for step in RECIPES.get(k, {}).get(when[k], []):
                if isinstance(step, tuple):
                    send(step[1])
                else:
                    step()
                yield TICK + (0.1 if k in ("grabbing", "grab_axis", "rotate_mode", "scale_mode") else 0)
    got = when_holds(when)
    reached = all(got[k] == v for k, v in when.items())
    st["fired"].clear()
    st["s"].engine.last_error = ""
    if reached:
        send(b["control"], b["event"])
        yield TICK + 0.15
    fired = list(st["fired"])
    res = {"i": i, "control": b["control"], "event": b["event"], "when": when, "does": label(b),
           "reached": reached, "states": got, "fired": fired, "ok_fired": i in fired,
           "error": st["s"].engine.last_error}
    if not reached:
        res["result"] = "not reached"
    elif i not in fired:
        res["result"] = "other binding" if fired else "nothing fired"
    elif res["error"]:
        res["result"] = "error"
    else:
        res["result"] = "ok"
    st["results"].append(res)
    json.dump(st["results"], open(os.path.join(out, "all_bindings.progress.json"), "w"), default=str)


def report():
    rows = st["results"]
    n = {k: sum(1 for r in rows if r["result"] == k) for k in ("ok", "error", "not reached", "other binding", "nothing fired")}
    pt = {"ok": "OK", "error": "erro", "not reached": "condição não alcançada", "other binding": "disparou outro",
          "nothing fired": "nada disparou"}
    lines = ["# Rodada de validação — todos os bindings", "",
             f"{len(rows)} bindings: " + ", ".join(f"{v} {pt[k]}" for k, v in n.items()), "",
             "| # | Controle | Evento | Condição | Ação | Resultado | Detalhe |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        cond = ", ".join(f"{k}={v}" for k, v in r["when"].items()) or "—"
        detail = r["error"] or ("" if r["result"] == "ok" else
                                (f"estados: {r['states']}" if r["result"] == "not reached" else f"disparou: {r['fired']}"))
        lines.append(f"| {r['i']} | {r['control']} | {r['event']} | {cond} | {r['does']} | {pt[r['result']]} | "
                     f"{str(detail).replace('|', '/')} |")
    open(os.path.join(out, "all_bindings.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(rows, open(os.path.join(out, "all_bindings.json"), "w"), default=str)


def start():
    st["main"] = next(iter(oswindow.process_windows()))
    u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0); oswindow.focus(st["main"])
    u.keybd_event(0x1B, 0, 0, 0); u.keybd_event(0x1B, 0, 2, 0)  # the splash
    pt = wintypes.POINT(0, 0); u.ClientToScreen(st["main"], ctypes.byref(pt))
    win = bpy.context.window_manager.windows[0]
    u.SetCursorPos(pt.x + win.width // 3, pt.y + win.height // 2)  # over the 3D View
    st["keep"] = {o.name for o in bpy.data.objects}
    s = g.connect(midi_in=FakeIn(), midi_out=FakeOut(), intro=False)
    st["s"] = s
    index = {id(b): i for i, b in enumerate(s.engine.mapping.bindings)}
    orig = s.engine._fire

    def fire(cid, event, b, value=None):
        st["fired"].append(index.get(id(b)))
        return orig(cid, event, b, value)

    s.engine._fire = fire
    st["bindings"] = list(s.engine.mapping.bindings)
    st["gen"] = (step for i, b in enumerate(st["bindings"]) for step in run_binding(i, b))
    st["t0"] = time.monotonic()


def run():
    try:
        if "gen" not in st:
            start()
            return 0.5
        return next(st["gen"])
    except StopIteration:
        report()
        reset()
        g.disconnect()
        bpy.ops.wm.quit_blender()
        return None
    except Exception:
        import traceback
        st["results"].append({"i": -1, "result": "error", "error": traceback.format_exc()[-800:]})
        json.dump(st["results"], open(os.path.join(out, "all_bindings.progress.json"), "w"), default=str)
        return TICK


bpy.app.timers.register(run, first_interval=2.0, persistent=True)
