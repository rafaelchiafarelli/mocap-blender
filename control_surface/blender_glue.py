"""Blender side: connect/disconnect operators, sidebar panel, the timer.

Incoming MIDI arrives on a WinMM thread and only goes into a queue; a
bpy.app timer (every 20 ms, main thread) drains it into the engine and drives
the LEDs, because bpy must not be called from other threads.
"""

import queue
import time
from pathlib import Path

import bpy

from .engine import Engine, Mapping
from .profile import Profile

HERE = Path(__file__).resolve().parent
DEFAULT_MAPPING = HERE / "mappings" / "blender_modes.json"
TICK_S = 0.02
MAX_MESSAGES_PER_TICK = 256


def _object_mode():
    obj = bpy.context.view_layer.objects.active
    return obj.mode if obj else "NONE"


STATES = {"object_mode": _object_mode}


def read_state(name):
    return STATES[name]()


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

    def __init__(self, mapping_path=DEFAULT_MAPPING, midi_in=None, midi_out=None):
        self.queue = queue.SimpleQueue()
        mapping = Mapping.load(mapping_path)
        profile = Profile.load(HERE / "devices" / f"{mapping.device}.json")
        mapping.validate(profile, set(STATES))
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
            lambda: int(time.monotonic() * 1000),
        )
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
