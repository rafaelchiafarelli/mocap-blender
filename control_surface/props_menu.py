"""The Properties editor, driven by the controller (deck B) and drawn by the add-on.

The structure comes from Blender itself (tasks 33-34):
- every Python-drawn tab (Render, Output, View Layer, Scene, World,
  Collection, Object, Particles, Physics, Object Data, Material, Texture):
  the tab's panels' draw() (and draw_header()) run on a recording layout
  that keeps `prop` (fields), `operator` (buttons, as actions),
  `operator_menu_enum` (menus of actions), `template_list` (lists: pick the
  active item) and `template_ID` / `prop_search` / ID pointer props (pick a
  datablock, or make a new one). Panels get a context stand-in
  (`_ButtonsContext`) with what the Properties editor would give them
  (context.camera, context.material, context.cloth, ...);
- Modifiers and Constraints, drawn in C: each item's RNA fields, plus Blender's
  Add menu, and Apply / Delete;
- Material and World surfaces, drawn as nodes: the inputs of the shader node
  plugged into the output (Base Color, Roughness, Strength, ...);
- Material slots and pickers come from Blender's own panels (a template_list
  and a template_ID); "New" makes a material with nodes.

Levels are built when entered; values are read live when drawn. The real
Properties editor follows: its tab changes, and a chosen modifier or
constraint becomes active with its panel expanded (the others collapsed).

- `toggle()` (IN): open; on a submenu: enter; on an action: run it; on an
  on/off: flip it; on a number or a list value: start editing, IN keeps.
- `step(pulses, amount)` (platter): move through the rows, or change the
  edited value (numbers by the field's own Blender increment times the S1
  VOL factor 1-10; angles 1-10°; whole numbers and list values one per ~14
  pulses).
- `cancel()` (OUT, short): while editing, put the old value back; else one
  level back; at the top, close. `close_all()` (SYNC, or OUT held 0.5 s):
  close from anywhere.
"""

import math
import types

import bpy

from . import add_menu

ANGLES = {"ANGLE", "EULER"}  # shown in degrees; the platter turns them 1-10° per pulse
PULSES_PER_ROW = 390 / 27    # ~14 platter pulses per row / per whole-number step
SKIP = {"rna_type", "name", "type", "is_override_data_editable", "persistent_uid",
        "show_expanded", "is_active", "use_pin_to_last", "execution_time", "active",
        "is_valid", "error_location", "error_rotation", "is_override_data_editable"}

# The Properties tabs in Blender's order: (label, editor tab id, panels' bl_context)
TABS = (
    ("Render", "RENDER", "render"), ("Output", "OUTPUT", "output"),
    ("View Layer", "VIEW_LAYER", "view_layer"), ("Scene", "SCENE", "scene"),
    ("World", "WORLD", "world"), ("Collection", "COLLECTION", "collection"),
    ("Object", "OBJECT", "object"), ("Modifiers", "MODIFIER", None),
    ("Particles", "PARTICLES", "particle"), ("Physics", "PHYSICS", "physics"),
    ("Constraints", "CONSTRAINT", None), ("Data", "DATA", "data"),
    ("Material", "MATERIAL", "material"), ("Texture", "TEXTURE", "texture"),
)
MODIFIER_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "LATTICE", "GREASEPENCIL", "CURVES", "POINTCLOUD", "VOLUME"}
MATERIAL_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META", "GREASEPENCIL", "CURVES", "POINTCLOUD", "VOLUME"}

_stack = []    # [{"title", "build", "items", "index", "tab", "modifier", "constraint"}]; empty = closed
_edit = None   # {"item", "old"} while a value is being edited
_acc = 0.0
_handle = None


# --- The context panels expect --------------------------------------------------

