# IAAFT surrogate review (2026-11-21)

Model: Claude Sonnet 5.5 (openrouter/anthropic/claude-sonnet-5.5). Environment: python 3.12.13, numpy 2.4.6, MFDFA 0.4.3, streamlit 1.58.0.
Scope: `git diff` of `mfdfa_engine.py` (`_surrogate_widths`, `_iaaft_generate`, `iaaft_surrogate`, `iaaft_surrogate_test`, `shuffled_surrogate_test`), `validation/iaaft_test.py`, `validation/surrogate_test.py`, `feature.md` as the spec. I read no skill files and no other .md files, and did not open the Schreiber–Schmitz PDF or the findings doc.
Run: `iaaft_test.py`, `surrogate_test.py`, `q_grid.py`, `cascade_pipeline.py` (all PASS), `basedpyright --level error` (19 errors = baseline; 8 in the engine, all implicit-Optional defaults, now at engine:102, 120, 387, 402), plus 4 read-only probes (below). The other harness scripts were not re-run; they don't touch changed code.

## 1. Verdict

1. The IAAFT **algorithm is implemented correctly** (spectrum step, rank step, ties, DC bin, seeding, exact value multiset, refactor inert).
2. The **statistical test is not calibrated** for heavy-tailed, correlated data: on a process for which the IAAFT null is exactly true (lognormal of fGn), it rejects at 82.5 % (nominal 5 %). The surrogates' width is 0.95–0.97 against a true null mean of 1.289.
3. The harness cannot see this: it checks one fGn and one cascade at n = 30, and the diagnostics report absolute spectral error and a cap count, neither of which flags the problem.
4. So the math is not yet "bullet proof" for the thesis. A significant IAAFT p-value must not be read as "nonlinear cascade structure" until a size (type-I error) study is run and, for heavy-tailed data, the null is shown to be calibrated.
5. The rest of the engine is unchanged from my earlier review (F3 is now fixed; F1, F2, F4 remain).

## 2. Verdict table

| Item | Verdict | Evidence |
|---|---|---|
| Spectrum step (`target_amp * fft/|fft|`, `irfft(n=n)`) | OK | engine `_iaaft_generate` (diff lines ~+297-304); DC bin: `rfft[0]` of any permutation equals the sum, sign kept, so it is exact; zero-magnitude bins handled without division. Even-N Nyquist bin loses its imaginary part in `irfft` — standard, negligible (fGn rel. spectral error 7.4e-07) |
| Rank/distribution step | OK | `argsort(argsort(z, stable), stable)` = ranks; `sorted_values[rank]` → exact multiset (probe + test: max\|diff\| 0.0) |
| Stopping rules | DEVIATION-DEFENSIBLE | (a) identical rank order, (b) relative change of error ≤ tol, (c) max_iter. (a) is the true fixed point; (b) can stop on a plateau that is not a good fit (see F1) |
| Determinism / RNG | OK | one `default_rng(seed)`, one permutation per attempt; same seed → identical surrogate and iteration count (iaaft_test PASS) |
| Input guard | OK | non-finite and non-1-D raise Hungarian `ValueError` (iaaft_test PASS) |
| `_surrogate_widths` refactor | OK | shuffle outputs byte-identical: fGn p=0.9032 (k=27, mean 0.0748), cascade p=0.0323 (k=0, mean 0.9130); `rng.permutation` call order unchanged |
| F3 (NaN observed width → p=1/(n+1)) | OK (fixed) | guard at engine:206-211; surrogate_test now asserts `ValueError` |
| p-value / percentile | OK | engine:255-256 unchanged; p form (1+k)/(n+1) verified by both harness scripts |
| `iaaft_surrogate_test` diagnostics | DEVIATION-DEFENSIBLE | return tuple as spec'd; but absolute error and cap count do not expose F1/F2 |
| Typecheck | OK | 19 errors, same as baseline |
| Calibration of the test | **VIOLATION (a/c, see F2)** | probes below |

