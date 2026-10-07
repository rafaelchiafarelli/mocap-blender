## 3. Free model → target skeleton

- **Depends on:** 1, assets/2
- **Contract:**
  - In: a free stylized character from an asset source
  - Requires: Rigify (bundled with Blender)
  - Delivers: the agent adapts the model (proportions, cleanup) and rigs it on the target skeleton; the steps written down so they can be repeated
- **Pre-work:** Rafael picks the test model
- **Out of scope:** retargeting, final film look
- **Tests:** headless check of the armature against the bone list; manual: test poses deform cleanly
