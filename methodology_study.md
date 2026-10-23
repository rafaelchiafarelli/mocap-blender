# Methodology study — making film assets with an AI agent

Hand-off from the 2026-10-06/07 planning session. This file starts a study of
**how assets for the film get created, changed, versioned and reused**, with an
AI agent automating the work but not doing the heavy lifting itself. It's
study material, not a plan yet. The results should turn into initiatives,
epics and tasks (see the `mocap-workflow` skill). After that, this file can be
removed.

## Context

- Mocap Studio captures body motion (P1–P5) and ends in Blender (`mocap-blender`
  = P5 importer: `mocap_take.json` → animated empties → NLA base track + correction track).
- Rafael is making a **film** in Blender on top of that. It needs characters,
  sets, backgrounds, cameras and storyboards, so it needs many tools plus
  orchestration around them.
- An initiative already exists in this repo: `initiatives/integration/`
  (install and test the tools through an AI agent, plus asset versioning). It
  was written **before** this methodology discussion and must be reworked to
  fit it. In particular, `assets/3-ai-generation` conflicts with the
  constraints below.

## Constraints (Rafael's, standing)

1. **Free and/or open-source only, and usable commercially.** No paid add-ons,
   asset packs or services. Decided 2026-10-12: the films aren't commercial
   yet but must be sellable later, so no non-commercial or capped
   "community" licenses, not even for tests.
2. **No local AI for code, models or script analysis.** That work is done by
   the hosted agent (Claude). Revised 2026-10-23: a model runs locally only if
   it performs well on the current equipment (RTX 4080 16 GB), measured in a
   task first; P3 mocap nets and local audio generation pass, and the models
   good enough for code, models or script analysis don't.
3. **Don't over-task the AI.** AI writes and maintains descriptions and code.
   Plain deterministic software builds the assets.
4. **Change one thing without changing everything.** An edit touches only the
   unit it names.
5. **Every change can be rolled back** to an earlier version.
6. **Blender 5.2.2 LTS** (Windows processing PC, portable zip). Tools must work
   with it out of the box.
7. Tool selection criteria: **automatable** (headless/Python), **works with
   Blender 5.2 out of the box**, **actively maintained**, **fits the workflow and
   process**.

## Draft methodology: recipes instead of prompts

1. **One asset library.** Blender asset libraries with catalogs. Scenes **link**
   assets rather than copying them in, so a fix to an asset reaches every shot.
   A change for one shot uses library overrides.
2. **Every asset has a recipe**, a small text file holding: source (download ID
   | generator + parameters + seed | hand-made), license, and pinned tool
   versions. To change a generated asset, you change the recipe and rebuild,
   not edit the mesh by hand.
3. **Generators are headless scripts**: `blender -b --python gen.py -- recipe.yaml`,
   wrapping the tools below. Same recipe gives the same result. No AI at build time.
4. **Sets are built from a layout file** (`set.yaml`: terrain, sky, scatter
   rules, buildings, props, named marks, cameras), assembled by a runner.
5. **The AI's role** (hosted Claude):
   - writes and edits recipes and layout files
   - writes new generators as reviewed, tested code
   - looks at renders and screenshots and suggests changes

   It is never part of the build. Interactive BlenderMCP work is for exploring
   ideas only.
6. **Order of preference for a new asset:** reuse one from the library →
   download a CC0 asset → generate it with a recipe → make it by hand (hero
   characters, where taste matters).
7. **Automatic checks as the test suite:** the asset opens headless in 5.2,
   scale is in meters, naming follows the rules, a license is recorded,
   polygon counts stay within budget.
8. **Versioning:** text files (recipes, layouts, shot files) in git. Built
   outputs (`.blend`, images) are stored by content hash outside git, with each
   recipe version mapped to its output hash. Large binaries never go into code
   repos.
9. **Small, named units, each with its own file and history.** The agent edits
   only the unit Rafael names, **reports** knock-on effects instead of applying
   them, and rebuilds only what changed. Variants (A/B of one unit) can sit side
   by side until one is picked.

## Who builds the assets (decided 2026-10-12)

Rafael's team builds the assets, and AI is not the whole of it:

- **Procedural first.** Bones/rigs, faces, eye movement and everything else that
  existing tools already do procedurally (Rigify, MPFB2, Geometry Nodes, the
  built-ins above) are made **with those tools**. AI only adjusts a few things
  here and there.
- **Specialised asset agents.** Creating new assets is done by AI agents
  specialised per kind of asset. They **drive the procedural tools** (writing
  recipes, layouts and generator code) to go faster, rather than producing the
  asset themselves.
