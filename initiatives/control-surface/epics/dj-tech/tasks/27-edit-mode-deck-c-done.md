## 27. Deck C in mesh Edit Mode

- **Depends on:** task 26.
- **Contract:**
  - In: Rafael (2026-11-21): deck C should make sense in Edit Mode; he
    agreed: 1–4/RE/IN/platter/cage on the selected vertices, OUT deletes by
    the select mode, clear/apply only in Object Mode. First change made in
    the `mocap-studio/mocap-blender` submodule.
  - Delivers: `grab.py` Edit Mode targets (bmesh), cage box of the selected
    vertices, Esc back to the very start; `delete_selected` in Edit Mode;
    docs.
- **Pre-work:** none.
- **Out of scope:** more Edit Mode actions (Rafael wants more; to be
  listed).
- **Tests:** pytest; a windowed Blender check on the cube's top face (move Z,
  cage scale X from the −X side, Esc, rotate 90°, delete in face mode).
