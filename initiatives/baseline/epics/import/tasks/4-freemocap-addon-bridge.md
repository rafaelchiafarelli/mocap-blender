## 4. FreeMoCap add-on bridge

- **Depends on:** bootstrap
- **Contract:**
  - In: FreeMoCap output in `extract/`
  - Requires: official FreeMoCap add-on installed
  - Delivers: operator that calls the FreeMoCap add-on to generate the reference rig
- **Pre-work:** Check the current API of the FreeMoCap add-on
- **Out of scope:** custom retargeting
- **Tests:** headless on a fixture
