"""The settings of the object just added from the Add menu (task 52).

Deck A's Add menu ran its operator from the add-on's timer, where `bpy.ops`
makes no undo step and does not register the operator: Blender's "Adjust Last
Operation" panel stayed on the previous Shift+A, and changing it undid back to
that step, so the object added from the controller vanished (Rafael,
2026-11-23). `run()` now calls the operator with Blender's undo flag
(`run_operator(..., undo=True)`): one undo step, registered, so Blender's panel
is this operator's.

Then the settings open at once as a level of the Properties menu, in the 4-Mix
window, edited with deck A (IN / platter / OUT / SYNC) or the mouse:
- the level's fields belong to a PropertyGroup made for this operator
  (`_make_group`: the operator's visible properties, same types, limits,
  units and enum items) — not to the registered operator itself, which
  Blender may free (another operator, Ctrl+Z, file load) while the window
  still draws it;
- `flush()` (once per timer tick) sees a changed value and redoes the add
  without Blender's undo (`ed.undo` from the timer fails or crashes, see
  adjust.py): Object Mode deletes the objects the add made and runs it again
  (EXEC_DEFAULT, every value including location and rotation); Edit Mode
  restores a copy of the meshes (adjust's snapshot) and runs it again. A run
  that fails goes back to the last good values. The registered operator's
  properties get the new values too, so Blender's own panel matches;
- `end()` (the level closed, the mode changed, the objects gone, the
  registered operator gone): an undo step for the changed result, so Ctrl+Z
  after another action comes back to it, not to the first values.
"""

import bpy

from . import adjust

GROUP_ATTR = "control_surface_add_config"

_session = None  # {"op", "idname", "pointer", "title", "objects", "copies", "mode", "base", "last", "changed"}
_group_cls = None


def active():
    return _session is not None


def _idname(op):
    module, name = op.split(".", 1)
    return f"{module.upper()}_OT_{name}"


def _registered(pointer):
    """The registered operator with this pointer, looked up afresh (never kept)."""
    for o in bpy.context.window_manager.operators:
        if o.as_pointer() == pointer:
            return o
    return None


def _value(v):
    return tuple(v) if hasattr(v, "__len__") and not isinstance(v, str) else v


def _all_values(props):
    return {p.identifier: _value(getattr(props, p.identifier))
            for p in props.bl_rna.properties if p.identifier != "rna_type"}


# --- The PropertyGroup the level edits ---------------------------------------

def _prop_def(p, value):
    """A bpy.props definition like the operator's property p, defaulting to value."""
    kw = {"name": p.name, "description": p.description}
    arr = getattr(p, "is_array", False) and p.array_length > 0
    if arr:
        kw["size"] = p.array_length
    if p.type == "BOOLEAN":
        return (bpy.props.BoolVectorProperty if arr else bpy.props.BoolProperty)(default=value, **kw)
    if p.type == "INT":
        kw.update(min=p.hard_min, max=p.hard_max, soft_min=p.soft_min, soft_max=p.soft_max, step=max(1, p.step))
        return (bpy.props.IntVectorProperty if arr else bpy.props.IntProperty)(default=value, **kw)
    if p.type == "FLOAT":
        kw.update(min=p.hard_min, max=p.hard_max, soft_min=p.soft_min, soft_max=p.soft_max,
                  step=p.step, precision=p.precision)
        f = bpy.props.FloatVectorProperty if arr else bpy.props.FloatProperty
        for extra in ({"subtype": p.subtype, "unit": p.unit}, {"subtype": p.subtype}, {}):
            try:
                return f(default=value, **kw, **extra)
            except (TypeError, ValueError):
                continue
    if p.type == "ENUM" and not p.is_enum_flag:
        items = [(e.identifier, e.name, e.description, e.icon, i) for i, e in enumerate(p.enum_items)]
        if items and value in {i[0] for i in items}:
            return bpy.props.EnumProperty(items=items, default=value, **kw)
    return None


def _make_group(props):
    """Register a PropertyGroup with the visible properties of `props`; [names] in order."""
    global _group_cls
    _drop_group()
    ann, names = {}, []
    for p in props.bl_rna.properties:
        if p.identifier == "rna_type" or p.is_hidden or p.is_readonly:
            continue
        d = _prop_def(p, _value(getattr(props, p.identifier)))
        if d is not None:
            ann[p.identifier] = d
            names.append(p.identifier)
    cls = type("CONTROLSURFACE_PG_add_config", (bpy.types.PropertyGroup,), {"__annotations__": ann})
    bpy.utils.register_class(cls)
    _group_cls = cls
    setattr(bpy.types.WindowManager, GROUP_ATTR, bpy.props.PointerProperty(type=cls))
    return names


