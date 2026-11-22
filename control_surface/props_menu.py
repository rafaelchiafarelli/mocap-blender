"""The Properties editor, driven by the controller (deck B) and drawn by the add-on.

Like add_menu.py, the structure comes from Blender itself:
- the Object tab: the Python panels of the Properties editor for that tab
  (`bl_space_type` PROPERTIES, `bl_context` "object"), whose draw() is called
  with a recording layout that keeps every `layout.prop(data, name)`;
- the Modifiers tab: modifier panels are drawn in C, so each modifier's
  fields are its RNA properties; plus "Add Modifier ›" read from Blender's
  OBJECT_MT_modifier_add menu, and Apply / Delete per modifier.

Levels are built when entered, values are read live when drawn. The real
Properties editor follows: its tab changes, and the chosen modifier becomes
active with its panel expanded (the others collapsed).

- `toggle()` (IN): open; on a submenu: enter; on an action: run it; on a
  boolean: flip it; on a number or a list: start editing, IN again keeps.
- `step(pulses, amount)` (platter): move through the rows, or change the
  edited value (numbers by `amount`, the S1 VOL step; whole numbers and list
  entries one per ~14 pulses).
- `cancel()` (OUT): while editing, put the old value back; else close.
"""

import math
import types

import bpy

from . import add_menu

ANGLES = {"ANGLE", "EULER"}  # shown in degrees; the platter turns them 1-10° per pulse
PULSES_PER_ROW = 390 / 27  # ~14 platter pulses per row / per whole-number step
TABS = (("Object", "OBJECT", "object"), ("Modifiers", "MODIFIER", None))
SKIP = {"rna_type", "name", "type", "is_override_data_editable", "persistent_uid",
        "show_expanded", "is_active", "use_pin_to_last", "execution_time"}

_stack = []    # [{"title", "build", "items", "index"}]; empty = closed
_edit = None   # {"item", "old"} while a value is being edited
_acc = 0.0
_handle = None


# --- Rows ----------------------------------------------------------------------
# A row is one of:
#   {"text", "build"}                    a submenu, built when entered
#   {"text", "data", "prop", "index"}    a field (index None: not an array item)
#   {"text", "run"}                      an action (a callable)

class _PropRecorder:
    """A fake UILayout that keeps every prop() call; the rest returns itself."""

    def __init__(self, out):
        object.__setattr__(self, "out", out)

    def prop(self, data, prop, text=None, index=-1, invert_checkbox=False, **kw):
        self.out.append((data, prop, text, index, invert_checkbox))

    def __getattr__(self, name):
        return lambda *a, **k: self

    def __setattr__(self, k, v):
        pass


class _FakePanel:
    """Stands in for a Panel instance so its draw() can run on the recorder."""

    def __init__(self, cls, layout):
        self.layout = layout
        self._cls = cls

    def __getattr__(self, k):
        v = getattr(self._cls, k)
        return types.MethodType(v, self) if isinstance(v, types.FunctionType) else v


def _rna_prop(data, prop):
    try:
        return data.bl_rna.properties[prop]
    except (AttributeError, KeyError):
        return None


def _field_rows(data, prop, text=None, index=-1):
    """One row per editable field; arrays without an index become one row per item."""
    p = _rna_prop(data, prop)
    if p is None or p.is_readonly or p.type not in {"BOOLEAN", "INT", "FLOAT", "ENUM"}:
        return []
    if p.type == "ENUM" and p.is_enum_flag:
        return []
    label = text or p.name
    if getattr(p, "is_array", False) and index in (-1, None):
        names = "XYZW" if p.array_length <= 4 else [str(i) for i in range(p.array_length)]
        return [{"text": f"{label} {names[i]}", "data": data, "prop": prop, "index": i}
                for i in range(p.array_length)]
    return [{"text": label, "data": data, "prop": prop, "index": None if index in (-1, None) else index}]


def _panel_rows(context_name):
    """Rows of the Python Properties panels of one tab (subpanels as submenus)."""
    ctx = bpy.context
    panels = [c for c in bpy.types.Panel.__subclasses__()
              if getattr(c, "bl_space_type", "") == "PROPERTIES" and getattr(c, "bl_context", "") == context_name]
    parents = [c for c in panels if not getattr(c, "bl_parent_id", "")]
    parents.sort(key=lambda c: getattr(c, "bl_order", 0))

    def rows_of(cls):
        try:
            if hasattr(cls, "poll") and not cls.poll(ctx):
                return []
        except Exception:
            return []
        out = []
        try:
            cls.draw(_FakePanel(cls, _PropRecorder(out)), ctx)
        except Exception:
            pass
        rows = []
        for data, prop, text, index, invert in out:
            for r in _field_rows(data, prop, text, index):
                r["invert"] = invert
                rows.append(r)
        for child in panels:
            if getattr(child, "bl_parent_id", "") == cls.__name__:
                sub = rows_of(child)
                if sub:
                    rows.append({"text": getattr(child, "bl_label", child.__name__),
                                 "build": (lambda c=child: rows_of(c))})
        return rows

    rows = []
    for cls in parents:
        if rows_of(cls):
            rows.append({"text": getattr(cls, "bl_label", cls.__name__), "build": (lambda c=cls: rows_of(c))})
    return rows


