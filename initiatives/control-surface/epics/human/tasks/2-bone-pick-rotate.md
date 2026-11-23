## 2. Human Mode: pick bones by the hierarchy, rotate them with deck C's tools

- **Depends on:** task 1.
- **Contract:**
  - In: Rafael (2026-11-23): posing is what the film needs most.
  - Delivers:
    - Bone pick on the platter: from the active bone, steps to its parent,
      first child or next sibling (the buttons choosing which is decision
      D3), ~14 pulses per step as the vertex pick (dj-tech task 49); the
      bone's name shown as the snap marker's text.
    - `grab.py`'s rotate / move (and their axis buttons 1–4, the platter
      push, the 90° mode) acting on the selected pose bones: their
      `rotation_quaternion` / `rotation_euler` / `location` in the bone's
      local axes, Esc restoring the start.
    - Clear pose of the selection (Alt+R / Alt+G equivalents) on the buttons
      that clear transforms in Object Mode.
    - The `human.json` bindings for these; docs as in task 1.
- **Open decisions (Rafael):**
  - **D3** Which controls step parent / child / sibling and which deck the
    tools live on (deck C as in Object/Edit is proposed, for muscle memory).
  - **D4** Rotation axes: the bone's local axes (proposed, what animators
    use) or the view's.
- **Pre-work:** none beyond task 1's.
- **Tests:** pytest on a fake armature: hierarchy steps, rotate and Esc.
  Windowed: rotate `upper_arm.L` 90° on X from the controller. Hardware:
  Rafael poses an arm and a head.
