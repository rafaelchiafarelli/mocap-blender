"""Adjustable mesh operators (Inset, Bevel, Loop Cut) driven by the platter.

Blender's Inset/Bevel follow the mouse, and their values are changed after the
fact in "Adjust Last Operation" (which undoes and redoes the operator). This
module does the same from the controller, but without Blender's undo (`ed.undo`
from a timer fails its poll or crashes Blender, seen 2026-11-21): before the
first run it keeps a copy of every mesh in Edit Mode, and a redo restores
that copy and runs the operator again.

- `start(op, props, main, second)` runs the operator once with `props` and
  opens a session; `main` is the property the platter changes, `second` the
  one SHIFT + platter changes (or None).
- `change(which, amount)` only records the change; `flush()` (called once per
  timer tick) restores the copy and runs the operator again with the new
  values, so a fast platter costs one redo per tick, not one per message.
- `end()` keeps the result, frees the copies and closes the session.

Float properties change by `amount` (already scaled by the S1 VOL step);
integer ones by one per INT_PULSES platter pulses.
"""

import bmesh
import bpy

INT_PULSES = 390 / 27  # like the cage: ~14 platter pulses per +-1

_session = None  # {"op", "props", "main", "second", "acc", "dirty", "last_good", "copies"}


def _snapshot():
    """[(mesh, copy)] of every mesh in Edit Mode, selection included."""
    out = []
    for o in bpy.context.objects_in_mode_unique_data:
        if o.type == "MESH":
            copy = bpy.data.meshes.new("control_surface_adjust_copy")
            bmesh.from_edit_mesh(o.data).to_mesh(copy)
            out.append((o.data, copy))
    return out


def _restore(copies):
    for me, copy in copies:
        bm = bmesh.from_edit_mesh(me)
        bm.clear()
        bm.from_mesh(copy)
        bmesh.update_edit_mesh(me, loop_triangles=True, destructive=True)


def _free(copies):
    for _, copy in copies:
        try:
            bpy.data.meshes.remove(copy)
        except ReferenceError:  # Ctrl+Z already removed it (made after the undo step; task 52)
            pass


def adjusting():
    """The operator being adjusted ('mesh.bevel', ...), or 'NONE'."""
    return _session["op"] if _session else "NONE"


def active():
    return _session is not None


def start(op, props, main, second=None):
    global _session
    from .blender_glue import run_operator

    end()
    copies = _snapshot()
    result = run_operator(op, dict(props))
    if "FINISHED" not in result:
        _free(copies)
        return result
    _session = {"op": op, "props": dict(props), "main": main, "second": second,
                "acc": {}, "dirty": False, "last_good": dict(props), "copies": copies}
    return result


def change(which, amount):
    """Platter (`which` 'main') or SHIFT + platter ('second')."""
    if _session is None:
        raise RuntimeError("nothing to adjust")
    prop = _session[which]
    if prop is None:
        return {"FINISHED"}
    props = _session["props"]
    if isinstance(props[prop], int) and not isinstance(props[prop], bool):
        acc = _session["acc"].get(prop, 0.0)
        if acc * amount < 0:
            acc = 0.0
        acc += 1 if amount > 0 else -1
        n = int(acc / INT_PULSES)
        _session["acc"][prop] = acc - n * INT_PULSES
        if not n:
            return {"FINISHED"}
        props[prop] = max(1, props[prop] + n)
    else:
        props[prop] = max(0.0, props[prop] + amount)
    _session["dirty"] = True
    return {"FINISHED"}


def flush():
    """Undo the last run and run again with the current values (once per tick)."""
    if _session is None or not _session["dirty"]:
        return
    from .blender_glue import run_operator

    _session["dirty"] = False
    _restore(_session["copies"])
    result = run_operator(_session["op"], dict(_session["props"]))
    if "FINISHED" in result:
        _session["last_good"] = dict(_session["props"])
    else:  # e.g. too many cuts: go back to the last values that worked
        _session["props"] = dict(_session["last_good"])
        _restore(_session["copies"])
        run_operator(_session["op"], dict(_session["props"]))


def end():
    global _session
    if _session is not None:
        s, _session = _session, None
        _free(s["copies"])
    return {"FINISHED"}
