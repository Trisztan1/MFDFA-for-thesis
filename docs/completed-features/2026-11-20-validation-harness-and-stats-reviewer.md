# Feature: `validation/` MF-DFA harness (+ deferred `@stats-reviewer` subagent)

Archived 2026-11-20. See `plan.md` for the current roadmap.

## Purpose

The harness feeds signals with known correct answers through the app's own engine functions and checks the numbers: fGn (monofractal, so almost no width), the binomial cascade (exact theoretical h(q)/τ(q)), and the installed package vs an independent reference implementation. It protects the engine against silent breakage when `main()` is refactored, and gives thesis-quotable validation evidence. It validates the MFDFA math only — not the gaze data, not upstream preprocessing.

## Scope

**In scope (implemented now):** 7 check scripts + 1 shared helper under `validation/`, plus this spec revision.

**Step 2 (approved 2026-11-20):** `.opencode/agents/stats-reviewer.md` created per R1 (V2 format; permissions verified by structural check). AGENTS.md updated (subagents line + corrected the stale gitignore note). **Still pending: the first review report (R4)** — run only when the owner asks, on a scope the owner chooses.

**Out of scope:** any change to `mfdfa_engine.py`, `pages/`, `utils/`; fixing whatever the checks or reviewer find; test frameworks, CI, pre-commit hooks, new dependencies; migrating the three V1 agent files; validating upstream gaze preprocessing.

## Requirements — harness (R2)

Shared `validation/_common.py` — repo-root bootstrap, engine import (compute layer only), the standard pipeline (identical to the app-style pipeline in `docs/references/mfdfa_app_review_reference.md` §8/Appendix B: lags 10..N/4, 40 log-spaced ints; fit band `[lag.size//8 : int(lag.size/1.5)]`; q = linspace(−5, 5, 101) after the |q| ≤ 0.1 filter; order 1; robust width with `q_width_max=4, positive_q_only=False, f_floor=0.0`), version printing, and a PASS/FAIL collector that exits 0/1.

| Script | What it checks | Threshold / rule |
|---|---|---|
| `package_vs_ref.py` | Installed package vs the Appendix-A reference implementation (B2), seeded 4000-sample standard normal, q=±4,±2 | max rel. error < **1e-10** (prior 2.9e-16; headroom for other numpy/BLAS builds) |
| `q_grid.py` | The engine, not the package: default grid keeps **99** q (asymmetric: nearest negative −0.2, nearest positive +0.1); F columns == len(q_list); `get_dfa` q=2 column equals a direct q=[2] run; even `q_num=100` keeps 98 with no misalignment | exact counts; allclose 1e-12 |
| `fgn_width_baseline.py` | fGn H=0.7, N=4096, 12 fixed seeds: spurious width of a true monofractal; also prints h(2) recovery | mean raw and robust width < **0.12** (priors: raw 0.070 ± 0.031, robust 0.056 ± 0.024); h(2) within 0.7 ± 0.15 |
| `cascade_pipeline.py` | Binomial cascade vs closed-form theory: τ(q) = −log2(p^q+(1−p)^q), h = (1+τ)/q. **Asserted, two tiers:** (1) deterministic B3 cascade, p=0.3, 14 levels — pipeline ground truth, reproduces the priors exactly: max\|dh\| < **0.1** (measured 0.038), robust ratio ∈ **[0.85, 1.15]** (measured 0.965); (2) the engine's own randomized cascade (what the app generates), 6 seeds, measurement-based bounds: mean max\|dh\| < **0.25** (measured 0.108 ± 0.049, per-seed 0.053–0.184), all < 0.30, ratios ∈ [0.55, 1.35] (observed 0.648–1.225), mean ratio ∈ [0.80, 1.25] — the randomized arrangement has genuine negative-q scatter the deterministic prior does not show. τ(q) printed. **p=0.55 informational only**, both generators (deterministic priors 0.124/2.74 and 0.044/1.59; engine cascade 0.027/0.92 and 0.011/1.14) — estimator bias dominates, never assert on it | as listed |
| `negative_q_damage.py` | Clean spiky baseline **asserted** (F finite/positive, sane h(q)). Exact-zero run **asserted blocked** by the app's page-level fit-band gate (`utils.pages_logic.get_valid_fitting_range`): F² collapses to exactly 0 → negative-q F = 0.0 → h(−4) NaN → gate BLOCKS. Constant (interpolated-like) runs **measured and printed, not asserted** — F stays finite/positive and the gate does NOT catch them (measured h(−4) 0.643 → 0.948; B5 prior 0.637 → 0.818), the documented unguarded hazard | as listed |
| `surrogate_test.py` | p-value form verified **behaviourally** from engine output: k = p·(n+1)−1 must be an exact integer in [0, n] and p must equal (1+k)/(n+1) — catches the historical precedence bug (p ≈ 2.0). Then n=30 fixed-seed runs: fGn N=4096 **not** significant (p > 0.05); cascade p=0.3, 14 levels **significant** (p ≤ 0.05, expected k=0 → 1/31) | as listed |
| `fou_subtract_one.py` | fOU path (generated, `subtract_one=True`) recovers the generated H; fGn upload-like path (`subtract_one=False`) recovers its true H; applying −1 to the fGn slope lands outside (0,1); source-level assert that `pages/dfa.py` passes `subtract_one=False` exactly once (upload branch) and the generated branch relies on the default True | tolerances set after engine re-measurement |

