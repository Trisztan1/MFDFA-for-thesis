# Engine review — MF-DFA compute pipeline (2026-11-21)

Model: Claude Sonnet 5.5 (openrouter/anthropic/claude-sonnet-5.5). Read-only review; this is the only file written.
Environment printed by the harness: python 3.12.13 | numpy 2.4.6 | MFDFA 0.4.3 | streamlit 1.58.0.

Files examined: `mfdfa_engine.py` (all), `pages/dfa.py`, `pages/mf_dfa.py`, `utils/pages_logic.py`, installed `.venv/lib/python3.12/site-packages/MFDFA/{MFDFA.py,fgn.py}`, `validation/*.py` (sources of `_common`, `negative_q_damage`, `surrogate_test`, `hq_fit_quality`; the other scripts only by output). `singspect.py` was **not** read (the engine does not import it). Only the headings of `docs/references/mfdfa_app_review_reference.md` were looked at; no section body from it or from `docs/reviews/2026-11-20-*` was used.
Scripts run: all 8 listed validation scripts, `basedpyright`, 5 read-only `python -c` probes (reproduced below). Note: the task text says "9 scripts"; `validation/` contains 8 runnable scripts plus `_common.py` (a helper, not a test).

## 1. Verdict (5 lines)

1. For noise-like input, a fit band that starts at about s ≥ 10, and a signal with no constant-value runs, the engine is numerically sound: package ≡ independent reference to 3.135e-16, q/lag/column alignment holds for every q_num tried, R² list is complete, tau/alpha/f formulas are right, p-value expression is right.
2. Two real defects: **F2** (the fit-band gate `pages_logic.py:92-96` passes constant-value runs; h(−4) moved 0.643 → 0.948 in the harness) and **F3** (a NaN real width gives the smallest possible p-value, 1/101).
3. The raw width is set by the one-sided gradient estimates at q = ±5 (min/max alpha sit at the two edge q), so only the robust width (|q| ≤ 4) should be reported as the thesis number; robust width itself still depends mildly on q_num (cascade 1.4093 / 1.4323 / 1.4462 for 21 / 51 / 101).
4. App defaults (`fit_start = 0`, s = 3) are not the harness settings: on the generated cascade (p = 0.25, 14 levels, seed 0) the default fit is blocked by the gate (h(−4) = NaN); with fit start at s ≥ 10 it is not.
5. Width error against theory is estimator bias at finite N (class c) and must not be read as an implementation error; numbers below.

## 2. Verdict table