class _ButtonsContext:
    """What the Properties editor's context gives its panels, else bpy.context."""

    def __init__(self, tab):
        obj = bpy.context.object
        scene = bpy.context.scene
        x = {"space_data": types.SimpleNamespace(pin_id=None, use_pin_id=False, context=tab, type="PROPERTIES"),
             "world": scene.world, "collection": bpy.context.collection}
        if obj is not None:
            data_names = {"MESH": "mesh", "CURVE": "curve", "SURFACE": "curve", "FONT": "curve",
                          "CAMERA": "camera", "LIGHT": "light", "LATTICE": "lattice", "ARMATURE": "armature",
                          "META": "meta_ball", "SPEAKER": "speaker", "LIGHT_PROBE": "lightprobe",
                          "GREASEPENCIL": "grease_pencil", "VOLUME": "volume", "POINTCLOUD": "pointcloud",
                          "CURVES": "curves"}
            if obj.type in data_names:
                x[data_names[obj.type]] = obj.data
            slots = getattr(obj, "material_slots", None)
            x["material"] = obj.active_material
            x["material_slot"] = slots[obj.active_material_index] if slots and len(slots) else None
            mods = {m.type: m for m in getattr(obj, "modifiers", [])}
            x.update(cloth=mods.get("CLOTH"), soft_body=mods.get("SOFT_BODY"), fluid=mods.get("FLUID"),
                     dynamic_paint=mods.get("DYNAMIC_PAINT"), collision=mods.get("COLLISION"),
                     rigid_body=getattr(obj, "rigid_body", None),
                     rigid_body_constraint=getattr(obj, "rigid_body_constraint", None),
                     field=getattr(obj, "field", None))
            ps = obj.particle_systems.active if hasattr(obj, "particle_systems") else None
            x.update(particle_system=ps, particle_settings=ps.settings if ps else None)
            if obj.type == "ARMATURE":
                x["bone"] = obj.data.bones.active
        self._x = x

    def __getattr__(self, k):
        if k in self._x:
            return self._x[k]
        # A member only the Properties editor provides (e.g.
        # particle_system_editable): None, so the panel goes on drawing.
        return getattr(bpy.context, k, None)

    def path_resolve(self, path, coerce=True):
        """Custom Properties panels resolve their data by a context path."""
        head = path.split(".", 1)[0]
        if head in self._x and self._x[head] is not None:
            obj = self._x[head]
            return obj.path_resolve(path.split(".", 1)[1], coerce) if "." in path else obj
        return bpy.context.path_resolve(path, coerce)


# --- Recording a panel ------------------------------------------------------------

class _Props:
    def __init__(self):
        object.__setattr__(self, "_d", {})

    def __setattr__(self, k, v):
        self._d[k] = v

    def __getattr__(self, k):
        return None


class _PropRecorder:
    """A fake UILayout: keeps fields, buttons, menus of buttons, lists, datablock pickers."""

    def __init__(self, out):
        object.__setattr__(self, "out", out)

    def prop(self, data, prop, text=None, index=-1, invert_checkbox=False, **kw):
        self.out.append(("prop", data, prop, text, index, invert_checkbox))

    def operator(self, op, text=None, icon=None, **kw):
        p = _Props()
        self.out.append(("op", op, text, p, icon))
        return p

    def operator_menu_enum(self, op, prop, text=None, **kw):
        self.out.append(("enum_menu", op, prop, text))

    def template_list(self, listtype, list_id="", dataptr=None, propname="", active_dataptr=None,
                      active_propname="", *a, **kw):
        self.out.append(("list", dataptr, propname, active_dataptr, active_propname))

    def template_curve_mapping(self, data, prop, *a, **kw):
        self.out.append(("curve", data, prop))

    def template_ID(self, data, prop, new="", *a, **kw):
        self.out.append(("id", data, prop, new))

    def prop_search(self, data, prop, *a, text=None, **kw):
        self.out.append(("id", data, prop, ""))

    def __getattr__(self, name):
        return lambda *a, **k: self  # row(), column(), separator(), label(), template_* ...

    def __setattr__(self, k, v):
        pass


class _FakePanel:
    """Stands in for a Panel instance so its draw() can run on the recorder."""

    def __init__(self, cls, layout):
        self.layout = layout
        self._cls = cls

    def __getattr__(self, k):
        return add_menu.bind_like_instance(self._cls, k, self)


