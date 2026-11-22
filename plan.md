# Plan

## Completed

- **2026-11-22 — IAAFT surrogate test — engine + validation.**
  Archived: `docs/completed-features/2026-11-22-feature-iaaft-surrogate-test-engine-validation.md`.
  Review: `docs/reviews/2026-11-21-iaaft-review.md` — algorithm and the
  byte-identical refactor confirmed; calibration gap documented (see the
  planned calibration feature below).
- **2026-11-21 — Surrogate NaN guard (F3) + honest fit-end display (F1).**
  Archived: `docs/completed-features/2026-11-21-feature-surrogate-nan-guard-f3-honest-fit-end-display-f1.md`.
  Source: review findings F3/F1 in `docs/reviews/2026-11-21-engine-review.md`.
- **2026-11-21 — Fix `compute_hq` R² append bug + add regression test.**
  Archived: `docs/completed-features/2026-11-21-feature-fix-compute-hq-r-append-bug-add-regression-test.md`.
- **2026-11-20 — Validation harness + `@stats-reviewer` agent.** Archived:
  `docs/completed-features/2026-11-20-validation-harness-and-stats-reviewer.md`.
- **2026-11-21 — Full MF-DFA math pipeline review (Sonnet 5.5).**
  Report: `docs/reviews/2026-11-21-engine-review.md`. Findings F1–F9.

## Planned (accepted by owner, not yet specified)

- **IAAFT calibration for the thesis data** (source:
  `docs/reviews/2026-11-21-iaaft-review.md`; owner decision 2026-11-22):
  - **Goal:** determine whether the IAAFT test can be calibrated to be
    reliable on the thesis data (gaze displacement series,
    `docs/sample_data/`: 2 participants x 9 puzzles, N = 714-17,224,
    7.6-19.8 % zeros, longest constant run <= 3; provenance:
    `docs/references/data-processing.md`). **If it cannot be calibrated for
    all series, that is an accepted outcome:** document it in the thesis
    limitations section (owner decision) and keep the shuffle test as the
    weaker, valid test.
  - **Size study** (`validation/iaaft_size.py`): rejection rate at p <= 0.05
    under known-true nulls — fGn H=0.5/0.7/0.9 and lognormal-of-fGn at
    several tail strengths — R >= 200 realizations, n=39 surrogates,
    binomial intervals, fixed seeds; assert only on the Gaussian fGn case,
    print the heavy-tailed rates (review suggestion 1).
  - **Honest diagnostics** (engine): relative spectral error
    `mean((A - A_s)^2) / mean(A^2)` and the stop reason (rank fixed point /
    tol / cap) in the diagnostics tuple; flag a surrogate set as unreliable
    above a pinned relative-error threshold (review suggestion 2).
  - **Fidelity on the real sample data:** per-series relative spectral error,
    stop reason, and whether the observed width sits inside the surrogate
    null cloud; characterize tail heaviness. This answers "is it usable on
    *my* data", which synthetic nulls alone cannot (review section 5).
  - **Decision rule (fixed in the spec):** usable if the Gaussian fGn case is
    calibrated and the data-like heavy-tailed false-alarm rate stays bounded
    (about <= 10 %); otherwise the limitations route.
  - **Optional remedy if miscalibration persists:** parametric-bootstrap null
    (fit a linear model, rescale to the data distribution, build the null
    from fresh realizations) as a second null — review suggestion 4; needs
    supervisor input before building.
- **IAAFT surrogate test — UI integration** (deferred until the calibration
  feature is resolved): radio selector `Keveres (shuffle) / IAAFT` (default
  shuffle), method-aware explanation text (fixes the hardcoded "100-szor"),
  unified results table + `(k, n)` + alpha=0.05 verdict line. Must state the
  null as "linear Gaussian process, rescaled" (not "no cascade"), show the
  surrogate null distribution (mean/sd/interval) next to the observed width,
  and surface the unreliability flag from the calibration feature. Load the
  `developing-with-streamlit` skill (see AGENTS.md). Candidate to also absorb
  the owner's planned CSV export of results (session-state storage +
  download at the end).

## Upstream (gaze_processor project — separate repository)

- **F2**: constant-value runs from linear interpolation pass the fit-band
  gate unguarded (h(−4) 0.643 → 0.948). Solved upstream: verify/add the
  longest constant-velocity run to the QC output, then set `fit_start` above
  it when analyzing in this app. The owner confirmed the data comes from the
  gaze processor, so upstream prevention + manual fit-range awareness is the
  chosen approach.

## Open questions (for the owner/supervisor, no code change)

- **Asymmetry sign convention** (review item 14): the code computes
  `asymmetry = right_width − left_width`. Check the cited paper's convention;
  if it differs, state it explicitly in the methods section.
- **F8**: the fOU H = slope − 1 validation ran on the harness fit band
  (~22..~640 samples), not the app's default slider range. The crossover sits
  at 1/theta time units (~3,333 samples at theta=0.3, delta_t=0.001); keep
  the DFA fit band below it (`lag_stop ≤ 3.5` with current defaults). The
  owner confirmed a visible bend when increasing the max window past the
  crossover — expected fOU physics, handled by keeping the fit band below it.
- **Robust width vs q density** (review item 15): robust width varies mildly
  with q_num (cascade: 1.409/1.432/1.446 for 21/51/101 q values). Report the
  q-grid used with every thesis number.
- **App defaults vs validated settings** (engine-review F4, re-flagged by the
  IAAFT review): the app's default fit band starts at `fit_start = 0`
  (smallest lag s = 3) while the validated band and README guidance use
  s >= 10. Not scheduled yet — it changes numbers the app reports by default.
  Decide: change the defaults, or warn in the UI.

## Deferred (no action planned)

- **F7** latent hazards (`subtract_one=True` default, no tolerance check on
  q=2, unseeded `generate_fou`): no current caller is affected; the
  validation harness pins the correct behavior.
- **F9** cosmetic items: `plot_hq` y-axis clipped to [0, 2]; 3-point fit
  minimum; package docstring vs code inconsistency (|q| ≤ 0.1 removed, not
  just q=0).
- **`s_min` guard** (earlier open finding, now covered by the upstream F2
  decision): do not add to the engine; rely on upstream gap handling and
  manual fit-range selection.
