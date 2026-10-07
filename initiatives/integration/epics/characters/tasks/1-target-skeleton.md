## 1. Target skeleton

- **Depends on:** versioning
- **Contract:**
  - In: —
  - Requires: one skeleton every film character uses, so the mocap can later be retargeted onto any of them
  - Delivers: the skeleton definition (bone names, hierarchy, rest pose, axes) as a reference `.blend` in the library plus a written bone list in this repo
- **Pre-work:** **Decide** with Rafael which skeleton (e.g. MPFB2's default rig, Rigify's human metarig, Mixamo's). Flag: when retargeting starts (phase 2), the bone list likely becomes a contract in `mocap-contracts`
- **Out of scope:** retargeting
- **Tests:** a headless script checks the reference `.blend` against the bone list
