"""The add-on's own grab / scale / rotate, and the deck's transform tools.

Blender's own G/S/R can't be used: they recompute the objects from the mouse
on every move (a platter push would be lost), and nothing outside them can
confirm them. The modal operator here:
- follows the mouse like G (free: in the view plane; X/Y/Z: along that
  global axis), like S (factor = mouse distance to the pivot / start
  distance; uniform, or one axis) or like R (the mouse's angle around the
  pivot; free: around the view axis, or around a global axis);
- adds the controller's pushes (`push`) on top of the mouse;
- ends with left click / Enter (confirm), right click / Esc (cancel), or
  `request("confirm")` from the controller;
- Object Mode, every selected object, around their median point.

**Tools** (one at a time per deck, Rafael 2026-11-21): SYNC (the platter
moves the view: `sync` off/on/blink), MOVE (a grab from 1-4), SCALE (RE) and
ROTATE (IN). SCALE/ROTATE stay armed after their grab ends, until the
selection changes. Turning one tool on turns the others off and confirms a
running grab.
"""

import math

import bpy
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

AXES = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
TIMER_S = 0.02
DEG_PER_PUSH_UNIT = 100.0  # a rotate push of `step` (0.01-0.10) = 1-10 degrees
ARMABLE = ("SCALE", "ROTATE")
SYNC_VALUES = ("off", "on", "blink")

_running = None  # the running grab's shared state, or None
_armed = None    # {"mode": SCALE/ROTATE, "selection": names when armed}, or None
_sync = "off"


def _selection():
    return frozenset(o.name for o in bpy.context.selected_objects)


def state():
    return None if _running is None else {"axis": _running["axis"], "mode": _running["mode"]}


def tool_mode(mode):
    """OFF / RUNNING (its grab runs) / ARMED (on, no grab) for SCALE or ROTATE.

    An armed tool turns off as soon as the selection differs from the one it
    was armed with (another object selected, or none).
    """
    global _armed
    if _armed is None or _armed["mode"] != mode:
        return "OFF"
    if _running is not None:
        return "RUNNING" if _running["mode"] == mode else "ARMED"
    if _selection() != _armed["selection"]:
        _armed = None
        return "OFF"
    return "ARMED"


def sync_mode():
    return _sync


def end_tools(keep=None):
    """Turn every tool off except `keep`; confirm a running grab."""
    global _armed, _sync
    if _running is not None:
        request("confirm")
    if keep != "SYNC":
        _sync = "off"
    if keep not in ARMABLE:
        _armed = None


def arm(mode):
    global _armed
    _armed = {"mode": mode, "selection": _selection()}


def sync_cycle():
    """SYNC: off -> on -> blink -> off; on turns the other tools off."""
    global _sync
    new = SYNC_VALUES[(SYNC_VALUES.index(_sync) + 1) % len(SYNC_VALUES)]
    if new != "off":
        end_tools(keep="SYNC")
    _sync = new
    return {"FINISHED"}


def request(what, **kw):
    """From the controller: confirm / cancel / axis=<A> / push.

    confirm/cancel detach the grab at once (a new one may start right away);
    its operator ends on its next tick.
    """
    global _running
    if _running is None:
        raise RuntimeError("no grab running")
    if what == "axis":
        _running["axis"] = kw["axis"]
    elif what == "push":
        _running["pushes"].append((kw["amount"], kw.get("along", "right")))
    else:
        _running["end"] = what
        _running = None
    return {"FINISHED"}