| # | Item | Verdict | Evidence | Severity |
|---|------|---------|----------|----------|
| 1 | float64 1-D, finite, profile once, `modified=False` | OK | `.to_numpy().astype(float).ravel()` + `isfinite` (dfa.py:62-65, mf_dfa.py:88-91); package builds Y once (MFDFA.py:159), `modified=False` (MFDFA.py:22); time axis used only in plots (engine:243-254). Probe: `F.dtype float64, lag.dtype int64` | – |
| 2 | subtract-one only on fOU; `compute_hq` never on fOU | OK; latent hazard (F7) | `compute_hq` callers: mf_dfa.py:41 (cascade), :110 (upload), engine:215 (surrogate); dfa.py never calls it. Upload `subtract_one=False` (dfa.py:85); fOU uses default `True` (dfa.py:27, engine:102). fou_subtract_one.py PASS | cosmetic |
| 3 | lag used = lag returned | OK | engine:88 takes `lag_mf` from MFDFA; package returns filtered lag (MFDFA.py:126-127, 272) | – |
| 4 | lag int/unique/≥order+2/≤N/4; effective scale count | DEVIATION-DEFENSIBLE | int+unique engine:77; package `lag > order+1` MFDFA.py:126. N/4 only a UI warning (pages_logic.py:181, 279). Probe: requested 100 → 85 unique lags (fGn N=4096, lag 0.5–3), 90 (cascade, lag 0.5–3.6, last lag 3981 < N/4 = 4096). `lag_stop = log10(2N)` → NaN F, no exception (probe) | can change a number |
| 5 | `s_min` guard | **VIOLATION (a)** for constant runs; exact-zero runs OK | No guard in engine:74-90 or package MFDFA.py:126. Exact zero: gate BLOCK, h(−4)=nan (negative_q_damage). Constant runs: gate ALLOW, h(−4) 0.643→0.948. See F2 | changes a number the thesis reports (if such runs exist) |
| 6 | surrogates reuse real lag | OK (equivalent) | lag recomputed (engine:204) but is a pure function of the parameters; same index slice (engine:210, 215) | – |
| 7 | q used = q kept | OK | engine:85 and MFDFA.py:150 use the same predicate. Probe, kept counts: q_num 21→20, 51→50, 101→99, 100→98 (even). q_grid.py: `dfa_mf (85, 99) vs q_list 99`; even q_num=100 keeps 98, columns aligned | – |
| 8 | q=2 column | OK (latent hazard) | `argmin(abs(q-2))` (engine:96); q_grid.py "q used: 2.000000, max \|diff\| 0.00e+00". No tolerance check if 2 is outside the grid; DFA page always passes defaults | cosmetic |
| 9 | non-finite F detected | DEVIATION-DEFENSIBLE | Engine has no guard; `compute_hq` runs before `valid` is read (mf_dfa.py:41, 110) but does not raise: NaN/−inf columns → hq NaN (hq_fit_quality.py PASS; zero-run h(−4)=nan). Only the page gate (pages_logic.py:92-96) stops display. Misses near-zero F (F2) | can change a number |
| 10 | slice-then-log, same range | OK with one note | `compute_hq`: `np.log(dfa_mf[slice,i])` (engine:124), lag log then slice (engine:123); `fit_dfa_exponent` logs whole arrays then slices (engine:103-104) — same values, only extra log warnings. Same slice for all q and gate. Probe: independent slice-then-log polyfit vs `compute_hq`: max diff 0.0. **End index is exclusive: F1** | cosmetic / can change a number |
| 11 | R² | OK | `r2.append(1 - var(resid)/var(yv) if var(yv) > 0 else nan)` (engine:129) parses as `append((…) if … else nan)`, always appends. hq_fit_quality.py: len(hq)=len(r2)=len(q)=99 incl. constant/NaN/zero columns (R² NaN). Consumers use `np.isnan`/`np.nanmin` (engine:305-307, 360-362) | – |
| 12 | min R² over all kept q | OK | `r2` computed for every q (engine:121-131), passed whole (mf_dfa.py:53, 128) | – |
| 13 | tau/alpha/f | OK | engine:138-142; kept q, ascending. Probe: recompute with `np.gradient(q*h-1, q)` → max diff 0.0 for tau, alpha, f (note: same formula, so only guards against wrong-argument bugs). Cascade h(q)/tau(q) vs theory: see §5 | – |
| 14 | width/peak/asymmetry definitions | OK as coded; sign/normalisation [OPEN] | raw = max−min of all alpha (engine:177-179). Robust: \|q\| ≤ `q_width_max`, optional q>0, f ≥ `f_floor` (engine:150-154); call sites use 4 / False / 0.0 (mf_dfa.py:10-11, 44, 112; surrogate engine:191-192, f_floor default 0.0). Peak = alpha at argmax f (engine:166, 182); asymmetry = right − left, unnormalised (engine:169, 185). Probe fGn: max f = 0.99993 (≈1, so peak lands near q≈0). Sign/normalisation vs the cited literature not checked | – |
| 15 | gradient edges / q-count sensitivity | DEVIATION-DEFENSIBLE | `np.gradient` default edge_order=1 (engine:141, 69). Probe: alpha min at index 98 (q=+5), max at index 0 (q=−5); alpha[0]=0.7627, alpha[1]=0.7622. Table in §5 | can change a number (raw width) |
| 16 | surrogate same q/order/fit/width | OK (fragile) | same functions (engine:204-219); constants duplicated engine:191-192 vs mf_dfa.py:10-11 | cosmetic |
| 17 | p-value | OK expression; **NaN input: F3** | engine:235 parenthesised correctly; percentile `[2.5, 97.5]` (engine:234). Probe, n=100: real width 0.0 → p=1.0; 9.0 → p=0.009900990099009901 (=1/101); NaN → p=0.009900990099009901 | changes a number (F3) |
| 18 | seed / non-finite surrogates | OK with caveats | `default_rng(seed)` engine:194; probe: identical surrogate mean on repeat with same seed. Bad surrogates dropped, ≤5n attempts, then `ValueError` (engine:197-228), uncaught at mf_dfa.py:118 | cosmetic |
| 19 | cascade generator | DEVIATION-DEFENSIBLE | engine:47-51 picks the larger half at random per node. Probe (n=10, p=0.3, seed 0): leaf-value counts by number of p-factors = [1,10,45,120,210,252,210,120,45,10,1], identical to the deterministic Kantelhardt multiset C(10,k); sum 0.9999999999999997. Only the temporal order differs | cosmetic |
| 20 | finite-q theory | OK | same `q_list` and `np.gradient` (engine:67-71; mf_dfa.py:43-47); denominators are the theoretical value (engine:400-410). cascade_pipeline.py: max\|dh\| 0.038 (deterministic) | – |
| H | general hazards | see F1–F9 | no mutable defaults; no `st.*` in compute functions (engine:16-237); implicit-Optional annotations flagged by typecheck (engine:102, 120, 256, 271) | cosmetic |