## 3. Findings (most severe first)

**F2. The IAAFT test is anti-conservative on heavy-tailed correlated data. Changes a number the thesis reports (the p-value / verdict). Confidence: high on the observation (direct comparison with fresh realizations); medium on the cause.**
The IAAFT null is "linear Gaussian process, possibly rescaled by a static nonlinearity". `exp(1.5·g)` with `g` = standardized fGn H=0.8 is exactly such a process, so a correct test should reject ≈ 5 %.
Probe 3 (N=4096, `np.random.seed(1000+i)`, 40 realizations, n=19 surrogates, p≤0.05 means k=0):
`fGn H=0.7: reject rate shuffle 0.175, iaaft 0.125`; `lognormal(1.5) of fGn H=0.8: shuffle 0.775, iaaft 0.825` (mean p 0.106 / 0.094).
Probe 4 compares against the true null (60 fresh realizations of that process): mean width 1.289, sd 0.181, 5–95 % [0.958, 1.555]. IAAFT surrogates of three realizations (n=40, seed 5):

| realization | observed | IAAFT mean (sd) | IAAFT p | diagnostics (mean iter, max iter, mean abs err, capped) | shuffle mean / p | rel. spectral err |
|---|---|---|---|---|---|---|
| 0 | 1.267 | 0.973 (0.160) | 0.049 | 456.3, 500, 4345.27, 24/40 | 1.099 / 0.049 | 0.024 |
| 1 | 1.442 | 0.952 (0.168) | 0.024 | 396.0, 500, 7974.19, 10/40 | 0.971 / 0.024 | 0.030 |
| 2 | 1.399 | 0.963 (0.135) | 0.024 | 447.8, 500, 9605.64, 23/40 | 1.020 / 0.024 | 0.023 |

The observed widths are typical draws of the null (1.27, 1.44, 1.40 vs 1.289 ± 0.181), yet the IAAFT null sits about 1.8 sd too low and is nearly as low as the shuffle null. Mechanism (hypothesis): the width of a heavy-tailed process depends on how its few extreme values cluster in time; IAAFT's last step is the rank mapping, which leaves the spectrum approximately but not exactly right (2–3 % of the power, and it is the low-frequency/phase structure that the DFA large scales see), and the surrogate loses clustering. The fGn rejection rate of 5/40 is borderline (P(≥5 | Binomial(40, 0.05)) ≈ 0.048) and 40 realizations is too few to settle mild bias; the lognormal result is not borderline. Any p-value near 0.02–0.05 on heavy-tailed data (gaze speed/velocity, cascades) is therefore unreliable.

**F1. For non-Gaussian marginals the iteration converges to a fixed point that does NOT match the spectrum, and the diagnostics say "converged".** Class (c) for the algorithm, (a) for the reporting. Changes a number the thesis reports (what the null means). Confidence: high.
Binomial cascade p=0.3, 14 levels, seed 7 (N=16384): `iaaft_surrogate(m, seed=1, max_iter=500, tol=0)` stops at iteration 32 because the rank order repeats (max_iter 100/500/2000 give the identical result), relative spectral error 0.1292 (13 % of the power), lag-1 autocorrelation 0.3777 vs 0.5742 in the data. From the first probe: lag-5 0.178 vs 0.352, lag-50 0.085 vs 0.213; low-frequency (first 5 % of bins) relative error 0.108. The harness reports `capped=0/30` and "mean spectral error 6.712e-05" for the cascade, which looks small only because the error is absolute (mean squared target power is 5.485e-04). The unit assertion `err < 1e-6` is not applied to the cascade at all, and is not scale invariant. So the "significant" cascade result (p = 0.0323, k=0, n=30) is compared against surrogates with markedly weaker linear correlations than the data: part of the rejection can come from the unmatched spectrum, not only from nonlinearity.

