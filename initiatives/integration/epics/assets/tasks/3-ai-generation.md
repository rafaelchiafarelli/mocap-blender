## 3. AI 3D generation

- **Depends on:** versioning
- **Contract:**
  - In: one generator through BlenderMCP: Hyper3D Rodin (hosted, API key) or Hunyuan3D (hosted or local on the RTX 4080)
  - Requires: generated meshes go into the library, versioned, with the prompt that made them
  - Delivers: the agent generates a prop from text or an image and imports it
- **Pre-work:** **Decide** with Rafael which generator (cost, license of the output, local vs hosted)
- **Out of scope:** retopology / cleanup beyond what the agent does in Blender
- **Tests:** manual agent session; prompt stored next to the mesh
