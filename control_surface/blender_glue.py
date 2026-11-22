"""Blender side: connect/disconnect operators, sidebar panel, the timer.

Incoming MIDI arrives on a WinMM thread and only goes into a queue; a
bpy.app timer (every 20 ms, main thread) drains it into the engine and drives
the LEDs, because bpy must not be called from other threads.
"""

import os
import queue
import tempfile
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from . import add_menu, adjust, grab, knob_select, props_menu

grab.END_TOOLS_HOOKS.append(adjust.end)
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


def _grab_axis():
    g = grab.state()
    return g["axis"] if g else "NONE"


STATES = {
    "grabbing": lambda: grab.state() is not None,
    "scale_mode": lambda: grab.tool_mode("SCALE"),
    "rotate_mode": lambda: grab.tool_mode("ROTATE"),
    "grab_snap": grab.snap_on,
    "props_menu": props_menu.is_open,
    "props_editing": props_menu.editing,
    "delete_armed": lambda: delete_armed(),
    "adjusting": adjust.adjusting,
    "adjust_active": adjust.active,
    "mesh_select_mode": lambda: _mesh_select_mode(),
    "sync_mode": grab.sync_mode,
    "cage": grab.cage_on,
    "add_menu": add_menu.is_open,
    "grab_axis": _grab_axis,
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


def grab_start(mode="MOVE", axis="FREE"):
    """Start the add-on's grab/scale (grab.py), invoked in the 3D View."""
    return run_operator("control_surface.grab", {"mode": mode, "axis": axis}, "INVOKE_DEFAULT")


def tool_toggle(mode):
    """RE (SCALE) / IN (ROTATE): off -> the other tools off, this one armed,
    and a free grab of it starts at once; second press -> the cage on (SHIFT +
    platter picks its fixed point); third press -> off (a running grab is
    confirmed)."""
    if grab.tool_mode(mode) != "OFF":
        if not grab.cage_on():  # second press: the cage on
            grab.cage_enable()
        else:                   # third press: off
            grab.end_tools()
        return {"FINISHED"}
    grab.end_tools()
    result = grab_start(mode, "FREE")
    if "RUNNING_MODAL" in result:
        grab.arm(mode)
    return result


def move_start(axis):
    """1-4 with no tool armed: a move grab; the other tools go off."""
    grab.end_tools()
    return grab_start("MOVE", axis)


_delete_armed = None  # (mode, selection) when OUT was pressed once, else None


def _selection_key():
    """What a delete would act on: the mode and the selected objects (or, in
    Edit Mode, the selected vertices' count per mesh)."""
    if bpy.context.mode == "EDIT_MESH":
        sel = tuple((o.name, o.data.total_vert_sel) for o in bpy.context.objects_in_mode_unique_data
                    if o.type == "MESH")
    else:
        sel = tuple(sorted(o.name for o in bpy.context.selected_objects))
    return bpy.context.mode, sel


def delete_armed():
    """True while OUT was pressed once and the selection has not changed."""
    global _delete_armed
    if _delete_armed is not None and _delete_armed != _selection_key():
        _delete_armed = None
    return _delete_armed is not None


def delete_arm():
    """OUT, first press: arm the delete (OUT blinks); the second press deletes."""
    global _delete_armed
    grab.end_tools()
    _delete_armed = _selection_key()
    return {"FINISHED"}


def _delete_disarm():
    global _delete_armed
    _delete_armed = None


grab.END_TOOLS_HOOKS.append(_delete_disarm)


def delete_confirm():
    """OUT, second press: delete."""
    global _delete_armed
    _delete_armed = None
    return delete_selected()


def delete_selected():
    """Delete the selected objects (no confirmation, like X > Delete); in mesh
    Edit Mode the selected vertices / edges / faces, by the select mode. The
    deck's tools end first: a running grab must not hold deleted data."""
    grab.end_tools()
    if bpy.context.mode == "EDIT_MESH":
        vert, edge, face = bpy.context.tool_settings.mesh_select_mode
        return run_operator("mesh.delete", {"type": "FACE" if face else "EDGE" if edge else "VERT"})
    return run_operator("object.delete", {"use_global": False, "confirm": False})


def add_menu_toggle():
    """Deck A IN: the Add menu (add_menu.py). Running an item ends the deck's tools first."""
    if add_menu.is_open():
        grab.end_tools()
    return add_menu.toggle()


# --- Mesh Edit Mode tools on deck C (task 32) ---------------------------------

def extrude_start():
    """CUP in Edit Mode: extrude the selection, then the add-on's grab along its normal."""
    grab.end_tools()
    result = run_operator("mesh.extrude_region", {})
    if "FINISHED" not in result:
        return result
    return grab_start("MOVE", "NORMAL")


def adjust_start(op, props, main, second=None):
    """Inset / Bevel in Edit Mode: run once, then the platter adjusts `main`
    (and SHIFT + platter `second`)."""
    grab.end_tools()
    return adjust.start(op, props, main, second)


def loopcut_start():
    """SHIFT + CUP in Edit Mode: one loop cut across the ring of the active (or
    first selected) edge; the platter then sets the number of cuts."""
    import bmesh

    grab.end_tools()
    obj = bpy.context.edit_object
    if obj is None or obj.type != "MESH":
        raise RuntimeError("loop cut needs a mesh in Edit Mode")
    bm = bmesh.from_edit_mesh(obj.data)
    act = bm.select_history.active
    edge = act if isinstance(act, bmesh.types.BMEdge) else next((e for e in bm.edges if e.select), None)
    if edge is None:
        raise RuntimeError("select an edge for the loop cut")
    objects = list(bpy.context.objects_in_mode_unique_data)
    return adjust.start("mesh.loopcut", {"number_cuts": 1, "edge_index": edge.index,
                                         "object_index": objects.index(obj) if obj in objects else 0},
                        "number_cuts")


SELECT_MODES = ("VERT", "EDGE", "FACE")


def _mesh_select_mode():
    if bpy.context.mode != "EDIT_MESH":
        return "NONE"
    v, e, f = bpy.context.tool_settings.mesh_select_mode
    return "FACE" if f else "EDGE" if e else "VERT"


def select_mode_cycle():
    """VINYL MODE (deck C) in Edit Mode: vertex -> edge -> face -> vertex."""
    cur = _mesh_select_mode()
    nxt = SELECT_MODES[(SELECT_MODES.index(cur) + 1) % 3] if cur in SELECT_MODES else "VERT"
    return run_operator("mesh.select_mode", {"type": nxt})


ACTIONS = {
    "props_toggle": lambda: props_menu.toggle(),
    "props_step": lambda pulses, amount=0.01: props_menu.step(pulses, amount),
    "props_cancel": lambda: props_menu.cancel(),
    "extrude_start": extrude_start,
    "adjust_start": adjust_start,
    "adjust_change": lambda which, amount: adjust.change(which, amount),
    "adjust_end": lambda: adjust.end(),
    "loopcut_start": loopcut_start,
    "select_mode_cycle": select_mode_cycle,
    "add_menu_toggle": add_menu_toggle,
    "add_menu_step": lambda pulses: add_menu.step(pulses),
    "add_menu_back": lambda: add_menu.back(),
    "add_menu_cancel": lambda: (add_menu.close(), {"FINISHED"})[1],
    "delete_selected": delete_selected,
    "delete_arm": delete_arm,
    "delete_confirm": delete_confirm,
    "tool_toggle": tool_toggle,
    "move_start": move_start,
    "sync_cycle": lambda: grab.sync_cycle(),
    "cage_step": lambda delta: grab.cage_step(delta),
    "rotate_tip": lambda pulses: grab.rotate_tip(pulses),
    "rotate_snap_on": lambda: grab.rotate_snap_on(),
    "grab_start": grab_start,
    "grab_confirm": lambda: grab.request("confirm"),
    "grab_axis": lambda axis: grab.request("axis", axis=axis),
    "grab_push": lambda amount, along="right": grab.request("push", amount=amount, along=along),
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


# --- Two Blenders on one controller ------------------------------------------
# Windows MIDI Services lets several programs open the 4-Mix at once (tested
# 2026-11-21), so two connected Blenders would both act and both drive the
# LEDs. The controller belongs to the Blender that was focused last: each one
# writes its pid to a shared file when its window is in the foreground.
OWNER_FILE = os.path.join(tempfile.gettempdir(), "control_surface_owner.txt")
DEBUG_LOG = os.path.join(tempfile.gettempdir(), "control_surface_midi.log")


def _foreground_is_me():
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
        return pid.value == os.getpid()
    except Exception:  # not Windows: always the owner
        return True


def owner_is_me():
    """Claim the controller when focused; True if this Blender owns it."""
    me = str(os.getpid())
    try:
        with open(OWNER_FILE, encoding="ascii") as f:
            owner = f.read().strip()
    except OSError:
        owner = ""
    if owner != me and (_foreground_is_me() or not owner):
        try:
            with open(OWNER_FILE, "w", encoding="ascii") as f:
                f.write(me)
            owner = me
        except OSError:
            pass
    return owner == me


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
        # Injected ports (tests) never share the controller with another Blender.
        self.owner = owner_is_me if self.port_names != ("", "") else (lambda: True)

        self.debug = None  # an open log file while debugging
        self._debug_state = None
        self._t0 = time.monotonic()

        def send(*m):  # only the owning Blender drives the LEDs
            if self.engine.active:
                midi_out.send(*m)
            self._log("OUT" if self.engine.active else "out(standby, not sent)", m)

        self.engine = Engine(
            profile, mapping, send, run_operator, read_state,
            lambda: int(time.monotonic() * 1000), run_action,
        )
        if intro:
            self.engine.start_intro()
        self.device = profile.device

    def _log(self, kind, m, extra=""):
        if self.debug is None:
            return
        names = ", ".join(f"{c} {e}" for c, e in self.engine.profile.decode(*m)) if kind == "IN" else ""
        if kind != "IN":
            names = ", ".join(c for c, sp in self.engine.profile.controls.items()
                              if sp.get("led") and tuple(sp["led"]) == (m[0], m[1]) and "+SHIFT" not in c)
        self.debug.write(f"{(time.monotonic() - self._t0) * 1000:9.0f} ms  {kind:<24} "
                         f"{m[0]:02X} {m[1]:02X} {m[2]:02X}  {names}{extra}\n")
        self.debug.flush()

    def set_debug(self, on):
        if on and self.debug is None:
            self.debug = open(DEBUG_LOG, "a", encoding="utf-8")
            self.debug.write(f"--- debug on, pid {os.getpid()}, {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._debug_state = None
        elif not on and self.debug is not None:
            self.debug.write("--- debug off\n")
            self.debug.close()
            self.debug = None

    def _log_state(self):
        if self.debug is None:
            return
        st = (f"owner={'yes' if self.engine.active else 'no'} sync={grab.sync_mode()} "
              f"scale={grab.tool_mode('SCALE')} rotate={grab.tool_mode('ROTATE')} cage={grab.cage_on()} "
              f"grab={_grab_axis()} layers={self.engine.layers}")
        if st != self._debug_state:
            self._debug_state = st
            self.debug.write(f"{(time.monotonic() - self._t0) * 1000:9.0f} ms  STATE  {st}\n")
            self.debug.flush()

    def tick(self):
        self.engine.set_active(self.owner())
        for _ in range(MAX_MESSAGES_PER_TICK):
            try:
                msg = self.queue.get_nowait()
            except queue.Empty:
                break
            self._log("IN", msg)
            self.engine.handle(*msg)
        if self.engine.active:
            try:
                adjust.flush()  # at most one undo + redo per tick
            except Exception as e:
                self.engine.last_error = f"adjust: {e}"
        self._log_state()
        self.engine.update()

    def close(self):
        self.set_debug(False)
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


class CONTROLSURFACE_OT_debug(bpy.types.Operator):
    bl_idname = "control_surface.debug"
    bl_label = "Debug log"
    bl_description = "Log every MIDI message in and out, and the tool states, to %TEMP%/control_surface_midi.log"

    def execute(self, context):
        if _session is not None:
            _session.set_debug(_session.debug is None)
        return {"FINISHED"}


class CONTROLSURFACE_PT_panel(bpy.types.Panel):
    bl_label = "Control Surface"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DJ-Tech"

    def draw(self, context):
        col = self.layout.column()
        col.label(text=_status)
        if _session is not None and not _session.engine.active:
            col.label(text="Standby: another Blender has the controller (click here to take it)", icon="PAUSE")
        if _session is None:
            col.operator(CONTROLSURFACE_OT_connect.bl_idname, icon="PLUGIN")
        else:
            col.operator(CONTROLSURFACE_OT_disconnect.bl_idname, icon="CANCEL")
            col.operator(CONTROLSURFACE_OT_debug.bl_idname,
                         text="Debug log: ON (click to stop)" if _session.debug else "Debug log: off",
                         icon="REC" if _session.debug else "TEXT")
            layers = _session.engine.layers
            if layers:
                col.label(text="  ".join(f"{k}: {v}" for k, v in layers.items()))
            col.label(text=(f"sync: {grab.sync_mode()}  scale: {grab.tool_mode('SCALE')}  "
                            f"rotate: {grab.tool_mode('ROTATE')}  cage: {grab.cage_on()}  "
                            f"grab: {_grab_axis()}  owner: {'yes' if _session.engine.active else 'no'}"))
            for name, value in _session.engine.scales.items():
                col.label(text=f"{name}: {value * 100:.1f} cm")
            if _session.engine.last_error:
                col.label(text=_session.engine.last_error, icon="ERROR")


CLASSES = grab.CLASSES + (CONTROLSURFACE_OT_debug, CONTROLSURFACE_OT_connect, CONTROLSURFACE_OT_disconnect, CONTROLSURFACE_PT_panel)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    disconnect()
    grab.end_tools()
    add_menu.close()
    props_menu.close()  # release the ports, or they stay locked until Blender quits
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
