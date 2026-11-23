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

from . import add_menu, adjust, grab, grid_sizes, knob_select, menu_window, props_menu, snap, tour

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
    "cursor_axis": lambda: _cursor_axis,
    "cursor_pick": lambda: cursor_pick(),
    "snap_mode": lambda: snap.mode(),
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


# --- 3D cursor (deck A, task 43) ----------------------------------------------

_cursor_axis = "NONE"  # X / Y / Z: the axis the left platter (deck A) moves the 3D cursor along


def cursor_to_mouse():
    """1 (deck A): the 3D cursor to the mouse, like Shift + right click."""
    return run_operator("control_surface.cursor_to_mouse", {}, "INVOKE_DEFAULT")


CUP_AGAIN_S = 3.0        # a second CUP within this enters the vertex pick
PULSES_PER_VERTEX = 390 / 27  # ~14 platter pulses per vertex, like the menus
_cup_at = None           # when CUP (deck A) last sent the cursor to the active object
_pick = None             # {"points": [Vector], "index": int, "acc": float} while picking a vertex


def _active_vertices():
    """World positions of the active mesh's vertices (Edit Mode: its edit mesh;
    else the evaluated mesh, modifiers included)."""
    import numpy as np
    obj = bpy.context.view_layer.objects.active
    if obj is None or obj.type != "MESH":
        raise RuntimeError("the active object is not a mesh")
    if obj.mode == "EDIT":
        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        co = np.array([v.co for v in bm.verts], dtype=np.float64).reshape(-1, 3)
    else:
        me = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
    m = np.array(obj.matrix_world, dtype=np.float64)
    return co @ m[:3, :3].T + m[:3, 3]


def cursor_pick():
    return _pick is not None


def cursor_cup():
    """CUP (deck A): the 3D cursor to the active object; CUP again within 3 s:
    pick one of its vertices with the platter (CUP blinks); CUP again: done,
    the cursor stays there."""
    global _cup_at, _pick
    if _pick is not None:
        _pick = None
        return {"FINISHED"}
    now = time.monotonic()
    if _cup_at is not None and now - _cup_at <= CUP_AGAIN_S:
        _cup_at = None
        co = _active_vertices()
        order = tour.vertex_tour(co, bpy.context.scene.cursor.location)
        if not order:
            raise RuntimeError("the active object has no vertices")
        _pick = {"points": [Vector(co[i]) for i in order], "index": 0, "acc": 0.0}
        bpy.context.scene.cursor.location = _pick["points"][0]
        _redraw()
        return {"FINISHED"}
    _cup_at = now
    return run_operator("view3d.snap_cursor_to_active", {})


def cursor_pick_step(pulses):
    """Left platter (deck A) while picking: the cursor to the next / previous vertex."""
    if _pick is None:
        return {"FINISHED"}
    sign = 1 if pulses > 0 else -1
    if _pick["acc"] * sign < 0:
        _pick["acc"] = 0.0
    _pick["acc"] += sign
    n = int(_pick["acc"] / PULSES_PER_VERTEX)
    if n:
        _pick["acc"] -= n * PULSES_PER_VERTEX
        pts = _pick["points"]
        _pick["index"] = (_pick["index"] + n) % len(pts)
        bpy.context.scene.cursor.location = pts[_pick["index"]]
        _redraw()
    return {"FINISHED"}


def cursor_axis_toggle(axis):
    """2/3/4 (deck A): the platter moves the 3D cursor along X/Y/Z; the same button again: off."""
    global _cursor_axis
    _cursor_axis = "NONE" if _cursor_axis == axis else axis
    return {"FINISHED"}


_cursor_free = None  # (axis index, unsnapped coordinate, coordinate shown) of the grid walk


def cursor_move(amount):
    """Left platter (deck A): the 3D cursor along the chosen global axis, in metres.
    Grid snapping (VINYL lit): the platter moves an unsnapped coordinate and the
    cursor shows it rounded to the viewport grid (`grid_size`, S2 VOL), so a
    1 cm step still crosses a 1 m grid."""
    global _cursor_free
    if _cursor_axis not in ("X", "Y", "Z"):
        return {"FINISHED"}
    loc = bpy.context.scene.cursor.location
    i = "XYZ".index(_cursor_axis)
    if snap.mode() == "grid":
        if _cursor_free is None or _cursor_free[0] != i or abs(_cursor_free[2] - loc[i]) > 1e-9:
            _cursor_free = (i, loc[i], loc[i])   # the cursor was moved by something else
        free = _cursor_free[1] + amount
        loc[i] = snap.round_to(free, grid_size())
        _cursor_free = (i, free, loc[i])
    else:
        loc[i] += amount
        _cursor_free = None
    _redraw()
    return {"FINISHED"}