def _module_rank(module_name):
    """Blender registers its UI modules in bl_ui._modules order, add-ons after."""
    try:
        import bl_ui
        names = list(getattr(bl_ui, "_modules", []))
    except ImportError:
        names = []
    short = module_name.rsplit(".", 1)[-1]
    if module_name.startswith("bl_ui.") and short in names:
        return names.index(short)
    return len(names) + 1


def _panel_order(cls):
    """The order the Properties editor draws panels in: bl_order, then the order
    of registration (the module's `classes` tuple), not of definition."""
    import sys
    mod = sys.modules.get(cls.__module__)
    classes = list(getattr(mod, "classes", ()) or ())
    headerless = "HIDE_HEADER" in getattr(cls, "bl_options", set())
    return (not headerless,  # header-less panels (context, "Enable physics for") come first
            getattr(cls, "bl_order", 0), _module_rank(cls.__module__),
            classes.index(cls) if cls in classes else len(classes))


def _button_label(op, props):
    """A button without text (e.g. a curve preset): its enum argument's name."""
    try:
        mod, name = op.split(".", 1)
        rna = getattr(getattr(bpy.ops, mod), name).get_rna_type()
        for k, v in props.items():
            p = rna.properties[k]
            if p.type == "ENUM":
                n = next((e.name for e in p.enum_items if e.identifier == v), "")
                if n:
                    return n
    except Exception:
        pass
    return add_menu._op_label(op)


def _enum_options(data, prop):
    """[(identifier, name, icon)] of an enum field. Dynamic enums only list the
    current value through RNA; the render engine is rebuilt from the engines."""
    p = _rna_prop(data, prop)
    items = [(e.identifier, e.name, e.icon) for e in p.enum_items]
    if prop == "engine" and isinstance(data, bpy.types.RenderSettings):
        items = [("BLENDER_EEVEE", "EEVEE", "NONE"), ("BLENDER_WORKBENCH", "Workbench", "NONE")]
        for eng in bpy.types.RenderEngine.__subclasses__():
            idn = getattr(eng, "bl_idname", "")
            if idn and idn not in {i[0] for i in items}:
                items.append((idn, getattr(eng, "bl_label", idn), "NONE"))
    return items


def _rna_prop(data, prop):
    try:
        return data.bl_rna.properties[prop]
    except (AttributeError, KeyError):
        return None


def _field_rows(data, prop, text=None, index=-1):
    """One row per editable field; arrays without an index become one row per item;
    an ID pointer becomes a datablock picker."""
    p = _rna_prop(data, prop)
    if p is None or p.is_readonly:
        return []
    if p.type == "POINTER":
        return _id_rows(data, prop, text)
    if p.type not in {"BOOLEAN", "INT", "FLOAT", "ENUM"} or (p.type == "ENUM" and p.is_enum_flag):
        return []
    label = (text or "").strip() or p.name
    if getattr(p, "is_array", False) and index in (-1, None):
        names = ("RGBA" if p.subtype in {"COLOR", "COLOR_GAMMA"} else "XYZW") \
            if p.array_length <= 4 else [str(i) for i in range(p.array_length)]
        return [{"text": f"{label} {names[i]}", "data": data, "prop": prop, "index": i}
                for i in range(p.array_length)]
    return [{"text": label, "data": data, "prop": prop, "index": None if index in (-1, None) else index}]


def _id_collection(type_name):
    """bpy.data's collection of datablocks of this RNA type ('Material' -> bpy.data.materials)."""
    for p in bpy.data.bl_rna.properties:
        if p.type == "COLLECTION" and getattr(p.fixed_type, "identifier", "") == type_name:
            return getattr(bpy.data, p.identifier)
    return None


