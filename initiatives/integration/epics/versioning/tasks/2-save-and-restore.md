## 2. Save and restore

- **Depends on:** 1
- **Contract:**
  - In: an asset file in the library
  - Requires: the tool chosen in 1
  - Delivers: one documented way (command or script) to save a version with a message, list versions, and restore any of them
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** save, change, save, restore the first version: the file is byte-identical (sha256) to the first save
