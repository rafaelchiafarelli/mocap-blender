## 37. Properties menu: OUT goes back, SYNC / long OUT close, Blender's order, enum options

- **Depends on:** task 36.
- **Contract:**
  - In: Rafael (2026-11-22): OUT closing the menu is bad: one level back
    until out; SYNC closes, or OUT held > 0.5 s. Render Engine showed no
    options; the Shutter Curve buttons were unusable; the order must be the
    Properties editor's. (Icons like Blender's, and the curve widget: see
    the proposal in the session — a drawn overlay cannot show them.)
  - Delivers: `cancel` = back, `close_all`; OUT press/release timing
    (`LONG_PRESS_S`); SYNC R/B → close, lit while open; `_panel_order`
    (registration order); enum options as a level (`_enum_options`, render
    engines rebuilt); `_button_label` for icon-only buttons (icons
    recorded); docs, the action list, screenshot
    `review/2026-11-22/menu-properties-render-ordem.png`.
- **Pre-work:** a probe of the render engine enum (RNA lists only the
  current engine) and of the panel order (definition vs registration).
- **Out of scope:** Blender icons and curve widgets (need Blender's own UI).
- **Tests:** pytest; a windowed Blender check through MIDI messages (Render
  rows equal the editor's, engine options and Cycles picked, shutter curve
  presets named, OUT back twice, OUT held 0.8 s closes, SYNC closes).