def _drop_group():
    global _group_cls
    if _group_cls is not None:
        try:
            delattr(bpy.types.WindowManager, GROUP_ATTR)
        except AttributeError:
            pass
        bpy.utils.unregister_class(_group_cls)
        _group_cls = None


def group():
    return getattr(bpy.context.window_manager, GROUP_ATTR, None)


def _group_values(names):
    g = group()
    return {n: _value(getattr(g, n)) for n in names}


# --- Run, redo, end ----------------------------------------------------------

def _new_objects(before):
    return [o.name for o in bpy.data.objects if o.as_pointer() not in before]


def run(op, args):
    """Deck A IN on an item: add with an undo step, then open its settings."""
    from . import props_menu
    from .blender_glue import run_operator

    end()
    mode = bpy.context.mode
    copies = adjust._snapshot() if mode == "EDIT_MESH" else []
    before = {o.as_pointer() for o in bpy.data.objects}
    result = run_operator(op, dict(args), "INVOKE_DEFAULT", undo=True)
    ops = bpy.context.window_manager.operators
    last = ops[-1] if len(ops) else None
    if "FINISHED" not in result or last is None or last.bl_idname != _idname(op):
        adjust._free(copies)  # a dialog, a file browser, or nothing to set
        return result
    names = _make_group(last.properties)
    if not names:
        adjust._free(copies)
        return result
    global _session
    _session = {"op": op, "pointer": last.as_pointer(), "title": last.name, "names": names,
                "objects": _new_objects(before) if mode != "EDIT_MESH" else [],
                "copies": copies, "mode": mode, "base": _all_values(last.properties),
                "last": _group_values(names), "changed": False}
    props_menu.open_level(last.name, _rows, config=True)
    return result


def _rows():
    from . import props_menu
    g = group()
    if _session is None or g is None:
        return []
    rows = []
    for n in _session["names"]:
        rows += props_menu._field_rows(g, n)
    return rows


def _still_valid():
    s = _session
    if bpy.context.mode != s["mode"] or _registered(s["pointer"]) is None:
        return False
    return all(n in bpy.data.objects for n in s["objects"])


def _remove_objects(names):
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        data = o.data
        bpy.data.objects.remove(o)
        coll = getattr(bpy.data, _DATA_COLL.get(getattr(data, "id_type", ""), ""), None)
        if data is not None and data.users == 0 and coll is not None:
            coll.remove(data)  # the data the add made; shared data stays


_DATA_COLL = {"MESH": "meshes", "CURVE": "curves", "LIGHT": "lights", "CAMERA": "cameras",
              "META": "metaballs", "LATTICE": "lattices", "ARMATURE": "armatures",
              "GREASEPENCIL": "grease_pencils", "GREASEPENCIL_V3": "grease_pencils",
              "SPEAKER": "speakers", "LIGHT_PROBE": "lightprobes", "VOLUME": "volumes",
              "POINTCLOUD": "pointclouds", "CURVES": "hair_curves"}


def _apply(values):
    """Redo the add with `values` over the first run's; True if it worked."""
    from .blender_glue import run_operator

    s = _session
    if s["mode"] == "EDIT_MESH":
        adjust._restore(s["copies"])
        before = None
    else:
        _remove_objects(s["objects"])
        before = {o.as_pointer() for o in bpy.data.objects}
    result = run_operator(s["op"], {**s["base"], **values})
    if before is not None:
        s["objects"] = _new_objects(before)
    return "FINISHED" in result


def flush():
    """Once per timer tick: end if the level or the object is gone; redo on a change."""
    from . import props_menu

    if _session is None:
        return
    if not props_menu.config_open() or not _still_valid():
        end()
        return
    values = _group_values(_session["names"])
    if values == _session["last"]:
        return
    if _apply(values):
        _session["last"] = values
        _session["changed"] = True
        reg = _registered(_session["pointer"])
        if reg is not None:  # Blender's own panel shows the same values
            for n, v in values.items():
                try:
                    setattr(reg.properties, n, v)
                except (AttributeError, TypeError, ValueError):
                    pass
    else:  # e.g. a value the operator refuses: back to the last good one
        g = group()
        for n, v in _session["last"].items():
            setattr(g, n, v)
        _apply(_session["last"])


def end():
    """Keep the result: an undo step if it was changed; close the level."""
    global _session
    from . import props_menu

    if _session is None:
        return {"FINISHED"}
    s, _session = _session, None
    if props_menu.config_open():
        props_menu.close()
    adjust._free(s["copies"])
    if s["changed"] and bpy.context.mode == s["mode"]:  # not after a Ctrl+Z left the mode
        try:
            from .blender_glue import run_operator
            run_operator("ed.undo_push", {"message": s["title"]})
        except Exception:
            pass
    return {"FINISHED"}


def unregister():
    global _session
    if _session is not None:
        adjust._free(_session["copies"])
        _session = None
    _drop_group()
