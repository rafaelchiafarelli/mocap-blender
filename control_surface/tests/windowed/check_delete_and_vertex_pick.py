"""Windowed check (task 49). Through a real Session with fake MIDI ports: the armed
delete ends after 5 s and on another key; armed on deck A and confirmed on deck D;
CUP (deck A): cursor to the object, CUP again = vertex pick, the platter walks the
vertices, CUP again ends with the cursor kept. Task 51: the second CUP counts only while
CUP's LED is lit (3 s), in Object Mode; deck A's CUP / CUE / PLAY/PAUSE (SHIFT too) turn
the cursor axis (2/3/4) off. Task 54: deck A's IN (the Add menu) turns the axis and the
vertex pick off, and 1-4 do nothing while it is open. No mouse. Writes delete_pick.json.

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


def s11():
    log.append(["mode", bpy.context.object.mode])
    press(0x91, 0x0A)                                   # CUP: to the object, lit 3 s


def s12():
    log.append(["CUP lit after 2.5 s", st["s"].engine.flashing("CUP L/A")])
    press(0x91, 0x0A)                                   # 2nd CUP while lit: pick


def s13():
    log.append(["2nd CUP while lit -> pick (must be True)", g.cursor_pick()])
    press(0x91, 0x0A)                                   # 3rd: done
    st["after3"] = True


def s14():
    log.append(["CUP lit by the 3rd press", st["s"].engine.flashing("CUP L/A")])
    press(0x91, 0x0A)                                   # CUP: to the object (a 4th within the 3rd's light)


def s15():
    log.append(["4th CUP -> to the object, no pick (must be False)", g.cursor_pick()])


def s16():
    press(0x91, 0x0A)                                   # CUP after the light went off


def s17():
    log.append(["CUP after the light -> no pick (must be False)", g.cursor_pick()])


def axis_step(name, note):
    def f():
        a0 = g.read_state("cursor_axis")
        press(0x91, note)
        st["last"] = (name, a0)
    def h():
        log.append([f"axis after {name} (was {st['last'][1]})", g.read_state("cursor_axis")])
        if g.read_state("cursor_axis") != "NONE":
            press(0x91, 0x07)                           # 2 again: off
    return f, h


def arm_x():
    if g.read_state("cursor_axis") != "X":
        press(0x91, 0x07)


axis_seq = []
for name, note in (("CUP", 0x0A), ("CUE", 0x0B), ("PLAY/PAUSE", 0x0C), ("SHIFT+CUP", 0x4A), ("SYNC (keeps it)", 0x05)):
    f, h = axis_step(name, note)
    axis_seq += [(3.3, arm_x), (0.5, f), (0.5, h)]

def t0():
    g._cursor_axis, g._pick = "NONE", None
    press(0x91, 0x07)                                   # 2: axis X


def t1():
    log.append(["axis armed", g.read_state("cursor_axis")])
    press(0x91, 0x02)                                   # IN: the Add menu


def t2():
    log.append(["after IN: axis (must be NONE)", g.read_state("cursor_axis"), "add menu", g.read_state("add_menu")])
    press(0x91, 0x08)                                   # 3 with the menu open


def t3():
    log.append(["3 with the Add menu open: axis (must be NONE)", g.read_state("cursor_axis")])
    press(0x91, 0x05)                                   # SYNC: close the menu


def t4():
    press(0x91, 0x0A)                                   # CUP: to the object


def t5():
    press(0x91, 0x0A)                                   # CUP again: vertex pick


def t6():
    log.append(["pick on", g.cursor_pick()])
    press(0x91, 0x02)                                   # IN: the Add menu


def t7():
    log.append(["after IN: pick (must be False)", g.cursor_pick(), "add menu", g.read_state("add_menu")])
    press(0x91, 0x05)


seq_task54 = [(3.3, t0), (0.5, t1), (0.5, t2), (0.5, t3), (0.5, t4), (0.5, t5), (0.5, t6), (0.5, t7)]

seq = [(1.0, s0), (0.5, s1), (5.6, s2), (0.5, s3), (0.5, s4), (0.5, s5), (0.5, s6), (0.5, s7), (0.5, s8), (0.5, s9), (0.5, s10),
       (3.3, s11), (2.5, s12), (0.5, s13), (0.5, s14), (0.5, s15), (3.3, s16), (0.5, s17)] + axis_seq + seq_task54


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
