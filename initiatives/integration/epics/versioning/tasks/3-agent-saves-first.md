## 3. Agent saves before editing

- **Depends on:** 2, setup/3
- **Contract:**
  - In: the save command from 2
  - Requires: a rule in the agent rules file, and if possible a Claude Code hook that enforces it
  - Delivers: the agent saves a version before any change to an asset and names that version in its report
- **Pre-work:** **Confirm** whether a hook can enforce it or it stays a rule only
- **Out of scope:** —
- **Tests:** manual agent session: ask for an edit, then restore the version the agent reports
