## 38. The 4-Mix Properties window (Blender's own widgets)

- **Depends on:** task 37.
- **Contract:**
  - In: Rafael (2026-11-22): icons equal to Blender's and the shutter curve
    widget; he is building the Properties editor "from outside"; chose a
    separate window (proposal 2).
  - Delivers: `CONTROLSURFACE_OT_props_window` (a new window, an empty
    Image Editor, sidebar tab "4-Mix"), `CONTROLSURFACE_PT_props_window`
    (current level with real widgets, cursor row in red), recorded curve
    widgets, tab icons; the overlay hidden while the window exists; a
    button in the DJ-Tech panel; docs, the action list, screenshots
    `review/2026-11-22/janela-4mix-*.png`.
- **Pre-work:** probes: a context-less panel inside a Properties editor
  (lands among the originals, order not controllable), pinning (only the
  Tool tab), the Texture tab (not available).
- **Out of scope:** sizing the window / sidebar (no Python API).
- **Tests:** pytest; windowed Blender checks (window opened, sidebar tab
  4-Mix chosen by the operator, Motion Blur level with checkbox, dropdown
  and sliders, Shutter Curve with the curve widget and preset icons).