- **No wasted AI effort.** An agent never spends its resources rebuilding what
  a procedural tool already provides.

This is the execution side the pre-production planners (`mocap-preprod`) hand
specifications to. The roster of asset agents is defined when TicTac enters
production.

## Worked example: the storyboard

Argument (pre-script story) → storyboard with Grease Pencil, then
Storypencil/Storytools.

```
story/
  argument.md                 ← Rafael's text, never touched by the agent
  sequences/seq010.md         ← agent's breakdown into shots (Rafael approves)
  sets/kitchen.yaml           ← set + named marks: window, door, table_left…
  characters/stranger.yaml    ← identity + which proxy figure stands in for them
  shots/seq010/sh030.yaml     ← one file per shot
```

```yaml
# shots/seq010/sh030.yaml
set: kitchen
camera: { mark: cam_a, lens: 35 }
characters:
  - { id: ana,      mark: table_left,  pose: sitting }
  - { id: bruno,    mark: table_right, pose: sitting }
  - { id: stranger, mark: window,      pose: standing }
action: "The stranger appears behind them; neither notices."
```

**Change request:** "the stranger shows up in the door, not the window."
1. The agent edits only `sh030.yaml` (`window` → `door`) and shows the diff first.
2. The builder sees that only sh030's inputs changed, so only sh030's panel is
   rebuilt. All other panels stay byte-identical.
3. Knock-on effects are flagged, not applied, e.g. "sh040 still has the stranger
   at the window, change it too?"
4. The change is one commit ("sh030: stranger enters through the door").
   Restoring = check out the old shot file and rebuild, or take the stored panel.
5. Optionally keep `window` and `door` as two variants until one is chosen.

**How panels are drawn (proposal):**
- Each shot is a 3D blocking: set marks, gray proxy figures on marks, camera.
- The **Grease Pencil Line Art** modifier gives the drawn look.
- Storypencil puts one scene per shot as a strip in the VSE.
- Rafael's hand drawing goes on a separate Grease Pencil layer that a rebuild
  never touches. If the shot under it changes, the layer is flagged "needs
  review."

## Curated tool list (checked 2026-10-07)

