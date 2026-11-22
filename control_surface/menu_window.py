"""The 4-Mix window: the deck menus (Add, Properties) drawn with Blender's own widgets.

It follows the menus (task 42): `follow()` runs on every menu change and opens
the window when a menu opens, sizes it to the current level, and closes it when
both menus are closed. The window is an NLA editor without header, channels or
footer, as wide as its sidebar, whose tab "4-Mix" draws the level (icons, dropdowns, checkboxes,
sliders, curve widgets). Mouse: a row click works like IN, the field widgets
edit directly, ◀ is OUT and ✕ is SYNC. A click outside the window (the
window loses the keyboard focus) closes both menus, like SYNC.

Blender's API cannot size, place or focus a window, so `oswindow` does it
through user32. The position the window was left at is remembered in Blender's
config folder.
"""

import json
import os

import bpy

from . import add_menu, oswindow, props_menu

WINDOW_SCREEN = "4-Mix Properties"
CATEGORY = "4-Mix"
WATCH_S = 0.1             # focus check period
MAX_HEIGHT_FRACTION = 0.85  # of the main window's height; longer levels scroll
# The NLA editor's sidebar is the only one that shows a single tab (ours) and an
# opaque background (probed 2026-11-22 against Image, Text, Node, Sequencer and
# Spreadsheet editors, which add Tool/View/Text/Filters tabs or a grid behind).
SPACE = "NLA_EDITOR"
ROW_UNITS = 1.1           # a row's height in UI units (20 px × ui_scale)
CURVE_UNITS = 9           # a curve widget with its buttons, in rows
MARGIN_UNITS = 1.0        # sidebar padding above and below the panel, in rows

_hwnd = None        # the 4-Mix OS window
_main_hwnd = None   # Blender's main OS window (for the default position)
_had_focus = False  # the window got the keyboard after it settled
_settled = False    # sized, placed and focused: from then on, losing the focus closes
_size = None        # (w, h) last client size set
_units = 0.0        # the drawn level's height in rows, from the panel's draw


# --- Finding, opening, closing --------------------------------------------------

def window():
    wm = bpy.context.window_manager
    return next((w for w in (wm.windows if wm else ()) if w.screen.name == WINDOW_SCREEN), None)


def is_open():
    return window() is not None


def _wanted():
    return props_menu.is_open() or add_menu.is_open()


def follow():
    """Called on every menu change: open, refit or close the window."""
    try:
        win = window()
        if _wanted():
            if win is None:
                _open()
            else:
                _fit()
        elif win is not None:
            _close(win)
    except Exception as e:  # the overlay still shows the menu
        print(f"control_surface: 4-Mix window: {e}")


def _open():
    global _hwnd, _main_hwnd, _had_focus, _size, _settled
    wm = bpy.context.window_manager
    main = next(w for w in wm.windows if w.screen.name != WINDOW_SCREEN)
    area = next((a for a in main.screen.areas if a.type == "VIEW_3D"), main.screen.areas[0])
    region = next(r for r in area.regions if r.type == "WINDOW")
    before = oswindow.process_windows()
    _main_hwnd = oswindow.foreground() or (next(iter(before)) if len(before) == 1 else _main_hwnd)
    with bpy.context.temp_override(window=main, area=area, region=region):
        bpy.ops.screen.area_dupli("INVOKE_DEFAULT")
    new = wm.windows[-1]
    new.screen.name = WINDOW_SCREEN
    target = new.screen.areas[0]
    target.type = SPACE
    space = target.spaces.active
    space.show_region_ui = True
    for name in ("show_region_header", "show_region_channels", "show_region_footer", "show_region_hud"):
        if hasattr(space, name):
            setattr(space, name, False)
    fresh = oswindow.process_windows() - before
    _hwnd = next(iter(fresh)) if len(fresh) == 1 else None
    _had_focus = False
    _settled = False
    _size = None
    if not bpy.app.timers.is_registered(_settle):
        bpy.app.timers.register(_settle, first_interval=0.05)
    if not bpy.app.timers.is_registered(_watch):
        bpy.app.timers.register(_watch, first_interval=WATCH_S)


def _close(win):
    global _hwnd, _size
    _save_position()
    try:
        with bpy.context.temp_override(window=win):
            bpy.ops.wm.window_close()
    except RuntimeError as e:
        print(f"control_surface: closing the 4-Mix window: {e}")
    _hwnd = None
    _size = None


