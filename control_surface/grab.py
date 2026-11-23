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
- snapping (task 45, `snap.py`, Blender's magnet): grid → move lands on a
  grid of `step`, scale factors in steps of 10 × `step`; geometry → the
  selection snaps to the vertex / edge / face under the mouse.

**Tools** (one at a time per deck, Rafael 2026-11-21): SYNC (the platter
moves the view: `sync` off/on/blink), MOVE (a grab from 1-4), SCALE (RE) and
ROTATE (IN). SCALE/ROTATE stay armed after their grab ends, until the
selection changes. Turning one tool on turns the others off and confirms a
running grab.
"""

import math

import blf
import bmesh
import bpy
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

from . import snap as snapping

AXES = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
TIMER_S = 0.02
DEG_PER_PUSH_UNIT = 100.0
# The 4-Mix platter sends ~390 pulses per turn, each +-1 whatever the speed
# (measured 2026-11-21, review/2026-11-21/teste-volta-platter.csv). One turn
# walks through all 27 cage points.
PLATTER_PULSES_PER_TURN = 390
CAGE_POINTS = 27
PULSES_PER_CAGE_POINT = PLATTER_PULSES_PER_TURN / CAGE_POINTS
PULSES_PER_TIP = PLATTER_PULSES_PER_TURN / 4  # SHIFT + platter in a rotation: a quarter turn = 90°  # a rotate push of `step` (0.01-0.10) = 1-10 degrees
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


# --- Snap marker (task 49): what the snapping is doing, drawn during a grab --

_snap_marker = None   # {"hit": Vector | None, "kind": str, "src": Vector | None, "grid": float | None}
_marker_handle = None


def _draw_snap_marker():
    m = _snap_marker
    if not m:
        return
    region, rv3d = bpy.context.region, bpy.context.region_data
    if region is None or rv3d is None:
        return
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    font = 0
    blf.size(font, 13 * bpy.context.preferences.system.ui_scale)
    if m.get("hit") is not None:
        c = view3d_utils.location_3d_to_region_2d(region, rv3d, m["hit"])
        if c is not None:
            r = 9 * bpy.context.preferences.system.ui_scale
            ring = [(c.x + r * math.cos(a * math.pi / 12), c.y + r * math.sin(a * math.pi / 12)) for a in range(25)]
            gpu.state.line_width_set(2)
            shader.uniform_float("color", (1.0, 0.55, 0.0, 1.0))
            batch_for_shader(shader, "LINE_STRIP", {"pos": ring}).draw(shader)
            if m.get("src") is not None:
                s = view3d_utils.location_3d_to_region_2d(region, rv3d, m["src"])
                if s is not None:
                    gpu.state.point_size_set(8)
                    shader.uniform_float("color", (1.0, 1.0, 1.0, 0.9))
                    batch_for_shader(shader, "POINTS", {"pos": [s]}).draw(shader)
            blf.color(font, 1.0, 0.6, 0.1, 1.0)
            blf.position(font, c.x + r + 4, c.y + r, 0)
            blf.draw(font, m.get("kind", ""))
    if m.get("grid") or m.get("factor"):
        blf.color(font, 1.0, 0.6, 0.1, 1.0)
        blf.position(font, 20, 20, 0)
        blf.draw(font, f"snap: grid {m['grid'] * 100:g} cm" if m.get("grid")
                 else f"snap: scale in steps of {m['factor']:g}")
    elif m.get("kind") is not None and m.get("hit") is None:
        blf.color(font, 1.0, 0.6, 0.1, 1.0)
        blf.position(font, 20, 20, 0)
        blf.draw(font, "snap: geometry (no target under the mouse)")
    gpu.state.point_size_set(1)
    gpu.state.line_width_set(1)
    gpu.state.blend_set("NONE")


def _marker_show(on):
    global _marker_handle, _snap_marker
    if on and _marker_handle is None:
        _marker_handle = bpy.types.SpaceView3D.draw_handler_add(_draw_snap_marker, (), "WINDOW", "POST_PIXEL")
    elif not on:
        _snap_marker = None
        if _marker_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_marker_handle, "WINDOW")
            _marker_handle = None


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


END_TOOLS_HOOKS = []  # called by end_tools (e.g. the adjust session ends)


def end_tools(keep=None):
    """Turn every tool off except `keep`; confirm a running grab."""
    global _armed, _sync
    for hook in END_TOOLS_HOOKS:
        hook()
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


def rotate_snap_on():
    """Second press of the running rotation's axis button: the platter now
    turns in 90° steps (rotate_tip); the third press confirms."""
    if _running is None or _running["mode"] != "ROTATE":
        raise RuntimeError("no rotation running")
    _running["snap"] = True
    return {"FINISHED"}


def snap_on():
    return _running is not None and bool(_running.get("snap"))


def rotate_tip(pulses):
    """Platter in a rotation's 90° mode: every quarter platter turn, the total
    angle jumps to the next multiple of 90° from where the rotation started
    (a "tip over"); the mouse's share is absorbed."""
    if _running is None or _running["mode"] != "ROTATE":
        raise RuntimeError("no rotation running")
    acc = _running.get("tip_acc", 0.0)
    if acc * pulses < 0:
        acc = 0.0
    acc += pulses
    n = int(acc / PULSES_PER_TIP)
    _running["tip_acc"] = acc - n * PULSES_PER_TIP
    if n:
        _running["tips"] = _running.get("tips", 0) + n
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
        if _running["mode"] == "ROTATE":  # start over on the new axis (Rafael, 2026-11-22)
            _running["reset"] = True
    elif what == "push":
        _running["pushes"].append((kw["amount"], kw.get("along", "right")))
    else:
        _running["end"] = what
        _running = None
    return {"FINISHED"}


def grid_size():
    """The grid of the snapping's grid mode: the `step` scale (S1 VOL), 0.01 m without a session."""
    try:
        from .blender_glue import step_value
        return step_value()
    except Exception:
        return 0.01


class CONTROLSURFACE_OT_grab(bpy.types.Operator):
    bl_idname = "control_surface.grab"
    bl_label = "Grab / Scale / Rotate (control surface)"
    bl_description = ("Move, scale or rotate the selected objects (Edit Mode: the selected vertices) "
                      "with the mouse and the controller")
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    mode: bpy.props.EnumProperty(items=[(m, m.title(), "") for m in ("MOVE", "SCALE", "ROTATE")])
    axis: bpy.props.EnumProperty(items=[(a, a, "") for a in ("FREE", "X", "Y", "Z", "NORMAL")])

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
        self.normal = self._mean_normal() if self.edit else Vector((0, 0, 1))
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
        self.snap = None  # the 90° mode's angle, or None
        self.targets = None  # snapping.Targets, built the first time geometry snapping is needed
        self._hit_kind = None
        _marker_show(True)
        self.shared = _running = {"axis": self.axis, "mode": self.mode, "pushes": [], "end": None,
                                  "rebase": False}
        self.timer = context.window_manager.event_timer_add(TIMER_S, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _axis_vec(self, axis):
        """A global axis, or NORMAL: the selection's mean normal (Edit Mode, for Extrude)."""
        if axis == "NORMAL":
            return self.normal
        return AXES[axis]

    def _mean_normal(self):
        """World-space mean normal of the selected faces (else vertices); Z if none."""
        n = Vector()
        for o, bm, verts in getattr(self, "meshes", []):
            nm = o.matrix_world.to_3x3().inverted().transposed()
            faces = [f for f in bm.faces if f.select]
            for e in (faces or verts):
                n += nm @ e.normal
        return n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))

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

    def _reset_to_start(self):
        """A rotation's axis changed: undo what was turned so far and start the new
        axis from 0° (the 90° mode stays on and re-aligns to the new axis)."""
        self.start, self.vstart = self.orig
        for o in self.objs:
            o.matrix_world = self.start[o.name][2]
        if self.edit:
            self._set_verts(lambda w0: w0)
        self.mouse0 = self.mouse
        self.push_angle = 0.0
        self.shared.pop("tips", None)
        self.shared["tip_acc"] = 0.0
        if self.snap is not None:
            self.snap = None
            self._snap_to_grid()

    def _rebase(self, context):
        """Go on from where the objects/vertices are now, around the current pivot."""
        context.view_layer.update()
        self._take_start()
        self.pivot = self._pivot()
        self.mouse0 = self.mouse
        self.push_move, self.push_scale, self.push_angle = Vector(), 1.0, 0.0
        if self.snap is not None:  # 90° mode goes on on the new axis, aligned to it
            self.snap = None
            self._snap_to_grid()
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

    # --- snapping (task 45) ---------------------------------------------------

    def _snap_hit(self):
        """Geometry mode: the world point under the mouse to snap to, or None."""
        if self.mouse is None:
            return None
        if self.targets is None:
            self.targets = snapping.Targets(bpy.context, exclude={o.name for o in self.objs})
        hit = self.targets.find(bpy.context, self.region, self.rv3d, self.mouse, snapping.elements())
        self._hit_kind = hit[1] if hit else None
        return hit[0] if hit else None

    def _snap_points(self):
        """The selection's points at the start: vertices (Edit Mode), else the
        origins and the corners of each object's box."""
        if self.edit:
            return [w for ws in self.vstart for w in ws]
        pts = []
        for o in self.objs:
            p0, _, m0 = self.start[o.name]
            pts.append(p0)
            pts += [m0 @ Vector(c) for c in o.bound_box]
        return pts

    def _marker(self, off=False, **m):
        """What the snapping does now, for the marker drawn in the viewport."""
        global _snap_marker
        if off:
            _snap_marker = None
            return
        grid = "grid" in m or "factor" in m
        _snap_marker = {"hit": m.get("hit"), "src": m.get("src"), "grid": m.get("grid"),
                        "factor": m.get("factor"), "kind": None if grid else (self._hit_kind or "")}

    def _snap_source(self, hit, for_scale=False, moved_by=None):
        """The point of the selection that lands on hit (Blender's Snap With).
        CLOSEST, moving: the point that is nearest the mouse on screen where the
        mouse is taking the selection (moved_by) — the corner/vertex being
        pointed at; in 3D the nearest point swaps between top and bottom
        corners with the depth (seen 2026-11-22). Scale: nearest in 3D."""
        how = snapping.snap_target()
        if for_scale or how == "CLOSEST":
            pts = [p for p in self._snap_points() if not for_scale or (p - self.pivot).length > 1e-6]
            if not pts:
                return self.pivot
            if moved_by is not None and self.mouse is not None:
                def screen_dist(p):
                    xy = view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, p + moved_by)
                    return (xy - self.mouse).length if xy is not None else float("inf")
                return min(pts, key=screen_dist)
            return min(pts, key=lambda p: (p - hit).length)
        if how == "ACTIVE" and not self.edit:
            act = bpy.context.view_layer.objects.active
            if act is not None and act.name in self.start:
                return self.start[act.name][0]
        return self.pivot

    def _apply(self):
        axis, mode = self.shared["axis"], self.shared["mode"]
        moved = self.mouse0 is not None
        snap_mode = snapping.mode()
        if mode == "MOVE":
            d = self.push_move.copy()
            if moved:
                d += self._plane_point(self.mouse) - self._plane_point(self.mouse0)
            if axis != "FREE":
                d = self._axis_vec(axis) * d.dot(self._axis_vec(axis))
            if snap_mode == "grid" and axis != "NORMAL":
                axes = "XYZ" if axis == "FREE" else axis
                d = snapping.grid_point(self.pivot + d, grid_size(), axes) - self.pivot
            elif snap_mode == "geometry" and moved:
                hit = self._snap_hit()
                if hit is not None:
                    src = self._snap_source(hit, moved_by=d)
                    d = hit - src
                    if axis != "FREE":
                        d = self._axis_vec(axis) * d.dot(self._axis_vec(axis))
                    self._marker(hit=hit, src=src + d)
                else:
                    self._marker(hit=None)
            if snap_mode == "grid":
                self._marker(grid=grid_size())
            elif snap_mode == "off":
                self._marker(off=True)
            if self.edit:
                self._set_verts(lambda w0: w0 + d)
            for o in self.objs:
                self._set_world_location(o, self.start[o.name][0] + d)
        elif mode == "SCALE":
            f = self.push_scale
            c = self._pivot_2d()
            if moved and c is not None and (self.mouse0 - c).length > 1:
                f *= (self.mouse - c).length / (self.mouse0 - c).length
            if snap_mode == "grid":
                q = 10 * grid_size()
                f = snapping.round_to(f, q) or (q if f >= 0 else -q)
                self._marker(factor=q)
            elif snap_mode == "off":
                self._marker(off=True)
            elif snap_mode == "geometry" and moved:
                hit = self._snap_hit()
                self._marker(hit=hit)
                if hit is not None:
                    src = self._snap_source(hit, for_scale=True)
                    if axis in ("FREE", "NORMAL"):
                        den = (src - self.pivot).length
                        if den > 1e-6:
                            f = (hit - self.pivot).length / den
                    else:
                        i = "XYZ".index(axis)
                        den = src[i] - self.pivot[i]
                        if abs(den) > 1e-6:
                            f = (hit[i] - self.pivot[i]) / den
            k = (Vector((f, f, f)) if axis in ("FREE", "NORMAL")
                 else Vector([f if a == axis else 1.0 for a in "XYZ"]))
            if self.edit:
                self._set_verts(lambda w0: self.pivot + Vector([a * b for a, b in zip(w0 - self.pivot, k)]))
            for o in self.objs:
                p0, s0, _ = self.start[o.name]
                o.scale = Vector([a * b for a, b in zip(s0, k)])
                self._set_world_location(o, self.pivot + Vector([a * b for a, b in zip(p0 - self.pivot, k)]))
        else:  # ROTATE
            toward_viewer = self.rv3d.view_rotation @ Vector((0, 0, 1))
            rot_axis = toward_viewer if axis == "FREE" else self._axis_vec(axis)
            angle = self.push_angle
            c = self._pivot_2d()
            if self.snap is not None:  # 90° mode: the mouse is ignored
                angle = self.snap
            elif moved and c is not None and min((self.mouse0 - c).length, (self.mouse - c).length) > 1:
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
                self.push_move += self._axis_vec(axis) * amount
            else:
                v = Vector((1, 0, 0)) if along == "right" else Vector((0, 1, 0))
                self.push_move += (self.rv3d.view_rotation @ v) * amount
        self.shared["pushes"].clear()

    def _rotation_angle(self):
        """The rotation's total angle now (pushes + mouse), as _apply computes it."""
        angle = self.push_angle
        c = self._pivot_2d()
        if self.mouse0 is not None and c is not None and min((self.mouse0 - c).length, (self.mouse - c).length) > 1:
            toward_viewer = self.rv3d.view_rotation @ Vector((0, 0, 1))
            rot_axis = toward_viewer if self.shared["axis"] == "FREE" else self._axis_vec(self.shared["axis"])
            a = math.atan2(*(self.mouse - c).yx) - math.atan2(*(self.mouse0 - c).yx)
            angle += a if rot_axis.dot(toward_viewer) >= 0 else -a
        return angle

    def _start_angle_on_axis(self):
        """The rotation the objects already have on the current global axis
        (the first object's world Euler), so the 90° mode lands on 0/90/180/270
        in absolute terms. Edit Mode and the free axis have no such reference: 0."""
        axis = self.shared["axis"]
        if self.edit or axis in ("FREE", "NORMAL") or not self.objs:
            return 0.0
        return self.start[self.objs[0].name][2].to_euler("XYZ")["XYZ".index(axis)]

    def _snap_to_grid(self):
        """Turn the 90° mode on (or re-align it after an axis change): the
        angle to the nearest absolute multiple of 90°."""
        quarter = math.pi / 2
        a0 = self._start_angle_on_axis()
        self.snap = round((a0 + self._rotation_angle()) / quarter) * quarter - a0

    def _take_tips(self):
        """90° mode: on entering it, snap to the nearest multiple of 90°; then
        every tip turns exactly ±90°."""
        if not self.shared.get("snap") or self.shared["mode"] != "ROTATE":
            return
        if self.snap is None:
            self._snap_to_grid()
        n = self.shared.pop("tips", 0)
        self.snap += n * math.pi / 2

    def _end(self, context, confirm):
        global _running
        context.window_manager.event_timer_remove(self.timer)
        _marker_show(False)
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
        if self.shared.pop("reset", False):
            self._reset_to_start()
        if self.shared["rebase"]:
            self._rebase(context)
        self._take_pushes()
        self._take_tips()
        self._apply()
        if context.area:
            context.area.tag_redraw()
        return {"RUNNING_MODAL"}


CLASSES = (CONTROLSURFACE_OT_grab,)