**Kept** (each still to be confirmed on 5.2 in a task's pre-work):

| Purpose | Tool | Notes |
|---|---|---|
| Scatter, arrays, layout | Geometry Nodes Essentials modifiers (built in since 5.0: Scatter on Surface, Array, Instance on Elements, Randomize Transforms, Curve to Tube) | Built in, scriptable |
| Sky / sunsets | Sky Texture, multiple scattering (5.0) | Built in |
| Fog, clouds | Volume Grid / SDF nodes (5.0) | Built in |
| Terrain | A.N.T. Landscape (official extension) | Community-maintained, "no support". Test on 5.2 |
| Trees | Modular Tree (extension) | GPL/MIT, v5.5.2 (2026-05-13), Blender ≥ 4.3.1 |
| Real places | Blosm, base version | GPL, active (commit 2026-04). OSM buildings without textures, terrain, roads, water |
| Materials, HDRIs, models | ambientCG | CC0, free API, no key |
| Materials, HDRIs, models | Poly Haven | CC0 assets (fine). **Its API is non-commercial only**, so download by hand, never through the API |
| Models, materials, scenes | BlenderKit (GPL add-on) | Large free tier, commercial use OK. Automating it outside its UI is unverified |
| Storyboard | Grease Pencil (+ Line Art), Storypencil / Storytools | Storypencil confirmed only up to 4.1. Storytools supports 5.0+ |
| Characters | Rigify (built in), MPFB2 (CC0) | Sculpt → retopo → UV → texture → Rigify workflow from Blender Studio's "Stylized Character Workflow" video |
| Agent link | BlenderMCP | Exploring only, not the build path |
| Other built-ins | Bool Tool (extension), Mantaflow, cloth sim, particles, Compositor, VSE | Free replacements for the paid add-ons in the "Make your first Movie" video |

**Dropped:**
- Sapling Tree Gen: broken on 5.0/5.1.
- OpenScatter: archived 2026-08.
- Infinigen: Blender 4.2, last release 2024. Watch list only.
- BuildingNodes, Buildify: Blender 3.x, stale.
- BlenderProc: built for synthetic training data, stale.
- AI mesh generators (Hunyuan3D, TRELLIS, Rodin): local GPU or paid.
- Everything paid from the "first movie" video: HardOps/BoxCutter, Auto-Rig
  Pro, Botaniq, Sanctus, Pure Sky Pro, Khaos, etc.

**Gaps:** buildings and interiors. No maintained, free, 5.x generator. The idea
is our own Geometry Nodes generators, written by the agent as tested code.

## Findings from a first-try project

An early test film (since removed) was taken from its argument to a sequence
breakdown. Where the methodology fell short:

| # | Friction | Decision |
|---|---|---|
| F1 | A film needs a **bible** (look, light, palette, materials, camera rules) above everything else | A "bible" unit. Generic change requests ("make it look 70s") go only into the bible, or are refused |
| F2 | The agent finds story questions it can't resolve | The film's own work follows initiatives → epics → tasks. Story questions get their own file |
| F3 | Story dependencies between sequences (setup/payoff) aren't file inputs | Declare the links explicitly. A continuity agent is probably needed |
| F4 | A set appears in several sequences and its state changes over the film | Sets have a **state timeline**. Detect what can be captured once and assembled later |
| F5 | A character can have no body (voice + a device) | A "voice/device" character type for now |
| F6 | Actions with no floor contact (flying, falling) | The actor stands on an apple box, and each take records **what touches the ground and what the ground is** (apple box ≠ set floor) |
| F7 | Film order ≠ capture order: actors perform better in continuous blocks | Separate the **capture plan** (continuous performance blocks) from the **film's shots** (which cut ranges out of takes) |
| F8 | Future films may be hybrid (CG + live action) | Don't build it now, but each element of a shot declares **CG or filmed plate** |
| F9 | The creator's original is a binary (slides, .docx) | It stays out of git, and a literal text transcription is the tracked source, redone when the original changes |

## Open questions for Rafael

1. ~~**Is the film commercial?**~~ **Answered 2026-10-12:** treat every film as
   commercial. ambientCG (+ BlenderKit, per-asset license checked) for
   automation; Poly Haven by hand only.
2. **Storyboard style:** is line art from 3D blocking good enough?
3. **Where does this live?** The suggestion is a new film-toolbox repo
   (submodule of `mocap-studio`) so `mocap-blender` stays the P5 importer. The
   `integration` initiative would move there. Not decided yet.
4. **Versioning tool** for built outputs: git + LFS, DVC, or checksummed
   snapshot folders on `G:`.
5. **Recipe / shot / layout file formats:** fields, units, naming, where the
   "marks" vocabulary lives.
6. **Target skeleton** for all characters. It becomes a `mocap-contracts`
   contract when retargeting starts (phase 2).
7. **Agent editing rules:** the scope of an edit, what counts as a knock-on
   effect, when to ask.
8. Which character / set / camera add-ons Rafael already has in mind.

## Suggested next steps for the study

1. Answer questions 1–3. They decide where the work lives and its scope.
2. Write down the unit model (asset, set, shot, variant), and for each unit:
   its file, its inputs, what rebuilds when it changes.
3. Define the recipe and shot file formats (contract-first, small).
4. Prototype the storyboard example end to end on paper: argument → shots →
   change → selective rebuild → rollback.
5. Turn the result into initiatives (storyboard first, since it exercises the
   whole methodology on something small), and rework `initiatives/integration/`.

## Sources

- Videos: [Stylized Character Workflow with Blender](https://youtu.be/f-mx-Jfx9lA)
  (Blender Studio), [Make your first Movie in blender](https://youtu.be/sy4EfjjKAmM)
- [BlenderMCP](https://mcpservers.org/servers/ahujasid/blender-mcp)
- [Infinigen](https://infinigen.org/), [Infinigen releases](https://github.com/princeton-vl/infinigen/releases)
- [Sapling Tree Gen reviews](https://extensions.blender.org/add-ons/sapling-tree-gen/reviews/)
- [A.N.T. Landscape](https://projects.blender.org/extensions/ant_landscape)
- [Modular Tree](https://extensions.blender.org/add-ons/modular-tree/)
- [OpenScatter (archived)](https://github.com/GitMay3D/OpenScatter)
- [Blender 5.0 rendering notes](https://developer.blender.org/docs/release_notes/5.0/rendering/),
  [CG Cookie: everything new in 5.0](https://cgcookie.com/posts/everything-new-in-blender-5-0)
- [Blosm](https://github.com/vvoovv/blosm)
- [BlenderKit](https://github.com/BlenderKit/blenderkit)
- [Poly Haven API](https://polyhaven.com/our-api), [ambientCG API v3](https://docs.ambientcg.com/api/v3/)
- [Storypencil manual](https://www.blender.org/manual/en/addons/sequencer/storypencil.html),
  [Storytools](https://extensions.blender.org/add-ons/storytools/)
