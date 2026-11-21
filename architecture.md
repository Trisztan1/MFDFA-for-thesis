# Architecture

Actual architecture of the MF-DFA thesis app, as verified by reading the code on 2026-11-19. This file documents what exists; it does not describe planned functionality.

## 1. Overview

Single-user Streamlit multipage application for MF-DFA (multifractal detrended fluctuation analysis) of time series, built as a thesis demo. All UI text is Hungarian. The app wraps the `MFDFA` PyPI package (LRydin/MFDFA) for the fluctuation computation and adds its own spectrum, width statistics, surrogate test, and validation code on top. It analyzes two kinds of input:

- **Generated validation signals** with known scaling properties: fractional Ornstein–Uhlenbeck (monofractal) and a random binomial cascade (multifractal, with closed-form theoretical spectrum).
- **Uploaded preprocessed series**: single-column CSVs prepared externally (per `docs/references/`, these come from the separate `gaze_processor` project; e.g. gaze-displacement/velocity series).

## 2. Technologies and dependencies

- Python 3.12 (`.python-version`); environment managed with `uv`, virtualenv in `.venv`.
- `requirements.txt` — fully pinned, lock-style list (every transitive dependency; also pins the dev tool `basedpyright`). Rebuild with `uv pip sync requirements.txt`.
- Runtime: `streamlit==1.58.0`, `plotly==6.8.0`, `numpy==2.4.6`, `pandas==3.0.3`, `MFDFA==0.4.3` (also provides `fgn`, fractional Gaussian noise).
- No test framework, no formatter/linter config, no CI, no README.
- `basedpyright` is pinned but has no config file; typechecking is a manual command:
  `.venv/bin/basedpyright mfdfa_engine.py pages/ validation/`
- `.gitignore` excludes `__pycache__/`, `.venv/`, `.DS_Store`, `.streamlit/secrets.toml`, and agent configuration (`.opencode/`, `opencode.json`). `AGENTS.md` is no longer gitignored.

## 3. Structure

```text
mfdfa_streamlit_start.py   Entry point: st.navigation over the pages
mfdfa_engine.py            All computation + plotting (coupled to Streamlit)
pages/home.py              Intro page
pages/dfa.py               Monofractal (DFA) analysis page
pages/mf_dfa.py             Multifractal (MF-DFA) analysis page
pages/upload.py            CSV upload, preview, selection
utils/pages_logic.py       Shared UI helpers (sidebar widgets, plot wrappers)
utils/__init__.py          Empty package init
validation/                MF-DFA numerical harness (9 scripts)
  _common.py               Shared bootstrap, standard pipeline, PASS/FAIL collector
  q_grid.py                q-grid alignment and column-count checks
  package_vs_ref.py        Package vs independent reference implementation
  fgn_width_baseline.py    Monofractal spurious-width baseline (fGn)
  cascade_pipeline.py      Binomial cascade vs closed-form theory (two-tier)
  negative_q_damage.py     Zero-run and constant-run hazard detection
  surrogate_test.py        Surrogate (shuffle) test p-value and behaviour
  fou_subtract_one.py      Slope-convention correctness (subtract_one toggle)
  hq_fit_quality.py        R² fit-quality regression test (append-bug trap)
docs/completed-features/   Archived feature specifications
docs/references/           Reference documents (methodology, review guidelines)
docs/reviews/              Review reports (written by @stats-reviewer)
```

## 4. Modules and responsibilities

### mfdfa_engine.py — compute layer

- `generate_fou(t_final, delta_t, theta, sigma, H)` — fractional Ornstein–Uhlenbeck process via Euler integration of `fgn` increments; monofractal test signal.
- `binomial_cascade(n_levels, p, seed)` — 1D random binomial (multiplicative) cascade measure of length `2**n_levels`; multifractal validation signal.
- `cascade_theoretical_width(p)` — asymptotic spectrum width Δα assuming an infinite q-range.
- `cascade_theoretical_spectrum(p, q_list)` — theoretical τ(q), α, f(α) over the finite q-range actually used, via the same Legendre steps as the empirical pipeline.
- `run_mfdfa(y, lag_start, lag_stop, lag_num, q_start, q_stop, q_num, order)` — builds an integer, `np.unique` log-spaced lag list; builds `q_list = np.linspace(q_start, q_stop, q_num)` and drops `|q| <= 0.1` (q≈0 is unstable); calls `MFDFA(y, lag=lag, q=q_list, order=order)`; returns `(lag_mf, dfa_mf, q_list)`.
- `get_dfa(dfa_mf, q_list)` — slices the q≈2 column out of the MF run; the DFA (monofractal) page reuses the MF result instead of a separate computation.
- `fit_dfa_exponent(lag_mf, dfa, fit_start, fit_end, subtract_one)` — log-log linear fit over the selected index band; returns `(slope, intercept, H, R²)` where `H = slope - 1` if `subtract_one` else `slope`.
- `get_q_show()` — default q values highlighted in the fluctuation plot `(-5, -2, -1, 1, 2, 5)`.
- `compute_hq(lag_mf, dfa_mf, q_list, fit_start, fit_end)` — per-q log-log slopes h(q) and R². **Fixed 2026-11-21:** a conditional-expression-as-statement bug (`r2.append(...) if ... else np.nan`) was silently skipping appends when `var(yv)==0` or `yv` contained NaN/inf — the third closing `)` was one character too early, making `r2` shorter than `hq`/`q_list`. Fixed to `r2.append(... if ... else np.nan)` with `np.nanmin` in both consumer sites.
- `spectrum(hq, q_list)` — Legendre transform: `tau = q*h(q) - 1`, `alpha = np.gradient(tau, q)`, `f(alpha) = q*alpha - tau`.
- `spectrum_stats(alpha, f_alpha)` — raw spectrum width Δα, α peak, left/right asymmetry.
- `spectrum_width_robust(alpha, f_alpha, q_list, q_width_max, positive_q_only, f_floor)` — trimmed statistics: drops fragile extreme-q points (`|q| > q_width_max`, optionally q≤0) and `f < f_floor`.
- `shuffled_surrogate_test(signal, n_surrogates, robust_width, mfdfa_parameters, fit_start, fit_end, seed)` — permutation surrogates (distribution preserved, temporal order destroyed); runs the full MF-DFA pipeline per surrogate, skipping invalid ones (up to `5*n` attempts); returns surrogate mean/median/std, 2.5–97.5 percentile interval, and p-value `(1 + #{widths >= observed}) / (n + 1)`. Raises a Hungarian `ValueError` if too few valid surrogates.