**Tolerance protocol (all scripts):** the priors above come from a plain package pipeline; every quantity is re-measured once with the app's engine over several seeds, then thresholds are set with margin (~mean + 3 sd, or at least 2× the observed value). Fixed seeds; print seeds, versions, input sizes, measured values and chosen thresholds; exit 0 on pass, 1 on fail; import only compute-layer functions (importing the engine pulls in streamlit — expected, suppress warnings, never call plotting).

## Requirements — Step 2 (R1/R3 implemented 2026-11-20; R4 pending scope)

`.opencode/agents/stats-reviewer.md` in V2 format:
- No `model` field → inherits the session's model (verified opencode behavior), overridable per run.
- Permissions: `edit` deny on `*`, allow on `docs/reviews/**` (reviewer writes its own report, cannot touch code). **V2 permission rules do support wildcard command patterns on raw shell text** (verified against the V2 agents docs), so `shell` can be restricted to `.venv/bin/python validation/*`, `.venv/bin/basedpyright`, `git status`, `git diff`, `find`, `wc`, `cat`, `head` rather than a blanket allow. `webfetch`/`websearch` denied.
- Prompt: the reference doc is a **checklist and a prior, not ground truth** — the agent must verify its claims about the package (q filter, both-ends segmentation, no q=0 branch) against the source installed in `.venv`, and run the harness for numerics; verdict classes OK / VIOLATION / DEVIATION-DEFENSIBLE / UNVERIFIABLE / [OPEN]; findings classified as bug / defensible-choice / estimator-bias; file:line citations mandatory; writes its report to `docs/reviews/YYYY-MM-DD-<scope>.md`; ends with a "could not verify" list.

Then (still deferred): ~~one AGENTS.md line under Subagents~~ done 2026-11-20; the first report remains optional and awaits the owner's scope choice.

## Constraints

- `feature.md` is the only existing file modified; everything else is new files under `validation/`.
- No dependency changes, no engine/page changes, no frameworks.
- Verified against installed sources (2026-11-19): package q-filter `MFDFA.py:150`; both-ends segmentation `MFDFA.py:198-199`; no q=0 branch (`MFDFA.py:315` TODO); `fgn` uses the legacy global `np.random` (`fgn.py:60-61`) → seedable via `np.random.seed`.
- **Open finding:** reference doc §6 states the engine has an `s_min = max(order+2, zero_run+1)` guard against exact-zero runs. No such guard exists in `mfdfa_engine.py:74-90` or in the package (`MFDFA.py:125-127` enforces only `lag > order+1`). The app's *actual* zero-run defense is the page-level fit-band gate, which blocks deterministically (F² collapses to exactly 0 → negative-q F = 0.0 → h(−4) NaN) — asserted in `negative_q_damage.py`. Constant-run (interpolated-like) damage remains unguarded by anything (gate allows it; measured h(−4) 0.643 → 0.948). How to resolve (add the guard as a future feature vs rely on upstream prevention) is a user decision, out of scope here.

## Acceptance criteria

1. `.venv/bin/python validation/<script>.py` exits 0 for all 7 scripts.
2. Each script prints seeds, versions, input sizes, measured values, and chosen thresholds; thresholds follow the tolerance protocol and are documented in each script header.
3. No file outside `validation/` and `feature.md` is created or modified.
4. Typecheck is run on `validation/` and the real result reported.