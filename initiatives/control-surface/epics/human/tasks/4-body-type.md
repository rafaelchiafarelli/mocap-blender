## 4. Human Mode: silhouette, biotype and body fat

- **Status:** planned, on hold; blocked until the editor has them.
- **Depends on:** tasks 1–3; `mocap-studio` initiative `body-type-selection`,
  task `editor-sheet/1-design-panel` (silhouette, biotype with its two other
  parts, body fat in `hm_editor`; nothing built as of 2026-11-23).
- **Contract:**
  - In: Rafael (2026-11-08 and 2026-11-23): the character sheet's order —
    silhouette and biotype, then height and body fat, then the measures;
    each step fills the next one's starting values, what is typed wins.
  - Delivers, in `human.json`:
    - Silhouette: one button per silhouette of the gender (female:
      ampulheta, pêra, triângulo invertido, retângulo, oval; male: trapézio,
      triângulo invertido, retângulo, triângulo, oval), the current one lit.
    - Biotype: three buttons for the main type (ecto, meso, endo), two knobs
      for the other two parts (up to 35% each, 65% together).
    - Body fat %: a fader.
    - The measures of task 3 following the cascade as the editor computes
      it; this add-on computes nothing of the body.
    - Docs as in task 1.
- **Open decisions (Rafael):** the controls, once the editor's fields exist.
- **Tests:** as task 2, on the new fields.