def _modifier_rows(obj, mod):
    rows = [{"text": "Show in Viewport", "data": mod, "prop": "show_viewport", "index": None},
            {"text": "Show in Render", "data": mod, "prop": "show_render", "index": None}]
    for p in mod.bl_rna.properties:
        if p.identifier in SKIP or p.identifier.startswith("show_"):
            continue
        rows += _field_rows(mod, p.identifier)
    name = mod.name
    rows.append({"text": "Apply", "run": lambda: _modifier_op("object.modifier_apply", obj, name)})
    rows.append({"text": "Delete", "run": lambda: _modifier_op("object.modifier_remove", obj, name)})
    return rows


def _modifier_op(op, obj, name):
    from .blender_glue import run_operator

    if bpy.context.mode != "OBJECT" and op == "object.modifier_apply":
        raise RuntimeError("Apply works in Object Mode")
    with bpy.context.temp_override(object=obj, active_object=obj):
        result = run_operator(op, {"modifier": name})
    _back_and_rebuild()
    return result


def _add_modifier_rows():
    """Blender's Add Modifier menu; an item adds the modifier and goes back to the list."""
    def wrap(items):
        out = []
        for it in items:
            if "items" in it:
                out.append({"text": it["text"], "build": (lambda sub=it["items"]: wrap(sub))})
            else:
                out.append({"text": it["text"], "run": (lambda it=it: _add_modifier(it))})
        return out
    return wrap(add_menu.read_menu("OBJECT_MT_modifier_add"))


def _add_modifier(item):
    from .blender_glue import run_operator

    result = run_operator(item["op"], item["props"])
    while len(_stack) > 2:  # back to Object/Modifiers › Modifiers
        _stack.pop()
    _rebuild()
    level = _stack[-1]
    level["index"] = len(level["items"]) - 1  # the new modifier, last in the stack
    _sync_properties()
    return result


def _modifiers_rows():
    obj = bpy.context.object
    if obj is None:
        return []
    rows = [{"text": "Add Modifier", "build": _add_modifier_rows}]
    for mod in obj.modifiers:
        rows.append({"text": mod.name, "build": (lambda m=mod: _modifier_rows(obj, m)), "modifier": mod.name})
    return rows


def _root_rows():
    obj = bpy.context.object
    rows = [{"text": "Object", "build": lambda: _panel_rows("object"), "tab": "OBJECT"}]
    if obj is not None and hasattr(obj, "modifiers") and obj.type in {"MESH", "CURVE", "SURFACE", "FONT", "LATTICE", "GREASEPENCIL"}:
        rows.append({"text": "Modifiers", "build": _modifiers_rows, "tab": "MODIFIER"})
    return rows


# --- Values ----------------------------------------------------------------------

def _get(item):
    v = getattr(item["data"], item["prop"])
    return v[item["index"]] if item["index"] is not None else v


def _set(item, value):
    if item["index"] is not None:
        arr = getattr(item["data"], item["prop"])
        arr[item["index"]] = value
    else:
        setattr(item["data"], item["prop"], value)


def _value_text(item):
    if "data" not in item:
        return None
    try:
        p = _rna_prop(item["data"], item["prop"])
        v = _get(item)
    except Exception:
        return "?"
    if p.type == "BOOLEAN":
        return "on" if bool(v) != bool(item.get("invert")) else "off"
    if p.type == "ENUM":
        return next((e.name for e in p.enum_items if e.identifier == v), str(v))
    if p.type == "FLOAT":
        if p.subtype in ANGLES:
            return f"{math.degrees(v):.1f}°"
        if p.subtype in {"DISTANCE", "TRANSLATION"}:
            return f"{v:.3f} m"
        return f"{v:.3f}"
    return str(v)


# --- State and actions -------------------------------------------------------

def is_open():
    return bool(_stack)


def editing():
    return _edit is not None


def _rebuild():
    for level in _stack:
        if level.get("build"):
            level["items"] = level["build"]()
            level["index"] = min(level["index"], max(0, len(level["items"]) - 1))


