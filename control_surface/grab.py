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

import bmesh
import bpy
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

AXES = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
TIMER_S = 0.02
DEG_PER_PUSH_UNIT = 100.0
# The 4-Mix platter sends ~390 pulses per turn, each +-1 whatever the speed
# (measured 2026-11-21, review/2026-11-21/teste-volta-platter.csv). One turn
# walks through all 27 cage points.
PLATTER_PULSES_PER_TURN = 390
CAGE_POINTS = 27
PULSES_PER_CAGE_POINT = PLATTER_PULSES_PER_TURN / CAGE_POINTS  # a rotate push of `step` (0.01-0.10) = 1-10 degrees
ARMABLE = ("SCALE", "ROTATE")
SYNC_VALUES = ("off", "on", "blink")

_running = None  # the running grab's shared state, or None
_armed = None    # {"mode": SCALE/ROTATE, "selection": names when armed}, or None
_sync = "off"
_cage_acc = 0.0  # platter pulses not yet turned into a cage step
_draw_handle = None


# --- Cage: a fixed point on the selection's box for SCALE / ROTATE ---------

def _edit_selection():
    """[(object, bmesh, selected verts)] of the meshes in Edit Mode."""
    out = []
    for o in bpy.context.objects_in_mode_unique_data:
        if o.type == "MESH":
            bm = bmesh.from_edit_mesh(o.data)
            verts = [v for v in bm.verts if v.select]
            if verts:
                out.append((o, bm, verts))
    return out


def _cage_points():
    """27 points of the selection's world-axis bounding box: centre, 6 face
    centres, 12 edge midpoints, 8 corners (in that order). In Edit Mode the
    box of the selected vertices, else of the selected objects."""
    if bpy.context.mode == "EDIT_MESH":
        corners = [o.matrix_world @ v.co for o, _, verts in _edit_selection() for v in verts]
    else:
        corners = [o.matrix_world @ Vector(c) for o in bpy.context.selected_objects for c in o.bound_box]
    if not corners:
        return []
    lo = Vector([min(c[i] for c in corners) for i in range(3)])
    hi = Vector([max(c[i] for c in corners) for i in range(3)])
    mid = (lo + hi) / 2
    pick = {-1: lo, 0: mid, 1: hi}
    offsets = [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)]
    offsets.sort(key=lambda o: sum(map(abs, o)))  # centre, faces, edges, corners
    return [Vector([pick[o[i]][i] for i in range(3)]) for o in offsets]


def cage_on():
    return _armed is not None and _armed.get("cage") is not None


def cage_point():
    pts = _cage_points()
    return pts[_armed["cage"] % len(pts)] if pts and cage_on() else None


def cage_step(delta):
    """SHIFT + platter pulse(s): one cage point every PULSES_PER_CAGE_POINT
    pulses (one turn = all 27 points); a running grab goes on from where it
    is, around the new point."""
    global _cage_acc
    if not cage_on():
        raise RuntimeError("no cage (press RE or IN a second time)")
    if _cage_acc * delta < 0:  # turned the other way: start counting again
        _cage_acc = 0.0
    _cage_acc += delta
    steps = int(_cage_acc / PULSES_PER_CAGE_POINT)
    if steps == 0:
        return {"FINISHED"}
    _cage_acc -= steps * PULSES_PER_CAGE_POINT
    _armed["cage"] = (_armed["cage"] + steps) % CAGE_POINTS
    if _running is not None:
        _running["rebase"] = True
    _tag_redraw()
    return {"FINISHED"}


def _cage_enable():
    global _draw_handle, _cage_acc
    _armed["cage"] = 0
    _cage_acc = 0.0
    if _running is not None:
        _running["rebase"] = True
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(_draw_cage, (), "WINDOW", "POST_VIEW")
    _tag_redraw()


def _cage_disable():
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
        _tag_redraw()


def _draw_cage():
    if not cage_on():
        return
    pts = _cage_points()
    if not pts:
        return
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    edges = [(0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7)]
    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(1.5)
    shader.uniform_float("color", (1.0, 0.6, 0.1, 0.8))
    batch_for_shader(shader, "LINES", {"pos": [c[i] for e in edges for i in e]}).draw(shader)
    gpu.state.point_size_set(5)
    shader.uniform_float("color", (1.0, 0.6, 0.1, 0.6))
    batch_for_shader(shader, "POINTS", {"pos": pts}).draw(shader)
    gpu.state.point_size_set(14)
    shader.uniform_float("color", (1.0, 1.0, 0.2, 1.0))
    batch_for_shader(shader, "POINTS", {"pos": [pts[_armed["cage"] % len(pts)]]}).draw(shader)
    gpu.state.point_size_set(1)
    gpu.state.line_width_set(1)
    gpu.state.blend_set("NONE")


def _tag_redraw():
    wm = bpy.context.window_manager
    for win in (wm.windows if wm else ()):
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


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
        _cage_disable()
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
        _cage_disable()