def _id_rows(data, prop, text=None, new_op=""):
    """A datablock picker: a submenu of the datablocks that fit, plus New."""
    p = _rna_prop(data, prop)
    if p is None or p.type != "POINTER" or p.is_readonly:
        return []
    type_name = p.fixed_type.identifier
    if type_name == "ID":  # a generic pointer (e.g. Object.data): the current value's type
        cur = getattr(data, prop, None)
        type_name = cur.bl_rna.identifier if cur is not None else ""
    coll = _id_collection(type_name)
    if coll is None:
        return []

    def build():
        rows = [{"text": "(none)", "run": lambda: (setattr(data, prop, None), _back_and_rebuild())}] \
            if not p.is_never_none else []
        for db in coll:
            rows.append({"text": db.name, "run": (lambda db=db: (setattr(data, prop, db), _back_and_rebuild()))})
        if hasattr(coll, "new"):
            rows.append({"text": "New", "run": lambda: _new_id(coll, type_name, data, prop)})
        return rows

    def current():
        v = getattr(data, prop, None)
        return getattr(v, "name", "—") if v is not None else "—"

    return [{"text": text or p.name, "build": build, "value": current}]


def _new_id(coll, type_name, data, prop):
    try:
        db = coll.new(type_name)
    except TypeError:
        raise RuntimeError(f"cannot make a new {type_name} here")
    if type_name in {"Material", "World"}:
        db.use_nodes = True
    setattr(data, prop, db)
    _back_and_rebuild()


def _list_rows(dataptr, propname, active_dataptr, active_propname):
    """A list (template_list): a submenu whose rows make an item the active one."""
    coll = getattr(dataptr, propname, None)
    if coll is None or active_dataptr is None:
        return []
    label = _rna_prop(dataptr, propname).name if _rna_prop(dataptr, propname) else propname

    def build():
        rows = []
        for i, item in enumerate(coll):
            name = getattr(item, "name", "") or f"#{i}"
            rows.append({"text": name, "run": (lambda i=i: (setattr(active_dataptr, active_propname, i), _rebuild())),
                         "value": (lambda i=i: "active" if getattr(active_dataptr, active_propname, -1) == i else "")})
        return rows

    def current():
        i = getattr(active_dataptr, active_propname, -1)
        return getattr(coll[i], "name", str(i)) if 0 <= i < len(coll) else "—"

    return [{"text": label, "build": build, "value": current}]


def _action_row(text, op, props):
    return {"text": text, "run": lambda: _run_and_rebuild(op, props)}


def _run_and_rebuild(op, props, call="INVOKE_DEFAULT"):
    from .blender_glue import run_operator

    obj = bpy.context.object
    with bpy.context.temp_override(object=obj, active_object=obj):
        result = run_operator(op, props, call)
    _rebuild()
    return result


def _panel_rows(context_name, tab):
    """Rows of the Python Properties panels of one tab (subpanels as submenus)."""
    ctx = _ButtonsContext(tab)
    panels = [c for c in bpy.types.Panel.__subclasses__()
              if getattr(c, "bl_space_type", "") == "PROPERTIES" and getattr(c, "bl_context", "") == context_name]
    panels.sort(key=_panel_order)
    parents = [c for c in panels if not getattr(c, "bl_parent_id", "")]

    def record(cls):
        out = []
        fake = _FakePanel(cls, _PropRecorder(out))
        for fn in ("draw_header", "draw"):
            if hasattr(cls, fn):
                try:
                    getattr(cls, fn)(fake, ctx)
                except Exception:
                    pass
        return out

    def rows_of(cls):
        try:
            if hasattr(cls, "poll") and not cls.poll(ctx):
                return []
        except Exception:
            return []
        rows, seen = [], set()
        for rec in record(cls):
            kind = rec[0]
            if kind == "prop":
                _, data, prop, text, index, invert = rec
                if data is None or (id(data), prop, index) in seen:
                    continue
                seen.add((id(data), prop, index))
                for r in _field_rows(data, prop, text, index):
                    r["invert"] = invert
                    rows.append(r)
            elif kind == "op":
                _, op, text, p, icon = rec
                props = dict(p._d)
                row = _action_row(text or _button_label(op, props), op, props)
                row["icon"] = icon
                rows.append(row)
            elif kind == "enum_menu":
                _, op, prop, text = rec
                items = add_menu._enum_items(op, prop)
                if items:
                    rows.append({"text": text or add_menu._op_label(op),
                                 "build": (lambda op=op, prop=prop, items=items:
                                           [_action_row(n, op, {prop: i}) for i, n in items])})
            elif kind == "list":
                rows += _list_rows(*rec[1:])
            elif kind == "curve":
                _, data, prop = rec
                if data is not None:
                    rows.append({"text": _rna_prop(data, prop).name if _rna_prop(data, prop) else prop,
                                 "curve": (data, prop)})
            elif kind == "id":
                _, data, prop, new = rec
                if data is not None:
                    rows += _id_rows(data, prop)
        for child in panels:
            if getattr(child, "bl_parent_id", "") == cls.__name__:
                if rows_of(child):
                    rows.append({"text": getattr(child, "bl_label", child.__name__),
                                 "build": (lambda c=child: rows_of(c))})
        return rows

    rows = []
    for cls in parents:
        sub = rows_of(cls)
        if not sub:
            continue
        if "HIDE_HEADER" in getattr(cls, "bl_options", set()) or not getattr(cls, "bl_label", ""):
            rows += sub  # a panel without a header: its rows belong to the tab itself
        else:
            rows.append({"text": cls.bl_label, "build": (lambda c=cls: rows_of(c))})
    return rows


