## 2. Human Mode: phenotype, height and weight

- **Status:** planned, on hold.
- **Depends on:** task 1.
- **Contract:**
  - In: Rafael (2026-11-23): phenotype = age, ancestry and gender, on the
    controller; what exists in the editor today.
  - Delivers, in `human.json`:
    - Gender: two buttons, male / female (`Scene.hm_editor.sex`), the LED of
      the current one lit.
    - Knobs: age (`macro_age`, 0.5–1, the editor's adult minimum), ancestry
      (`race_african`, `race_asian`, `race_caucasian`, which the editor keeps
      summing to 1).
    - Faders: height (`macro_height`) and weight (`macro_weight`), muscle
      and proportions if there's room (decision D1).
    - Pickup: a control takes over only once it reaches the current value
      (as `Engine._tap_ok`), so entering the mode never jumps the body.
    - Buttons: Save recipe (`hm_editor.save_recipe`), Build
      (`hm_editor.build`).
    - The value of each control while it moves, on the viewport (as the grid
      note, dj-tech task 50).
    - Docs as in task 1.
- **Open decisions (Rafael):** **D1** which knobs and faders; decided with
  task 3's measures, so the whole controller is laid out once.
- **Tests:** pytest with a fake `Scene.hm_editor`: value scaling, ancestry
  sum, pickup. Hardware: Rafael changes age, gender and height.
