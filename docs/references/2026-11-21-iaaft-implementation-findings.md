# IAAFT surrogate test — implementation findings

Prepared 2026-11-21 for the MF-DFA thesis app. Scope: how to **implement** the
Iterated Amplitude Adjusted Fourier Transform (IAAFT) surrogate test in this
repository. Research questions about what IAAFT can or cannot prove are out of
scope, except where the answer changes what the code must compute or report.

Every claim below is traceable to a source in the bibliography; inline `[n]`
markers point there.

---

## 1. What the algorithm is, in implementation terms

IAAFT generates surrogate time series that keep two linear properties of the
input and destroy nonlinear temporal structure [1][2][3]:

- the **power spectrum** (= linear autocorrelation), approximately;
- the exact **multiset of values** (amplitude distribution), exactly.

The null hypothesis is "the data come from a (possibly nonlinearly rescaled)
stationary linear Gaussian process" [1][2]. For this app it is the natural next
step after the shuffle test: shuffling destroys *all* temporal structure
(linear and nonlinear), whereas IAAFT removes only the nonlinear part — so a
significant IAAFT result means "more multifractal structure than a linear
process with the same spectrum and distribution could produce", which is the
claim the thesis wants [3][10].

---

## 2. The algorithm — step by step

This is the formulation shared by the original paper [1], the review article
[3], and the application paper [12]:

1. **Targets.** Store the sorted values of the signal `x`
   (`sorted_values = np.sort(x)`) and the Fourier amplitudes
   `target_amp = np.abs(np.fft.rfft(x))`.
2. **Initialization.** Start from a random permutation of `x` (the paper calls
   this the j = 0 iteration [1]).
3. **Iterate:**
   a. **Spectrum step.** Fourier-transform the current surrogate, replace its
      amplitudes by `target_amp`, keep its phases, and inverse-transform.
   b. **Distribution step.** Rank-order the result back onto the original
      values: replace the i-th smallest value with `sorted_values[i]`.
4. **Stop** when a convergence criterion is met or `max_iter` is reached
   (see §4). The algorithm is not expected to converge in the strict sense for
   finite N [1][2].
5. **Output.** Return the surrogate. Always end with the distribution step if
   you want an exact value distribution; or return both final stages
   ("exact spectrum" and "exact distribution"), as TISEAN does [2].

Implementation detail that matters: step 3a must preserve the phases of the
*current* surrogate, not those of the original — the phase randomization comes
from the random starting permutation and is only reshaped by the iteration
[1][2][3].

---

## 3. Reference implementations surveyed

| Source | Language | Spectrum | Convergence | Defaults |
|---|---|---|---|---|
| NeuroKit2 `signal_surrogate` [4] | Python/NumPy | `rfft`/`irfft`; amplitudes scaled by `t/abs(t)` | RMSD between squared amplitude spectra, `atol`/`rtol` | `max_iter=1000`, `atol=1e-8`, `rtol=1e-10`; returns surrogate, iterations, normalized RMSD |
| mftoolkit `iaaft_surrogate` [5] | Python/NumPy | `rfft`/`irfft`; mean squared amplitude error | relative change of spectral error `< tol` | `max_iter=1000`, `tol=1e-8`; warns on non-convergence |
| Biotuner `iaaft_surrogate` [6] | Python/NumPy | `rfft`/`irfft`; mean squared time-domain difference | `abs(prev_diff - diff) < tol` | `n_iter=100`, `tol=1e-6` |
| TimeseriesSurrogates.jl `IAAFT` [7] | Julia | periodogram, optionally binned (`W` bins) | relative periodogram deviation `< tol` | `M=100`, `tol=1e-6`, `W=75` |
| opendeviationbar-hurst `iaaft.rs` [9] | Rust | full FFT | rank ordering unchanged between iterations | `max_iter` caller-set (docs suggest 100–500) |
| `wol-fi/multifractal` `iaaft` [10] | R (Henning Rust 2006 code) | periodogram or ACF | relative change `< tolerance` | `tol=0.01`, `maxit=100` |
| `nmitrou/Simulations` `IAAFT.m` [11] | MATLAB | full FFT | rank-order index unchanged (`indnew == indold`) | `maxiter=1000` |
| TISEAN `surrogates` program [2] | TISEAN (C) | full FFT | "until no further improvement can be made"; returns last two stages | — |
| `machine-climate/iaaft` [8] | Python | FFT, Venema et al. variant | (variant of IAAFT) | 1000 surrogates example |

