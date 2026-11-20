# Feature: Fix `compute_hq` R² append bug + add regression test

Archived 2026-11-21. See `plan.md` for the current roadmap.

## Purpose

`mfdfa_engine.py:129` (`compute_hq`) has a conditional-expression-as-statement bug:

```python
r2.append(1 - np.var(resid) / np.var(yv)) if np.var(yv) > 0 else np.nan
```

When the condition is false (perfectly flat log–log line where `var(yv)==0`, or
`yv` contains NaN/inf because `nan > 0` is False), `np.nan` is evaluated and
discarded — **nothing is appended**, so `r2` becomes shorter than `hq` and
`q_list`. The remaining entries silently slide out of alignment with q, and the
"min R² across q" readout (two consumer sites) drops the worst column and
reports a healthier number than reality.

This bug was discovered during the `validation/` harness feature but is out of
scope there (the spec excluded engine changes). It pins a tripwire between the
pipeline's numerical output and the R² quality readout that the user relies on
to judge fit quality.

## Scope

### In scope
1. One new test file: `validation/hq_fit_quality.py`.
2. One line change in `mfdfa_engine.py:129`: move the conditional inside the
   `append` call so a NaN is appended instead of nothing.
3. Two consumer changes in `mfdfa_engine.py`:
   - `:305`: `plot_fluctuation_mf` — `r2.min()` → `np.nanmin(r2)` + visible
     NaN count.
   - `:358`: `plot_spectrum_stats` — same change.
4. A repo-wide grep for the same pattern (`x.append(...) if ... else ...`):
   report every hit; fix only trivially identical hits in `mfdfa_engine.py`;
   list any in `pages/` or `utils/` without changing them.

### Explicitly out of scope
- The `s_min` guard (the constant-run hazard from the open finding in
  `plan.md`). This is a separate methodological design decision.
- Any change to `pages/`, `utils/`, or the gaze processor.
- New dependencies, test frameworks, CI, or pre-commit hooks.
- The `@stats-reviewer` first report (R4 from the previous feature; still
  pending the owner's scope choice).

## Requirements

### R1 — Test-first: `validation/hq_fit_quality.py`

Follow the existing validation script rules: `.venv/bin/python validation/hq_fit_quality.py`,
fixed seeds, prints seeds/versions/sizes, exits 0 on pass, 1 on fail, imports
only compute-layer functions (`_common` + `engine`), suppresses warnings.

**A — Normal inputs (must PASS on current code too):**
- Run `engine.run_mfdfa` + `engine.compute_hq` on:
  (i)  fGn H=0.7, N=4096 (via `np.random.seed`, matching the `fgn` convention)
  (ii) `engine.binomial_cascade` p=0.3, 14 levels, seed fixed
- For each: assert `len(hq) == len(r2) == len(q_list)`, every R² finite and
  in `(0, 1 + 1e-12]`. Print min/max R² per signal.

**B — Degenerate columns (MUST FAIL on current code at exit 1):**
- Construct a hand-made dfa_mf-like F matrix. Call `engine.compute_hq` directly
  with the real `lag_mf` and `q_list` from a fGn run but replace F with a
  controlled matrix containing:
  (i)  one column exactly constant across scales (zero-variance log–log line)
  (ii) one column containing a NaN
  (iii) one column containing 0 so that log(0) = −inf
- Assert that `len(hq) == len(r2) == len(q_list)` still holds.
- Assert that the affected R² entries are NaN (not missing).
- Assert that the non-degenerate columns give normal R² values.
- Print the R² vector so the failing output is visible on the current code.

Also assert that `len(hq) == len(q_list)` — the same bug pattern exists for
`hq` (`np.polyfit` over garbage returns NaN, which IS appended, so `hq` does
not shrink — this check adds a safety pin for any future change to the polyfit
handling).

### R2 — Engine fix: `mfdfa_engine.py:129`

Smallest possible change. Replace:

```python
r2.append(1 - np.var(resid) / np.var(yv)) if np.var(yv) > 0 else np.nan
```

with:

```python
r2.append(1 - np.var(resid) / np.var(yv) if np.var(yv) > 0 else np.nan)
```

(The correct idiom already exists 17 lines above at line 112 in
`fit_dfa_exponent`, which uses the assignment form `r2 = 1 - ... if ...
else np.nan`.)

### R3 — Consumer fix: honest R² readout (`mfdfa_engine.py:305` and `:358`)

Both lines currently read:

```python
st.write(f"min fit R² across q: {r2.min():.4f}")
```

Change to something like:

```python
n_nan = np.isnan(r2).sum()
st.write(f"min fit R² across q: {np.nanmin(r2):.4f}"
         + (f" (NaN in {n_nan}/{len(r2)} fits)" if n_nan else ""))
```

So a NaN never makes the reported minimum look better than reality (bare
`np.nanmin` without a count would silently mask the bad columns). If *all*
entries are NaN, `nanmin` returns NaN → the readout shows "NaN" — honest and
self-documenting.

### R4 — Pattern grep

Search every `.py` file under `mfdfa_engine.py`, `pages/`, `utils/` for the
pattern `x.append(...) if ... else ...` (a conditional expression used as a
statement). Report every hit with file:line. Fix only trivially identical hits
in `mfdfa_engine.py`; list any in `pages/` or `utils/` without changing them.

### R5 — Verification

1. Run `validation/hq_fit_quality.py` — must pass (exit 0).
2. Run all existing `validation/*.py` scripts — all must pass (exit 0),
   proving no numerical regression on healthy signals.
3. Run `.venv/bin/basedpyright mfdfa_engine.py pages/ validation/` and report
   the real result.

## Constraints

- No new dependencies. No changes to `requirements.txt`.
- The fix touches only `mfdfa_engine.py` (lines 129, 305, 358).
- The test file follows the existing validation script conventions exactly.
- Architecture implication: note in `architecture.md` `compute_hq` description
  will need updating after completion (the "Note (fixed 2026-11-20)" stub is
  already there — it's still accurate, just the date on the note will reflect
  the actual fix date).
- The `@stats-reviewer` agent (from the previous feature) can later verify
  the fix by running the harness — structurally independent verification.

## Acceptance criteria

1. `.venv/bin/python validation/hq_fit_quality.py`:
   - On the unfixed code: exits 1, prints visible failure for case B.
   - On the fixed code: exits 0, all assertions pass.
2. All original validation scripts continue to exit 0 after the fix.
3. The "min R² across q" readout in the app shows an honest `np.nanmin` value
   and appends a "(NaN in N/M fits)" suffix when any R² is NaN.
4. The pattern grep (`x.append(...) if ... else ...`) finds no surviving
   instance of the bug pattern in the codebase after the fix.