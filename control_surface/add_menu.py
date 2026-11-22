"""Blender's Add menu (Shift+A), driven by the controller and drawn by the add-on.

An open Blender menu only answers the mouse and the keyboard, so the add-on
reads the menu's structure instead: it calls the menu classes' draw() with a
recording layout (`_Recorder`), which gives exactly Blender's items, add-ons'
items included, for the current mode. The list is drawn in the 3D View
(POST_PIXEL) with the current item highlighted.

- `toggle()` (deck A IN): closed -> open at the top; open -> enter the
  highlighted submenu, or run the highlighted item (in the 3D View, like the
  menu) and close.
- `step(pulses)` (deck A platter): one item every PULSES_PER_ITEM pulses.
- `close()` (deck A OUT): cancel, the menu closes without adding.
- `back()`: one level up; at the top, close (not bound now).
"""

import types

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader

PULSES_PER_ITEM = 390 / 27  # like the cage: ~14 platter pulses per item
VISIBLE = 14                # items shown around the highlighted one

# Shift+A's menu per mode (the keymaps call these).
ROOT_MENUS = {
    "OBJECT": "VIEW3D_MT_add",
    "EDIT_MESH": "VIEW3D_MT_mesh_add",
    "EDIT_CURVE": "VIEW3D_MT_curve_add",
    "EDIT_SURFACE": "VIEW3D_MT_surface_add",
    "EDIT_METABALL": "VIEW3D_MT_metaball_add",
    "EDIT_ARMATURE": "TOPBAR_MT_edit_armature_add",
}

_stack = []   # [{"title", "items", "index"}], empty = closed
_acc = 0.0    # platter pulses not yet turned into a step
_handle = None


# --- Reading a menu ----------------------------------------------------------

class _Props:
    def __init__(self):
        object.__setattr__(self, "_d", {})

    def __setattr__(self, k, v):
        self._d[k] = v

    def __getattr__(self, k):
        return None


class _Recorder:
    """A fake UILayout: records operator / menu / enum calls, ignores the rest."""

    def __init__(self, out):
        object.__setattr__(self, "out", out)

    def operator(self, op, text=None, icon=None, **kw):
        p = _Props()
        self.out.append(("op", op, text, p))
        return p

    def menu(self, name, text=None, icon=None, **kw):
        self.out.append(("menu", name, text))

    def menu_contents(self, name):
        self.out.append(("menu", name, None))

    def operator_enum(self, op, prop, **kw):
        self.out.append(("enum_flat", op, prop, None))

    def operator_menu_enum(self, op, prop, text=None, icon=None, **kw):
        self.out.append(("enum_menu", op, prop, text))

    def __getattr__(self, name):
        return lambda *a, **k: self  # row(), column(), separator(), label() ...

    def __setattr__(self, k, v):
        pass  # operator_context, enabled, ...


def _op_label(op):
    try:
        mod, name = op.split(".", 1)
        return getattr(getattr(bpy.ops, mod), name).get_rna_type().name
    except Exception:
        return op


def _enum_items(op, prop):
    try:
        mod, name = op.split(".", 1)
        p = getattr(getattr(bpy.ops, mod), name).get_rna_type().properties[prop]
        return [(e.identifier, e.name) for e in p.enum_items]
    except Exception:
        return []


def read_menu(name, depth=0):
    """[{"text", "op", "props"} | {"text", "items": [...]}] for Blender menu `name`."""
    cls = getattr(bpy.types, name, None)
    if cls is None or depth > 4:
        return []
    out = []

    class Fake:
        """Stands in for the menu instance: the layout is the recorder, and the
        menu class's own helpers (e.g. operator_modifier_add) are bound to it."""

        def __getattr__(self, k):
            v = getattr(cls, k)
            return types.MethodType(v, self) if isinstance(v, types.FunctionType) else v

    fake = Fake()
    fake.layout = _Recorder(out)
    try:
        cls.draw(fake, bpy.context)
    except Exception:
        return []
    items = []
    for rec in out:
        kind = rec[0]
        if kind == "op":
            items.append({"text": rec[2] or _op_label(rec[1]), "op": rec[1], "props": dict(rec[3]._d)})
        elif kind == "menu":
            sub = read_menu(rec[1], depth + 1)
            if sub:
                label = rec[2] or getattr(getattr(bpy.types, rec[1], None), "bl_label", rec[1])
                items.append({"text": label, "items": sub})
        else:
            _, op, prop, text = rec
            enum = [{"text": n, "op": op, "props": {prop: i}} for i, n in _enum_items(op, prop)]
            if kind == "enum_flat":
                items.extend(enum)
            elif enum:
                items.append({"text": text or _op_label(op), "items": enum})
    return items


# --- State and actions -------------------------------------------------------

def is_open():
    return bool(_stack)


def _mode():
    return bpy.context.mode


