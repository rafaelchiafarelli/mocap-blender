## 3. Agent rules

- **Depends on:** 2
- **Contract:**
  - In: —
  - Requires: one rules file the Blender agent always loads (a project skill or `CLAUDE.md` section, decided in pre-work)
  - Delivers: the first rules: work only through BlenderMCP, save before risky edits, never touch the locked NLA base track, report every change it made. Each new rule Rafael adds later is one commit to this file.
- **Pre-work:** **Confirm** with Rafael where the rules live and the first list
- **Out of scope:** the save-before-edit mechanism itself (versioning/3)
- **Tests:** manual agent session: the agent quotes the rules and refuses an edit that breaks one
