"""Run inside Blender: blender -b --factory-startup --python blender_smoke.py -- <repo root>

Exits non-zero on failure (with --python-exit-code). Uses fake MIDI ports for
the A/B round trip, and the real WinMM only to list ports and to check that a
missing controller gives a clear error.
"""

import sys

root = sys.argv[sys.argv.index("--") + 1]
sys.path.insert(0, root)

import bpy  # noqa: E402

import control_surface  # noqa: E402
from control_surface import blender_glue, winmm  # noqa: E402


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


control_surface.register()
assert hasattr(bpy.types, "CONTROLSURFACE_PT_panel")

bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.view_layer.objects.active
assert cube.mode == "OBJECT"

fin, fout = FakeIn(), FakeOut()
s = blender_glue.connect(midi_in=fin, midi_out=fout)
s.queue.put((0x90, 0x2A, 0x7F))  # A
s.tick()
assert cube.mode == "EDIT", cube.mode
assert (0x90, 0x2A, 127) in fout.sent, fout.sent
s.queue.put((0x90, 0x2B, 0x7F))  # B
s.tick()
assert cube.mode == "OBJECT", cube.mode
assert fout.sent[-1] == (0x90, 0x2B, 127) or (0x90, 0x2B, 127) in fout.sent[-2:], fout.sent
bpy.ops.object.mode_set(mode="EDIT")  # changed outside the controller
s.tick()
assert fout.sent[-2:] in ([(0x90, 0x2A, 127), (0x90, 0x2B, 0)], [(0x90, 0x2B, 0), (0x90, 0x2A, 127)]), fout.sent

bpy.ops.object.mode_set(mode="OBJECT")
s.queue.put((0x90, 0x2C, 0x7F))  # C
s.tick()
assert cube.mode == "VERTEX_PAINT", cube.mode
s.queue.put((0x90, 0x2B, 0x7F))  # B
s.tick()
assert cube.mode == "OBJECT", cube.mode
s.queue.put((0x90, 0x2D, 0x7F))  # D on a mesh: Pose fails, kept as an error
s.tick()
assert cube.mode == "OBJECT" and "D press" in s.engine.last_error, s.engine.last_error
bpy.ops.object.armature_add()
rig = bpy.context.view_layer.objects.active
s.queue.put((0x90, 0x2D, 0x7F))  # D on an armature
s.tick()
assert rig.mode == "POSE", rig.mode
assert (0x90, 0x2D, 127) in fout.sent[-4:], fout.sent

control_surface.unregister()  # must release the ports and turn LEDs off
assert fin.closed and fout.closed
assert set(fout.sent[-4:]) == {(0x90, n, 0) for n in (0x2A, 0x2B, 0x2C, 0x2D)}, fout.sent

ins, outs = winmm.list_ports()
print("WinMM ports:", ins, outs)
if not any("4-mix" in n.lower() for n in ins):
    try:
        blender_glue.Session()
        raise AssertionError("expected MidiError without the controller")
    except winmm.MidiError as e:
        assert "not found" in str(e), e
print("SMOKE OK")
