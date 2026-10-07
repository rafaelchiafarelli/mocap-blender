## 2. BlenderMCP link

- **Depends on:** 1
- **Contract:**
  - In: BlenderMCP add-on + MCP server (`ahujasid/blender-mcp`), pinned release
  - Requires: Claude Code (WSL) reaches the add-on's socket in Windows Blender (WSL mirrored networking, so `localhost` works); the MCP server registered in this repo's `.mcp.json`
  - Delivers: the agent can read the scene, create and change objects, take a viewport screenshot and run Python in Blender
- **Pre-work:** **Confirm** the pinned BlenderMCP release works on Blender 5.2, and whether the MCP server runs in WSL (`uvx`) or on Windows
- **Out of scope:** asset sources and AI generators (assets epic)
- **Tests:** manual agent session: create a cube, move it, take a screenshot, read the transform back
