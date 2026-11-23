## 3. The editor's sliders on the platter: the Human menu

- **Depends on:** task 1; dj-tech tasks 33–42 (the Properties menu,
  `props_menu.py`, and the 4-Mix window, `menu_window.py`).
- **Contract:**
  - In: Rafael (2026-11-23): level 3 of 3, every MPFB slider reachable from
    the controller.
  - Delivers:
    - A menu on deck D (IN opens, platter moves, IN edits, OUT back, SYNC
      closes, as deck B) that lists the 3D View sidebar panels of category
      **Human** (`hm_editor/__init__.py:653`) in their order, and inside each
      its rows, read with the same recording fake layout as
      `props_menu._panel_rows` (`_PropRecorder`): sliders, enums, toggles,
      operators. The panels' `poll` decides what shows, so a plain human
      gets the shape panels and a built one the face and layer panels.
    - Editing a float moves it by the platter, the step as deck B
      (S1 VOL factor); a measure field (`tape_*`, cm) the same.
    - The 4-Mix window shows the Human level (`menu_window.follow`).
    - Docs as in task 1.
  - Not delivered: the editor's own text fields (Name, Find a slider, file
    paths), which stay on the keyboard.
- **Open decisions (Rafael):**
  - **D6** Generalize `props_menu` to read any panel set (Properties editor,
    or the sidebar's tab X), or a separate `human_menu.py` reusing its
    recorder. Proposal: generalize, so any add-on's sidebar tab works later.
  - **D7** Typed measures (`tape_*`) take ~2 s each and Blender waits
    (`docs/character-editor.md`): fire the set only when IN confirms, not on
    every platter pulse. Proposal: yes.
- **Pre-work:** none beyond task 1's.
- **Tests:** pytest: the recorder reads the Human panels from a fake;
  windowed `check_menu_window.py`-style check of the Human level; hardware:
  Rafael changes a nose slider and a typed waist from the platter.