# --- Modifiers and constraints (drawn in C) -------------------------------------------

def _rna_rows(item, first=()):
    rows = []
    for name in first:
        rows += _field_rows(item, name)
    for p in item.bl_rna.properties:
        if p.identifier in SKIP or p.identifier in first or p.identifier.startswith("show_"):
            continue
        rows += _field_rows(item, p.identifier)
    return rows


def _modifier_rows(obj, mod):
    rows = [{"text": "Show in Viewport", "data": mod, "prop": "show_viewport", "index": None},
            {"text": "Show in Render", "data": mod, "prop": "show_render", "index": None}]
    rows += _rna_rows(mod)
    name = mod.name
    rows.append({"text": "Apply", "run": lambda: _item_op("object.modifier_apply", obj, {"modifier": name})})
    rows.append({"text": "Delete", "run": lambda: _item_op("object.modifier_remove", obj, {"modifier": name})})
    return rows


def _constraint_rows(obj, con):
    rows = _rna_rows(con, first=("mute", "influence", "target", "subtarget"))
    name = con.name
    rows.append({"text": "Apply", "run": lambda: _item_op("constraint.apply", obj, {"constraint": name, "owner": "OBJECT"})})
    rows.append({"text": "Delete", "run": lambda: _item_op("constraint.delete", obj, {"constraint": name, "owner": "OBJECT"})})
    return rows


def _item_op(op, obj, props):
    from .blender_glue import run_operator

    if bpy.context.mode != "OBJECT" and op.endswith("apply"):
        raise RuntimeError("Apply works in Object Mode")
    with bpy.context.temp_override(object=obj, active_object=obj):
        result = run_operator(op, props)
    _back_and_rebuild()
    return result


def _add_rows(menu_items, after):
    """Blender's Add menu items as actions; running one goes back to the list."""
    out = []
    for it in menu_items:
        if "items" in it:
            out.append({"text": it["text"], "build": (lambda sub=it["items"]: _add_rows(sub, after))})
        else:
            out.append({"text": it["text"], "run": (lambda it=it: after(it))})
    return out


def _added(item):
    from .blender_glue import run_operator

    obj = bpy.context.object
    with bpy.context.temp_override(object=obj, active_object=obj):
        result = run_operator(item["op"], item["props"])
    while len(_stack) > 2:  # back to Properties › Modifiers/Constraints
        _stack.pop()
    _rebuild()
    level = _stack[-1]
    level["index"] = len(level["items"]) - 1  # the new one, last in the stack
    _sync_properties()
    return result


def _modifiers_rows():
    obj = bpy.context.object
    if obj is None:
        return []
    rows = [{"text": "Add Modifier", "build": lambda: _add_rows(add_menu.read_menu("OBJECT_MT_modifier_add"), _added)}]
    for mod in obj.modifiers:
        rows.append({"text": mod.name, "build": (lambda m=mod: _modifier_rows(obj, m)), "modifier": mod.name})
    return rows


