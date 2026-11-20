# Inspection

Analytical snapshot of the repository as found on 2026-11-19, from a read-only inspection. This is not a roadmap: it records what exists, how it behaves, and what is unclear. No source code was modified.

## 1. Intended purpose

A thesis demo app for MF-DFA analysis of time series. The pipeline is validated on synthetic signals with known scaling (fractional Ornstein–Uhlenbeck for the monofractal case, a random binomial cascade for the multifractal case, both with theoretical references), then applied to real preprocessed data: single-column CSV series uploaded by the user (per `docs/references/`, gaze-displacement series produced by the separate `gaze_processor` project).

## 2. Current behavior

- **Home** — title, greeting, a "Mi is az az MFDFA?" header; no further content.
- **DFA page** — toggle "Generálj jelet". Generated branch: fOU signal from sidebar parameters (H, theta, sigma, t_final, delta_t, step), raw + integrated plots, F(s) log-log plot with fitted line, H and R² readout (slope convention: `subtract_one=True`). Uploaded branch: requires a loaded file and "Analízis megkezdése"; validates one-column, finite, numeric data; builds a time axis from the sampling rate; same analysis with `subtract_one=False`.
- **MF-DFA page** — generated branch: binomial cascade (levels, p, seed; p=0.5 rejected), full MF-DFA pipeline (lag/q/order parameters, fit-range sliders), per-q fluctuation curves with fit band, h(q), τ(q), f(α) plots, and spectrum statistics reported both raw and robust, compared against the cascade's asymptotic and finite-q theoretical values as % errors. Uploaded branch: same analysis plus an optional shuffled-surrogate test (default 100 surrogates, seedable) reporting mean/median/std, 95% interval, and p-value.
- **Upload page** — multi-CSV upload with in-app preview, file selection, "Load file", and "Delete files"; loading a file resets analysis and surrogate state.

## 3. Existing functionality and development state

- The core MF-DFA pipeline is complete and works end-to-end on both branches (generated and uploaded).
- Git history (9 commits) shows iterative development: upload UI → uploaded-data DFA → helper refactor with a `utils` package → validation and surrogate features → analysis guides.
- Working tree at inspection time: a whitespace-only reindent in `pages/home.py` (uncommitted) and untracked `docs/references/` containing two reference documents (a methodology/implementation review reference for the MF-DFA app, and a summary of the gaze-processor data that feeds this project).
- No tests, no README, no CI. `basedpyright` is pinned in `requirements.txt` but has no config file.

## 4. Notable observations and limitations

1. **AGENTS.md "Gotchas" are stale relative to the current code.** Two of the three listed gotchas no longer apply:
   - The claimed swapped-argument call `plot_signal_cum_sum(measure, time)` in `mf_dfa.py` does not exist; both pages route through `utils.pages_logic.integrated_signal_plot`, which passes `(time, signal)` in the correct order.
   - The claimed unused re-imports of `MFDFA`/`fgn`/`pandas`/`plotly` in `dfa.py`/`mf_dfa.py` do not exist; both pages import only `numpy`, `streamlit`, `mfdfa_engine`, and `pages_logic` (numpy is genuinely used in `dfa.py`; it is unused in `mf_dfa.py`).
   - The third gotcha (fit indices passed straight into fitting functions) is still accurate.
2. **Computation is coupled to Streamlit.** All plotting lives in `mfdfa_engine.py` and calls `st.plotly_chart` directly, so the numerical pipeline cannot be exercised without a Streamlit runtime — a structural obstacle to automated testing.
3. **No automated verification.** Correctness currently rests on in-app validation (cascade recovery error, surrogate test) and manual inspection; regressions in the engine would not be caught automatically.
4. **Fit-range indices.** `fit_start`/`fit_end` are slider indices into `lag_mf`; the actual scale window is only surfaced via a caption, so an off-by-a-few slip is easy to miss. `compute_hq` fits all q at the same index band; `get_valid_fitting_range` warns when any q has non-finite or non-positive fluctuations there.
5. **Duplicated/odd UI logic (harmless but noteworthy):** `sidebar_fitting_rane_mf` is a near-copy of `sidebar_fitting_range` (name typo "rane"); `dfa.py` assigns `start_analysis` from the button return and then immediately reassigns it from session state; `utils/pages_logic.py` contains a placeholder `main()` and a `__main__` guard; `sg_length_of_the_signal` returns a 0-d numpy array rather than a plain int.
6. **Hardcoded robustness knobs.** `q_width_max = 4` and `positive_q_only = False` are fixed at the top of `mf_dfa.py:main()`; the surrogate test also hardcodes them. They are not user-configurable.
7. **Surrogate test placement.** It is only offered in the uploaded-data branch of `mf_dfa.py`, not for the generated cascade branch (which instead validates against theory).
8. **Redundant computation.** `plot_fluctuation_mf` re-fits per-q intercepts that `compute_hq` already computed; minor, but it means the plotted fit lines and the reported h(q) come from two separate fits.
9. **Minor UI typos:** "It tudod megnézni…" (missing "t") on both analysis-page titles; "fügvény" for "függvény" in a subheader; a stray "ez elemezni" in the upload selectbox label.
10. **`home.py` is a stub** — the "Mi is az az MFDFA?" section has no content.
11. **Environment note.** `.venv` is untracked and currently broken (created before the project moved to `.../thesis_projects/`, so `activate` and all console-script shebangs point to the old absolute path). Rebuild with `rm -rf .venv && uv venv .venv && uv pip sync requirements.txt`.

## 5. Questions and uncertainties (for discussion, not decisions)

- Should the stale AGENTS.md gotchas be corrected (documentation-only change)?
- Should the robustness knobs (`q_width_max`, `positive_q_only`, `f_floor`) be exposed in the UI or stay fixed methodological choices?
- Is the current fit-band gating (hide spectrum plots when any q is invalid in the band) the desired UX, or should only the affected q be excluded?
- Will the `home.py` intro section be filled in, and is a README wanted for the repository itself?
- Nothing in the repo records the intended final analysis parameters (q-range defaults, lag band) for the thesis; if these are standardized somewhere external, they are not reflected here.
