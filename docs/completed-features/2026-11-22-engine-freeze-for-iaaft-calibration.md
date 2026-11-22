# Feature: Engine freeze for IAAFT calibration

## Purpose

The IAAFT calibration work that follows (Phase 0 instrument verification, then
the size study) measures the surrogate test *through* this engine, so the
engine must first reach a fixed, honestly reported state — any number-moving
change after the study would invalidate it. This feature lands the last such
changes and freezes the state:

1. **Honest IAAFT diagnostics** (IAAFT review F1 + F5): relative spectral
   error and stop reason per surrogate. The failure class the calibration
   will hunt is invisible in today's absolute-error diagnostics; every
   calibration row needs "where did the iteration stop, how bad is the fit".
2. **Engine-review F4**: the app's default fit band moves to the validated
   s ≥ 10. The last number-changing item; at current defaults the app's own
   cascade demo is blocked by the fit gate.
3. **Freeze**: a JSON analysis protocol + a sha256/commit-hash function + a
   git tag, so every future result row is attributable to exact code and
   settings — and a durable results record (`docs/results/`, R4) so every
   measured value can be compared later.

This absorbs the "honest diagnostics" sub-item planned under the calibration
feature in `plan.md` (plan.md is updated at `/complete`).

The frozen protocol is the **source of truth for every number the thesis
reports**: the calibration runs under it, and the real-series numbers are
produced under it as well (the calibration feature's fidelity analysis does
exactly that, on the standard pipeline). The interactive app remains a demo
whose widget defaults differ from the protocol — a deliberate, documented
difference (R3), not an accident.

## Scope

**In scope** (implementation order, one commit per item):

- R0 — pre-flight baseline (no code changes).
- R1 — IAAFT diagnostics + n_capped fix (`mfdfa_engine.py`,
  `validation/iaaft_test.py`).
- R2 — default fit band s ≥ 10 (`utils/pages_logic.py`, two sidebar
  functions; new `validation/default_fit_band.py`).
- R3 — protocol freeze (new `validation/iaaft_protocol.json`,
  `validation/_protocol.py`, `validation/protocol_check.py`; tag).
- R4 — durable results record (new committed `docs/results/`; one dated,
  hash-stamped file written by this feature).

**Out of scope:**

- Phase 0 instrument verification, the independent IAAFT reference
  implementation, the size study, any calibration measurement (next feature).
- Engine F2 constant-run guard — the owner decision stands: handled upstream
  in the gaze processor; provably inert on the 18 sample series (worst
  nonzero const run = 2 samples < any window scale; the length-3 const runs
  are zero runs, which the gate blocks loudly).
- IAAFT UI integration and the null-hypothesis label (deferred UI feature).
- Engine F6 (raw-width edges — the study measures robust width), F7, F9, and
  the 8 engine implicit-Optional type errors (documented baseline).
- Parametric-bootstrap null; the unreliability flag (calibration feature).
- Any change to surrogate generation, `_surrogate_widths`, the p-value, or
  `shuffled_surrogate_test`.

## Requirements

**R0 — pre-flight baseline.** Run all 9 existing harness scripts and
`.venv/bin/basedpyright mfdfa_engine.py pages/ validation/` before any edit;
record the outputs (expected: 9/9 PASS; 19 errors — 8 engine,
4 `pages/dfa.py`, 7 `pages/mf_dfa.py`). The baseline is recorded in the results
file (R4); the completion summary reports it and the end state against it.

**R1 — honest IAAFT diagnostics (reporting only).**

1. `_iaaft_generate` and `iaaft_surrogate` return
   `(surrogate, iterations, rel_spectral_error, stop_reason)`, where
   `rel_spectral_error = mean((A − A_s)²) / mean(A²)` over the rfft
   amplitude bins of the final surrogate (A = target amplitudes), and
   `stop_reason ∈ {"rank_fixed_point", "tolerance", "cap"}`. When both break
   conditions hold in one iteration, rank fixed point wins (checked first).
2. `iaaft_surrogate_test` keeps the 7-tuple
   `(mean, median, std, lower, upper, p, diagnostics)`; `diagnostics =
   (mean_iterations, max_iterations_used, mean_rel_spectral_error,
   max_rel_spectral_error, stop_counts)` with
   `stop_counts = (n_rank_fixed_point, n_tolerance, n_capped)`.
3. IAAFT F5 fix: `n_capped` counts only `stop_reason == "cap"`; a surrogate
   that meets a stopping rule exactly at `max_iter` is counted under that
   rule, not as capped.