def _constraints_rows():
    obj = bpy.context.object
    if obj is None:
        return []
    add = [{"text": e.name, "op": "object.constraint_add", "props": {"type": e.identifier}}
           for e in bpy.types.Constraint.bl_rna.properties["type"].enum_items]
    rows = [{"text": "Add Constraint", "build": lambda: _add_rows(add, _added)}]
    for con in obj.constraints:
        rows.append({"text": con.name, "build": (lambda c=con: _constraint_rows(obj, c)), "constraint": con.name})
    return rows


# --- Node surfaces (Material, World) ------------------------------------------------

def _surface_node(tree, output_type):
    """The node plugged into the active output's Surface input, or None."""
    if tree is None:
        return None
    outputs = [n for n in tree.nodes if n.type == output_type]
    out = next((n for n in outputs if getattr(n, "is_active_output", False)), outputs[0] if outputs else None)
    if out is None or "Surface" not in out.inputs or not out.inputs["Surface"].is_linked:
        return None
    return out.inputs["Surface"].links[0].from_node


def _node_rows(node):
    rows = []
    for sock in node.inputs:
        if sock.is_linked or not getattr(sock, "enabled", True) or not hasattr(sock, "default_value"):
            continue
        rows += _field_rows(sock, "default_value", sock.name)
    return rows


def _surface_rows(idblock, output_type):
    """The surface shader's inputs; 'Use Nodes' when the datablock has none."""
    if idblock is None:
        return []
    if not idblock.use_nodes:
        return [{"text": "Surface", "build": lambda: [
            {"text": "Use Nodes", "run": lambda: (setattr(idblock, "use_nodes", True), _rebuild())}]}]
    node = _surface_node(idblock.node_tree, output_type)
    if node is None:
        return []
    return [{"text": f"Surface: {node.name}", "build": lambda: _node_rows(node)}]


# --- Material slots ------------------------------------------------------------------

def _material_rows():
    """The surface shader's inputs, then Blender's own Material panels (slots list,
    material picker, settings)."""
    obj = bpy.context.object
    rows = _surface_rows(obj.active_material, "OUTPUT_MATERIAL") if obj is not None else []
    return rows + _panel_rows("material", "MATERIAL")


def _world_rows():
    scene = bpy.context.scene
    return _surface_rows(scene.world, "OUTPUT_WORLD") + _panel_rows("world", "WORLD")


# --- The tabs ----------------------------------------------------------------------

def _root_rows():
    obj = bpy.context.object
    rows = []
    for label, tab, ctx_name in TABS:
        if tab in {"OBJECT", "PHYSICS", "CONSTRAINT", "DATA"} and obj is None:
            continue
        if tab == "MODIFIER" and (obj is None or obj.type not in MODIFIER_TYPES):
            continue
        if tab == "PARTICLES" and (obj is None or obj.type != "MESH"):
            continue
        if tab == "MATERIAL" and (obj is None or obj.type not in MATERIAL_TYPES):
            continue
        if tab == "DATA":
            if obj.data is None:
                continue
            label = obj.type.replace("_", " ").title().replace("Greasepencil", "Grease Pencil")
        build = {"MODIFIER": _modifiers_rows, "CONSTRAINT": _constraints_rows,
                 "MATERIAL": _material_rows, "WORLD": _world_rows}.get(tab)
        if build is None:
            build = (lambda c=ctx_name, t=tab: _panel_rows(c, t))
        if tab == "TEXTURE" and not build():
            continue  # nothing to show there for this object
        rows.append({"text": label, "build": build, "tab": tab, "icon": _TAB_ICONS.get(tab, "NONE")})
    return rows


_TAB_ICONS = {e.identifier: e.icon for e in bpy.types.SpaceProperties.bl_rna.properties["context"].enum_items}
_TAB_ICONS["DATA"] = "MESH_DATA"


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
    if "value" in item:
        try:
            return item["value"]()
        except Exception:
            return "?"
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
            try:
                level["items"] = level["build"]()
            except Exception:
                level["items"] = []
            level["index"] = min(level["index"], max(0, len(level["items"]) - 1))
    _redraw()


def _back_and_rebuild():
    if len(_stack) > 1:
        _stack.pop()
    _rebuild()


