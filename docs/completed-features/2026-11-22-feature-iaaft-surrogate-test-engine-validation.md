# Feature: IAAFT surrogate test — engine + validation

## Purpose

Close review finding F5 (`docs/reviews/2026-11-21-engine-review.md`): the
surrogate test is currently shuffle-only. Shuffling destroys *all* temporal
order, so its null hypothesis is "no temporal structure at all" — a
significant p-value cannot distinguish multifractality produced by nonlinear
cascade structure from structure a *linear* process would show anyway.

The IAAFT surrogate (Schreiber & Schmitz 1996) keeps the input's power
spectrum (linear correlations, approximately) and its exact value
distribution, destroying only the nonlinear temporal structure. Its null
hypothesis is "a stationary linear Gaussian process, possibly nonlinearly
rescaled". A significant IAAFT result therefore supports the thesis claim:
the robust spectrum width DA exceeds what a linear process with the same
spectrum and distribution produces.

Implementation source:
`docs/references/2026-11-21-iaaft-implementation-findings.md` (algorithm
section 2, convergence criteria section 4, pitfalls section 5, validation
plan section 7; 17-entry bibliography). The code is written from the
published algorithm, not copied from any surveyed repository (license note,
findings section 3).

Scope split (owner decision, 2026-11-21): **this feature is engine +
validation only.** UI integration (radio selector, method-aware result table)
is a separate follow-up feature — see `plan.md`.

## Scope

### In scope

1. **R1 — `iaaft_surrogate`:** single-surrogate generator in
   `mfdfa_engine.py` (compute layer).
2. **R2 — shared surrogate-loop helper:** extract the existing loop from
   `shuffled_surrogate_test` (mfdfa_engine.py:205-249) into one private
   helper used by both tests.
3. **R3 — `iaaft_surrogate_test`:** full surrogate test, same contract as
   the shuffle test plus convergence diagnostics.
4. **R4 — new `validation/iaaft_test.py`** (10th harness script).
5. **R5 — one-line fix** of the stale citation at
   `validation/surrogate_test.py:5` ("mfdfa_engine.py:235" → the actual
   line of the p-value computation after this refactor).

### Explicitly out of scope

- All UI changes: radio selector, method-aware explanation text, verdict
  line, convergence caption, results-table changes. Follow-up feature.
- CSV export / session-state persistence of results (owner's stated future
  direction; the 7-tuple return shape keeps it possible without engine
  changes later).
- AAFT, the Venema stochastic variant, CAAFT; end-matching/trimming
  preprocessing; multivariate or unevenly sampled data.
- Surrogate testing on the generated-cascade branch of the page.
- Removing or weakening the shuffle test; any change to fitting, spectrum,
  or width-statistics code.
- Replacing existing `use_container_width` calls (no UI code is touched).

## Requirements

### R1 — `iaaft_surrogate(signal, seed=None, max_iter=500, tol=1e-6)` (mfdfa_engine.py)

Generates one IAAFT surrogate of a 1-D real signal; placed next to
`shuffled_surrogate_test` in the compute layer.

1. **Input guard:** reject non-finite values (and non-1-D input) with a
   Hungarian `ValueError`:
   "Az IAAFT surrogate generálásához 1-D, véges (nem NaN/inf) jel szükséges."
   Rationale (findings section 5.3): rank ordering with NaN is undefined.
2. **Targets:** `sorted_values = np.sort(signal)`;
   `target_amp = np.abs(np.fft.rfft(signal))`.
3. **Init:** `surrogate = np.random.default_rng(seed).permutation(signal)`
   (the j = 0 iteration of the paper).
4. **Iterate** at most `max_iter` times:
   - **Spectrum step:** `fft = np.fft.rfft(surrogate)`; impose the target
     amplitudes while keeping the *current* surrogate's phases
     (`new_fft = target_amp * fft / |fft|`), without ever dividing by zero
     — bins with zero magnitude get `target_amp` imposed directly (note
     `rfft[0]` equals the signal sum for every permutation, so imposing it
     directly is exact); back-transform with
     `np.fft.irfft(new_fft, n=len(signal))`.
   - **Distribution step:** rank-order the result onto the original values
     with a **stable** sort (`kind="stable"`) — repeated values (cascade,
     quantized data) must map reproducibly (findings section 5.5).
   - **Stop when** (a) the rank ordering is identical to the previous
     iteration's, or (b) the relative change of the mean squared amplitude
     error falls below `tol`, or (c) `max_iter` is reached.
5. **Return** `(surrogate, iterations, final_spectral_error)` where
   `final_spectral_error = mean((target_amp - |rfft(surrogate)|)^2)`.
   The result always ends on the distribution step, so the value multiset
   is exact (findings section 5.1).
6. **Determinism:** the only entropy source is the seeded permutation; same
   signal + seed → identical return values. No global RNG use.

### R2 — shared private helper (mfdfa_engine.py)

Extract the body of `shuffled_surrogate_test` (F3 guard, attempts cap,
per-surrogate pipeline, statistics, p-value; mfdfa_engine.py:198-249) into a
private helper, e.g. `_surrogate_widths(signal, n_surrogates, robust_width,
mfdfa_parameters, fit_start, fit_end, generate)` where
`generate(signal, rng)` yields one candidate surrogate:

- shuffle path: `generate` returns `rng.permutation(signal)` — the RNG call
  sequence must remain *exactly* what it is today;
- the F3 NaN guard and the insufficient-surrogates error live once in the
  helper, so both tests are protected by construction.