All implementations share steps 1–4 above; they differ only in the
convergence test and in which final stage is returned [2][4][5][6][7][9][10][11].

**License note:** the surveyed code carries mixed licenses — Biotuner's docs and
code are MIT [6]; `machine-climate/iaaft`'s README says LGPL v3 while the
repository page says AGPL-3.0 [8]; `LeonardoRicci/iaaft` states LGPL v3 /
GPL v3 [13]. We should implement from the algorithm description (and the
short sketch in §5), not by copying those files; check each license before
reusing any code fragment.

---

## 4. Convergence criteria — what to implement

Three practical families appear in the code above:

1. **Rank-order stability** — stop when the rank ordering after the
   distribution step is identical to the previous iteration's ordering
   [2][9][11]. This is the least strict criterion; it typically triggers after
   a handful of iterations.
2. **Spectral discrepancy** — stop when the relative change of a spectral
   error falls below a tolerance [4][5][6][7][10]. The error is computed either
   on the amplitude spectrum (NeuroKit2, mftoolkit) or on the periodogram
   (Julia, R). Implementations use relative changes with tolerances between
   `1e-10` and `1e-2` [4][5][10].
3. **Iteration cap** — always needed because strict convergence is not
   guaranteed for finite N [1][2]. Caps found: 100 [6][7], 1000 [4][5][11].

The 1996 paper's own experiment used about 7 iterations to reach the nominal
false-rejection rate [1]; for our implementation the cap should be generous
(e.g. 100–1000) and non-convergence should be surfaced, not hidden [5].

**Recommended combination** (consistent with the survey): stop when either
(a) the rank ordering is unchanged, or (b) the relative change of the mean
squared spectrum error is below a tolerance, or (c) `max_iter` is reached;
return the last rank-ordered surrogate (exact distribution) and report the
iteration count and final spectral error. That matches TISEAN's "return the
last two stages" philosophy [2] and the majority of Python implementations
[4][5][6].

---

## 5. Implementation pitfalls that apply to this project

1. **Always finish on the distribution step** unless you return both variants,
   because only that guarantees the exact value multiset [1][2]. The
   spectrum is then only approximately matched — state that in the report/UI.
2. **Use the real FFT** (`np.fft.rfft` / `np.fft.irfft`) for a real-valued
   signal: half the arrays, and it guarantees a real output [4][5][6].
3. **Validate the input**: all-finite, 1-D float array. Sorting (and thus rank
   ordering) with NaN is undefined — the Rust implementation needed a dedicated
   NaN test to avoid a panic [9]. Our engine already requires finite uploads
   (`pages/mf_dfa.py`), but the surrogate generator should not assume it.
4. **Determinism**: pass an explicit RNG seeded per surrogate, as in the
   existing shuffle test (`np.random.default_rng(seed)`). With a fixed seed the
   IAAFT output must be identical across runs; this is testable.
5. **Ties in the rank step**: signal values may repeat (cascade, quantised
   tracker data). Use a stable sort (`kind="stable"`) so repeated values map
   reproducibly.
6. **Periodicity assumption**: Fourier-based methods treat the data as one
   period of a periodic signal; the TISEAN documentation recommends trimming so
   that the ends approximately match, to avoid spurious rejections [2]. This is
   an optional preprocessing precaution, not part of the core loop.
