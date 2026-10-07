# integration — epics (execution order)

1. **setup** — Blender, the agent link, the agent's rules (3 tasks)
2. **versioning** — asset store, save/restore, agent saves before every edit (3 tasks)
3. **assets** — free and AI-generated asset sources (3 tasks)
4. **characters** — target skeleton, MPFB2, free model → Rigify, Rafael's add-ons (4 tasks)
5. **sets** — Infinigen exteriors and interiors, Rafael's add-ons (3 tasks)
6. **cameras** — camera control add-on (1 task)

`versioning` comes before the content epics so nothing they make can be lost.
After `versioning`, epics 3–6 are independent of each other.

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green.
