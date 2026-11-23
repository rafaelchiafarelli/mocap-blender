"""Windowed check (task 49). Through a real Session with fake MIDI ports: the armed
delete ends after 5 s and on another key; armed on deck A and confirmed on deck D;
CUP (deck A): cursor to the object, CUP again = vertex pick, the platter walks the
vertices, CUP again ends with the cursor kept. No mouse. Writes delete_pick.json.

Run from WSL:
    ./run.sh check_delete_and_vertex_pick.py
"""
import json
import os
import sys

import bpy

root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface  # noqa: E402

control_surface.register()
from control_surface import blender_glue as g  # noqa: E402


class FakeIn:
    def close(self):
        pass


class FakeOut:
    def send(self, *m):
        pass

    def close(self):
        pass


log = []
st = {}
r3 = lambda v: [round(c, 4) for c in v]


def press(b0, b1):
    st["s"].queue.put((b0, b1, 0x7F))
    st["s"].queue.put((b0, b1, 0x00))


def select_only(name):
    bpy.ops.object.select_all(action="DESELECT")
    o = bpy.data.objects[name]
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def s0():
    st["s"] = g.connect(midi_in=FakeIn(), midi_out=FakeOut(), intro=False)
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(3, 0, 0))
    bpy.context.active_object.name = "Victim"
    select_only("Victim")
    press(0x93, 0x03)                                   # OUT deck C: arm


def s1():
    log.append(["armed after OUT", g.delete_armed()])


def s2():
    log.append(["armed 5.5 s later (must be False)", g.delete_armed()])
    press(0x93, 0x03)                                   # arm again


def s3():
    log.append(["armed again", g.delete_armed()])
    press(0x92, 0x0B)                                   # CUE deck B: another key


def s4():
    log.append(["after another key (must be False)", g.delete_armed(), "Victim exists", "Victim" in bpy.data.objects])
    press(0x91, 0x03)                                   # OUT deck A: arm


def s5():
    log.append(["armed on deck A", g.delete_armed()])
    press(0x94, 0x03)                                   # OUT deck D: delete


def s6():
    log.append(["deleted from deck D", "Victim" not in bpy.data.objects])
    select_only("Cube")
    bpy.context.scene.cursor.location = (5, 5, 5)
    press(0x91, 0x0A)                                   # CUP deck A: to the object


def s7():
    log.append(["cursor after CUP", r3(bpy.context.scene.cursor.location), "pick", g.cursor_pick()])
    press(0x91, 0x0A)                                   # CUP again within 3 s: pick


def s8():
    st["v0"] = r3(bpy.context.scene.cursor.location)
    log.append(["pick on, first vertex", st["v0"], "pick", g.cursor_pick()])
    for _ in range(15):                                 # one vertex (~14 pulses)
        st["s"].queue.put((0xB1, 0x0F, 0x41))


def s9():
    v1 = r3(bpy.context.scene.cursor.location)
    log.append(["after 15 pulses", v1, "a cube corner", all(abs(abs(c) - 1) < 1e-4 for c in v1), "moved", v1 != st["v0"]])
    press(0x91, 0x0A)                                   # CUP: done


def s10():
    log.append(["after the 3rd CUP", r3(bpy.context.scene.cursor.location), "pick", g.cursor_pick()])


seq = [(1.0, s0), (0.5, s1), (5.6, s2), (0.5, s3), (0.5, s4), (0.5, s5), (0.5, s6), (0.5, s7), (0.5, s8), (0.5, s9), (0.5, s10)]


def run():
    if not seq:
        json.dump(log, open(os.path.join(out, "delete_pick.json"), "w"))
        g.disconnect()
        bpy.ops.wm.quit_blender()
        return None
    _, f = seq.pop(0)
    try:
        f()
    except Exception as e:
        import traceback
        log.append(["error", f.__name__, traceback.format_exc()[-500:]])
    return seq[0][0] if seq else 0.5


bpy.app.timers.register(run, first_interval=1.5)