def toggle():
    """IN: open; on an item: enter its submenu, or run it and close."""
    global _acc
    if not _stack:
        root = ROOT_MENUS.get(_mode())
        if root is None:
            raise RuntimeError(f"no Add menu in {_mode()}")
        items = read_menu(root)
        if not items:
            raise RuntimeError("the Add menu is empty here")
        _stack.append({"title": "Add", "items": items, "index": 0})
        _acc = 0.0
        _show()
        return {"FINISHED"}
    level = _stack[-1]
    item = level["items"][level["index"]]
    if "items" in item:
        _stack.append({"title": item["text"], "items": item["items"], "index": 0})
        _acc = 0.0
        _redraw()
        return {"FINISHED"}
    close()
    from .blender_glue import run_operator  # 3D View context, like the menu
    return run_operator(item["op"], item["props"], "INVOKE_DEFAULT")


def step(pulses):
    """Platter: one item every PULSES_PER_ITEM pulses, wrapping."""
    global _acc
    if not _stack:
        return {"FINISHED"}
    if _acc * pulses < 0:  # turned the other way: count again
        _acc = 0.0
    _acc += pulses
    n = int(_acc / PULSES_PER_ITEM)
    if n:
        _acc -= n * PULSES_PER_ITEM
        level = _stack[-1]
        level["index"] = (level["index"] + n) % len(level["items"])
        _redraw()
    return {"FINISHED"}


def back():
    """OUT: one level up; at the top, close."""
    global _acc
    if _stack:
        _stack.pop()
        _acc = 0.0
    if not _stack:
        close()
    _redraw()
    return {"FINISHED"}


def close():
    global _handle
    _stack.clear()
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
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _rect(shader, x, y, w, h, color):
    shader.uniform_float("color", color)
    batch_for_shader(shader, "TRIS", {"pos": [(x, y), (x + w, y), (x + w, y + h), (x, y), (x + w, y + h), (x, y + h)]},
                     ).draw(shader)


def draw_list(title, rows, idx, footer, side="left", editing=False):
    """Draw a menu box in the current 3D View region.

    rows: [(text, value or None, has_submenu)]; idx: the highlighted row;
    side: "left" (right of the toolbar) or "right" (left of the sidebar);
    editing: the highlighted row's value is being changed (another colour).
    """
    scale = bpy.context.preferences.system.ui_scale
    size, line, pad = int(13 * scale), int(20 * scale), int(10 * scale)
    region = bpy.context.region
    first = max(0, min(idx - VISIBLE // 2, len(rows) - VISIBLE))
    shown = rows[first:first + VISIBLE]
    values = any(r[1] is not None for r in rows)
    width = int((360 if values else 260) * scale)
    height = line * (len(shown) + 2) + pad
    regions = bpy.context.area.regions
    if side == "left":
        # Right of the toolbar and below the view's name text (they overlap the region).
        x = next((r.width for r in regions if r.type == "TOOLS"), 0) + int(16 * scale)
    else:
        ui = next((r.width for r in regions if r.type == "UI" and r.width > 1), 0)
        x = region.width - ui - width - int(70 * scale)  # clear of the navigation gizmo
    y_top = region.height - int(110 * scale)
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    _rect(shader, x, y_top - height, width, height, (0.1, 0.1, 0.1, 0.85))
    font = 0
    blf.size(font, size)
    blf.color(font, 1.0, 0.6, 0.1, 1.0)
    blf.position(font, x + pad, y_top - line, 0)
    blf.draw(font, title)
    for i, (text, value, sub) in enumerate(shown):
        y = y_top - line * (i + 2)
        current = first + i == idx
        if current:
            colour = (0.75, 0.45, 0.15, 0.9) if editing else (0.28, 0.45, 0.75, 0.9)
            _rect(shader, x + 4, y - int(5 * scale), width - 8, line, colour)
        blf.color(font, 1.0, 1.0, 1.0, 1.0 if current else 0.8)
        blf.position(font, x + pad, y, 0)
        blf.draw(font, text + ("  ›" if sub else ""))
        if value is not None:
            blf.color(font, 0.85, 0.9, 1.0, 1.0 if current else 0.75)
            blf.position(font, x + int(width * 0.62), y, 0)
            blf.draw(font, value)
    blf.color(font, 0.7, 0.7, 0.7, 0.8)
    blf.position(font, x + pad, y_top - height + int(6 * scale), 0)
    blf.draw(font, f"{idx + 1}/{len(rows)}   {footer}")
    gpu.state.blend_set("NONE")


def _draw():
    if not _stack:
        return
    level = _stack[-1]
    rows = [(it["text"], None, "items" in it) for it in level["items"]]
    draw_list(" › ".join(lv["title"] for lv in _stack), rows, level["index"],
              "IN: open/insert   OUT: cancel")
