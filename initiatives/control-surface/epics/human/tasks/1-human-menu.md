## 1. The Human menu: a third menu, next to Add and Properties

- **Depends on:** dj-tech tasks 33–42 (the Properties menu, `props_menu.py`;
  the 4-Mix window, `menu_window.py`) and 51 (0.1.53). At run time, the Human
  Model Editor (`mocap-studio/human-model/hm_editor`) and MPFB 2.0.18 in the
  same Blender 5.2.2; this add-on never imports `hm_editor`.
- **Contract:**
  - In: Rafael (2026-11-23): the MPFB human is edited from a floating menu,
    like the Add (deck A IN) and Properties (deck B IN) menus, one more menu
    in that set — not a work mode that takes the whole controller. It works
    only when the scene has a human, or to add one.
  - Delivers:
    - A Human menu opened by the control of decision D1, navigated like the
      Properties menu (platter moves, IN enters/edits/keeps, OUT back or
      reverts, held 0.5 s closes, SYNC closes, a click outside closes).
    - Its levels are the 3D View sidebar panels of category **Human**
      (`hm_editor/__init__.py:653`), in the editor's order, read through the
      same recording fake layout as `props_menu._panel_rows`; each panel's
      `poll` decides what shows. So with no human only adding one is offered
      (New male / New female / Open recipe, as the editor's main panel,
      `hm_editor/__init__.py:697`), with a plain human the shape panels and
      measures, with a built model the face, layers and pose panels.
    - The menu acts on the scene's human (`Scene.hm_editor.body`,
      `HM_controls`), not on the selection: editing another object doesn't
      change what it edits.
    - Floats move by the platter, step as deck B (S1 VOL factor); a typed
      measure (`tape_*`, ~2 s each) is applied only on IN, not per pulse.
    - The 4-Mix window shows the Human level (`menu_window.follow`), and
      only one of Add / Properties / Human is open at a time (decision D3).
    - Without the editor installed, the menu reports "Human Model Editor
      isn't installed" in `last_error`.
    - `acoes-4mix.md`, `README.md`, `CLAUDE.md`, `docs/specification.md`,
      version bump.
  - Not delivered: the editor's text fields (Name, Find a slider, paths) stay
    on the keyboard.
- **Open decisions (Rafael):**
  - **D1** The control that opens it. Candidates free today: SHIFT + IN
    deck B (beside Properties), S3 PLAY.
  - **D2** Outside Object Mode the editor greys its sliders
    (`hm_editor/__init__.py:709`). Either the editor allows editing in any
    mode (a small `mocap-studio` change, its own task there; proposed), or
    the menu leaves and re-enters the current mode around each edit.
  - **D3** Generalize `props_menu` to read any panel set (the Properties
    editor or a sidebar tab; proposed, so any add-on's tab can follow), or a
    separate `human_menu.py` reusing its recorder.
- **Pre-work:** the editor installed in the Windows Blender
  (`python3 human-model/install_editor.py`, mocap-studio); a recipe and a
  built `.blend` for the hardware check.
- **Tests:** pytest: the recorder reads the Human panels from a fake for the
  three cases (no human, plain, built). Windowed: a `check_menu_window.py`-
  style check of the Human level. Hardware: Rafael adds a human from the
  menu, changes a nose slider and a typed waist, and moves a face muscle on a
  built model, with another object in Edit Mode.
