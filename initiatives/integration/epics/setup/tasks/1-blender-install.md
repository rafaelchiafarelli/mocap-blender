## 1. Blender install

- **Depends on:** —
- **Contract:**
  - In: `blender-5.2.2-windows-x64.zip`
  - Requires: unzipped to `G:\mocap-studio-downloads\apps\blender\5.2.2\`, with its line in `SHA256SUMS`
  - Delivers: a pinned portable Blender, plus the version of its bundled Python written in `DEPENDENCIES.md` (the open question that baseline bootstrap/1 also needs answered)
- **Pre-work:** none
- **Out of scope:** any add-on
- **Tests:** `blender.exe -b --python-expr` prints the version and the bundled Python version