### mfdfa_engine.py — presentation layer

All plotting functions call `st.plotly_chart` directly, so the engine module is coupled to a Streamlit runtime:

`plot_signal_raw`, `plot_signal_cum_sum` (mean-centered cumulative sum), `plot_fluctuation` (F(s) log-log with fitted line), `plot_fluctuation_mf` (per-q F(s) curves, fit-line overlays, fit-band highlight, min fit R²), `plot_hq`, `plot_tau`, `plot_spectrum`, `plot_spectrum_stats` (raw vs robust columns, surrogate result table, cascade theoretical-error columns; Hungarian labels).

### pages/

- `home.py` — `set_page_config`, title, one-line intro, and a "Mi is az az MFDFA?" header with no content under it yet.
- `dfa.py` — monofractal page. Sidebar toggle "Generálj jelet": **on** → fOU parameters, `generate_fou`, `run_mfdfa` (default q-range −5..5), `get_dfa`, `fit_dfa_exponent` with default `subtract_one=True` (fOU is level-like; slope ≈ H+1). **off** → uploaded-data branch: session checks, `file_check`, validation (exactly 1 column, numeric, all finite — otherwise `st.error` + `st.stop`), sampling-rate-derived time axis, same pipeline with `subtract_one=False` (uploaded signals are increment-like, e.g. velocity; slope ≈ H).
- `mf_dfa.py` — multifractal page. **Cascade branch**: `binomial_cascade`, full MF-DFA pipeline, empirical raw + robust spectrum stats, and theoretical comparison — both the asymptotic Δα and the finite-q theoretical spectrum — reported as % errors. **Uploaded branch**: same pipeline plus an optional shuffled-surrogate test (sidebar button, parameters `n_surrogates` default 100, seed). Both branches gate the h(q)/τ(q)/spectrum display on `get_valid_fitting_range` (all finite and positive fluctuations in the fit band) and show a warning otherwise. Robustness knobs `q_width_max = 4`, `positive_q_only = False` are hardcoded at the top of `main()`.
- `upload.py` — multi-file CSV uploader stored as DataFrames in `st.session_state.database` keyed by filename; selectbox + "Load file" sets `selected_file`; "Delete files" clears the database and bumps `uploader_key_version` to force a fresh uploader widget; loading a file resets `analysis_started` and `surrogate_test_run`.

### utils/pages_logic.py

Shared UI helpers used by both analysis pages: session-state init (`session_checks`), file access (`file_check`), time-axis construction (`getting_time`), signal length display, fitting-range validity (`get_valid_fitting_range`, `valid_conditional_display`), sidebar widgets (fOU / cascade parameters, DFA / MF-DFA parameters, fitting-range sliders, sampling rate, step, surrogate parameters, analysis/clear buttons), and plot wrappers (`raw_signal_plot`, `integrated_signal_plot`, `fluctuation_function_plot`, `fluctuation_mfdfa_plot`, `gen_hurst_plot`, `mass_exponent_plot`, `singularity_spectrum_plot`, `spectrum_statistics_plot`) that add a Hungarian subheader/caption and delegate to `mfdfa_engine`.

## 5. Relationships and data flow

