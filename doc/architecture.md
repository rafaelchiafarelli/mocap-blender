# mocap-blender — architecture

Diagram: [`diagrams/mocap-blender-overview.drawio`](diagrams/mocap-blender-overview.drawio)
(draw.io).

The repository holds two Blender-side parts of Mocap Studio.

| Part | Folder | State (2026-11-22) | Documentation |
|---|---|---|---|
| P5 capture add-on | [`mocap_blender/`](../mocap_blender/) | planned, no code yet: import `mocap_take.json` (from `mocap-adapt`, contract in `mocap-contracts`) as animated empties, NLA layers (locked capture + correction track), FreeMoCap bridge | [`../README.md`](../README.md), [`../initiatives/baseline/`](../initiatives/baseline/baseline.md) |
| Control surface | [`control_surface/`](../control_surface/) | working, version 0.1.57: the DJ-Tech 4-Mix MIDI controller as part of Blender's interface | [`../control_surface/docs/`](../control_surface/docs/README.md) |

## Control surface in one paragraph

A Blender extension. A WinMM input thread queues the controller's MIDI
messages; a 20 ms Blender timer feeds them to a pure-Python engine that
decodes them with a device profile (JSON) and runs the first matching binding
of a mapping (JSON): a Blender operator or one of the add-on's actions (a
modal grab with platter pushes and snapping, the Add and Properties menus
read from Blender's own UI code, the 3D cursor, Edit Mode tools). Every tick
the engine also reads Blender's state and drives the controller's LEDs from
the mapping's indicators. The menus are shown in a small "4-Mix window" drawn
with Blender's widgets, which follows the menus and answers the mouse.
Details: [`control_surface/docs/specification.md`](../control_surface/docs/specification.md).

## Runtime and tools

- Blender 5.2.2 portable on `G:\mocap-studio-downloads\apps\blender\5.2.2\`
  (`mocap-studio/DEPENDENCIES.md`); the control surface is built and installed
  with `blender --command extension`.
- Tests: `pytest` at the repository root (pure tests + a headless Blender
  smoke test); windowed checks in `control_surface/tests/windowed/`.
- Planning: [`../initiatives/`](../initiatives/README.md) — `baseline`,
  `integration`, `control-surface` (epic `dj-tech`, tasks 1–53).