4. No change to the iteration, the RNG call order, `_surrogate_widths`, the
   p-value, or the shuffle test.
5. Regression (byte-exact, same seeds as `validation/iaaft_test.py`):
   capture full-precision reprs of the IAAFT test outputs before the edit
   (fGn k=25, cascade k=0) and require exact equality after; shuffle pins
   unchanged (fGn p=0.9032/k=27, cascade p=0.0323/k=0).
6. `validation/iaaft_test.py` updated: stop-reason checks (a known
   converging case stops on a rule; `max_iter` below convergence → "cap");
   the F5 edge case (max_iter set exactly to the pinned convergence
   iteration → not cap); fGn relative error below a pinned threshold
   (≤ 1e-5; measured ~7e-7); determinism extended to the new fields;
   behavioural p/k checks re-pinned exactly.

**R2 — default fit band s ≥ 10 (engine F4).**

1. New pure helper in `utils/pages_logic.py`:
   `default_fit_start(lag_mf, max_index) -> int` — first index with
   `lag_mf >= 10`; 0 if the grid never reaches s=10; clamped to `max_index`.
2. `sidebar_fitting_range` (pages_logic.py:195) and
   `sidebar_fitting_rane_mf` (pages_logic.py:314) use it as the `fit_start`
   slider default. Slider min/max and the `fit_end` default stay unchanged;
   if `lag_mf[-1] < 10`, show a Hungarian warning that the grid is too short
   for the validated band.
3. Hungarian help/caption text in both fit-range sections states that the
   validated band starts at s ≥ 10 (the README condition).
4. New harness script `validation/default_fit_band.py` (no Streamlit
   runtime; calls only pure helpers):
   - Pre-registered — fails before / passes after: generated cascade
     (14 levels, p=0.25, seed 0 — the page defaults) on the default MF-DFA
     grid; the `default_fit_start` band passes `get_valid_fitting_range`,
     and a negative control documents that the fit_start=0 band is blocked.
   - fOU default-band check (closes engine F8): same generation as
     `fou_subtract_one.py` (t_final=20, delta_t=0.001, theta=0.3, sigma=0.1,
     H=0.7, seeds 0/1/2), app-default lag grid (log10 0.5–3.0, 100 lags) +
     the default fit rule, `subtract_one=True`; |H − 0.7| < 0.15
     (the pinned FOU_TOL, fou_subtract_one.py:38).
   - fGn upload-path sanity on the same rule, |H − 0.7| < 0.10 (FGN_TOL).
   - Before/after printout (reporting, not assertions), recorded in the
     results file (R4): fit_start=0 vs the
     new default, for the demo signals and — when present —
     `docs/sample_data/2_v.sz./puzzle_03.csv` and
     `docs/sample_data/3_v.sz./puzzle_03.csv` (skip cleanly with an explicit
     note when absent, so the script exits 0 on a fresh clone). Columns: fit
     band, gate status, h(−4), h(−2), h(2), h(4), width_raw, width_robust,
     min R² (MF-DFA) / H, R² (DFA). Blocked configurations are reported as
     such — the `fit_end` default is out of scope, and short series may stay
     blocked at the top of the band.

**R3 — freeze.**

1. New `validation/iaaft_protocol.json` (stdlib JSON) freezing the
   calibration protocol: lag grid rule (10..N/4, 40 log-spaced ints), q grid
   (linspace(−5, 5, 101), |q| ≤ 0.1 dropped), fit band rule
   (indices `[lag.size//8 : int(lag.size/1.5)]`), polynomial order 1, robust
   width settings (q_width_max=4, positive_q_only=False, f_floor=0.0),
   n_surrogates 39, IAAFT max_iter 500, tol 1e-6, and seed policy, plus a
   preprocessing summary (pointer to `docs/references/data-processing.md` +
   the interpolated-gap cap). The JSON also carries an explicit `role`
   declaration and an `app_defaults` section: the protocol is what produces
   every reported thesis number and all calibration results, while the
   app's widget defaults (log10 0.5–3.0 / 0.5–3.6, 100 lags, band: first
   lag ≥ 10 → end) are recorded there as **different from the protocol**
   (lag-grid density, range, and band rule). The methods sentence for the
   thesis follows from it: reported numbers come from the protocol
   pipeline; app results at its defaults or any other widget settings are
   demo/exploratory.