def _sync_properties():
    """The real Properties editor shows the tab (and the modifier/constraint) being edited."""
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
    if obj is None:
        return
    for key, coll in (("modifier", getattr(obj, "modifiers", None)), ("constraint", obj.constraints)):
        name = next((lv.get(key) for lv in _stack if lv.get(key)), None)
        if coll is not None and name and name in coll:
            for m in coll:
                m.show_expanded = m.name == name
            try:
                coll.active = coll[name]
            except AttributeError:
                pass


def toggle():
    """IN: open / enter / run / flip / start or keep an edit."""
    global _edit, _acc
    if not _stack:
        rows = _root_rows()
        if not rows:
            raise RuntimeError("nothing to show")
        _stack.append({"title": "Properties", "build": _root_rows, "items": rows,
                       "index": next((i for i, r in enumerate(rows) if r["text"] == "Object"), 0)})
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
        try:
            items = item["build"]()
        except Exception as e:
            raise RuntimeError(f"{item['text']}: {e}")
        _stack.append({"title": item["text"], "build": item["build"], "items": items, "index": 0,
                       "icon": item.get("icon") if item.get("tab") else None,
                       "tab": item.get("tab"), "modifier": item.get("modifier"),
                       "constraint": item.get("constraint")})
        _acc = 0.0
        _sync_properties()
    elif "run" in item:
        item["run"]()
    elif "data" in item:
        p = _rna_prop(item["data"], item["prop"])
        if p.type == "BOOLEAN":
            _set(item, not _get(item))
        elif p.type == "ENUM":  # its options, as a level: IN picks one and goes back
            def options(item=item):
                cur = _get(item)
                return [{"text": name, "icon": icon,
                         "run": (lambda i=ident: (_set(item, i), _stack.pop(), _rebuild())),
                         "value": (lambda i=ident: "●" if _get(item) == i else "")}
                        for ident, name, icon in _enum_options(item["data"], item["prop"])]
            opts = options()
            cur = _get(item)
            _stack.append({"title": item["text"], "build": options, "items": opts,
                           "index": next((n for n, o in enumerate(opts) if o["value"]() == "●"), 0)})
            _acc = 0.0
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
            # Blender's own increment for the field (the one dragging it uses), times
            # the S1 VOL factor 1-10 (amount comes scaled 0.01-0.10); angles 1-10°.
            factor = abs(amount) / 0.01
            if p.subtype in ANGLES:
                delta = math.radians(factor)
            else:
                base = p.step / 100 if p.step else 0.01
                if p.soft_max - p.soft_min <= 1.0:  # factors (0-1): fine steps
                    base = min(base, 0.01)
                delta = base * factor
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
    """OUT (short press): while editing, put the old value back; else one level
    back; at the top, close."""
    global _edit, _acc
    if _edit is not None:
        _set(_edit["item"], _edit["old"])
        _edit = None
        _redraw()
        return {"FINISHED"}
    if len(_stack) > 1:
        _stack.pop()
        _acc = 0.0
        _rebuild()
        _sync_properties()
        return {"FINISHED"}
    close()
    return {"FINISHED"}


def close_all():
    """SYNC, or a long OUT press: close the menu from any level (an edit is undone)."""
    global _edit
    if _edit is not None:
        _set(_edit["item"], _edit["old"])
        _edit = None
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


# --- The 4-Mix Properties window (Blender's own widgets) -----------------------
# A separate window whose single area is an empty Image Editor; its sidebar
# shows the current level with Blender's widgets (icons, dropdowns, curve
# widgets). While such a window exists, the viewport overlay is not drawn.

WINDOW_SCREEN = "4-Mix Properties"


def window_open():
    wm = bpy.context.window_manager
    return any(w.screen.name == WINDOW_SCREEN for w in (wm.windows if wm else ()))


