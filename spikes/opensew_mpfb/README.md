# Spike: MPFB ↔ opensew-2 link

Can opensew-2 (pattern-based garments, GPL-3.0) dress a **live** MPFB
character: helpers masked, macro shape keys still editable, a rig attached,
the way a film character is kept, not a baked copy?

Answer from this spike: **yes, after a small patch to opensew-2's body
measurement.** Without it, every MPFB rig (Mixamo included) gave a hip of
135–162 cm on a 161 cm body.

## Pins

| What | Version |
|---|---|
| Blender | 5.2.2 (Mocap Studio pin) |
| opensew-2 | `86b4322` (upstream `main`, 2026-08-26) + `patches/` |
| MPFB | developed against git `650c5c5` (2.0.18); extension-store build should work, not verified |

## Run

```bash
cd spikes/opensew_mpfb
./setup.sh                 # BLENDER=/path/to/blender ./setup.sh if not on PATH
./run_test.sh              # default rig, woman + man, ~1 min
./run_test.sh --drape      # + sew and drape T-shirt and trousers, ~6 min
./run_test.sh --rig rigify # or --rig mixamo; --figure WOMAN|MAN
```

`setup.sh` clones opensew-2 into `.cache/` (ignored), applies the patch and
**symlinks** `clothing_design` into Blender's user add-ons. It does not
install MPFB: get it from *Edit › Preferences › Get Extensions*.

Output in `out/` (ignored): `report.json` and one `.blend` per figure (per
garment with `--drape`) to open in the GUI. Exit code 0 = no failures; known
issues print `WARN` and do not fail the run.

## What the test checks

1. MPFB body measured like opensew-2's own reference avatar (Nora / Theo),
   built from the same MPFB macros: chest, waist, hip ±4 cm, neck ±2.5 cm.
2. All 8 limbs found on the chosen rig; landmarks in anatomical order;
   figure (man/woman) guessed right; Collision modifier on the body.
3. Changing an MPFB macro (weight 0.5 → 0.85) changes the next measurement.
4. All 9 opensew-2 presets draft onto the body.
5. `--drape`: T-shirt and trousers sew and drape with < 2 % of the cloth
   inside the skin, and the T-shirt's sleeves are still round the arms
   (rays out of the upper-arm axis; nearest-point penetration can not see an
   arm that left the sleeve).

## Results on the development machine (bpy 5.2.2, headless)

| Rig | Woman chest/waist/hip/neck (ref 87.5/67.2/91.5/32.9) | Man (ref 102.1/79.9/93.6/38.5) |
|---|---|---|
| default | 87.6 / 67.1 / 91.5 / 33.4 | 103.7 / 79.9 / 93.6 / **44.9** |
| rigify | 84.8 / 67.1 / 91.5 / 35.3 | 100.6 / 79.9 / 93.6 / **46.5** |
| mixamo | 84.9 / 67.2 / 91.5 / 33.3 | 99.6 / 79.9 / 93.6 / 39.1 |

Drape, default rig: T-shirt 0.3 % / 0.2 % inside the skin (woman / man),
trousers 0.0 %, 75–100 s each on 2 CPU cores.

## The patch (`patches/0001-…`)

All in `clothing_design/avatar.py`:

- ignore MPFB's non-skin vertex groups (`body`, side masks, `helper-*`,
  `joint-*`, `mhmask-*`) when picking a sample's dominant group; the
  full-weight `body` group won everywhere and the arms were measured as chest;
- `RIG_DIALECTS`: torso landmark bones for MPFB's default rig (spine numbered
  top-down: `spine01` is the upper chest) and MPFB's Rigify metarig (neck on
  `spine.005`);
- limb chains / groups for MPFB's default rig (`upperarm01`, `lowerarm01`,
  `wrist`, `upperleg01`, `lowerleg01`);
- keep `upper_arm`, `lowerarm`, `finger`, `metacarpal` and the Rigify deltoid
  helper out of the torso cross-sections (MPFB's A-pose hangs the fingers at
  hip height).

opensew-2's own `tests/test_presets.py` still passes with the patch.

## Patch 0002: sewing force on sleeved garments

opensew-2's Sew runs the stitch with **unlimited** sewing springs. More than
half of a T-shirt's sleeve-cap springs start out crossing the shoulder and arm
(sleeve round the arm, armhole on the torso), and they drag the cap through
the arm faster than the collision can push it back: the arm ends up outside
the sleeve. It happens on opensew's own Nora and Theo without patch 0001, so
it is opensew's, not the MPFB link. opensew's `tests/test_fit.py` passes
anyway (nearest-point penetration and sleeve reach both miss it).

The patch (`sim.sew_force_for`, `sim.stitch_frames_for`): with Sew Force at 0,
a garment with sleeves stitches at force 15 for at least 50 frames; without
sleeves it stays unlimited (capped, the dress no longer seats on the
shoulders). Measured, first 10 cm of each upper arm, points off the arm and
rays with cloth inside the skin, unlimited -> patched:

| Body | T-shirt | Jacket | Hoodie |
|---|---|---|---|
| Nora | 5/10, 14 -> 0/10, 0 | 3/10, 5 -> 0/10, 0 | 6/10, 18 -> 0/10, 0 |
| MPFB woman (Rigify) | 6/10, 21 -> 0/10, 0 | 6/10, 11 -> 0/10, 0 | 0/10, 8 -> 1/10, 0 |
| Theo | 3/10, 23 -> 1/10, 6 | 0/10, 0 -> 0/10, 0 | 1/10, 6 -> 0/10, 0 |

**Still open:** the MPFB man (default rig): his left upper arm comes through
the top of the T-shirt sleeve, cloth 22-34 mm inside the skin 7.5 cm down the
arm; `run_test.sh --drape` fails on it. No force/frames pair tried (8-15,
50-100) clears it.

## Known issue

**Man's neck on the default and Rigify rigs reads 45–47 cm (ref 38.5).** Both
rigs weight the front of the neck, under the chin, to the jaw bone. The
measurement masks the jaw, so the horizontal ring breaks before the scan
reaches the real neck and stops at the trapezius. Effect: men's necklines
cut ~8 cm too wide. A measurement perpendicular to the neck bone (convex hull,
tape-measure style) gave 36–38 cm in a prototype, but it reads women ~4 cm
under opensew's own reference, so it changes drafting for every rig. Left for
a decision, not patched here.

## Look at in the GUI

- Necklines climb the neck during the stitch (4-8 cm above the neck base on
  the women), opensew's own "tops ride up" known issue.

- Women's T-shirt drapes short, hem near the waist rather than the hip.
  Possibly the MPFB A-pose (arms ~45°, opensew's avatars use 60°) pulling the
  sleeves up. Compare with `--drape` output.

## Open items (not in this spike)

- Expose the parameters the presets already take (sleeve length, length-to,
  flare); the UI only exposes ease.
- New presets: leggings, blouse.
- Finalize keeps the cloth solver and pins edges to the skin (Surface
  Deform) instead of binding garments to the rig.
- Patterns as data (a contract), not code.
- Garment → MHCLO via MPFB's `ClothesService.create_mhclo_from_clothes_matching`
  so MPFB's refit follows body edits.
