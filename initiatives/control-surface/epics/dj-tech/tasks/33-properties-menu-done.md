## 33. Deck B: the Properties menu (Object, Modifiers)

- **Depends on:** task 32.
- **Contract:**
  - In: Rafael (2026-11-21): a solution like the Add menu for the
    Properties editor; deck B, Object and Modifiers first, the real
    Properties editor follows. Explained how to add a Mirror modifier.
  - Delivers: `props_menu.py` (rows from Blender's own panels / modifier
    RNA / Add Modifier menu, values live, editing with the platter, OUT
    reverts, Properties sync); `add_menu.draw_list` shared drawing (left /
    right); `read_menu` binds the menu class's helpers; deck B bindings and
    LEDs; docs, the action list, a screenshot.
- **Pre-work:** none.
- **Out of scope:** other tabs (Data, Material, …); undo steps for value
  changes; template fields (lists, curves, ramps, datablock pickers).
- **Tests:** pytest; windowed Blender check through MIDI messages (Add
  Modifier › Generate › Mirror added, fields listed, a flip, Merge Distance
  0.001 → 0.031 → OUT back, Properties tab MODIFIER with Mirror expanded,
  screenshot `review/2026-11-21/menu-properties-deck-b.png`); the Object
  tab's Transform and Visibility fields (degrees, inverted checkboxes).
