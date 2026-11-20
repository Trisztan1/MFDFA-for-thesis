# Plan

## Completed

- **2026-11-21 — Fix `compute_hq` R² append bug + add regression test.**
  Archived: `docs/completed-features/2026-11-21-feature-fix-compute-hq-r-append-bug-add-regression-test.md`.
- **2026-11-20 — Validation harness + `@stats-reviewer` agent.** Archived:
  `docs/completed-features/2026-11-20-validation-harness-and-stats-reviewer.md`.

## Future

### Open finding (from completed features)
Reference doc §6 claims an `s_min = max(order+2, zero_run+1)` guard against
exact-zero runs in the engine. No such guard exists. The app's actual zero-run
defense is the page-level fit-band gate, which blocks deterministically.
Constant-run (interpolated-like) damage passes through unguarded (h(−4)
measured 0.643 → 0.948). Potential next feature: add the guard, or document
reliance on upstream gap collapsing.