# --- Grid size (task 50): S2 VOL sets the 3D Views' grid scale ---------------

_grid_index = None      # index into grid_sizes.SIZES last set from S2 VOL
_grid_note = None       # (text, until monotonic) shown in the viewports
_grid_note_handle = None
GRID_NOTE_S = 1.5


def _view3d_spaces():
    wm = bpy.context.window_manager
    for win in (wm.windows if wm else ()):
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                yield area.spaces.active


def grid_size():
    """The viewport grid (Blender's overlay grid scale) of the 3D View in the
    context, else of the first one; 1 m without a 3D View."""
    space = getattr(bpy.context, "space_data", None)
    if space is None or getattr(space, "type", "") != "VIEW_3D":
        space = next(_view3d_spaces(), None)
    return space.overlay.grid_scale if space is not None else 1.0


def grid_set(value):
    """S2 VOL (value 0..127) → grid scale of every 3D View, from grid_sizes.SIZES."""
    global _grid_index
    current = _grid_index if _grid_index is not None else grid_sizes.nearest(grid_size())
    i = grid_sizes.pick(value, current)
    size = grid_sizes.SIZES[i]
    changed = i != _grid_index or any(abs(sp.overlay.grid_scale - size) > 1e-9
                                      for sp in _view3d_spaces())
    _grid_index = i
    if changed:
        for sp in _view3d_spaces():
            sp.overlay.grid_scale = size
        _grid_note_show(f"grid: {grid_sizes.label(size)}")
    return {"FINISHED"}


def _draw_grid_note():
    import blf
    note = _grid_note
    if note is None or time.monotonic() > note[1]:
        return
    font = 0
    blf.size(font, 16 * bpy.context.preferences.system.ui_scale)
    blf.color(font, 1.0, 0.6, 0.1, 1.0)
    blf.position(font, 20, 44 * bpy.context.preferences.system.ui_scale, 0)
    blf.draw(font, note[0])


def _grid_note_show(text):
    global _grid_note, _grid_note_handle
    _grid_note = (text, time.monotonic() + GRID_NOTE_S)
    if _grid_note_handle is None:
        _grid_note_handle = bpy.types.SpaceView3D.draw_handler_add(_draw_grid_note, (), "WINDOW", "POST_PIXEL")
        bpy.app.timers.register(_grid_note_check, first_interval=0.25)


def _grid_note_check():
    global _grid_note, _grid_note_handle
    if _grid_note is not None and time.monotonic() <= _grid_note[1]:
        return 0.25
    _grid_note = None
    if _grid_note_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_grid_note_handle, "WINDOW")
        _grid_note_handle = None
    _redraw()
    return None


def step_value():
    """The `step` scale (S1 VOL), 0.01 m without a session."""
    if _session is None:
        return 0.01
    return _session.engine.scales.get("step", 0.01)


class CONTROLSURFACE_OT_cursor_to_mouse(bpy.types.Operator):
    """The 3D cursor to the mouse (Blender's Shift + right click), from the controller"""
    bl_idname = "control_surface.cursor_to_mouse"
    bl_label = "3D Cursor to Mouse"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        # Invoked from the timer: the event is the window's last known mouse
        # position. Blender's own operator needs the 3D View region under it.
        mx, my = event.mouse_x, event.mouse_y
        for area in context.window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for region in area.regions:
                if (region.type == "WINDOW" and region.x <= mx < region.x + region.width
                        and region.y <= my < region.y + region.height):
                    with context.temp_override(area=area, region=region):
                        result = bpy.ops.view3d.cursor3d("INVOKE_DEFAULT")
                    if snap.mode() == "geometry":  # VINYL blinking: onto the vertex/edge/face under the mouse
                        rv3d = area.spaces.active.region_3d
                        xy = (mx - region.x, my - region.y)
                        targets = snap.Targets(context, edit_unselected=True)
                        hit = targets.find(context, region, rv3d, xy, snap.elements())
                        if hit is not None:
                            context.scene.cursor.location = hit[0]
                    return result
        self.report({"WARNING"}, "the mouse is not over a 3D View")
        return {"CANCELLED"}


