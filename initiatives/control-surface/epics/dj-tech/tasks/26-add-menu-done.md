## 26. Deck A: the Add menu

- **Depends on:** task 25.
- **Contract:**
  - In: Rafael (2026-11-21): deck A IN shows the menu, the platter moves to
    the wanted item (the same options as Blender's Add menu); IN on a
    submenu enters it, on an item inserts it.
  - Delivers: `add_menu.py` (menu read from Blender's own classes, drawn in
    the viewport), actions `add_menu_toggle`/`_step`/`_back`, state
    `add_menu`; bindings (IN, OUT = back, platter) and IN's LED; docs.
- **Pre-work:** a probe reading `VIEW3D_MT_add` with a recording layout.
- **Out of scope:** deck C behaviour in Edit Mode (to be decided).
- **Tests:** pytest; a windowed Blender check (17 top items as Blender's,
  Light/Metaball submenus filled, Mesh › UV Sphere inserted, back/close,
  Edit Mode opens the mesh menu) with a screenshot
  (`review/2026-11-21/menu-add-deck-a.png`).