class CONTROLSURFACE_OT_grab(bpy.types.Operator):
    bl_idname = "control_surface.grab"
    bl_label = "Grab / Scale / Rotate (control surface)"
    bl_description = "Move, scale or rotate the selected objects with the mouse and the controller"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    mode: bpy.props.EnumProperty(items=[(m, m.title(), "") for m in ("MOVE", "SCALE", "ROTATE")])
    axis: bpy.props.EnumProperty(items=[(a, a, "") for a in ("FREE", "X", "Y", "Z")])

    @classmethod
    def poll(cls, context):
        if context.mode != "OBJECT":
            cls.poll_message_set("grab/scale/rotate works in Object Mode only")
            return False
        if not context.selected_objects:
            cls.poll_message_set("select an object first")
            return False
        return context.region_data is not None

    def invoke(self, context, event):
        global _running
        if _running is not None:
            self.report({"WARNING"}, "a grab is already running")
            return {"CANCELLED"}
        context.view_layer.update()  # matrix_world current after a grab that just ended
        self.objs = list(context.selected_objects)
        self.start = {o.name: (o.matrix_world.translation.copy(), o.scale.copy(), o.matrix_world.copy())
                      for o in self.objs}
        self.pivot = sum((s[0] for s in self.start.values()), Vector()) / len(self.objs)
        self.region, self.rv3d = context.region, context.region_data
        # The mouse start is its first real move: invoked from the controller's
        # timer, the event's position can be stale (e.g. the mouse on another
        # window), and the objects must not jump.
        self.mouse0 = self.mouse = None
        self.push_move = Vector()
        self.push_scale = 1.0
        self.push_angle = 0.0
        self.shared = _running = {"axis": self.axis, "mode": self.mode, "pushes": [], "end": None}
        self.timer = context.window_manager.event_timer_add(TIMER_S, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _mouse(self, event):
        return Vector((event.mouse_x - self.region.x, event.mouse_y - self.region.y))

    def _plane_point(self, xy):
        return view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, xy, self.pivot)

    @staticmethod
    def _set_world_location(o, p):
        """Place o's origin at world point p via its location (not matrix_world,
        which is stale right after a scale change and would undo it)."""
        if o.parent:
            p = (o.parent.matrix_world @ o.matrix_parent_inverse).inverted() @ p
        o.location = p

    def _pivot_2d(self):
        return view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, self.pivot)

    def _apply(self):
        axis, mode = self.shared["axis"], self.shared["mode"]
        moved = self.mouse0 is not None
        if mode == "MOVE":
            d = self.push_move.copy()
            if moved:
                d += self._plane_point(self.mouse) - self._plane_point(self.mouse0)
            if axis != "FREE":
                d = AXES[axis] * d.dot(AXES[axis])
            for o in self.objs:
                self._set_world_location(o, self.start[o.name][0] + d)
        elif mode == "SCALE":
            f = self.push_scale
            c = self._pivot_2d()
            if moved and c is not None and (self.mouse0 - c).length > 1:
                f *= (self.mouse - c).length / (self.mouse0 - c).length
            k = Vector((f, f, f)) if axis == "FREE" else Vector([f if a == axis else 1.0 for a in "XYZ"])
            for o in self.objs:
                p0, s0, _ = self.start[o.name]
                o.scale = Vector([a * b for a, b in zip(s0, k)])
                self._set_world_location(o, self.pivot + Vector([a * b for a, b in zip(p0 - self.pivot, k)]))
        else:  # ROTATE
            toward_viewer = self.rv3d.view_rotation @ Vector((0, 0, 1))
            rot_axis = toward_viewer if axis == "FREE" else AXES[axis]
            angle = self.push_angle
            c = self._pivot_2d()
            if moved and c is not None and min((self.mouse0 - c).length, (self.mouse - c).length) > 1:
                a = math.atan2(*(self.mouse - c).yx) - math.atan2(*(self.mouse0 - c).yx)
                # Counter-clockwise on screen turns counter-clockwise as seen by the viewer.
                angle += a if rot_axis.dot(toward_viewer) >= 0 else -a
            m = (Matrix.Translation(self.pivot) @ Matrix.Rotation(angle, 4, rot_axis)
                 @ Matrix.Translation(-self.pivot))
            for o in self.objs:
                o.matrix_world = m @ self.start[o.name][2]

    def _take_pushes(self):
        for amount, along in self.shared["pushes"]:
            mode, axis = self.shared["mode"], self.shared["axis"]
            if mode == "SCALE":
                self.push_scale *= max(0.01, 1.0 + amount)
            elif mode == "ROTATE":
                self.push_angle += math.radians(amount * DEG_PER_PUSH_UNIT)
            elif axis != "FREE":
                self.push_move += AXES[axis] * amount
            else:
                v = Vector((1, 0, 0)) if along == "right" else Vector((0, 1, 0))
                self.push_move += (self.rv3d.view_rotation @ v) * amount
        self.shared["pushes"].clear()

    def _end(self, context, confirm):
        global _running
        context.window_manager.event_timer_remove(self.timer)
        if not confirm:
            for o in self.objs:
                o.matrix_world = self.start[o.name][2]
        if _running is self.shared:
            _running = None
        for area in context.window.screen.areas:
            area.tag_redraw()
        return {"FINISHED"} if confirm else {"CANCELLED"}

    def modal(self, context, event):
        if self.shared["end"]:  # ended by the controller
            return self._end(context, self.shared["end"] == "confirm")
        if event.type == "MOUSEMOVE":
            self.mouse = self._mouse(event)
            if self.mouse0 is None:
                self.mouse0 = self.mouse
        elif event.type in {"LEFTMOUSE", "RET", "NUMPAD_ENTER"} and event.value == "PRESS":
            return self._end(context, True)
        elif event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            return self._end(context, False)
        elif event.type in {"MIDDLEMOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE"}:
            return {"PASS_THROUGH"}  # navigate the view while grabbing
        self._take_pushes()
        self._apply()
        if context.area:
            context.area.tag_redraw()
        return {"RUNNING_MODAL"}


CLASSES = (CONTROLSURFACE_OT_grab,)