7. **Cost**: each iteration costs two FFTs — negligible next to the MF-DFA
   pipeline that must run on every surrogate. The dominant cost in this app is
   the per-surrogate `run_mfdfa`, as in the existing shuffle test [3].
8. **Report the null correctly in the UI**: IAAFT surrogates preserve the
   spectrum, so the resulting p-value answers "is the multifractal width larger
   than a *linear* process with the same spectrum and distribution produces?"
   — a different (stronger) claim than the shuffle test [3][10]. Brief caveat:
   published analyses note that IAAFT surrogates can still carry residual phase
   correlations, so the null is approximate [14][15]; the UI text should avoid
   overclaiming.

---

## 6. Short reference sketch (our own implementation, from the algorithm)

Not copied from any listed repository; it follows the steps in §2 and the
convergence recommendation in §4. Written as pseudocode for the spec — the
actual implementation belongs in `mfdfa_engine.py` and must reuse the existing
`run_mfdfa` pipeline.

```python
def iaaft_surrogate(signal, seed=None, max_iter=200, tol=1e-6):
    """Generate one IAAFT surrogate of a 1-D real signal."""
    rng = np.random.default_rng(seed)
    values = np.sort(signal)
    amp = np.abs(np.fft.rfft(signal))

    surrogate = rng.permutation(signal)
    prev_err = np.inf

    for _ in range(max_iter):
        # spectrum step: keep phases, impose target amplitudes
        fft = np.fft.rfft(surrogate)
        new_fft = amp * (fft / np.abs(fft))       # d.c. component needs care
        z = np.fft.irfft(new_fft, n=len(signal))

        # distribution step: rank-order onto the original values
        ranks = np.argsort(np.argsort(z, kind="stable"), kind="stable")
        surrogate = values[ranks]

        # convergence: relative change of squared amplitude error
        err = np.mean((amp - np.abs(np.fft.rfft(surrogate))) ** 2)
        if abs(prev_err - err) <= tol * abs(prev_err):
            break
        prev_err = err

    return surrogate
```

Notes for the real implementation:

- the d.c. (first) rfft coefficient has phase 0; dividing by `abs(fft)`
  produces a division-by-zero if a bin is exactly zero — guard the d.c. term
  (impose its amplitude directly) or use the `t / abs(t)` style used by
  NeuroKit2 [4];
- return also the iteration count and final error, so a validation script can
  assert convergence;
- the surrounding test function should mirror `shuffled_surrogate_test`
  (same pipeline, same statistic, same `(1 + k)/(n + 1)` p-value), with the
  same finite-width guard added in the 2026-11-21 feature.

---

## 7. What the project validation should assert (mirroring the shuffle test)

Consistent with our existing validation protocol (fixed seeds, printed
versions, exit 0/1):

1. **Exact distribution** — `sorted(surrogate) == sorted(signal)` exactly
   (allclose with zero tolerance), at any iteration count [1][2].
2. **Spectrum preserved** — final relative spectral error below the chosen
   tolerance; print the achieved error and iteration count.
3. **Determinism** — same seed → identical surrogate.
4. **Behavioural discrimination**:
   - fGn H = 0.7 (linear noise with the right spectrum) → **not** significant
     against IAAFT surrogates (its width is finite-sample noise);
   - binomial cascade p = 0.3, 14 levels → **significant** (its multifractal
     width comes from temporal ordering that IAAFT removes while keeping the
     value multiset).
   These mirror the existing shuffle-test expectations [16] and must be
   measured before thresholds are fixed, per the project's tolerance protocol.
5. **Cost** — report wall time per surrogate so the UI can warn.

---

## Bibliography

[1] Schreiber, T., & Schmitz, A. (1996). *Improved surrogate data for
nonlinearity tests.* Physical Review Letters 77(4), 635–638.
doi:10.1103/PhysRevLett.77.635. Full text consulted via the arXiv version:
https://arxiv.org/abs/chao-dyn/9909041 (also stored locally in this
repository as `Schreiber and Schmitz - 1996 - Improved Surrogate Data for
Nonlinearity Tests.pdf`; the PDF itself could not be opened by the reviewing
tool, so the arXiv page was used).

