"""The add-on's own grab / scale: a modal operator driven by the mouse AND
by the controller.

Blender's own G/S can't be used: it recomputes the objects from the mouse on
every move (a platter push would be lost), and nothing outside it can confirm
it. This one:
- follows the mouse like G (free: in the view plane; X/Y/Z: along that
  global axis) or like S (factor = mouse distance to the pivot / start
  distance; uniform, or one axis);
- adds the controller's pushes (`push`) on top of the mouse;
- ends with left click / Enter (confirm), right click / Esc (cancel), or
  `request("confirm")` from the controller;
- Object Mode, every selected object; scale around their median point.

`state()` is what the LEDs read: None, or {"axis": ..., "mode": ...}.
"""

import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

AXES = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
TIMER_S = 0.02

_running = None  # the running operator's shared state, or None


def state():
    return None if _running is None else {"axis": _running["axis"], "mode": _running["mode"]}


def request(what, **kw):
    """From the controller: confirm / cancel / axis=<A> / push."""
    if _running is None:
        raise RuntimeError("no grab running")
    if what == "axis":
        _running["axis"] = kw["axis"]
    elif what == "push":
        _running["pushes"].append((kw["amount"], kw.get("along", "right")))
    else:
        _running["end"] = what
    return {"FINISHED"}


class CONTROLSURFACE_OT_grab(bpy.types.Operator):
    bl_idname = "control_surface.grab"
    bl_label = "Grab / Scale (control surface)"
    bl_description = "Move or scale the selected objects with the mouse and the controller"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    mode: bpy.props.EnumProperty(items=[("MOVE", "Move", ""), ("SCALE", "Scale", "")])
    axis: bpy.props.EnumProperty(items=[(a, a, "") for a in ("FREE", "X", "Y", "Z")])

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and context.selected_objects and context.region_data

    def invoke(self, context, event):
        global _running
        if _running is not None:
            self.report({"WARNING"}, "a grab is already running")
            return {"CANCELLED"}
        self.objs = list(context.selected_objects)
        self.start = {o.name: (o.matrix_world.translation.copy(), o.scale.copy()) for o in self.objs}
        self.pivot = sum((p for p, _ in self.start.values()), Vector()) / len(self.objs)
        self.region, self.rv3d = context.region, context.region_data
        # The mouse start is its first real move: invoked from the controller's
        # timer, the event's position can be stale (e.g. the mouse on another
        # window), and the objects must not jump.
        self.mouse0 = self.mouse = None
        self.push_move = Vector()
        self.push_scale = 1.0
        _running = {"axis": self.axis, "mode": self.mode, "pushes": [], "end": None}
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

    def _apply(self):
        axis = _running["axis"]
        moved = self.mouse0 is not None
        if _running["mode"] == "MOVE":
            d = self.push_move.copy()
            if moved:
                d += self._plane_point(self.mouse) - self._plane_point(self.mouse0)
            if axis != "FREE":
                d = AXES[axis] * d.dot(AXES[axis])
            for o in self.objs:
                self._set_world_location(o, self.start[o.name][0] + d)
        else:
            f = self.push_scale
            c = view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, self.pivot)
            if moved and c is not None and (self.mouse0 - c).length > 1:
                f *= (self.mouse - c).length / (self.mouse0 - c).length
            k = Vector((f, f, f)) if axis == "FREE" else Vector([f if a == axis else 1.0 for a in "XYZ"])
            for o in self.objs:
                p0, s0 = self.start[o.name]
                o.scale = Vector([a * b for a, b in zip(s0, k)])
                self._set_world_location(o, self.pivot + Vector([a * b for a, b in zip(p0 - self.pivot, k)]))

    def _take_pushes(self):
        for amount, along in _running["pushes"]:
            if _running["mode"] == "SCALE":
                self.push_scale *= max(0.01, 1.0 + amount)
                continue
            axis = _running["axis"]
            if axis != "FREE":
                self.push_move += AXES[axis] * amount
            else:
                v = Vector((1, 0, 0)) if along == "right" else Vector((0, 1, 0))
                self.push_move += (self.rv3d.view_rotation @ v) * amount
        _running["pushes"].clear()

    def _end(self, context, confirm):
        global _running
        context.window_manager.event_timer_remove(self.timer)
        if not confirm:
            for o in self.objs:
                o.scale = self.start[o.name][1]
                self._set_world_location(o, self.start[o.name][0])
        _running = None
        for area in context.window.screen.areas:
            area.tag_redraw()
        return {"FINISHED"} if confirm else {"CANCELLED"}

    def modal(self, context, event):
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
        if _running["end"]:
            return self._end(context, _running["end"] == "confirm")
        self._take_pushes()
        self._apply()
        context.area.tag_redraw() if context.area else None
        return {"RUNNING_MODAL"}


CLASSES = (CONTROLSURFACE_OT_grab,)
