## 47. Software documentation of the control surface

- **Depends on:** task 46.
- **Contract:**
  - In: Rafael (2026-11-22): documentation of the code, of how to use it,
    of the tests and of how the process works: a software specification,
    flow and sequence diagrams, UML where it fits, in draw.io; in
    mocap-blender and in control_surface; push; update mocap-studio; list the
    tests still to do (he runs a test session with the debug log on).
  - Delivers: `control_surface/docs/` (README, specification, usage,
    testing with the open test list, 9 draw.io diagrams); `doc/architecture.md`
    and `doc/diagrams/mocap-blender-overview.drawio` at the repository root;
    `control_surface/tests/windowed/` (the windowed checks of tasks 42–45 and
    `run.sh`); README links; `docs/` excluded from the zip.
- **Pre-work:** none (draw.io is not installed: the diagrams are written as
  uncompressed draw.io XML and checked to parse).
- **Out of scope:** behaviour changes.
- **Tests:** pytest (153); `run.sh check_snap_menu.py` through the runner.