## 3. Findings (most severe first)

**F2. Constant-value runs pass the fit-band gate; no `s_min` guard anywhere. VIOLATION (a). Changes a number the thesis reports if the data contain such runs. Confidence: high (reproduced by the harness).**
Mechanism: inside a constant run the profile is linear, so order-1 detrending leaves ~0 residual (MFDFA.py:214). For q<0, `float_power(F, q/2)` (MFDFA.py:247-253) makes that window dominate the mean. If F² is exactly 0, the window gives `inf`, so `F_q = 0` and the gate (`finite and > 0`, pages_logic.py:94) blocks it. If F² is tiny but non-zero, F stays finite and positive, the gate passes, and h(q<0) is silently inflated.
Reproduction: `.venv/bin/python validation/negative_q_damage.py` prints
`zero-run (500 samples): ... h(-4)=nan | h(-2)=nan` → `gate=BLOCK`;
`constant-runs (20 x 15 samples): F finite=True, F>0=True | h(-4)=0.948 | h(-2)=0.724 | h(2)=0.571 | h(4)=0.541` → "app fit-band gate would ALLOW this signal (… measured here: 0.643 -> 0.948)". The clean baseline is h(−4)=0.643, h(−2)=0.594, h(2)=0.527, h(4)=0.508. Positive-q values moved little (0.527 → 0.571 at q=2), so the damage is concentrated in negative q, which widens the spectrum. Not defensible for interpolated/held-sample data unless the thesis reports it.

**F3. NaN real width yields the minimum p-value. VIOLATION (a). Can change a number in some settings. Confidence: high (reproduced).**
`spectrum_width_robust` returns NaN when no q survives the |q| ≤ 4 and f ≥ 0 filter (engine:158-159); mf_dfa.py:118-120 passes it to `shuffled_surrogate_test` without an `isfinite` check; `surrogate_widths >= nan` is all False, so k = 0 (engine:235). Reproduction (fGn H=0.7, N=4096, np.random.seed(3), n=100, seed 1):
`shuffled_surrogate_test(y,100,0.0,...)` → p = 1.0; `(…,9.0,…)` → p = 0.009900990099009901; `(…,np.nan,…)` → p = 0.009900990099009901. A NaN observed width prints as "significant at the maximum level".