[2] Schreiber, T. *TISEAN 2.1 documentation — Iterative Fourier transform
method.* Max Planck Institute for the Physics of Complex Systems.
https://www.pks.mpg.de/tisean/TISEAN_2.1/docs/chaospaper/node37.html

[3] Schreiber, T., & Schmitz, A. (2000). *Surrogate time series.* Physica D
142(3–4), 346–382. doi:10.1016/S0167-2789(00)00043-9 (verified via the
publisher record; free preprint: arXiv:chao-dyn/9909037,
https://arxiv.org/abs/chao-dyn/9909037). Algorithm restatement and the
argument for IAAFT over AAFT.

[4] NeuroKit2 — `signal_surrogate` source (IAAFT implementation).
https://neuropsychology.github.io/NeuroKit/_modules/neurokit2/signal/signal_surrogate.html

[5] MF-Toolkit — `mftoolkit.mfsources` source (IAAFT implementation).
https://mf-toolkit.readthedocs.io/en/latest/_modules/mftoolkit/mfsources.html

[6] Biotuner — `biotuner.resonance.nulls` source (IAAFT implementation).
https://antoinebellemare.github.io/biotuner/_modules/biotuner/resonance/nulls.html

[7] Haaga, K. A., & Datseris, G. — TimeseriesSurrogates.jl (Julia), IAAFT
method; package paper doi:10.21105/joss.04414.
Source (commit-pinned): https://github.com/JuliaDynamics/TimeseriesSurrogates.jl/blob/3e82aa0ef2c370d5e8c7c14c3717642242688989/src/methods/iaaft.jl
Documentation: https://juliadynamics.github.io/TimeseriesSurrogates.jl/stable/

[8] Goswami, B. — `machine-climate/iaaft` (Python IAAFT implementation, after
Venema, Ament & Simmer 2006).
https://github.com/machine-climate/iaaft

[9] `opendeviationbar-hurst` — IAAFT implementation in Rust
(`iaaft.rs`), with convergence-by-rank-stability and NaN handling.
https://docs.rs/opendeviationbar-hurst/latest/src/opendeviationbar_hurst/iaaft.rs.html

[10] Schadner, W. — `multifractal` R package, `iaaft` (based on Henning Rust,
2006).
https://rdrr.io/github/wol-fi/multifractal/man/iaaft.html

[11] MIT — `Simulations/matlab_codes/IAAFT.m` (MATLAB implementation).
https://github.com/nmitrou/Simulations/blob/master/matlab_codes/IAAFT.m

[12] Keylock, C. J. (2017). *A multifractal surrogate data generation
algorithm that preserves pointwise Hölder regularity structure, with initial
applications to turbulence.* arXiv:1701.00579 (contains a clear restatement of
the IAAFT iteration).
https://arxiv.org/abs/1701.00579

[13] Perinelli, A., & Ricci, L. — `LeonardoRicci/iaaft` (MATLAB and Python
IAAFT functions).
https://github.com/LeonardoRicci/iaaft

[14] *Revisiting algorithms for generating surrogate time series.*
arXiv:1111.1414 (notes residual phase correlations in AAFT/IAAFT
surrogates).
https://arxiv.org/abs/1111.1414

[15] *Surrogates with random Fourier phases.* arXiv:0812.2380 (same caveat,
with a distribution-based convergence measure).
https://arxiv.org/abs/0812.2380

[16] This repository — `validation/surrogate_test.py` (existing shuffle-test
expectations: fGn not significant, cascade significant).

[17] Venema, V., Ament, F., & Simmer, C. (2006). *A stochastic iterative
amplitude adjusted Fourier Transform algorithm with improved accuracy.*
Nonlinear Processes in Geophysics 13, 321–328.
doi:10.5194/npg-13-321-2006 — the variant implemented in [8] (cited in that
README).