def _back_and_rebuild():
    if len(_stack) > 1:
        _stack.pop()
    _rebuild()


def _sync_properties():
    """The real Properties editor shows the tab (and the modifier) being edited."""
    tab = next((lv.get("tab") for lv in _stack if lv.get("tab")), None)
    if tab is None:
        return
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "PROPERTIES":
                try:
                    area.spaces.active.context = tab
                except TypeError:
                    pass
                area.tag_redraw()
    obj = bpy.context.object
    mod_name = next((lv.get("modifier") for lv in _stack if lv.get("modifier")), None)
    if tab == "MODIFIER" and obj is not None and mod_name and mod_name in obj.modifiers:
        for m in obj.modifiers:
            m.show_expanded = m.name == mod_name
        obj.modifiers.active = obj.modifiers[mod_name]


def toggle():
    """IN: open / enter / run / flip / start or keep an edit."""
    global _edit, _acc
    if not _stack:
        rows = _root_rows()
        if not rows:
            raise RuntimeError("nothing to show (select an object)")
        _stack.append({"title": "Properties", "build": _root_rows, "items": rows, "index": 0})
        _acc = 0.0
        _show()
        return {"FINISHED"}
    if _edit is not None:  # IN again: keep the new value
        _edit = None
        _redraw()
        return {"FINISHED"}
    level = _stack[-1]
    if not level["items"]:
        return {"FINISHED"}
    item = level["items"][level["index"]]
    if "build" in item:
        _stack.append({"title": item["text"], "build": item["build"], "items": item["build"](), "index": 0,
                       "tab": item.get("tab"), "modifier": item.get("modifier")})
        _acc = 0.0
        _sync_properties()
    elif "run" in item:
        item["run"]()
    elif "data" in item:
        p = _rna_prop(item["data"], item["prop"])
        if p.type == "BOOLEAN":
            _set(item, not _get(item))
        else:
            _edit = {"item": item, "old": _get(item)}
            _acc = 0.0
    _redraw()
    return {"FINISHED"}


def step(pulses, amount=0.01):
    """Platter: move through the rows, or change the value being edited."""
    global _acc
    if not _stack:
        return {"FINISHED"}
    if _edit is not None:
        item = _edit["item"]
        p = _rna_prop(item["data"], item["prop"])
        if p.type == "FLOAT":
            delta = math.radians(amount * 100) if p.subtype in ANGLES else amount
            v = _get(item) + (delta if pulses > 0 else -delta)
            _set(item, min(max(v, p.hard_min), p.hard_max))
            _redraw()
            return {"FINISHED"}
    sign = 1 if pulses > 0 else -1  # one per platter message (pulses may come scaled)
    if _acc * sign < 0:
        _acc = 0.0
    _acc += sign
    n = int(_acc / PULSES_PER_ROW)
    if not n:
        return {"FINISHED"}
    _acc -= n * PULSES_PER_ROW
    if _edit is not None:
        item = _edit["item"]
        p = _rna_prop(item["data"], item["prop"])
        if p.type == "INT":
            _set(item, min(max(_get(item) + n, p.hard_min), p.hard_max))
        elif p.type == "ENUM":
            ids = [e.identifier for e in p.enum_items]
            cur = _get(item)
            _set(item, ids[(ids.index(cur) + n) % len(ids)] if cur in ids else ids[0])
    else:
        level = _stack[-1]
        if level["items"]:
            level["index"] = (level["index"] + n) % len(level["items"])
    _redraw()
    return {"FINISHED"}


def cancel():
    """OUT: while editing, put the old value back; else close the menu."""
    global _edit
    if _edit is not None:
        _set(_edit["item"], _edit["old"])
        _edit = None
        _redraw()
        return {"FINISHED"}
    close()
    return {"FINISHED"}


def close():
    global _handle, _edit
    _stack.clear()
    _edit = None
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        _handle = None
    _redraw()


# --- Drawing -----------------------------------------------------------------

def _show():
    global _handle
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (), "WINDOW", "POST_PIXEL")
    _redraw()


def _redraw():
    wm = bpy.context.window_manager
    for win in (wm.windows if wm else ()):
        for area in win.screen.areas:
            if area.type in {"VIEW_3D", "PROPERTIES"}:
                area.tag_redraw()


def _draw():
    if not _stack:
        return
    level = _stack[-1]
    rows = [(it["text"], _value_text(it), "build" in it) for it in level["items"]] or [("(empty)", None, False)]
    footer = "platter: value   IN: keep   OUT: undo" if _edit else "IN: open/set   OUT: close"
    add_menu.draw_list(" › ".join(lv["title"] for lv in _stack), rows, level["index"], footer,
                       side="right", editing=_edit is not None)
