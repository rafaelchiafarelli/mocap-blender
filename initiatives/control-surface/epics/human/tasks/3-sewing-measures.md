## 3. Human Mode: the sewing measures on knobs

- **Status:** planned, on hold.
- **Depends on:** task 1; task 2 for the layout (D1).
- **Contract:**
  - In: Rafael (2026-11-23): the pattern-making measures on knobs, one knob
    per measure; they drive the rest of the body.
  - Delivers, in `human.json`:
    - One knob or fader per measure of the editor's tape
      (`hm_editor/tape.py`, `Scene.hm_editor.tape_<key>`, cm), the ones of
      the pattern-making sheet first (the 15 of
      `G:\mocap-studio-downloads\Modelagem_Plana-referencia.pdf`).
    - A measure takes ~2 s to solve and Blender waits
      (`docs/character-editor.md`), so the knob shows the asked value on the
      viewport while it turns and applies it once it stops (decision D2).
    - The measure's knob range: what the sliders can reach, the panel's
      "Punho 16.9 (pediu 40.0)" shown when it stops short.
    - A button for **Reaplicar medidas** (`hm_editor.refit`).
    - Docs as in task 1.
- **Open decisions (Rafael):**
  - **D1** (with task 2) which measure on which control.
  - **D2** apply when the knob stops (proposed) or on a button.
- **Tests:** pytest: the settle timer, the range, the shown value. Hardware:
  Rafael sets waist and hip from the knobs and checks the panel.
