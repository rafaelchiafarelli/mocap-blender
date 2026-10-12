## 3. Placeholder character

- **Depends on:** 1
- **Contract:**
  - In: a character JSON (film root): `name`, MPFB macro values (`gender`, `age`, `muscle`, `weight`, `height`, `proportions`, `race`), and a skin colour (linear RGB)
  - Requires: MPFB `HumanService.create_human` + `add_builtin_rig(basemesh, "rigify.human")`
  - Delivers: `character.blend` with the body mesh skinned to a Rigify human **metarig** (deforming directly, no generated Rigify rig), feet on the floor, facing −Y
- **Decisions:**
  - Claude, for Rafael's review: a neutral placeholder, not the film's character design. The metarig is used directly because its bone names match FreeMoCap's rig and the retarget only needs rotations.
- **Pre-work:** none
- **Out of scope:** clothes, hair, eyes, the face rig
- **Tests:** the .blend has the mesh and a metarig with `upper_arm.L`, `hand.R`, `spine.006`; every macro value is the one asked for
