"""Blender side: connect/disconnect operators, sidebar panel, the timer.

Incoming MIDI arrives on a WinMM thread and only goes into a queue; a
bpy.app timer (every 20 ms, main thread) drains it into the engine and drives
the LEDs, because bpy must not be called from other threads.
"""

import queue
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from . import knob_select
from .engine import Engine, Mapping
from .profile import Profile

HERE = Path(__file__).resolve().parent
DEFAULT_MAPPING = HERE / "mappings" / "blender_modes.json"
TICK_S = 0.02
MAX_MESSAGES_PER_TICK = 256


def _object_mode():
    obj = bpy.context.view_layer.objects.active
    return obj.mode if obj else "NONE"


def _region_3d():
    place = _view3d()
    return place[1].spaces.active.region_3d if place else None


def _view_perspective():
    """PERSP / ORTHO / CAMERA of the first 3D View, or NONE."""
    rv3d = _region_3d()
    return rv3d.view_perspective if rv3d else "NONE"


# Looking direction of each axis view (Numpad 1/3/7, with Ctrl for the opposite side).
AXIS_VIEWS = {
    "FRONT": (0, 1, 0), "BACK": (0, -1, 0),
    "RIGHT": (-1, 0, 0), "LEFT": (1, 0, 0),
    "TOP": (0, 0, -1), "BOTTOM": (0, 0, 1),
}


def _view_axis():
    """Which axis view the first 3D View looks along, or NONE (also in camera view)."""
    rv3d = _region_3d()
    if rv3d is None or rv3d.view_perspective == "CAMERA":
        return "NONE"
    look = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
    for name, d in AXIS_VIEWS.items():
        if look.dot(Vector(d)) > 0.9999:
            return name
    return "NONE"


def _orbit_selection():
    """Preferences → Navigation → Orbit Around Selection."""
    return bool(bpy.context.preferences.inputs.use_rotate_around_active)


STATES = {
    "object_mode": _object_mode, "view_perspective": _view_perspective,
    "view_axis": _view_axis, "orbit_selection": _orbit_selection,
}


def read_state(name):
    return STATES[name]()


def camera_move(x=0.0, y=0.0, forward=0.0):
    """Move the scene camera in metres along its own axes: x right, y up,
    forward along its view direction (a dolly; the lens is not touched)."""
    cam = bpy.context.scene.camera
    if cam is None:
        raise RuntimeError("the scene has no camera")
    delta = cam.matrix_world.to_3x3().normalized() @ Vector((x, y, -forward))
    cam.matrix_world = Matrix.Translation(delta) @ cam.matrix_world
    return {"FINISHED"}


def view_move(x=0.0, y=0.0):
    """Move the first 3D View's centre by (x, y) metres along the view's right/up
    (the same directions as view3d.view_pan PANRIGHT/PANUP, but in metres)."""
    rv3d = _region_3d()
    if rv3d is None:
        raise RuntimeError("no 3D View")
    rv3d.view_location += rv3d.view_rotation @ Vector((x, y, 0.0))
    return {"FINISHED"}


def view_projection(type):
    """Set the first 3D View to ORTHO or PERSP (leaves camera view, like Numpad 5)."""
    rv3d = _region_3d()
    if rv3d is None:
        raise RuntimeError("no 3D View")
    rv3d.view_perspective = type
    return {"FINISHED"}


def orbit_selection_toggle():
    """Toggle Preferences → Navigation → Orbit Around Selection.

    wm.context_toggle does the same but always returns {'CANCELLED'}
    (no undo step for preferences), which would show as an error.
    """
    inputs = bpy.context.preferences.inputs
    inputs.use_rotate_around_active = not inputs.use_rotate_around_active
    return {"FINISHED"}


def outliner_objects():
    """Selectable, visible objects of the view layer in Outliner order:
    collections depth first (child collections before objects), objects by name."""
    vl = bpy.context.view_layer
    out, seen = [], set()

    def walk(lc):
        if lc.exclude:
            return
        for child in lc.children:
            walk(child)
        for obj in sorted(lc.collection.objects, key=lambda o: o.name):
            if obj.name not in seen and obj.visible_get(view_layer=vl) and not obj.hide_select:
                seen.add(obj.name)
                out.append(obj)

    walk(vl.layer_collection)
    return out


_knob_anchor = {}  # knob control -> anchor index, set when the knob leaves its centre


def select_by_knob(value, knob="", center=knob_select.CENTER):
    """Select one object (and make it active) by a centre-tap knob's position.

    Leaving the centre anchors on the active selected object (or none); see
    knob_select.pick. Object Mode only.
    """
    if value == center:
        _knob_anchor.pop(knob, None)
        return {"FINISHED"}
    if _object_mode() not in ("OBJECT", "NONE"):
        raise RuntimeError("object selection works in Object Mode only")
    objs = outliner_objects()
    if knob not in _knob_anchor:
        active = bpy.context.view_layer.objects.active
        _knob_anchor[knob] = objs.index(active) if active in objs and active.select_get() else None
    i = knob_select.pick(len(objs), _knob_anchor[knob], value, center)
    if i is None:
        return {"FINISHED"}
    target = objs[i]
    if bpy.context.view_layer.objects.active is not target or len(bpy.context.selected_objects) != 1:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
    return {"FINISHED"}


ACTIONS = {
    "select_by_knob": select_by_knob,
    "camera_move": camera_move, "view_move": view_move,
    "view_projection": view_projection, "orbit_selection_toggle": orbit_selection_toggle,
}


