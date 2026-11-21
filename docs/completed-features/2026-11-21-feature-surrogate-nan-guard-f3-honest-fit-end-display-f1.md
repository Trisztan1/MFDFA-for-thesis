# Feature: Surrogate NaN guard (F3) + honest fit-end display (F1)

## Purpose

Two defects from the 2026-11-21 engine review (`docs/reviews/2026-11-21-engine-review.md`):

- **F3 (numerically dangerous):** `shuffled_surrogate_test` (mfdfa_engine.py:190-237)
  accepts a NaN observed `robust_width`. Then `surrogate_widths >= nan` is all
  False, so k = 0 and the p-value becomes the minimum possible, `1/(n+1)` —
  reporting **maximum significance** for a signal that could not produce a valid
  width at all. If this fires on real thesis data the reported conclusion is
  backwards.
- **F1 (misleading):** every fit slices `[fit_start:fit_end]`, so the last
  fitted scale is index `fit_end - 1`, but the sidebar caption
  (utils/pages_logic.py:205, :324) and the gray fit band
  (mfdfa_engine.py:299) display `lag_mf[fit_end]` as included. The reviewer
  measured no visible numerical effect, so this is a reporting-honesty fix, not
  a math fix.

## Scope

### In scope
1. **F3a — engine guard:** reject a non-finite `robust_width` at the top of
   `shuffled_surrogate_test`, before any surrogate is generated.
2. **F3b — page handling:** `pages/mf_dfa.py` catches the resulting
   `ValueError` and shows a Hungarian warning instead of a traceback. The same
   handler catches the pre-existing "not enough valid surrogates" `ValueError`
   (currently uncaught — review item 18), closing both with one change.
3. **F1 — display honesty (display-only, no numeric change):** all three
   display sites report the last *actually fitted* scale (`fit_end - 1`).
4. **Test:** a regression check in `validation/surrogate_test.py` that a NaN
   observed width does not yield a p-value.

### Explicitly out of scope
- Making the fit slice inclusive (`fit_end + 1`). Rejected: it touches ~8 slice
  sites and would require re-validating every harness threshold for zero
  numerical benefit (reviewer measured no visible H change).
- IAAFT / phase-randomised surrogates (F5) — planned as a separate feature.
- Constant-run handling (F2) — handled upstream in the gaze processor.
- Usage-guideline documentation — already written 2026-11-21 (`README.md`,
  `architecture.md` §7, `plan.md`).
- Any of the deferred cosmetic items (F7, F9).

## Requirements

### R1 — Engine guard (mfdfa_engine.py, `shuffled_surrogate_test`)

Immediately after the parameter unpacking and before `rng`/the loop, validate
the observed width:

```python
if not np.isfinite(robust_width):
    raise ValueError(
        "A mért robusztus spektrumszélesség nem véges (NaN vagy inf), "
        "ezért a surrogate teszt nem értelmezhető. Ellenőrizd az illesztési "
        "tartományt és a q-tartományt."
    )
```

- Must raise `ValueError` (consistent with the existing insufficient-surrogates
  error at :224-228), not return a NaN tuple.
- Message in Hungarian (UI text convention).
- No other behavior change: valid widths must produce byte-identical results
  (same p-value, same surrogate statistics, same seeds) as today.

### R2 — Page handling (pages/mf_dfa.py)

The surrogate invocation (`pages/mf_dfa.py:115-122`) is wrapped so both failure
modes surface as a warning:

```python
if st.session_state.surrogate_test_run:
    st.session_state.surrogate_test_run = False
    with st.spinner("In progress..."):
        try:
            surrogate_results = mfdfa_engine.shuffled_surrogate_test(...)
        except ValueError as e:
            st.warning(str(e))
            surrogate_results = None
```

- After a failure, `surrogate_results = None` so `plot_spectrum_stats` renders
  its normal no-surrogate path (no broken table).
- `st.session_state.surrogate_test_run` already reset to `False` before the
  call, so the failed run does not loop.

### R3 — Fit-end display (display-only)

Three sites must report the last fitted scale, `fit_end - 1`:

1. `utils/pages_logic.py:205` — `sidebar_fitting_range` caption.
2. `utils/pages_logic.py:324` — `sidebar_fitting_rane_mf` caption.
3. `mfdfa_engine.py:299` — the gray fit band's right edge in
   `plot_fluctuation_mf`.

Bounds are safe by construction: the sliders enforce
`fit_start + 3 <= fit_end <= len(lag_mf) - 1`, so `fit_end - 1` is always a
valid index and always `> fit_start`.

Do **not** change any slice, the gate (`get_valid_fitting_range`), or the
fit-line overlays — those are already consistent with the exclusive slice.

### R4 — Regression test (validation/surrogate_test.py)

Add a check that runs `engine.shuffled_surrogate_test` with a NaN observed
width on the existing fGn signal and asserts it raises `ValueError`:

- `shuffled_surrogate_test(y, 30, np.nan, mfdfa_parameters, fit_start, fit_end, seed=1)`
  must raise `ValueError`.
- Also assert the healthy path is unchanged: the existing fGn (p > 0.05) and
  cascade (p <= 0.05) checks must still pass with identical values.
- Print the raised message and the unchanged p-values.

### R5 — Verification

1. `validation/surrogate_test.py` — passes, including the new NaN check.
2. All 9 `validation/*.py` scripts — all still exit 0 (proves no numerical
   regression).
3. `.venv/bin/basedpyright mfdfa_engine.py pages/ validation/` — report the
   real result (baseline is 19 pre-existing errors; must not increase).
4. Manual in-app check: MF-DFA page, uploaded branch — the caption reads the
   same scale as the leftmost plotted fit point, and the gray band's right edge
   sits on the last fitted point, not one past it.

## Constraints

- Only `mfdfa_engine.py`, `pages/mf_dfa.py`, `utils/pages_logic.py` and
  `validation/surrogate_test.py` change. No new files, no dependencies, no
  `requirements.txt` change.
- No numerical behavior change for valid inputs — the harness must reproduce the
  current numbers exactly.
- Architecture impact: none structural. After completion, `architecture.md` §7
  must update the F1/F3 bullets from "to fix" to fixed, and `plan.md` must move
  this feature to Completed. Note: the reviewer measured the harness as
  "8 runnable scripts plus `_common.py`" — `architecture.md` §6 still says
  "8 scripts" while §7 says 9; align both to one count at completion.
- The `fit_end` slider labels stay as-is (they are indices; the caption is what
  states the scale).

## Acceptance criteria

1. `shuffled_surrogate_test` with a NaN width raises `ValueError` with a
   Hungarian message; no borderline path returns
   `p == 1/(n_surrogates + 1)` for an invalid signal.
2. Valid-input surrogate results are numerically identical to before the change
   (fGn p > 0.05, cascade p <= 0.05, same values printed).
3. The MF-DFA uploaded branch shows a warning — not a traceback — for both a
   NaN width and an insufficient-surrogates failure.
4. Both sidebar captions and the gray fit band report `lag_mf[fit_end - 1]`,
   matching the points actually fitted.
5. All 9 validation scripts exit 0; typecheck error count does not exceed the
   19-error baseline.
