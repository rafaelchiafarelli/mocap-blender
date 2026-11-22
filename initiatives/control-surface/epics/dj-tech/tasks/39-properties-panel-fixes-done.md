## 39. Properties menu: every panel draws (Particles, Output, Custom Properties), header-less first

- **Depends on:** task 38.
- **Contract:**
  - In: Rafael (2026-11-22): images of the most interactive options
    (Motion Blur, Physics, Particles). Making them showed Particles ›
    Emission without its fields and Physics' order differing from the editor.
  - Delivers: context members missing → None; `path_resolve` on the
    context stand-in; `add_menu.bind_like_instance` (static methods); header-
    less panels first; images `review/2026-11-22/4mix-*.jpg`.
- **Pre-work:** a survey running every panel's poll/draw (66 → 55 errors,
  all polls of panels that do not apply).
- **Out of scope:** none.
- **Tests:** pytest; the survey; windowed screenshots of Physics (before
  and after Cloth), the Cloth panel, Particles and Particles › Emission.
