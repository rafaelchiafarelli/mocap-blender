## 34. Properties menu: every tab, constraints, node surfaces, lists and pickers

- **Depends on:** task 33.
- **Contract:**
  - In: Rafael (2026-11-21): the other Properties tabs too (camera,
    materials, physics, …); all three stages: every Python tab with its
    buttons; constraints and material/world node inputs; lists. He tests
    the next day.
  - Delivers: `props_menu.py` rewritten: tabs in Blender's order, filtered
    by the object; the recorder keeps buttons, enum menus, lists and
    datablock pickers; `_ButtonsContext` for panels' context members;
    header-less panels inlined; constraints like modifiers; node surface
    inputs; per-field increments (RNA step × S1 VOL factor, factors fine);
    docs, the action list, screenshot `review/2026-11-21/menu-properties-world.png`.
- **Pre-work:** a survey of every tab for a cube, a camera and a light.
- **Out of scope:** undo steps for value changes; curves, colour ramps and
  node trees beyond the surface shader's own inputs.
- **Tests:** pytest; windowed Blender check through MIDI messages (Physics ›
  Cloth; Copy Location with target Camera and influence 0.7; Roughness
  0.5 → 0.7; new material; vertex groups added and picked; lens edit and OUT
  back; world strength 1.0 → 1.4; editor tab followed each time); step
  sizes measured (lens 1 mm, roughness 0.01, location 1 cm, clip 0.1 m).