**F1. Fit band excludes `fit_end`, but the UI treats it as included. VIOLATION (a). Cosmetic (numerically small). Confidence: high.**
Slices are `[fit_start:fit_end]` (engine:103-104, 123-124, gate pages_logic.py:93); the sliders allow `fit_end` at most `len(lag_mf)-1` (pages_logic.py:201, 320), so the largest scale is never fitted and the caption (pages_logic.py:205, 324) and gray band (engine:299) report `lag_mf[fit_end]` as inside the fit. Probe (harness band 5:26): last scale used lag[25] = 194, n points = 21. Effect on the H estimate, 8 fGn seeds, default DFA params, fit_start at s ≥ 10: end exclusive mean 0.704, end inclusive mean 0.704 (no visible change).

**F4. App defaults differ from validated settings (s = 3, `fit_start = 0`). Class (b). Can change a number. Confidence: high for the observations, medium for the cause.**
Probe, generated cascade p = 0.25, 14 levels, seed 0, MF-DFA page defaults (lag 0.5–3.6, q ±5, 101, order 1): bad F only at s = 3 (49 q values from −5 to −0.2 are 0 or non-finite); gate result: default fit_start=0 → blocked (False); fit start at s ≥ 10 → allowed (True). Values: default h(−4)=nan, h(2)=0.833, h(4)=0.642, robust width 0.724 (computed from a NaN-contaminated h), raw nan, min R² nan; s ≥ 10: h(−4)=1.781, h(2)=0.830, h(4)=0.636, robust 1.623, theory (same q) 1.546, raw 1.640, min R² 0.9792. A likely cause (hypothesis, not tested separately): the cascade takes a few discrete values, so 3 consecutive points can be collinear in the profile and give F² = 0. On fGn (DFA page, 8 seeds, defaults) the H bias is small: mean 0.713 (fit_start=0) vs 0.704 (s ≥ 10). Note the unweighted OLS also weights large scales more because `unique(astype(int))` thins small scales (engine:77).

**F5. Surrogate test is a shuffle null only. [OPEN] / class (b). Confidence: medium.**
Shuffling destroys linear correlation as well as nonlinear structure. Harness: fGn H=0.7, N=4096, n=30, seed 5: observed robust Δα 0.0276, surrogate mean 0.0748, interval [0.0193, 0.1484], p = 0.9032 (k=27); cascade p=0.3: observed 1.4462, surrogate mean 0.9130, interval [0.7960, 1.0413], p = 0.0323 (k=0, the minimum for n=30). The null width changes with the signal's correlation, so "significant" cannot be read as "multifractal due to nonlinear cascade" without a phase-randomised surrogate (not implemented). The in-app text claims this (engine:369-373). Also, rejected surrogates (engine:212-213) condition the null; the rejection count is not reported (cosmetic).

**F6. Raw width is determined by the first-order edge estimates. Class (b). Can change a number. Confidence: high (probe).** alpha(q) is monotone here, so raw min/max sit at q = ±5 (indices 98 and 0) where `np.gradient` uses one-sided first-order differences. Raw vs robust (seeded, §5): robust is not affected by this, because the edge q are removed after the gradient is computed.

**F7. Latent hazards. Class (a), cosmetic. Confidence: high.** `fit_dfa_exponent(subtract_one=True)` is the default (engine:102) and the fOU call relies on it (dfa.py:27); a new caller on uploads would silently report H−1. If h(q) were ever computed on fOU, the subtraction would also have to be applied to the whole vector before `tau = q*h - 1` (engine:138); no such path exists today. `get_dfa` returns the nearest q to 2 without a tolerance check (engine:96). The `generate_fou` has no seed argument: `fgn` uses the global `np.random.normal` (fgn.py:60-61).