def _redraw():
    """Tag every area for redraw: changes made from a timer (selection,
    preferences) send no notifier, so the screen would only update when the
    mouse moves over it."""
    wm = bpy.context.window_manager
    for win in (wm.windows if wm else ()):
        for area in win.screen.areas:
            area.tag_redraw()


def run_action(name, args):
    try:
        return ACTIONS[name](**args)
    finally:
        _redraw()


def _view3d():
    wm = bpy.context.window_manager
    for win in (wm.windows if wm else ()):
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        return win, area, region
    return None


def run_operator(name, args, call="EXEC_DEFAULT"):
    """Run bpy.ops.<name>(**args) in a 3D View context.

    call is Blender's execution context: EXEC_DEFAULT, or INVOKE_DEFAULT for
    operators that only have an invoke (e.g. view3d.view_pan), which otherwise
    fail with "Invalid operator call".
    """
    module, op_name = name.split(".", 1)
    op = getattr(getattr(bpy.ops, module), op_name)
    place = _view3d()
    if place:
        win, area, region = place
        with bpy.context.temp_override(window=win, area=area, region=region):
            return op(call, **args)
    return op(call, **args)  # background / no 3D View


class Session:
    """One open controller. midi_in/midi_out are injectable for tests."""

    def __init__(self, mapping_path=DEFAULT_MAPPING, midi_in=None, midi_out=None, intro=True):
        self.queue = queue.SimpleQueue()
        mapping = Mapping.load(mapping_path)
        profile = Profile.load(HERE / "devices" / f"{mapping.device}.json")
        mapping.validate(profile, set(STATES), set(ACTIONS))
        self.port_names = ("", "")
        if midi_in is None or midi_out is None:
            from . import winmm

            ins, outs = winmm.list_ports()
            i, o = winmm.find_port(ins, profile.port_name_contains), winmm.find_port(outs, profile.port_name_contains)
            if i is None or o is None:
                raise winmm.MidiError(
                    f"{profile.device} not found. Inputs: {ins or 'none'}; outputs: {outs or 'none'}"
                )
            midi_out = winmm.MidiOut(o)
            try:
                midi_in = winmm.MidiIn(i, lambda *m: self.queue.put(m))
            except Exception:
                midi_out.close()
                raise
            self.port_names = (ins[i], outs[o])
        self.midi_in, self.midi_out = midi_in, midi_out
        self.engine = Engine(
            profile, mapping, midi_out.send, run_operator, read_state,
            lambda: int(time.monotonic() * 1000), run_action,
        )
        if intro:
            self.engine.start_intro()
        self.device = profile.device

    def tick(self):
        for _ in range(MAX_MESSAGES_PER_TICK):
            try:
                msg = self.queue.get_nowait()
            except queue.Empty:
                break
            self.engine.handle(*msg)
        self.engine.update()

    def close(self):
        try:
            self.engine.shutdown()
        finally:
            self.midi_in.close()
            self.midi_out.close()


_session = None
_status = "Disconnected"


def _timer():
    global _status
    if _session is None:
        return None
    try:
        _session.tick()
    except Exception as e:  # keep Blender alive; show it in the panel
        _status = f"Error: {e}"
    return TICK_S


def connect(**kwargs):
    global _session, _status
    disconnect()
    _knob_anchor.clear()
    _session = Session(**kwargs)
    _status = f"Connected: {_session.device}"
    if not bpy.app.timers.is_registered(_timer):
        bpy.app.timers.register(_timer, first_interval=0.0, persistent=True)
    return _session


def disconnect():
    global _session, _status
    if bpy.app.timers.is_registered(_timer):
        bpy.app.timers.unregister(_timer)
    if _session is not None:
        s, _session = _session, None
        s.close()
    _status = "Disconnected"


class CONTROLSURFACE_OT_connect(bpy.types.Operator):
    bl_idname = "control_surface.connect"
    bl_label = "Connect"
    bl_description = "Open the controller's MIDI ports and start the mapping"

    def execute(self, context):
        global _status
        try:
            connect()
        except Exception as e:
            _status = f"Error: {e}"
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class CONTROLSURFACE_OT_disconnect(bpy.types.Operator):
    bl_idname = "control_surface.disconnect"
    bl_label = "Disconnect"
    bl_description = "Turn the LEDs off and release the MIDI ports"

    def execute(self, context):
        disconnect()
        return {"FINISHED"}


class CONTROLSURFACE_PT_panel(bpy.types.Panel):
    bl_label = "Control Surface"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DJ-Tech"

    def draw(self, context):
        col = self.layout.column()
        col.label(text=_status)
        if _session is None:
            col.operator(CONTROLSURFACE_OT_connect.bl_idname, icon="PLUGIN")
        else:
            col.operator(CONTROLSURFACE_OT_disconnect.bl_idname, icon="CANCEL")
            layers = _session.engine.layers
            if layers:
                col.label(text="  ".join(f"{k}: {v}" for k, v in layers.items()))
            for name, value in _session.engine.scales.items():
                col.label(text=f"{name}: {value * 100:.1f} cm")
            if _session.engine.last_error:
                col.label(text=_session.engine.last_error, icon="ERROR")


CLASSES = (CONTROLSURFACE_OT_connect, CONTROLSURFACE_OT_disconnect, CONTROLSURFACE_PT_panel)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    disconnect()  # release the ports, or they stay locked until Blender quits
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
