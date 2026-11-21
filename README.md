# MF-DFA Thesis App

Streamlit multipage application for multifractal detrended fluctuation analysis
(MF-DFA) of time series, built as a thesis demo. All UI text is Hungarian.

## Run

```sh
.venv/bin/streamlit run mfdfa_streamlit_start.py
```

Python 3.12 via `uv` (`.venv`); dependencies fully pinned in
`requirements.txt` (rebuild: `uv pip sync requirements.txt`).
Typecheck: `.venv/bin/basedpyright mfdfa_engine.py pages/ validation/`.
Numerical validation harness: 9 scripts under `validation/`, each exits 0 on
pass (`_common.py` is the shared helper, not a test).

## Important usage findings (from the 2026-11-21 engine review)

These are conditions the review established for trusting the numbers. Read
them before quoting any output in the thesis.

### 1. Smallest fitted window: keep s ≥ 10

The package drops only scales ≤ order + 1, so the slider allows fits starting
at s = 3. On the generated binomial cascade the default fit (fit_start = 0)
was **blocked** by the validity gate: at s = 3, 49 of the 99 negative-q
fluctuation values are 0 or non-finite (the cascade takes a few discrete
values, so short windows can be perfectly detrended). With the fit starting
at s ≥ 10 everything is valid. Measured on the cascade (p = 0.25, 14 levels,
seed 0): default → h(−4) = NaN, robust width 0.724 (NaN-contaminated);
fit from s ≥ 10 → h(−4) = 1.781, robust width 1.623 vs theory 1.546.

**Rule: start the fit band at s ≥ 10 samples.**

### 2. Constant-value runs poison negative q (upstream issue)

Linear interpolation of missing gaze samples creates constant-velocity runs.
Inside such a run the profile is linear, order-1 detrending removes it almost
exactly, and the near-zero residuals dominate F_q for q < 0 — silently
inflating h(−4) (measured 0.643 → 0.948 with 20 runs of 15 samples) and
widening the spectrum. The app's fit-band gate does **not** catch this (F
stays finite and positive). Exact-zero runs are caught (the gate blocks
them); constant-value runs are not.

**Rule: the gaze processor must cap interpolation gaps below the smallest
fitted scale (or the fit must start above the longest constant run). This is
handled upstream; the app has no defense against it.**

### 3. Report the robust width, not the raw width

The raw spectrum width Δα_raw is determined by the `np.gradient` edge
estimates: the α minimum and maximum sit exactly at the two edge q values
(±5), where the derivative uses first-order one-sided differences — the
least accurate estimates in the whole spectrum. The robust width
(|q| ≤ 4, f ≥ 0) trims exactly those edge points.

The robust width still depends mildly on the q-grid density (cascade p = 0.3,
seed 7: 1.409 / 1.432 / 1.446 for 21 / 51 / 101 q values), so always report
the q-grid with the number.

**Rule: the thesis number is Δα (robust). Report the q-grid used.**

### 4. Width error vs theory is estimator bias, not a bug

The relative width error against the finite-q theoretical spectrum is
dominated by estimator bias at finite N (p = 0.55 at 14 levels gives a
robust ratio of 2.74 for a perfectly correct pipeline; the width does not
converge monotonically even at N = 2^18). Judge correctness by the h(q)/τ(q)
agreement instead: the deterministic cascade recovers h(q) with max |Δh| =
0.038 through the app's own pipeline.

### 5. fOU crossover: keep the fit band below 1/theta

The fractional Ornstein–Uhlenbeck signal is walk-like only below its
mean-reversion timescale. Above the crossover (roughly 1/theta time units =
1/(theta × delta_t) samples) the DFA slope bends toward 0 and the
H = slope − 1 correction stops being valid. With the default theta = 0.3,
delta_t = 0.001 the crossover is ~3,333 samples, so `lag_stop ≤ 3.5` is safe;
the default `lag_stop = 3.0` (max 1,000 samples) never crosses it. If you
change theta or delta_t, recalculate: crossover_samples ≈ 1/(theta × delta_t).

**Rule: keep the DFA fit band below 1/(theta × delta_t) samples.**

### 6. Asymmetry sign convention — check before quoting

The app computes `asymmetry = right_width − left_width` (positive = the
spectrum arch is longer on the right/smooth side). Conventions in the
literature vary (some papers use left − right). Check the sign convention of
the paper cited in the thesis; if it differs, state the convention
explicitly in the methods section.

### 7. Surrogate test: shuffle-only null

The p-value formula (1 + k)/(n + 1) is verified correct. But a plain shuffle
destroys linear correlation together with nonlinear structure, so
"significant" means "the width is not explained by the value distribution
alone" — not "caused by a nonlinear cascade." An IAAFT (phase-randomised)
surrogate test is planned to separate the two. Until then, word the
conclusion carefully.

## Validation status

All 9 harness scripts pass (fixed seeds, printed versions):
package ≡ independent reference implementation to 3.1e-16; q/lag/column
alignment holds for every q_num tried (21/51/100/101); fGn spurious width
baseline 0.070 ± 0.031 (raw) / 0.056 ± 0.024 (robust); deterministic cascade
max |Δh| = 0.038 vs theory; the R² append bug (fixed 2026-11-21) is pinned by
a regression test that fails on the bug and passes on the fix.

Full review: `docs/reviews/2026-11-21-engine-review.md`.
Roadmap and open questions: `plan.md`.