- `mfdfa_streamlit_start.py` registers the four pages via `st.navigation`; each page's `main()` reads sidebar parameters through `utils.pages_logic`, computes through `mfdfa_engine`, and renders through the engine's plotting functions.
- **Upload flow:** `upload.py` → `st.session_state.database[filename]` → `selected_file` → `dfa.py`/`mf_dfa.py` read the DataFrame via `file_check()` → validation → 1-D float signal → MF-DFA pipeline → plots. `sampling_rate` (default 150 Hz) only builds the time axis (`getting_time`); no coordinate processing happens in the pages.
- **Analysis gating:** `analysis_started` (set by "Analízis megkezdése", cleared by "Analízis törlése" or by loading a new file) controls whether the uploaded-data analysis runs; `surrogate_test_run` (set by "Run surrogate test") triggers exactly one surrogate computation, then resets to `False`.
- **Monofractal pipeline:** `run_mfdfa` (full q grid) → `get_dfa` (q=2 column) → `fit_dfa_exponent` → F(s) plot with fit line, H and R² readout.
- **Multifractal pipeline:** `run_mfdfa` → `compute_hq` → `spectrum` → `spectrum_stats` (raw) + `spectrum_width_robust` (trimmed) → plots. Cascade branch adds `cascade_theoretical_*` comparison; uploaded branch optionally adds `shuffled_surrogate_test`.
- **Slope convention:** `fit_dfa_exponent(subtract_one=...)` — `True` for integrated/level signals (generated fOU; slope ≈ H+1), `False` for increment/noise-like signals (uploaded series; slope ≈ H).

## 6. Entry points and validation

- Application: `mfdfa_streamlit_start.py` — run with `.venv/bin/streamlit run mfdfa_streamlit_start.py`. Running a `pages/*.py` file directly bypasses the navigation sidebar.
- Validation harness: 9 scripts under `validation/` (`_common.py` is the shared bootstrap, not a test) — run individually (`.venv/bin/python validation/<script>.py`) or inspect for per-check thresholds. Each exits 0 on pass, 1 on fail. Import only compute-layer functions; never call plotting functions.
- No CLI, no package build, no test entry points.

## 7. Testing

The `validation/` harness (9 scripts) exercises the app's own compute-layer functions against known ground truths: fGn (monofractal width baseline), binomial cascade (closed-form h(q)/τ(q)), and the installed MFDFA package vs an independent reference implementation. It also covers q-grid alignment, slope conventions, surrogate-test correctness, and zero/constant-run hazard detection. Run as `.venv/bin/python validation/<script>.py`; all scripts exit 0 on pass, 1 on fail.

There is no test framework, no CI, no pre-commit hooks. `basedpyright` is available for manual typechecking: `.venv/bin/basedpyright mfdfa_engine.py pages/ validation/`.

### Findings from the 2026-11-21 engine review (docs/reviews/2026-11-21-engine-review.md)

- **Constant-value runs (F2, upstream):** no `s_min` guard exists in the engine or the package. The page-level fit-band gate (`utils/pages_logic.get_valid_fitting_range`) blocks exact-zero runs deterministically, but constant-value runs (from linear interpolation upstream) pass it unguarded and silently inflate h(−4) (measured 0.643 → 0.948 in `validation/negative_q_damage.py`). Resolution (owner decision): handled upstream in the gaze processor (cap interpolated gaps below the smallest fitted scale); the app itself has no defense.
- **NaN observed width (F3, fixed 2026-11-21):** `shuffled_surrogate_test` now raises a Hungarian `ValueError` before any surrogate is generated if the observed robust width is non-finite (`mfdfa_engine.py:198-203`). The page catches it and shows `st.warning` (`pages/mf_dfa.py:118-124`); the same handler catches the pre-existing insufficient-surrogates error. Regression test: `validation/surrogate_test.py` (NaN → raises, healthy path byte-identical).
- **Fit-end exclusivity (F1, fixed 2026-11-21):** the fit slice `[fit_start:fit_end]` remains exclusive (unchanged numerically), but the sidebar captions (`utils/pages_logic.py:205`, `:324`) and the gray band's right edge (`mfdfa_engine.py:311`) now report `lag_mf[fit_end - 1]` — the last point actually fitted. Old caption overstated by one index at every slider position.
- **Usage conditions:** fit band from s ≥ 10; report the robust width (raw is set by the one-sided gradient edge estimates at q = ±5) and the q-grid with it; keep the fOU DFA fit band below 1/(theta × delta_t) samples; check the asymmetry sign convention against the cited paper. Stated in `README.md`.
- **Surrogate null:** shuffle-only; cannot separate linear correlation from nonlinear structure. IAAFT test planned (see `plan.md`).

## 8. Conventions

- UI text Hungarian; identifiers and most comments English (some Hungarian comments in the engine).
- Engine functions return plain tuples; pages unpack them positionally.
- `fit_start`/`fit_end` are integer slider indices into `lag_mf`, passed directly into all fitting functions; the resulting scale window is shown via a sidebar caption.
- q≈0 is excluded by construction (`run_mfdfa` drops `|q| <= 0.1`; the q-range widgets cannot produce 0 either).
- Dependencies are fully pinned; environment rebuilt via `uv pip sync requirements.txt`.

## Uncertainties

- The purpose of the `t_final ** H` amplitude scaling inside `generate_fou` is not documented in the code; it is reproduced as-is above without interpreting it.
- The default 150 Hz sampling rate is only a display assumption for uploaded series; the code does not verify it against the actual data.
