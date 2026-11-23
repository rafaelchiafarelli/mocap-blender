"""Run inside Blender: blender -b --factory-startup --python blender_smoke.py -- <repo root>

Exits non-zero on failure (with --python-exit-code). Uses fake MIDI ports and
a test mapping (bundled bindings + mode LEDs on CUE A-D) for the round trip,
and the real WinMM only to list ports and to check that a missing controller
gives a clear error.
"""

import sys
from pathlib import Path

root = sys.argv[sys.argv.index("--") + 1]
sys.path.insert(0, root)

import bpy  # noqa: E402

import control_surface  # noqa: E402
from control_surface import blender_glue, winmm  # noqa: E402

CUE = Path(__file__).resolve().parent / "data" / "modes_cue_leds.json"
CUE_A, CUE_B, CUE_C, CUE_D = 0x27, 0x28, 0x26, 0x29


class FakeIn:
    closed = False

    def close(self):
        self.closed = True


class FakeOut:
    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, *m):
        self.sent.append(m)

    def close(self):
        self.closed = True


def press(s, note):
    s.queue.put((0x90, note, 0x7F))
    s.tick()


control_surface.register()
assert hasattr(bpy.types, "CONTROLSURFACE_PT_panel")

bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.view_layer.objects.active
assert cube.mode == "OBJECT"

fin, fout = FakeIn(), FakeOut()
s = blender_glue.connect(mapping_path=CUE, midi_in=fin, midi_out=fout, intro=False)
press(s, 0x2A)  # A
assert cube.mode == "EDIT", cube.mode
assert (0x90, CUE_A, 127) in fout.sent, fout.sent
press(s, 0x2B)  # B
assert cube.mode == "OBJECT", cube.mode
assert fout.sent[-2:] in ([(0x90, CUE_A, 0), (0x90, CUE_B, 127)], [(0x90, CUE_B, 127), (0x90, CUE_A, 0)]), fout.sent
bpy.ops.object.mode_set(mode="EDIT")  # changed outside the controller
s.tick()
assert set(fout.sent[-2:]) == {(0x90, CUE_A, 127), (0x90, CUE_B, 0)}, fout.sent
bpy.ops.object.mode_set(mode="OBJECT")
press(s, 0x2C)  # C
assert cube.mode == "VERTEX_PAINT", cube.mode
press(s, 0x2B)  # B
assert cube.mode == "OBJECT", cube.mode
press(s, 0x2D)  # D on a mesh: Pose fails, kept as an error
assert cube.mode == "OBJECT" and "D press" in s.engine.last_error, s.engine.last_error
bpy.ops.object.armature_add()
rig = bpy.context.view_layer.objects.active
press(s, 0x2D)  # D on an armature
assert rig.mode == "POSE", rig.mode
assert (0x90, CUE_D, 127) in fout.sent[-4:], fout.sent

control_surface.unregister()  # must release the ports and turn LEDs off
assert fin.closed and fout.closed
assert set(fout.sent[-4:]) == {(0x90, n, 0) for n in (CUE_A, CUE_B, CUE_C, CUE_D)}, fout.sent

ins, outs = winmm.list_ports()
print("WinMM ports:", ins, outs)
if not any("4-mix" in n.lower() for n in ins):
    try:
        blender_glue.Session()
        raise AssertionError("expected MidiError without the controller")
    except winmm.MidiError as e:
        assert "not found" in str(e), e
# tour.vertex_tour (numpy, Blender's Python): nearest-neighbour walk (task 49)
import numpy as np  # noqa: E402
from control_surface.tour import TOUR_MAX, vertex_tour  # noqa: E402
_co = np.array([[0, 0, 0], [10, 0, 0], [1, 0, 0], [9, 0, 0], [2, 0, 0]], dtype=float)
assert vertex_tour(_co, (0.1, 0, 0)) == [0, 2, 4, 3, 1], vertex_tour(_co, (0.1, 0, 0))
assert sorted(vertex_tour(np.random.default_rng(1).random((200, 3)), (0, 0, 0))) == list(range(200))
assert vertex_tour(np.empty((0, 3)), (0, 0, 0)) == []
assert vertex_tour(np.zeros((TOUR_MAX + 1, 3)), (0, 0, 0)) == list(range(TOUR_MAX + 1))

print("SMOKE OK")