def arm(mode):
    global _armed
    _armed = {"mode": mode, "selection": _selection(), "cage": None}


def cage_enable():
    _cage_enable()


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
    bl_description = ("Move, scale or rotate the selected objects (Edit Mode: the selected vertices) "
                      "with the mouse and the controller")
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    mode: bpy.props.EnumProperty(items=[(m, m.title(), "") for m in ("MOVE", "SCALE", "ROTATE")])
    axis: bpy.props.EnumProperty(items=[(a, a, "") for a in ("FREE", "X", "Y", "Z")])

    @classmethod
    def poll(cls, context):
        if context.mode not in ("OBJECT", "EDIT_MESH"):
            cls.poll_message_set("grab/scale/rotate works in Object Mode and mesh Edit Mode")
            return False
        if context.mode == "OBJECT" and not context.selected_objects:
            cls.poll_message_set("select an object first")
            return False
        return context.region_data is not None

    def invoke(self, context, event):
        global _running
        if _running is not None:
            self.report({"WARNING"}, "a grab is already running")
            return {"CANCELLED"}
        context.view_layer.update()  # matrix_world current after a grab that just ended
        self.edit = context.mode == "EDIT_MESH"
        if self.edit:
            self.meshes = _edit_selection()
            if not self.meshes:
                self.report({"WARNING"}, "select some vertices first")
                return {"CANCELLED"}
            self.objs = []
        else:
            self.objs = list(context.selected_objects)
        self._take_start()
        self.orig = (self.start, self.vstart)  # what Esc restores, even after a rebase
        self.pivot = self._pivot()
        self.region, self.rv3d = context.region, context.region_data
        # The mouse start is its first real move: invoked from the controller's
        # timer, the event's position can be stale (e.g. the mouse on another
        # window), and the objects must not jump.
        self.mouse0 = self.mouse = None
        self.push_move = Vector()
        self.push_scale = 1.0
        self.push_angle = 0.0
        self.shared = _running = {"axis": self.axis, "mode": self.mode, "pushes": [], "end": None,
                                  "rebase": False}
        self.timer = context.window_manager.event_timer_add(TIMER_S, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _take_start(self):
        """Objects: origin, scale, matrix. Edit Mode: each selected vertex's world position."""
        self.start = {o.name: (o.matrix_world.translation.copy(), o.scale.copy(), o.matrix_world.copy())
                      for o in self.objs}
        self.vstart = ([[o.matrix_world @ v.co for v in verts] for o, _, verts in self.meshes]
                       if self.edit else [])

    def _pivot(self):
        """The cage point (scale/rotate with the cage on), else the median of the
        origins (Object Mode) or of the selected vertices (Edit Mode)."""
        if self.mode in ARMABLE and cage_on():
            p = cage_point()
            if p is not None:
                return p
        if self.edit:
            pts = [w for ws in self.vstart for w in ws]
            return sum(pts, Vector()) / len(pts)
        return sum((s[0] for s in self.start.values()), Vector()) / len(self.objs)

    def _set_verts(self, world_of):
        """Edit Mode: move every selected vertex to world_of(its start position)."""
        for (o, bm, verts), starts in zip(self.meshes, self.vstart):
            inv = o.matrix_world.inverted()
            for v, w0 in zip(verts, starts):
                v.co = inv @ world_of(w0)
            bmesh.update_edit_mesh(o.data, loop_triangles=False, destructive=False)

    def _rebase(self, context):
        """Go on from where the objects/vertices are now, around the current pivot."""
        context.view_layer.update()
        self._take_start()
        self.pivot = self._pivot()
        self.mouse0 = self.mouse
        self.push_move, self.push_scale, self.push_angle = Vector(), 1.0, 0.0
        self.shared["rebase"] = False

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
            if self.edit:
                self._set_verts(lambda w0: w0 + d)
            for o in self.objs:
                self._set_world_location(o, self.start[o.name][0] + d)
        elif mode == "SCALE":
            f = self.push_scale
            c = self._pivot_2d()
            if moved and c is not None and (self.mouse0 - c).length > 1:
                f *= (self.mouse - c).length / (self.mouse0 - c).length
            k = Vector((f, f, f)) if axis == "FREE" else Vector([f if a == axis else 1.0 for a in "XYZ"])
            if self.edit:
                self._set_verts(lambda w0: self.pivot + Vector([a * b for a, b in zip(w0 - self.pivot, k)]))
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
            if self.edit:
                self._set_verts(lambda w0: m @ w0)
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
            self.start, self.vstart = self.orig
            for o in self.objs:
                o.matrix_world = self.start[o.name][2]
            if self.edit:
                self._set_verts(lambda w0: w0)
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
        if self.shared["rebase"]:
            self._rebase(context)
        self._take_pushes()
        self._apply()
        if context.area:
            context.area.tag_redraw()
        return {"RUNNING_MODAL"}


CLASSES = (CONTROLSURFACE_OT_grab,)
