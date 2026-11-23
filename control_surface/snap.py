"""Snapping for the add-on's own move/scale and for the 3D cursor (task 45).

The state is Blender's own magnet (Shift+Tab), so the keyboard's G/S follow it
too and the LEDs show it whoever changed it:
- `off`      — `tool_settings.use_snap` off;
- `grid`     — on, elements GRID or INCREMENT only (mode A: positions on a
               grid of `step`, scale factors in steps of 10 × `step`);
- `geometry` — on, any other element (mode B: the vertex, edge or face of
               other geometry under the mouse).
`cycle()` (VINYL MODE) goes off → grid → geometry → off.

`Targets` collects, once per grab, the world positions of the geometry that
can be snapped to (visible meshes other than the moving ones; in Edit Mode
the edited meshes' unselected vertices); `find()` projects them each mouse
move and returns the nearest vertex, else edge point, within `RADIUS_PX`,
else the face under the mouse.
"""

import bmesh
import bpy
import numpy as np
from bpy_extras import view3d_utils
from mathutils import Vector

GRID = {"GRID", "INCREMENT"}
GEOMETRY_DEFAULT = {"VERTEX", "EDGE", "FACE"}
RADIUS_PX = 15            # × ui_scale: how near the mouse a vertex/edge must be
MAX_VERTS = 500_000       # skip snapping to scenes bigger than this (kept fast)

_last_geometry = None     # the geometry elements last used, restored by cycle()


def mode():
    ts = bpy.context.scene.tool_settings
    if not ts.use_snap:
        return "off"
    return "grid" if set(ts.snap_elements) <= GRID else "geometry"


def cycle():
    """VINYL MODE: off → grid → geometry → off (Blender's magnet and its elements)."""
    global _last_geometry
    ts = bpy.context.scene.tool_settings
    m = mode()
    if m == "off":
        ts.snap_elements = {"GRID"}
        ts.use_snap = True
    elif m == "grid":
        ts.snap_elements = _last_geometry or GEOMETRY_DEFAULT
        ts.use_snap = True
    else:
        _last_geometry = set(ts.snap_elements)
        ts.use_snap = False
    return {"FINISHED"}


def elements():
    return set(bpy.context.scene.tool_settings.snap_elements)


def snap_target():
    """Which point of the moving selection snaps: CLOSEST, CENTER, MEDIAN, ACTIVE."""
    return bpy.context.scene.tool_settings.snap_target


# --- Grid (mode A) -----------------------------------------------------------

def round_to(value, size):
    return round(value / size) * size if size > 0 else value


def grid_point(p, size, axes="XYZ"):
    """p with its coordinates on the given axes rounded to multiples of size."""
    return Vector([round_to(c, size) if a in axes else c for a, c in zip("XYZ", p)])


# --- Geometry (mode B) -------------------------------------------------------

