# Plan

## Completed

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

- **IAAFT surrogate test** (review finding F5): the current shuffle-only
  surrogate test destroys linear correlation along with nonlinear structure,
  so "significant" cannot be read as "multifractal due to nonlinear cascade."
  A phase-randomised (IAAFT) surrogate would separate the two. Requires a
  new implementation in the engine + a validation script (fGn should be
  non-significant against IAAFT surrogates; cascade should be significant).

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
