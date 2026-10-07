## 1. Asset store

- **Depends on:** setup
- **Contract:**
  - In: —
  - Requires: large binaries stay out of the code repos
  - Delivers: an asset library location (`.blend`, textures, HDRIs, generated meshes) and the versioning tool behind it, written down in `DEPENDENCIES.md` (layout section)
- **Pre-work:** **Decide** with Rafael the tool. Options: (a) a separate git repo with Git LFS for binaries; (b) DVC on top of git, with the data on `G:`; (c) Blender's own saves plus dated, checksummed snapshot folders on `G:`. Also decide: backup copy off the `G:` drive or not.
- **Out of scope:** the agent hook (3)
- **Tests:** a test asset is stored and its version is listed