class Targets:
    """World positions of the geometry that can be snapped to, taken once."""

    def __init__(self, context, exclude=(), edit_unselected=True):
        dg = context.evaluated_depsgraph_get()
        exclude = set(exclude)
        verts, edges, offset = [], [], 0
        self.ray_exclude = set(exclude)
        for o in context.visible_objects:
            if o.type != "MESH" or o.name in exclude:
                continue
            if o.mode == "EDIT":
                self.ray_exclude.add(o.name)  # its evaluated mesh moves with the grab
                if not edit_unselected:
                    continue
                bm = bmesh.from_edit_mesh(o.data)
                bm.verts.ensure_lookup_table()
                keep = [v for v in bm.verts if not v.select]
                if not keep:
                    continue
                index = {v.index: i for i, v in enumerate(keep)}
                co = np.array([o.matrix_world @ v.co for v in keep], dtype=np.float64)
                ed = np.array([(index[e.verts[0].index], index[e.verts[1].index]) for e in bm.edges
                               if e.verts[0].index in index and e.verts[1].index in index],
                              dtype=np.int64).reshape(-1, 2)
            else:
                me = o.evaluated_get(dg).data
                n = len(me.vertices)
                if not n:
                    continue
                co = np.empty(n * 3, dtype=np.float64)
                me.vertices.foreach_get("co", co)
                co = co.reshape(-1, 3)
                m = np.array(o.matrix_world, dtype=np.float64)
                co = co @ m[:3, :3].T + m[:3, 3]
                ed = np.empty(len(me.edges) * 2, dtype=np.int64)
                me.edges.foreach_get("vertices", ed)
                ed = ed.reshape(-1, 2)
            verts.append(co)
            edges.append(ed + offset)
            offset += len(co)
            if offset > MAX_VERTS:
                break
        self.verts = np.concatenate(verts) if verts else np.empty((0, 3))
        self.edges = np.concatenate(edges) if edges else np.empty((0, 2), dtype=np.int64)

    def _project(self, region, rv3d):
        """Region pixel coordinates of every vertex, and which are in front of the view."""
        if not len(self.verts):
            return np.empty((0, 2)), np.empty(0, dtype=bool)
        pm = np.array(rv3d.perspective_matrix, dtype=np.float64)
        h = np.c_[self.verts, np.ones(len(self.verts))] @ pm.T
        w = h[:, 3]
        front = w > 1e-6
        ndc = h[:, :2] / np.where(front, w, 1.0)[:, None]
        px = np.c_[(ndc[:, 0] + 1) * region.width / 2, (ndc[:, 1] + 1) * region.height / 2]
        return px, front

    def find(self, context, region, rv3d, mouse, elems):
        """(world point, kind) of the snap target under the mouse, or None.
        kind: VERTEX, EDGE or FACE (the first found, in that order)."""
        radius = RADIUS_PX * context.preferences.system.ui_scale
        m = np.array(mouse[:2], dtype=np.float64)
        px, front = self._project(region, rv3d)
        if "VERTEX" in elems and len(px):
            d = np.where(front, np.linalg.norm(px - m, axis=1), np.inf)
            i = int(np.argmin(d))
            if d[i] <= radius:
                return Vector(self.verts[i]), "VERTEX"
        if elems & {"EDGE", "EDGE_MIDPOINT", "EDGE_PERPENDICULAR"} and len(self.edges):
            a, b = self.edges[:, 0], self.edges[:, 1]
            ok = front[a] & front[b]
            pa, pb = px[a], px[b]
            ab = pb - pa
            ll = np.einsum("ij,ij->i", ab, ab)
            t = np.clip(np.einsum("ij,ij->i", m - pa, ab) / np.where(ll > 0, ll, 1), 0, 1)
            if "EDGE_MIDPOINT" in elems and "EDGE" not in elems:
                t = np.full_like(t, 0.5)
            q = pa + ab * t[:, None]
            d = np.where(ok, np.linalg.norm(q - m, axis=1), np.inf)
            i = int(np.argmin(d))
            if d[i] <= radius:
                w = self.verts[a[i]] + (self.verts[b[i]] - self.verts[a[i]]) * t[i]
                return Vector(w), "EDGE"
        if elems & {"FACE", "FACE_PROJECT", "FACE_NEAREST", "FACE_MIDPOINT", "VOLUME"}:
            hit = ray_under_mouse(context, region, rv3d, mouse, self.ray_exclude)
            if hit is not None:
                return hit, "FACE"
        return None


def ray_under_mouse(context, region, rv3d, mouse, exclude=()):
    """The first surface under the mouse, skipping the excluded objects."""
    origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse)
    direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse)
    dg = context.evaluated_depsgraph_get()
    for _ in range(64):
        ok, loc, _n, _i, obj, _m = context.scene.ray_cast(dg, origin, direction)
        if not ok:
            return None
        if obj is None or obj.original.name not in exclude:
            return loc
        # Step past the excluded surface; 0.1 mm was too little far from the
        # camera: the ray kept hitting the same face (seen 2026-11-22).
        origin = loc + direction * max(1e-3, (loc - origin).length * 1e-5)
    return None
