# mvp — mocap-blender

**Goal:** from one take's FreeMoCap output to a rendered shot of a rigged
placeholder character, headless and scripted, for the MVP in
`mocap-studio/MVP-plan.md` (steps 4–6).

**Scope:** the pinned Blender with MPFB and the FreeMoCap add-on, a reference
scene from the FreeMoCap add-on, an MPFB character with a Rigify metarig, the
retarget of the take onto it, and a shot (blockout set, camera, light, voice)
rendered with EEVEE.

**Out of scope:** the `MocapTake` contract and `mocap-adapt` (the MVP reads
FreeMoCap's output directly), face capture, finger quality, real assets, and
anything the `integration` initiative plans (BlenderMCP, versioning, asset
sources).

**Film material stays in the film root:** the character's settings and the
shot recipe are JSON files under `<film-root>/mvp/`, passed in by path.

**Initiative gate:** FreeMoCap's test recording renders as a shot on an MPFB
character; then the MVP's real take does.

Added 2026-10-12 by Claude, for Rafael's review (pre-approved as part of the
MVP run). Retargeting was "phase 2" in `baseline` and `integration`; the MVP
needs a simple one now, so it lives here and leaves those plans untouched.