def close():
    """Unregister: close the window whatever the menus say."""
    win = window()
    if win is not None:
        _close(win)


# --- Sidebar tab, size and position ---------------------------------------------

def _sidebar(win):
    return next((r for r in win.screen.areas[0].regions if r.type == "UI"), None)


def _settle():
    """After the window first draws: pick the 4-Mix tab, then size, place and focus it."""
    global _settled
    win = window()
    if win is None:
        return None
    ui = _sidebar(win)
    try:
        if ui is None or ui.width <= 1:
            raise ValueError("not drawn yet")
        ui.active_panel_category = CATEGORY
    except (AttributeError, TypeError, ValueError):
        _settle.tries = getattr(_settle, "tries", 0) + 1
        if _settle.tries < 40:
            return 0.05
    _settle.tries = 0
    win.screen.areas[0].tag_redraw()
    _fit(first=True)
    oswindow.focus(_hwnd)  # it takes the keyboard, so a click elsewhere is noticed
    _settled = True
    return None


def _unit():
    return 20 * bpy.context.preferences.system.ui_scale


def _fit(first=False):
    """Client size: the sidebar's width, the level's rows high (capped); position kept,
    or the remembered one when the window has just opened."""
    global _size
    win = window()
    if win is None or _hwnd is None:
        return
    ui = _sidebar(win)
    if ui is None or ui.width <= 1:
        return
    unit = _unit()
    w = ui.width + 2  # any narrower and Blender hides the sidebar (area too small)
    main = oswindow.rect(_main_hwnd)
    cap = (main[3] if main else 1400) * MAX_HEIGHT_FRACTION
    h = int(min(max(_units, 3) * unit * ROW_UNITS + MARGIN_UNITS * unit, cap))
    if not first and _size == (w, h):
        return
    if first:
        x, y = _start_position(w)
    else:
        x, y = (oswindow.rect(_hwnd) or (0, 0))[:2]
    oswindow.place(_hwnd, x, y, w, h)
    _size = (w, h)


def _config_file():
    return os.path.join(bpy.utils.user_resource("CONFIG"), "control_surface_window.json")