def _draw_row(layout, item, current):
    row = layout.row(align=True)
    row.alert = current
    row.label(text="", icon="TRIA_RIGHT" if current else "BLANK1")
    icon = item.get("icon") or "NONE"
    if "data" in item:
        kw = {"text": item["text"]}
        if item["index"] is not None:
            kw["index"] = item["index"]
        if item.get("invert"):
            kw["invert_checkbox"] = True
        try:
            row.prop(item["data"], item["prop"], **kw)
        except Exception:
            row.label(text=f"{item['text']}: ?")
    elif "curve" in item:
        row.label(text=item["text"], icon="FCURVE")
        try:
            layout.template_curve_mapping(*item["curve"])
        except Exception:
            layout.label(text="(curve)")
    elif "build" in item:
        value = _value_text(item)
        row.label(text=item["text"], icon=icon if icon != "NONE" else "RIGHTARROW_THIN")
        if value:
            row.label(text=value)
    else:  # an action
        row.label(text=item["text"], icon=icon if icon != "NONE" else "PLAY")


class CONTROLSURFACE_PT_props_window(bpy.types.Panel):
    bl_label = "Properties"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "4-Mix"

    @classmethod
    def poll(cls, context):
        return context.screen is not None and context.screen.name == WINDOW_SCREEN

    def draw(self, context):
        layout = self.layout
        if not _stack:
            layout.label(text="Deck B: IN opens the Properties", icon="INFO")
            return
        level = _stack[-1]
        crumbs = " › ".join(lv["title"] for lv in _stack)
        top = layout.row()
        top.label(text=crumbs, icon=next((lv.get("icon") for lv in _stack if lv.get("icon")), "PROPERTIES"))
        if _edit is not None:
            layout.label(text="editing: platter = value, IN keep, OUT undo", icon="GREASEPENCIL")
        col = layout.column(align=False)
        for i, item in enumerate(level["items"]):
            _draw_row(col, item, i == level["index"])
        layout.separator()
        layout.label(text="IN open/set · OUT back (hold: close) · SYNC close")


class CONTROLSURFACE_OT_props_window(bpy.types.Operator):
    bl_idname = "control_surface.props_window"
    bl_label = "Open 4-Mix Properties window"
    bl_description = "A separate window that shows the deck B Properties menu with Blender's own widgets"

    def execute(self, context):
        if window_open():
            self.report({"INFO"}, "the 4-Mix Properties window is already open")
            return {"CANCELLED"}
        win = context.window
        area = next((a for a in win.screen.areas if a.type == "VIEW_3D"), win.screen.areas[0])
        region = next(r for r in area.regions if r.type == "WINDOW")
        with context.temp_override(window=win, area=area, region=region):
            bpy.ops.screen.area_dupli("INVOKE_DEFAULT")
        new = context.window_manager.windows[-1]
        new.screen.name = WINDOW_SCREEN
        target = new.screen.areas[0]
        target.type = "IMAGE_EDITOR"
        target.spaces.active.show_region_ui = True
        # The sidebar's tab can only be chosen once it has been drawn: a moment later.
        bpy.app.timers.register(_select_sidebar_tab, first_interval=0.3)
        _redraw()
        return {"FINISHED"}


def _select_sidebar_tab(tries=[0]):
    wm = bpy.context.window_manager
    for w in wm.windows:
        if w.screen.name == WINDOW_SCREEN:
            for r in w.screen.areas[0].regions:
                if r.type == "UI":
                    try:
                        r.active_panel_category = "4-Mix"
                        w.screen.areas[0].tag_redraw()
                        return None
                    except (AttributeError, TypeError, ValueError):
                        pass
    tries[0] += 1
    return 0.3 if tries[0] < 10 else None


CLASSES = (CONTROLSURFACE_PT_props_window, CONTROLSURFACE_OT_props_window)


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
            if area.type in {"VIEW_3D", "PROPERTIES", "IMAGE_EDITOR"}:
                area.tag_redraw()


def _draw():
    if not _stack or window_open():  # the 4-Mix window shows it with Blender's widgets
        return
    level = _stack[-1]
    rows = [(it["text"], "(curve: see the 4-Mix window)" if "curve" in it else _value_text(it), "build" in it)
            for it in level["items"]] or [("(empty)", None, False)]
    footer = ("platter: value   IN: keep   OUT: undo" if _edit
              else "IN: open/set   OUT: back   SYNC: close")
    add_menu.draw_list(" › ".join(lv["title"] for lv in _stack), rows, level["index"], footer,
                       side="right", editing=_edit is not None)