**Hard constraint:** `shuffled_surrogate_test` keeps its public signature
and produces byte-identical results — the harness pins fGn p = 0.9032
(k = 27, surrogate mean 0.0748) and cascade p = 0.0323 (k = 0, surrogate
mean 0.9130) (`validation/surrogate_test.py`, seed 5, n = 30). Any drift is
a failure.

### R3 — `iaaft_surrogate_test(signal, n_surrogates, robust_width, mfdfa_parameters, fit_start, fit_end, seed=None, max_iter=500, tol=1e-6)`

Same contract as `shuffled_surrogate_test`, plus:

- one `np.random.default_rng(seed)` for the whole run; each attempt consumes
  exactly one `rng.permutation` (the IAAFT iteration itself draws no further
  randomness), so a fixed seed reproduces the run;
- per attempt: generate → `run_mfdfa` → `compute_hq` → `spectrum` →
  `spectrum_width_robust` (q_width_max = 4, positive_q_only = False); skip
  invalid candidates; attempts cap 5*n; same
  `p = (1 + #{widths >= observed}) / (n + 1)`;
- **return a 7-tuple**
  `(mean, median, std, lower, upper, p_value, diagnostics)` with
  `diagnostics = (mean_iterations, max_iterations_used,
  mean_final_spectral_error, n_capped)` where `n_capped` counts surrogates
  that stopped at `max_iter`. Capped surrogates are still used — reported,
  not silently discarded (findings section 4: non-convergence is surfaced,
  not hidden). This return shape is final so the later UI feature needs no
  engine change.

### R4 — `validation/iaaft_test.py` (new, 10th script)

House protocol (`print_header`/`Check`, fixed seeds, exit 0/1). Constants
mirror `surrogate_test.py` for comparability: n_surrogates = 30, surrogate
seed = 5, fGn via `np.random.seed(11); fgn(4096, 0.7)`, cascade
`n_levels=14, p=0.3, seed=7`, standard harness pipeline
(`_common.standard_run`, `hq_and_spectrum`).

Unit checks (direct `iaaft_surrogate` calls, one fixed seed):

1. exact distribution: `np.array_equal(np.sort(surr), np.sort(signal))` —
   zero tolerance, any iteration count;
2. `iterations` in `[1, max_iter]`; `final_spectral_error` printed and
   asserted below a threshold **pinned from the first measured run** and
   documented in the script (project tolerance protocol: measure, then fix
   the assert with margin);
3. determinism: two calls, same seed → identical surrogate (`array_equal`)
   and identical iterations;
4. non-finite input raises `ValueError` (message printed).

Behavioural checks (via `iaaft_surrogate_test`, standard pipeline):

5. fGn H=0.7: p-form check `(1+k)/(n+1)` with `k = p*(n+1) - 1` an exact
   integer in `[0, n]` — the small `p_form_ok` helper is duplicated here
   rather than imported across scripts; `surrogate_test.py` keeps its own
   copy;
6. fGn H=0.7 → **not significant** (p > 0.05);
7. cascade p=0.3, 14 levels → **significant** (p <= 0.05);
8. print observed width, surrogate stats, and the full diagnostics tuple;
9. wall time per surrogate printed (IAAFT cost vs `run_mfdfa` cost).

**Pre-registered expectations:** checks 6 and 7 are falsification criteria
fixed in advance (`plan.md`). If the first measured run contradicts them,
STOP and report to the owner — do not re-tune parameters silently.

### R5 — stale citation fix (validation/surrogate_test.py:5)

"mfdfa_engine.py:235" → the actual line of the p-value computation after
this refactor (re-check the final line number during implementation).

### R6 — Verification

1. `.venv/bin/python validation/iaaft_test.py` — exits 0, all checks PASS.
2. All 10 `validation/*.py` scripts — all exit 0.
3. `validation/surrogate_test.py` reproduces today's numbers exactly
   (fGn p=0.9032/k=27, cascade p=0.0323/k=0) — proves the R2 refactor is
   behaviorally inert.
4. `.venv/bin/basedpyright mfdfa_engine.py pages/ validation/` — real
   result reported; no increase over the 19-error baseline.
5. Smoke: both analysis pages import; `streamlit run
   mfdfa_streamlit_start.py` boots (HTTP 200). No manual UI check — this
   feature changes no UI.

## Constraints

- Only `mfdfa_engine.py`, new `validation/iaaft_test.py`, and the one
  corrected line in `validation/surrogate_test.py` change. No pages/utils
  changes, no new dependencies (numpy's `fft` only), no `requirements.txt`
  change.
- No numerical change on any existing path; all existing harness outputs
  byte-identical.
- Seeds recorded and printed by the new script; library versions printed via
  `print_header`.
- At `/complete`: `architecture.md` gains the two new engine functions and
  the private helper, the validation count 9 → 10, and the F5 bullet notes
  the engine part done / UI part planned; `plan.md` moves this feature to
  Completed with its archive path.

## Acceptance criteria

1. An IAAFT surrogate preserves the exact value multiset (zero-tolerance
   equality) at any iteration count; a fixed seed reproduces it exactly;
   non-finite input raises `ValueError`.
2. Shuffle-test outputs are byte-identical to today's (fGn p=0.9032/k=27;
   cascade p=0.0323/k=0) — the shared helper changed nothing.
3. `iaaft_surrogate_test` returns the 7-tuple with diagnostics; fGn is not
   significant and the cascade is significant against IAAFT surrogates
   (pre-registered; a contradiction stops the feature for review, not the
   threshold).
4. All 10 validation scripts exit 0; typecheck does not exceed the 19-error
   baseline; the app boots.
5. No file outside the three listed in Constraints changed.