def move_start(axis):
    """1-4 with no tool armed: a move grab; the other tools go off."""
    grab.end_tools()
    return grab_start("MOVE", axis)


_delete_armed = None  # (mode, selection) when OUT was pressed once, else None
_delete_armed_at = 0.0
DELETE_ARMED_S = 5.0  # the armed delete ends by itself after this (Rafael, 2026-11-22)


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
    if _delete_armed is not None and (_delete_armed != _selection_key()
                                      or time.monotonic() - _delete_armed_at > DELETE_ARMED_S):
        _delete_armed = None
    return _delete_armed is not None


def delete_arm():
    """OUT, first press: arm the delete (OUT blinks); the second press deletes."""
    global _delete_armed, _delete_armed_at
    grab.end_tools()
    _delete_armed = _selection_key()
    _delete_armed_at = time.monotonic()
    return {"FINISHED"}


def on_event(cid, event):
    """Every decoded event of the owning Blender, before its bindings: any key
    other than an OUT (on any deck, platter touches excepted) disarms the delete."""
    if (_delete_armed is not None and event == "press" and not cid.startswith("OUT ")
            and not cid.endswith(" touch")):
        _delete_disarm()


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


LONG_PRESS_S = 0.5
_props_out_at = None  # when OUT (deck B) went down, while the Properties menu is open


def _props_out_down():
    global _props_out_at
    _props_out_at = time.monotonic()
    return {"FINISHED"}


_add_out_at = None  # when OUT (deck A) went down, while the Add menu is open


def _add_out_down():
    global _add_out_at
    _add_out_at = time.monotonic()
    return {"FINISHED"}


def _add_out_up():
    """OUT (deck A) released: held >= 0.5 s closes the Add menu; a short press goes back."""
    global _add_out_at
    held = time.monotonic() - _add_out_at if _add_out_at is not None else 0.0
    _add_out_at = None
    return add_menu.close_all() if held >= LONG_PRESS_S else add_menu.back()


def _props_out_up():
    """OUT released: held >= 0.5 s closes the menu; a short press goes one level back."""
    global _props_out_at
    held = time.monotonic() - _props_out_at if _props_out_at is not None else 0.0
    _props_out_at = None
    return props_menu.close_all() if held >= LONG_PRESS_S else props_menu.cancel()


ACTIONS = {
    "props_toggle": lambda: props_menu.toggle(),
    "props_step": lambda pulses, amount=0.01: props_menu.step(pulses, amount),
    "props_cancel": lambda: props_menu.cancel(),
    "props_close": lambda: props_menu.close_all(),
    "props_out_down": lambda: _props_out_down(),
    "props_out_up": lambda: _props_out_up(),
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
    "add_menu_close": lambda: add_menu.close_all(),
    "add_out_down": lambda: _add_out_down(),
    "add_out_up": lambda: _add_out_up(),
    "delete_selected": delete_selected,
    "delete_arm": delete_arm,
    "delete_confirm": delete_confirm,
    "tool_toggle": tool_toggle,
    "move_start": move_start,
    "cursor_to_mouse": cursor_to_mouse,
    "cursor_axis_toggle": cursor_axis_toggle,
    "cursor_move": cursor_move,
    "grid_set": grid_set,
    "cursor_cup": cursor_cup,
    "cursor_pick_step": cursor_pick_step,
    "snap_cycle": lambda: snap.cycle(),
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
        self.engine.on_event = on_event
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
            col.label(text=f"grid (S2 VOL): {grid_sizes.label(grid_size())}")
            if _session.engine.last_error:
                col.label(text=_session.engine.last_error, icon="ERROR")


CLASSES = grab.CLASSES + menu_window.CLASSES + (CONTROLSURFACE_OT_cursor_to_mouse, CONTROLSURFACE_OT_debug, CONTROLSURFACE_OT_connect, CONTROLSURFACE_OT_disconnect, CONTROLSURFACE_PT_panel)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    disconnect()
    grab.end_tools()
    add_menu.close()
    props_menu.close()
    menu_window.close()  # release the ports, or they stay locked until Blender quits
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