**F8. fOU H = slope − 1 is validated only on the harness fit band. [OPEN]. Confidence: low.** fou_subtract_one.py: N=20000, seeds 0/1/2: slope 1.678/1.705/1.677, H 0.678/0.705/0.677, R² 0.9998. The app's default fit band (full range, lag 0.5–3) was not run.

**F9. Minor.** The package docstring says only q = 0 is removed (MFDFA.py:76-78) while the code removes |q| ≤ 0.1 (MFDFA.py:150). `plot_hq` fixes the y-axis to [0, 2] (engine:313), hiding values outside. `fit_end ≥ fit_start + 3` allows a 3-point fit (pages_logic.py:201, 320). Typecheck: engine has 8 implicit-Optional errors (engine:102, 120, 256, 271; lines 102/120/256/271 each twice); the full run reports 19 errors, 1062 warnings; I only inspected the engine's errors.

## 4. Package claims verified against the installed source

All verified by reading `MFDFA/MFDFA.py` (not run unless stated):
- Profile `cumsum(x − mean)` built once (159); `modified` default False (22).
- Segmentation from both ends: `Y_ = Y[:N − N%i]`, `Y_r = Y[N%i:]` → 2·floor(N/s) windows (198-199).
- Order-m polynomial fit per window; F² = `np.var` of residuals (ddof 0) (210-215); `F_q = float_power(mean(float_power(F, q/2)), 1/q)` (247-253). Reproduced numerically: package vs independent reference, max relative error 3.135e-16.
- No q = 0 branch (line 315 TODO). The q-filter removes |q| ≤ 0.1 (150). Returned: `lag, f` only, not q (272). Probe: linspace(−5, 5, 101) keeps 99 (q_grid.py), nearest kept −0.2 / +0.1 (asymmetric, as stated in the task).
- Lags: `lag > order + 1`, then rounded to int (126-127); returned lag can be shorter than requested. F = 0 with q<0 gives `inf` in the mean and 0 in F_q (gate sees 0).
- False/not confirmed: nothing found false. The docstring is inconsistent with the code (F9). `singspect.py` not read.

## 5. Harness results

Exit codes: the scripts end through `Check.finish()` (`sys.exit(0)` on pass). Each printed `PASS` as its final line, so exit 0 is inferred from that; I did not capture `$?` separately because the shell here rejected compound commands. `basedpyright` exited 1.

| Script | Result | Key numbers |
|---|---|---|
| q_grid.py | PASS | 99 kept; nearest −0.2/+0.1; `dfa_mf (85, 99)`; q=2 diff 0.00e+00; q_num=100 keeps 98 |
| package_vs_ref.py | PASS | max rel err 3.135e-16 (N=4000, default_rng(3), 15 lags, q=−4,−2,2,4) |
| fgn_width_baseline.py | PASS | fGn H=0.7, N=4096, seeds 0..11: h(2) 0.703 ± 0.023 (0.672..0.745); raw width 0.070 ± 0.031 (max 0.124); robust 0.056 ± 0.024 (max 0.101) |
| cascade_pipeline.py | PASS | deterministic p=0.3 14 levels: max\|dh\| 0.038, max\|dtau\| 0.180, robust width 1.102 vs theory 1.143 (ratio 0.965); engine cascade seeds 0–5: max\|dh\| mean 0.108 ± 0.049 (max 0.184), ratio 0.648..1.225 (mean 1.030); p=0.55 deterministic: ratio 2.74 @14 levels, 1.59 @16 (informational) |
| negative_q_damage.py | PASS (prints ALLOW for constant runs) | see F2 |
| surrogate_test.py | PASS | see F5 |
| fou_subtract_one.py | PASS | see F8; upload fGn slope 0.698/0.687/0.745 with `subtract_one=False`; wrongly corrected −0.302/−0.313/−0.255 |
| hq_fit_quality.py | PASS | len(hq)=len(r2)=len(q)=99; fGn R² 0.9940..0.9982; cascade R² 0.9553..0.9995; degenerate columns → NaN |
| basedpyright (engine, pages, validation) | exit 1 | 19 errors, 1062 warnings; engine errors are implicit-Optional defaults only |

