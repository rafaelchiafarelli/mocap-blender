# integration — mocap-blender

**Goal:** Every Blender tool the film needs (characters, sets, cameras, asset
sources) is installed, pinned, and driven by one AI agent (Claude Code through
BlenderMCP), with every asset versioned so any earlier state can be restored.

**Scope:** Install and test, each one through the agent: Blender 5.2.2 LTS,
BlenderMCP, a versioned asset store, Poly Haven, Sketchfab, one AI 3D generator,
a target skeleton, MPFB2, Rigify, Infinigen (exteriors) and Infinigen Indoors,
and the add-ons Rafael names for characters, sets and camera control.

**Out of scope:** Retargeting the captured motion onto characters (phase 2),
the film's real assets (this initiative proves the tools on test assets), and
any change to the `MocapTake` contract.

**Working model:** most assets are generated once and then changed with some
effort. So the agent never edits an asset that has no saved version, and every
change can be rolled back.

**Initiative gate:** In one agent session, starting from an empty file, the
agent builds a test scene: an Infinigen room, a Poly Haven HDRI, a character on
the target skeleton, and a camera set up with the camera add-on. Every step is
saved as a version, and restoring an earlier version brings the scene back
exactly.

**Agent rules grow as we go:** they live in one file (setup/3) and every new
rule is a commit to it.

Pins for everything installed here go in `mocap-studio/DEPENDENCIES.md`
(section C, or B for anything that runs in a container). General context:
`mocap-studio/HANDOFF.md`.
