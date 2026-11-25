"""Windowed check (task 55). SYNC ends a running movement where it is, through a real Session
with fake MIDI ports (and the real mouse resting over the 3D View):
- deck C rotate: IN, 2 (axis X), platter pushes (a free angle), SYNC -> confirmed, not snapped
  to 90°, the rotation tool still armed; the same for scale (RE, 3) and move (4);
- deck C without a grab: SYNC cycles the view's SYNC as before;
- deck A: 2 (axis X), platter, SYNC -> the axis off, the cursor stays (the platter no longer
  moves it); CUP, CUP (vertex pick), platter, SYNC -> the pick off, the cursor stays.
Writes sync.json.

Run from WSL (do not use the PC meanwhile):
    ./run.sh check_sync_confirms.py
"""
import ctypes
import json
import math
import os
import sys
from ctypes import wintypes

import bpy

root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface  # noqa: E402

control_surface.register()
from control_surface import blender_glue as g, grab, oswindow  # noqa: E402

u = ctypes.windll.user32
log, st = [], {}
C, A = 0x93, 0x91
IN, RE, SYNC, CUP = 0x02, 0x04, 0x05, 0x0A
NUM = {1: 0x06, 2: 0x07, 3: 0x08, 4: 0x09}


class FakeIn:
    def close(self): pass


class FakeOut:
    def send(self, *m): pass
    def close(self): pass


def press(b0, b1):
    st["s"].queue.put((b0, b1, 0x7F)); st["s"].queue.put((b0, b1, 0x00))


def platter(b0, n):
    for _ in range(abs(n)):
        st["s"].queue.put((b0, 0x0F, 0x41 if n > 0 else 0x3F))


def nudge():
    x, y = st["mouse"]
    u.SetCursorPos(x + 1, y); u.mouse_event(1, 1, 0, 0, 0)
    u.SetCursorPos(x, y); u.mouse_event(1, -1 & 0xFFFFFFFF, 0, 0, 0)


def cube():
    return bpy.data.objects["Cube"]


def r3(v):
    return [round(c, 4) for c in v]


def s0():
    st["main"] = next(iter(oswindow.process_windows()))
    u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0); oswindow.focus(st["main"])
    u.keybd_event(0x1B, 0, 0, 0); u.keybd_event(0x1B, 0, 2, 0)
    pt = wintypes.POINT(0, 0); u.ClientToScreen(st["main"], ctypes.byref(pt))
    win = bpy.context.window_manager.windows[0]
    st["mouse"] = (pt.x + win.width // 3, pt.y + win.height // 2)
    u.SetCursorPos(*st["mouse"])
    st["s"] = g.connect(midi_in=FakeIn(), midi_out=FakeOut(), intro=False)
    press(C, IN)                                          # rotate: a free rotation starts


def s1():
    press(C, NUM[2])                                      # axis X


def s2():
    platter(0xB3, 7)                                      # 7 pushes of step x 100 degrees
    nudge()


def s3():
    log.append(["rotating", g.read_state("grabbing"), "axis", g.read_state("grab_axis"),
                "SYNC LED state grabbing", g.read_state("grabbing")])
    press(C, SYNC)


def s4():
    x = math.degrees(cube().rotation_euler.x)
    log.append(["rotate after SYNC: grabbing (False)", g.read_state("grabbing"), "x degrees", round(x, 2),
                "not a 90° multiple", abs(x - 90 * round(x / 90)) > 1, "rotate_mode", g.read_state("rotate_mode"),
                "90° mode", g.read_state("grab_snap"), "error", st["s"].engine.last_error])
    grab.end_tools()
    cube().rotation_euler = (0, 0, 0)
    press(C, RE)                                          # scale: a free scale starts


def s5():
    press(C, NUM[3])                                      # axis Y


def s6():
    platter(0xB3, 5); nudge()


def s7():
    press(C, SYNC)


def s8():
    log.append(["scale after SYNC: grabbing (False)", g.read_state("grabbing"), "scale", r3(cube().scale),
                "scale_mode", g.read_state("scale_mode"), "error", st["s"].engine.last_error])
    grab.end_tools()
    cube().scale = (1, 1, 1)
    press(C, NUM[4])                                      # move on Z


def s9():
    platter(0xB3, 5); nudge()


def s10():
    press(C, SYNC)


def s11():
    log.append(["move after SYNC: grabbing (False)", g.read_state("grabbing"), "location", r3(cube().location),
                "error", st["s"].engine.last_error])
    st["sync0"] = g.read_state("sync_mode")
    press(C, SYNC)                                        # no grab: the view's SYNC


def s12():
    log.append(["SYNC without a grab: sync_mode", st["sync0"], "->", g.read_state("sync_mode")])
    grab.end_tools()
    bpy.context.scene.cursor.location = (0, 0, 0)
    press(A, NUM[2])                                      # deck A: cursor axis X


def s13():
    platter(0xB1, 10)


def s14():
    st["c1"] = r3(bpy.context.scene.cursor.location)
    log.append(["cursor moving", g.read_state("cursor_moving"), "cursor", st["c1"]])
    press(A, SYNC)


def s15():
    log.append(["deck A after SYNC: axis (NONE)", g.read_state("cursor_axis"), "moving", g.read_state("cursor_moving"),
                "cursor kept", r3(bpy.context.scene.cursor.location) == st["c1"]])
    platter(0xB1, 10)


def s16():
    log.append(["platter after SYNC: cursor unchanged", r3(bpy.context.scene.cursor.location) == st["c1"]])
    press(A, CUP)                                         # to the object


def s17():
    press(A, CUP)                                         # vertex pick


def s18():
    platter(0xB1, 15)


def s19():
    st["c2"] = r3(bpy.context.scene.cursor.location)
    log.append(["vertex pick", g.cursor_pick(), "cursor", st["c2"]])
    press(A, SYNC)


def s20():
    log.append(["deck A after SYNC: pick (False)", g.cursor_pick(), "cursor kept",
                r3(bpy.context.scene.cursor.location) == st["c2"], "error", st["s"].engine.last_error])


seq = [(1.5, s0), (0.6, s1), (0.6, s2), (0.6, s3), (0.6, s4), (0.6, s5), (0.6, s6), (0.6, s7), (0.6, s8),
       (0.6, s9), (0.6, s10), (0.6, s11), (0.6, s12), (0.6, s13), (0.6, s14), (0.6, s15), (0.6, s16),
       (0.6, s17), (0.6, s18), (0.6, s19), (0.6, s20)]


def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "sync.json"), "w"), default=str)
        g.disconnect(); bpy.ops.wm.quit_blender(); return None
    _, f = seq.pop(0)
    try:
        f()
    except Exception:
        import traceback
        log.append(["error", f.__name__, traceback.format_exc()[-600:]])
    return seq[0][0] if seq else 0.5


bpy.app.timers.register(run, first_interval=2.0)
