## 42. The 4-Mix window follows the menus

- **Depends on:** tasks 38, 40.
- **Contract:**
  - In: Rafael (2026-11-22): the separate window opened by a button is not
    good; the floating menu was liked because it shows only while working
    on it, and the window's icons and widgets (the motion blur curve) were
    liked. The sidebar of the 3D View was rejected. Wanted: the window opens
    with the menu and closes with SYNC/OUT, only as big as needed, without
    the header on top, answering the mouse, and a click outside it closes
    it like SYNC.
  - Delivers: `menu_window.py` (the window opens when the Add or the
    Properties menu opens and closes when both are closed; NLA editor base
    with header/channels/footer hidden; panel `HIDE_HEADER`; sized to the
    sidebar's width and the level's rows on every change; position kept in
    `control_surface_window.json`; focus taken, and losing it closes both
    menus like SYNC; rows clickable as IN, ← OUT, ✕ SYNC), `oswindow.py`
    (user32: find, size, place, focus); the button "Open 4-Mix Properties
    window" and its operator removed; version 0.1.44; README, CLAUDE.md,
    `acoes-4mix.md`; screenshots `review/2026-11-22/janela-4mix-segue-*.png`.
- **Pre-work:** probes (2026-11-22) of the sidebars of Image, NLA, Text,
  Node, Sequencer and Spreadsheet editors: only NLA shows a single tab with
  an opaque background; the Image Editor's tool header does not hide.
  A window narrower than the sidebar hides the sidebar.
- **Out of scope:** the sidebar's width (no Python API); the exact panel
  height (not reported by Blender: estimated from the rows).
- **Tests:** pytest (138, Blender smoke included); a windowed Blender 5.2.2
  check (open by `props_menu.toggle`, clicks through `menu_pick` to Render ›
  Motion Blur › Shutter Curve, window resized at each level, focus on the
  window, focus moved to the main window → both menus closed and the window
  gone, the Add menu opened and closed; screenshots).