**F3. The harness cannot detect F1/F2.** Class (a). iaaft_test checks one fGn (p=0.8387, k=25) and one cascade (p=0.0323, k=0) at n=30 — a pass is expected under both a calibrated and a miscalibrated test. The pre-registered expectation "cascade significant" holds, but a test that over-rejects everywhere would also satisfy it.

**F4. Observed data are not processed like the surrogates.** [OPEN], methodological. Surrogates go through a rank-mapping step that the data never saw; the bias in F2 is the visible effect. The common remedy is empirical calibration (e.g. Monte-Carlo null from a fitted linear model, or comparing with IAAFT surrogates of IAAFT surrogates). I did not test any remedy.

**F5. Minor.** `n_capped` counts `iterations >= max_iter`, which also counts a surrogate that converged exactly on the last iteration (cosmetic). For cascade data, reported `final_spectral_error` is meaningful only relative to the target power. The shuffle test remains a valid test of "no temporal structure at all", not of nonlinearity (earlier F5). Remaining items from the previous engine review are unchanged by this diff: F1 (fit-end exclusive), F2 (constant-value runs pass the fit-band gate), F4 (default fit_start=0, s=3).

## 4. Probe 1–2 numbers (convergence and fidelity)

- fGn H=0.7, N=4096 (`np.random.seed(11)`, surrogate seed 1): 60 iterations, absolute error 2.75e-08, relative error 7.44e-07, low-frequency relative error 2.45e-07; lag-1/5/50 autocorrelation 0.3096/0.0994/−0.0118 (data) vs 0.3096/0.0990/−0.0145 (surrogate). N=4095 (odd): 41 iterations, relative error 8.64e-07. Cumulative sum (random walk, N=4096): 434 iterations, relative error 5.48e-06.
- Cascade: see F1. Iterations 10 / 31 / 32 give relative error 0.1321 / 0.1292 / 0.1292.

## 5. Could not verify

- The cause of F2 (phase/clustering loss) — measured only the effect, not which statistic of the surrogate differs.
- Type-I error for linear heavy-tailed processes at other N, H, and tail strengths; only one setting, 40 realizations, n=19 per test.
- Power of the IAAFT test on the real multifractal cascade against a calibrated null.
- Effect of end-point mismatch (non-periodic ends) on the surrogates; only the random walk's iteration count suggests it matters, I did not measure the width.
- Whether any gaze or other real data are heavy-tailed enough for F2 to matter. That decides the thesis impact.

## 6. Suggestions (engine is not complete yet)

1. **Add a size study to the harness** (`validation/iaaft_size.py`): linear-null processes (fGn H=0.5/0.7/0.9 and lognormal(σ) of fGn), R ≥ 200 realizations, n=39 surrogates, report rejection rate at p ≤ 0.05 with a binomial interval; assert only on the fGn Gaussian case, print the heavy-tailed ones. Seeds fixed; runtime is minutes (probe 3 took 269 s for 80 tests of n=19).
2. **Report relative spectral error** (`mean((A−A_s)²)/mean(A²)`) and the stop reason (rank fixed point / tol / cap) in the diagnostics tuple; flag the test as unreliable when relative error exceeds a pinned threshold (fGn: 7e-07, cascade: 0.129, lognormal: ~0.02–0.03 with up to 24/40 capped).
3. **Report the surrogate null next to the observed width in the UI** (mean, sd, the interval) and state the null in methods: "linear Gaussian process, rescaled" — not "no cascade".
4. **Calibration option**: add a parametric-bootstrap (fit a linear Gaussian model, rescale, measure width) as a second null for heavy-tailed data; compare with IAAFT.
5. Still open from the engine review and independent of IAAFT: the constant-value-run guard (F2), the fit-end off-by-one (F1), and the `fit_start=0, s=3` default (F4). I would fix these before moving on to the UI, since they change numbers.