def _start_position(w):
    try:
        with open(_config_file(), encoding="utf-8") as f:
            p = json.load(f)
        return int(p["x"]), int(p["y"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    main = oswindow.rect(_main_hwnd)
    if main:  # near the top right of the main window, over the viewport
        return main[0] + main[2] - w - 80, main[1] + 120
    return 100, 100


def _save_position():
    r = oswindow.rect(_hwnd)
    if not r:
        return
    try:
        with open(_config_file(), "w", encoding="utf-8") as f:
            json.dump({"x": r[0], "y": r[1]}, f)
    except OSError:
        pass


# --- Click outside = SYNC ----------------------------------------------------------

def _watch():
    """While the window is open: once it has had the keyboard, losing it closes the menus."""
    global _had_focus
    if window() is None:
        _had_focus = False
        return None
    if _hwnd is None or not oswindow.available():
        return WATCH_S
    fg = oswindow.foreground_any()
    if fg == _hwnd and _settled:
        _had_focus = True
    elif _had_focus and fg:
        _had_focus = False
        close_menus()
        return None
    return WATCH_S


def close_menus():
    """Like SYNC on both decks: an edit in progress is undone, both menus close."""
    if add_menu.is_open():
        add_menu.close_all()
    if props_menu.is_open():
        props_menu.close_all()
    follow()


# --- Drawing -----------------------------------------------------------------

def _draw_row(layout, item, current, index):
    """One row of the Properties menu; returns its height in rows."""
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
        return 1
    if "curve" in item:
        row.label(text=item["text"], icon="FCURVE")
        try:
            layout.template_curve_mapping(*item["curve"])
        except Exception:
            layout.label(text="(curve)")
            return 2
        return 1 + CURVE_UNITS
    value = props_menu._value_text(item) if "build" in item else None
    if "build" in item:
        icon = icon if icon != "NONE" else "RIGHTARROW_THIN"
    else:  # an action
        icon = icon if icon != "NONE" else "PLAY"
    _pick_button(row, item["text"], icon, "PROPS", index)
    if value:
        row.label(text=value)
    return 1


def _pick_button(row, text, icon, menu, index):
    """A row's text as a flat button, left-aligned like a label: a click works like IN."""
    sub = row.row(align=True)
    sub.alignment = "LEFT"
    op = sub.operator(CONTROLSURFACE_OT_menu_pick.bl_idname, text=text, icon=icon, emboss=False)
    op.menu, op.index = menu, index


def _nav_row(layout, title, icon, menu):
    """The breadcrumbs, with ◀ (OUT) and ✕ (SYNC) for the mouse."""
    row = layout.row(align=True)
    row.label(text=title, icon=icon)
    op = row.operator(CONTROLSURFACE_OT_menu_back.bl_idname, text="", icon="BACK", emboss=False)
    op.menu = menu
    row.operator(CONTROLSURFACE_OT_menu_close.bl_idname, text="", icon="X", emboss=False)


class CONTROLSURFACE_PT_menu_window(bpy.types.Panel):
    bl_label = "4-Mix"
    bl_space_type = SPACE
    bl_region_type = "UI"
    bl_category = CATEGORY
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return context.screen is not None and context.screen.name == WINDOW_SCREEN

    def draw(self, context):
        global _units
        layout = self.layout
        units = 0.0
        if add_menu.is_open():  # deck A's Add menu, with Shift+A's icons
            lv = add_menu._stack[-1]
            _nav_row(layout, " › ".join(l["title"] for l in add_menu._stack), "ADD", "ADD")
            col = layout.column()
            for i, it in enumerate(lv["items"]):
                row = col.row(align=True)
                row.alert = i == lv["index"]
                row.label(text="", icon="TRIA_RIGHT" if i == lv["index"] else "BLANK1")
                icon = it.get("icon") or ("RIGHTARROW_THIN" if "items" in it else "NONE")
                _pick_button(row, it["text"] + ("  ›" if "items" in it else ""), icon, "ADD", i)
            units += 1 + len(lv["items"])
            if props_menu._stack:
                layout.separator()
                units += 0.5
        if props_menu._stack:
            stack = props_menu._stack
            level = stack[-1]
            _nav_row(layout, " › ".join(lv["title"] for lv in stack),
                     next((lv.get("icon") for lv in stack if lv.get("icon")), "PROPERTIES"), "PROPS")
            units += 1
            if props_menu._edit is not None:
                layout.label(text="editing: platter = value, IN keep, OUT undo", icon="GREASEPENCIL")
                units += 1
            col = layout.column(align=False)
            for i, item in enumerate(level["items"]):
                units += _draw_row(col, item, i == level["index"], i)
        if units != _units:
            _units = units
            if not bpy.app.timers.is_registered(_fit):
                bpy.app.timers.register(_fit, first_interval=0.0)  # not from inside a draw


class CONTROLSURFACE_OT_menu_pick(bpy.types.Operator):
    """Click on a row: like turning the platter to it and pressing IN"""
    bl_idname = "control_surface.menu_pick"
    bl_label = "Pick"
    bl_options = {"INTERNAL"}

    menu: bpy.props.EnumProperty(items=(("PROPS", "Properties", ""), ("ADD", "Add", "")))
    index: bpy.props.IntProperty()

    def execute(self, context):
        mod = add_menu if self.menu == "ADD" else props_menu
        if not mod._stack:
            return {"CANCELLED"}
        level = mod._stack[-1]
        if not 0 <= self.index < len(level["items"]):
            return {"CANCELLED"}
        level["index"] = self.index
        try:
            return mod.toggle()
        except Exception as e:
            self.report({"WARNING"}, str(e))
            return {"CANCELLED"}


class CONTROLSURFACE_OT_menu_back(bpy.types.Operator):
    """One level back (like OUT)"""
    bl_idname = "control_surface.menu_back"
    bl_label = "Back"
    bl_options = {"INTERNAL"}

    menu: bpy.props.EnumProperty(items=(("PROPS", "Properties", ""), ("ADD", "Add", "")))

    def execute(self, context):
        return add_menu.back() if self.menu == "ADD" else props_menu.cancel()


class CONTROLSURFACE_OT_menu_close(bpy.types.Operator):
    """Close the menus (like SYNC)"""
    bl_idname = "control_surface.menu_close"
    bl_label = "Close"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        close_menus()
        return {"FINISHED"}


CLASSES = (CONTROLSURFACE_PT_menu_window, CONTROLSURFACE_OT_menu_pick,
           CONTROLSURFACE_OT_menu_back, CONTROLSURFACE_OT_menu_close)