My probes:
- Width vs q count (standard harness params: lags 10..N/4, 40 lags, fit band `[size//8 : int(size/1.5)]`):

| signal | q_num → kept | raw | robust | theory raw / robust (same q) |
|---|---|---|---|---|
| fGn H=0.7 N=4096, seed 3 | 21→20 | 0.1167 | 0.1007 | – |
| | 51→50 | 0.1198 | 0.1008 | – |
| | 101→99 | 0.1209 | 0.1008 | – |
| | 100→98 | 0.1208 | 0.1006 | – |
| cascade p=0.3, 14 levels, seed 7 | 21→20 | 1.5230 | 1.4093 | 1.1792 / 1.1404 |
| | 51→50 | 1.5272 | 1.4323 | 1.1845 / 1.1423 |
| | 101→99 | 1.5283 | 1.4462 | 1.1861 / 1.1425 |
| | 100→98 | 1.5283 | 1.4430 | 1.1860 / 1.1419 |

The cascade empirical/theory robust ratio at 101 is 1.266 (seed 7); the harness ratios across seeds 0–5 vary 0.648..1.225 and p=0.55 at 14 levels gives 2.74, i.e. width error is estimator bias at finite N (class c), not an implementation error. The h(q) agreement (max|dh| 0.038 deterministic) is the better correctness evidence.
- Checks the harness does **not** cover: app-default fit (`fit_start=0`, s=3) on the generated cascade (F4); NaN `robust_width` into the surrogate test (F3); fit-end exclusivity (F1); q-grid dependence of the robust width; `lag_stop > N/4`; behaviour of the page on the F2 constant-run case end to end; `generate_fou` reproducibility.

## 6. Could not verify

- Item 14: the asymmetry sign convention and normalisation against the literature the thesis cites (no source in scope); `singspect.py` conventions.
- Item 15: whether the one-sided edge estimate is biased in magnitude — I only showed that raw min/max sit at the edge q, not the size of the bias versus a higher-order edge scheme.
- Item 13: the "independent computation" re-uses the same formulas (gradient of q·h−1); it guards argument order and indexing, not the definition itself. The definitions agree with the task's reference facts.
- F4 cause (discrete cascade values giving F² = 0 at s = 3) is a hypothesis; I measured only which lags/q are bad, not the window contents.
- F8: the fOU slope on the app's default fit band; and whether the fOU H bias grows past the mean-reversion crossover.
- 11 of the 19 `basedpyright` errors are in `pages/` or `validation/` and were not examined.
- Exit codes for the harness scripts were inferred from the `PASS` lines, not captured.

## 7. Next tests I would add (max 5)

1. `negative_q_damage`: add an assertion (currently print-only) that a signal with 20×15-sample constant runs is flagged by the app, e.g. min F² over windows < ε·median F², or a run-length check; expected: it fails today (gate ALLOW, h(−4) 0.643 → 0.948).
2. `shuffled_surrogate_test(y, 30, np.nan, …)` must raise or return NaN, not p = 1/31 (today 1/(n+1)); fGn H=0.7, N=4096, np.random.seed(3), seed 1.
3. Default-settings test: generated cascade p=0.25, 14 levels, seed 0, MF-DFA page defaults, `fit_start=0`: assert `get_valid_fitting_range` is True or that the page picks a start ≥ s_min; today it is False (s=3).
4. Fit-end test: `len(lag_mf[fit_start:fit_end])` equals the number of points the caption claims; or assert the largest slider setting includes `lag_mf[-1]`.
5. q-grid sweep on the cascade p = 0.3, seeds 0–5, q_num ∈ {21, 51, 101}: assert robust width varies by less than a stated tolerance (seed 7 today: 1.4093 / 1.4323 / 1.4462) and that raw width is not used as the headline number.