2. New `validation/_protocol.py`: `protocol_hashes() -> dict` — sha256 of
   the JSON file bytes + `git rev-parse HEAD`; validates required fields on
   load.
3. New harness script `validation/protocol_check.py`: asserts the required
   fields, prints both hashes, exit 0.
4. Tag `v0.2-engine-frozen` on the final commit of this feature (owner's
   action, or on explicit request; the name is confirmed by the owner then).

**R4 — durable results record.**

1. New committed directory `docs/results/`, mirroring the
   `docs/reviews/` naming convention: one dated file per experiment,
   `YYYY-MM-DD-<experiment>.md`.
2. Every results file is stamped with: the fixed seeds used, the library
   versions from the harness header (python, numpy, MFDFA, streamlit),
   and the `protocol_hashes()` output (protocol sha256 + engine commit)
   captured at run time — any value in the file is traceable to exact
   code and settings.
3. This feature writes one file —
   `docs/results/<YYYY-MM-DD>-engine-freeze.md` (dated with the
   implementation day), accumulating across the work items and committed
   alongside each: the R0 baseline, the R1 pre-change regression capture
   (full-precision reprs), the R2 before/after tables (demo signals + the
   two real series when present), and the R3 hashes.
4. Policy going forward, binding for the calibration feature: every
   experiment (Phase 0 cross-check, size study, real-series fidelity)
   writes its own dated file under `docs/results/`.
5. Real-data policy: derived per-series statistics (widths, p-values, QC
   numbers) are committed there — pseudonymous summary numbers the thesis
   reports anyway; the raw series stay gitignored in `docs/sample_data/`.

## Constraints

- No new dependencies: stdlib `json`/`hashlib`/`subprocess` only (PyYAML is
  not installed).
- Reuse engine functions; no MF-DFA or IAAFT reimplementation anywhere. The
  independent reference implementation for Phase 0 is the *next* feature,
  deliberately not this one.
- Byte-stability: R1 changes only return payloads and diagnostics. The only
  caller of the changed API is `validation/iaaft_test.py` (no IAAFT UI
  wiring exists). The archived IAAFT spec stays untouched as history;
  `architecture.md` is updated at `/complete`, not during implement.
- Streamlit/UI: load the `developing-with-streamlit` skill before touching
  pages; verify unfamiliar APIs against the pinned 1.58; all new UI text in
  Hungarian; no `use_container_width`; existing plot calls as-is.
- Tests-first for the two genuine defects (the n_capped edge case; the
  cascade default-band block). Every changed number gets a before/after
  table plus a one-sentence explanation; an unexplained change is a defect.
- `docs/sample_data/` is read-only local data (gitignored); harness scripts
  referencing it skip cleanly when it is absent.
- Typecheck must not exceed the 19-error baseline (the 8 engine
  implicit-Optional errors stay; fixing them is out of scope).
- Architectural changes (to be documented in `architecture.md` at
  `/complete`): `validation/` grows to 14 files (11 runnable scripts +
  `_common.py` + `_protocol.py` + `iaaft_protocol.json`); `utils/pages_logic.py` gains a pure, headless-testable
  fit-default helper; the IAAFT diagnostics tuple layout changes (engine
  API); a new committed `docs/results/` directory (dated, hash-stamped
  experiment records) is added to the project layout.

## Acceptance criteria

1. All 11 runnable harness scripts pass (9 existing + 2 new); the
   real-series section of `default_fit_band.py` skips cleanly when
   `docs/sample_data/` is absent.
2. Typecheck: ≤ 19 errors, no new ones (vs the R0 baseline).
3. R1 regression: IAAFT fGn (k=25) and cascade (k=0) p-values byte-exact vs
   the pre-change reprs; shuffle pins unchanged.
4. R2: the pre-registered cascade check fails on the pre-change code and
   passes after; the fOU default-band check passes at the pinned tolerance;
   the before/after table covers both real series (when present) and the
   demo signals with the fit-gate status per configuration; slider ranges
   unchanged (only the default value moved).
5. R3: the protocol JSON loads with all required fields, including the
   role declaration and the `app_defaults` difference; the
   `protocol_hashes()` output is recorded in the results file (R4) and
   the completion summary; the tag exists on the final commit.
6. The completion summary states which engine findings were deliberately
   left open (F2 with the upstream decision and QC evidence, F6, F7, F9) and
   what was not verified.
7. R4: `docs/results/` exists with the engine-freeze file — baseline,
   before/after tables, hashes — stamped with seeds, versions, and the
   `protocol_hashes()` output.
