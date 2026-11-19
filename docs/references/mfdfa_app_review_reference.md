# MFDFA App — Methodology and Implementation Reference (for independent review)

Prepared: 2026-11-12. Reference package version: **LRydin/MFDFA 0.4.3** (MIT license).

## 0. How to use this document

**Task for the reviewer:** judge whether the author's MFDFA implementation (a Streamlit/Plotly app that wraps the LRydin `MFDFA` package and adds its own spectrum, width, surrogate and validation code) is *correct* and *methodologically defensible* for its intended use. The app source code is not reproduced here; this document tells you what it *should* do, what the reference package *actually* does, and what to check.

**Do not start from scratch.** Use this document as follows:

1. Section 3 = the algorithm (what correct MFDFA is).
2. Section 4 = what the reference package does line by line (verified by reading the installed 0.4.3 source, including quirks that matter).
3. Sections 5–7 = what the app is meant to do on top of the package.
4. Section 8 = baseline numbers a *correct* pipeline produces (so you can tell implementation bugs from estimator bias).
5. Section 9 = the review checklist. Appendix A = an independent reference implementation (matches the package to 3e-16). Appendix B = reproducible checks.

**Status labels used throughout**

| Label | Meaning |
|---|---|
| `[REF]` | Verified against the LRydin source (v0.4.3) or cited literature |
| `[SPEC]` | Intended app behaviour as described by the author. **Must be verified against the app code**, not assumed |
| `[VERIFY]` | A specific detail the author could not state precisely; read the code |
| `[TESTED]` | Result of an independent test run while preparing this document (code in Appendix B) |
| `[OPEN]` | Known open methodological question |

**Separate three kinds of finding in your review:** (a) implementation bugs, (b) methodological choices that are defensible but must be reported, (c) estimator bias that any correct implementation would show (Section 8).

---

## 1. Sources (check claims against these)

| Source | Supports | Link |
|---|---|---|
| **LRydin/MFDFA** (GitHub) | The package the app wraps | https://github.com/LRydin/MFDFA |
| Package source, `MFDFA/MFDFA.py` | Core algorithm | https://github.com/LRydin/MFDFA/blob/master/MFDFA/MFDFA.py (raw: https://raw.githubusercontent.com/LRydin/MFDFA/master/MFDFA/MFDFA.py) |
| Package source, `MFDFA/singspect.py` | h(q), τ(q), α, f(α) helpers | https://github.com/LRydin/MFDFA/blob/master/MFDFA/singspect.py |
| Package source, `MFDFA/fgn.py` | Fractional Gaussian noise generator (Davies–Harte) | https://github.com/LRydin/MFDFA/blob/master/MFDFA/fgn.py |
| PyPI | Install / version | https://pypi.org/project/MFDFA/ |
| Docs | Package documentation (note: `singspect` is not in the rendered docs) | https://mfdfa.readthedocs.io/en/latest/ |
| Rydin Gorjão, Hassan, Kurths, Witthaut (2022), *MFDFA: Efficient multifractal detrended fluctuation analysis in python*, Computer Physics Communications 273, 108254 | Package paper | https://doi.org/10.1016/j.cpc.2021.108254 · arXiv: https://arxiv.org/abs/2104.10470 |
| Peng et al. (1994), *Mosaic organization of DNA nucleotides*, Phys. Rev. E 49(2), 1685–1689 | Original DFA | https://doi.org/10.1103/PhysRevE.49.1685 |
| **Kantelhardt et al. (2002)**, *Multifractal detrended fluctuation analysis of nonstationary time series*, Physica A 316(1–4), 87–114 | **The MFDFA definition**, binomial-cascade test series, shuffled/surrogate discussion | https://doi.org/10.1016/S0378-4371(02)01383-3 |
| Ihlen (2012), *Introduction to multifractal detrended fluctuation analysis in Matlab*, Front. Physiol. 3:141 | Practical guide, parameter choices | https://doi.org/10.3389/fphys.2012.00141 |
| Kelty-Stephen, Palatinus, Saltzman, Dixon (2013), *A tutorial on multifractality, cascades, and interactivity for empirical time series in ecological science*, Ecological Psychology 25(1), 1–62 | Theoretical framing (interaction-dominant dynamics), surrogate logic in psychology | look up by title |
| Halsey et al. (1986), *Fractal measures and their singularities*, Phys. Rev. A 33, 1141 | Legendre-transform formalism, f(α) | look up by title |
| Theiler et al. (1992), *Testing for nonlinearity in time series: the method of surrogate data*, Physica D 58, 77–94 | Surrogate data testing | look up by title |
| Phipson & Smyth (2010), *Permutation p-values should never be zero*, Stat. Appl. Genet. Mol. Biol. 9(1), Article 39 | The (1+k)/(n+1) permutation p-value | look up by title |
| NumPy docs | `numpy.polynomial.polynomial.polyfit` (ascending coefficients), `numpy.gradient` (edge_order, non-uniform spacing), `numpy.float_power` | https://numpy.org/doc/ |

The line numbers cited in Section 4 refer to the **installed PyPI 0.4.3 wheel** (`MFDFA/MFDFA.py`, 316 lines). The GitHub master file may differ by a line or two.

---

## 2. Study context and signal definition

- **Thesis:** MA psychology thesis, multifractal analysis of chess players' eye-tracking data (masters vs advanced players) during solving of 9 Lichess puzzles (3 difficulty levels × 3 puzzles, all 5-ply). Theoretical framing: Kelty-Stephen's interaction-dominant dynamics and Kantelhardt's MFDFA methodology. The multifractal part is framed as **exploratory**.
- **Tracker:** Gazepoint. Gaze signal used: `BPOGX`, `BPOGY` (binocular-average, unfiltered point of gaze, normalised 0–1 of screen width/height), with `BPOGV` (valid flag) and `BKID` (blink id) for masking.
- **Analysed window per puzzle:** the thinking phase, from a RETURN key-down to the following SPACE key-down (static board, no motor noise). One spectrum per puzzle per participant. No phase segmentation (the supervisor rejected proportional phase splitting).
- **Signal fed to MFDFA:** per-sample displacement magnitude `v[i] = hypot(x[i+1]−x[i], y[i+1]−y[i])`, one non-negative, spiky, zero-heavy, noise-like series per puzzle. Saccades are **kept** (intermittency between fixations and saccades is the phenomenon of interest). Fixation-only analysis was rejected (theory + too few points).
- **Signal length:** expected on the order of 10³–10⁴ samples per puzzle `[VERIFY with real sampling rate and durations]`. This is *short* for MFDFA, and short-signal spurious multifractality (especially on the negative-q side) is a known concern `[OPEN]`.
- **Anisotropy note `[OPEN]`:** `BPOGX` is a fraction of screen *width* and `BPOGY` a fraction of screen *height*. `hypot` on these mixes units unless the aspect ratio is corrected (e.g. multiply x by width/height, or convert to pixels/degrees). A global constant factor does not change MFDFA exponents, but anisotropic weighting is not a global constant. Effect likely small but unquantified.

---

## 3. MFDFA — the reference algorithm `[REF: Kantelhardt et al. 2002; Peng et al. 1994]`

### 3.1 Input assumptions
- 1-D real series `x_1…x_N`, **evenly sampled**, **no NaN/inf**.
- **Noise-like** (stationary-increment-like) input. The algorithm integrates internally, so passing an already integrated series (a position/level/random walk) integrates it twice (see 3.4).

### 3.2 Steps

```
1. Profile:        Y(i) = Σ_{k=1..i} ( x_k − mean(x) ),   i = 1..N

2. Segmentation:   for each integer scale s:  N_s = floor(N / s)
                   2·N_s non-overlapping segments of length s:
                   N_s counted from the START of Y and N_s counted from the END
                   (so the remainder N mod s is not discarded, once from each side)

3. Detrending:     in every segment ν fit a least-squares polynomial y_ν of order m
                   (x-axis 1..s; m = 1 is "DFA1", a straight line)
                   F²(ν, s) = (1/s) Σ_{i=1..s} [ Y_ν(i) − y_ν(i) ]²        (variance of residuals)

4. Fluctuation     F_q(s) = { (1/(2N_s)) Σ_{ν=1..2N_s} [F²(ν,s)]^{q/2} }^{1/q}      q ≠ 0
   function:       F_0(s) = exp{ (1/(4N_s)) Σ_{ν=1..2N_s} ln F²(ν,s) }               q = 0 (log average)

5. Scaling:        F_q(s) ∝ s^{h(q)}   →   h(q) = slope of ln F_q(s) vs ln s over a FIT RANGE of scales

6. Spectrum:       τ(q) = q·h(q) − 1
                   α(q) = dτ/dq = h(q) + q·h'(q)                (singularity strength / Hölder exponent)
                   f(α) = q·α − τ  = q·[α − h(q)] + 1 = 1 + q²·h'(q)   (singularity spectrum)
```

Consequences worth checking in any implementation:
- `f(α)` has its maximum, `f = 1`, at `q = 0` (because `τ(0) = −1`). If q = 0 is excluded, the observed maximum is slightly below 1.
- Monofractal: `h(q)` constant ⇒ `τ(q)` linear ⇒ spectrum collapses to a point (Δα = 0).
- Width: `Δα = α_max − α_min` (over the q range used).
- **Positive q** weights segments with *large* variance; **negative q** weights segments with *small* variance. So positive q is sensitive to spikes/outliers, and **negative q is sensitive to near-flat segments** (constant, interpolated, quantised, zero runs).
- `q = 2` gives classic DFA (`F_2(s) = sqrt(mean F²)`): DFA is a special case of MFDFA.

### 3.3 Scale range and fit range
- Smallest scale: `s ≥ order + 2` is the hard minimum; in practice the smallest scales show a downward curl (a polynomial fits a very short window almost perfectly, so too much variance is removed) and are excluded from the fit.
- Largest scale: commonly `s_max ≈ N/4` or lower (Kantelhardt 2002 `[VERIFY section]`); near N/4 there are only a handful of segments, so `F_q` is noisy, especially for |q| large.
- A **single** fit range for all q is standard, but crossovers can differ between q. The author's app uses one fit range (two sliders) for all q.
- `h(q)` = slope in **log–log** space; the log base is irrelevant if both axes use the same base.
- Extreme |q| (e.g. |q| = 5) are less reliable on short signals; this is why a "robust" width (Section 5.5) trims extreme q.

### 3.4 Noise-like vs walk-like input (critical for interpretation)
- For **stationary / noise-like** input (e.g. fractional Gaussian noise), `h(2) = H`, with `0 < H < 1` (`H > 0.5` persistent, `< 0.5` antipersistent). The DFA slope **is** H.
- For **nonstationary / walk-like** input (fBm, random walk, level or mean-reverting process such as the fractional Ornstein–Uhlenbeck process), the same procedure returns `h(2) = H + 1`, i.e. the slope is above 1. The LRydin README states this for its fOU example (`slope = H + 1`).
- Therefore: slope > 1 on an uploaded series means the series was already integrated (one extra integration ⇒ ~H+1; two ⇒ ~H+2). The correct fix is to differentiate the input *before* analysis, not to subtract 1 inside the algorithm.
- The package has an option `modified=True` (second cumulative sum, line 162–163) for strongly anticorrelated noise; the app is not expected to use it `[VERIFY]`.
- Boundary mapping: for noise-like input, antipersistent/persistent boundary is h = 0.5; for walk-like input it is h = 1.5.

---

## 4. The LRydin package: what the code actually does (v0.4.3) `[REF]`

### 4.1 `MFDFA(timeseries, lag, order=1, q=2, stat=False, modified=False, extensions={'EMD': False, 'eDFA': False, 'window': False})` → `(lag, f)`

Returns the (possibly filtered) `lag` and `f`, a matrix of shape `(len(lag), n_q_kept)`. **It does not return the q values that were kept.**

| Lines (MFDFA.py) | Behaviour | Why it matters |
|---|---|---|
| 125–127 | `lag = lag[lag > order + 1]`; `lag = np.round(lag).astype(int)` | Scales ≤ order+1 are silently dropped, so the **returned `lag` can be shorter than the input**. The caller must use the returned `lag`. `lag` must be a NumPy array (boolean indexing). |
| 133 | `timeseries.reshape(-1, 1)` | Input must be a NumPy array (a pandas Series has no such method), 1-D. |
| 147–153 | `q = np.asarray_chkfinite(q, dtype=float)`; **`q = q[(q < -.1) + (q > .1)]`** | **All q with \|q\| ≤ 0.1 are removed silently**, not only q = 0. Float rounding decides the borderline values (see 4.2). The kept q are *not returned*. |
| 156 | `X = np.linspace(1, lag.max(), lag.max())` | x-axis for the polynomial fits (1…s). |
| 159 | `Y = np.cumsum(timeseries - np.mean(timeseries))` | **Profile is built inside the package.** Feed the raw noise-like series. |
| 162–163 | `if modified is True: Y = np.cumsum(Y - np.mean(Y))` | Optional second integration. |
| 198–199 | `Y_ = Y[:N − N % i].reshape(...)`; `Y_r = Y[N % i:].reshape(...)` | Segments from the start **and** from the end (2·N_s segments), as in Kantelhardt. |
| 204–216 | order 0: `F = np.append(np.var(Y_, axis=1), np.var(Y_r, axis=1))`; else `polyfit(X[:i], Y_.T, order)` per segment, residual `Y_ − polyval(X[:i], p)`, `np.var(..., axis=1)` | `F` holds the **variances F²(ν,s)** (not RMS). `np.var` uses ddof=0 around the mean of the residuals, which is zero for a least-squares polynomial with an intercept, so this equals the mean squared residual. |
| 247–253 | `f = np.append(f, np.float_power(np.mean(np.float_power(F, q/2), axis=1), 1/q.T), axis=0)` | `F_q(s) = (mean F^{q/2})^{1/q}`. **No q = 0 branch** (`# TODO: Add log calculator for q ≈ 0`, line 315). If any `F = 0` and q < 0 → `inf` / divide-by-zero warning; no guard. |
| 256–263 | `stat=True` returns `std` of `F^{q/2}` | Not a meaningful error bar on h(q); app is not expected to use it `[VERIFY]`. |
| 221–244, 175–185, 265–266, 280–313 | `window`, `EMD`, `eDFA` extensions | Not expected to be used by the app `[VERIFY]`. |

**Core implementation, quoted for reference (MIT license, © Leonardo Rydin Gorjão; lines 125–159 and 193–253, condensed):**

```python
# Force lag to be ints, ensure lag > order + 1
lag = lag[lag > order + 1]
lag = np.round(lag).astype(int)
...
# Fractal powers as floats
q = np.asarray_chkfinite(q, dtype=float)
# Ensure q≈0 is removed, since it does not converge. Limit set at |q| < 0.1
q = q[(q < -.1) + (q > .1)]
# Reshape q to perform np.float_power
q = q.reshape(-1, 1)
# x-axis needed for polyfit
X = np.linspace(1, lag.max(), lag.max())
# "Profile" of the series
Y = np.cumsum(timeseries - np.mean(timeseries))
...
for i in lag:
    # Reshape into (N/lag, lag), once from the start, once from the end
    Y_  = Y[:N - N % i].reshape((N - N % i) // i, i)
    Y_r = Y[N % i:].reshape((N - N % i) // i, i)
    if order == 0:
        F = np.append(np.var(Y_, axis=1), np.var(Y_r, axis=1))
    else:
        # Perform a polynomial fit to each segments
        p   = polyfit(X[:i], Y_.T, order)
        p_r = polyfit(X[:i], Y_r.T, order)
        # Subtract the trend from the fit and calculate the variance
        F = np.append(np.var(Y_  - polyval(X[:i], p),   axis=1),
                      np.var(Y_r - polyval(X[:i], p_r), axis=1))
    # Calculate the Multifractal (Non)-Detrended Fluctuation Analysis
    f = np.append(f,
                  np.float_power(np.mean(np.float_power(F, q / 2), axis=1), 1 / q.T),
                  axis=0)
```

### 4.2 The q-filter in practice `[TESTED]`

| Requested grid | q removed by the package | q kept |
|---|---|---|
| `np.linspace(-5, 5, 101)` (the app default; step 0.1) | **−0.1 and 0.0** (because `-0.09999999999999964` is not `< -0.1`, while `0.10000000000000053` is `> 0.1`) | **99**, asymmetric: 49 negative (−5 … −0.2) and 50 positive (0.1 … 5) |
| `np.linspace(-5, 5, 100)` | ±0.0505 | 98, symmetric |
| `np.linspace(-5, 5, 99)` | 0.0 | 98 |
| `np.linspace(-5, 5, 201)` | −0.1, −0.05, 0.0, 0.05 | 197 |

Implications: (i) with the default grid the kept q set is **asymmetric around 0**; (ii) the number of columns in `f` is 99, **not 100 or 101**; (iii) any code that indexes columns of `f` with the *requested* q list (or only removes q = 0 itself) will **misalign q and columns or crash**. The author's plots show a gap around q = 0 that is wider on the negative side, consistent with the package filter. The author's explanatory text states "101 values, 100 remain" — that is not what the package does with the default grid.

### 4.3 `singspect.py` (present in the wheel, absent from the rendered docs)

Functions: `hurst_exponents`, `scaling_exponents`, `singularity_spectrum` (+ plot helpers and private `_slopes`, `_falpha`, `_clean_q`).

```python
# _slopes: slope of ln F_q vs ln s over lag[lim[0]:lim[1]]
slopes[i] = polyfit(np.log(lag[lim[0]:lim[1]]), np.log(mfdfa[lim[0]:lim[1], i]), 1)[1]
# numpy.polynomial.polynomial.polyfit returns ASCENDING coefficients: [intercept, slope]

# scaling_exponents
tau = q * slopes - 1                     # τ(q) = q h(q) − 1

# singularity_spectrum
alpha = np.gradient(tau) / np.gradient(q)   # ratio of index-space gradients
f     = q * alpha - tau                     # _falpha

# _clean_q: same |q| ≤ 0.1 filter as MFDFA()
q = q[(q < -.1) + (q > .1)]
```

Notes `[REF]`:
- Default fit range if `lim` is not given: `lim = [lag.size // 8, lag.size // 1.5]` (code). The docstring text states a different default.
- **Mutable default argument:** `lim: list = [False, False]` is mutated in place (`lim[0] = int(...)`), so after the first call without `lim`, the default list holds the first call's limits and is reused for later calls with a different `lag` size. Relevant only if the app calls these helpers with the default `lim`.
- The docstrings say α will be "centred > 1 for most cases" and h(q) "> 1 for most cases": that comment reflects the package's walk-like examples (fOU), not noise-like input.
- Changelog 0.4.3: "Reverting negative values in the estimation of the singularity strength α."
- The app computes its own slopes (`compute_hq`, `fit_dfa_exponent`) and may use `singspect` only as a cross-check `[VERIFY]`. **A strong review step is to run `singspect` on the same F matrix with the same `lim` and compare h(q), τ(q), α, f(α) with the app's values.**

### 4.4 `fgn(N, H)`
Davies–Harte fractional Gaussian noise, `N` must be `int`, `H` must be `float` in (0, 1), fails for H ≈ 0. Used for monofractal ground truth.

---

## 5. The app: intended behaviour `[SPEC — verify against code]`

### 5.1 Architecture
- Streamlit multipage app: `mfdfa_engine.py` (compute), `pages/home.py`, `pages/dfa.py`, `pages/mf_dfa.py` (presentation).
- Strict separation: **no Streamlit calls inside compute functions**. Uploaded files are held in a `st.session_state` dict keyed by filename (in memory only).
- UI convention: English labels, Hungarian help text; sidebar controls, results in the main area; "Advanced settings" expander for parameters.
- A single `MFDFA(...)` call with many q values; the q = 2 column is used for the monofractal (DFA) result `[VERIFY: how the q = 2 column is selected — float equality vs np.isclose, and that it survives the \|q\| ≤ 0.1 filter and the 99-column layout]`.

### 5.2 Inputs and contract
- **Uploaded real data:** a CSV with one column `y` = the 1-D signal to analyse (per-sample gaze displacement). The x axis (time/sample index) is **reconstructed from the length for plotting only** and is **never** passed to MFDFA as `lag` or as data. Sampling rate is used only for axis labels.
- **Generated signals** (validation): fractional Ornstein–Uhlenbeck (monofractal, walk-like/level process) and a binomial multiplicative cascade (multifractal ground truth).
- **Noise-vs-walk rule (author's design decision):** the app expects **noise-like** uploads, does not auto-detect the signal type, and has **no switch** to subtract 1 for uploads. The user is told to check the DFA slope: slope in (0,1) ⇒ noise-like OK; slope > 1 ⇒ already integrated ⇒ differentiate before uploading (slope > 2 ⇒ integrated twice). `H = slope − 1` is applied **only on the generated fOU path** (a level process whose DFA slope ≈ H + 1). `[VERIFY: (a) subtraction is never applied to uploads; (b) if the multifractal outputs are produced for the fOU path, the same −1 is applied to the whole h(q) vector before τ = q·h − 1, otherwise τ, α, f are wrong on that path.]`
- A previously observed live bug (h = −0.159) came from auto-inferring/applying the subtraction on the wrong signal type.

### 5.3 Parameters and scale construction
| Parameter | Intended default / rule |
|---|---|
| detrending `order` | 1 (DFA1). Minimum window = order + 2. |
| q range | −5 … 5 |
| number of q values (`q_num`) | default 101, UI min 11, max 201, step 2 (odd counts so that a symmetric linspace contains 0) — see 4.2 for what the package really keeps |
| scales | `s_min = max(order + 2, zero_run + 1)` where `zero_run` = longest run of exact zeros in the signal; `lag = np.unique(np.logspace(log10(s_min), log10(s_max), n_lags).astype(int))`; default `n_lags = 100`; UI shows both the chosen largest window and the largest usable window `N // 4` |
| fit range | two sliders `fit_start`, `fit_end`, which are **indices into the (unique) lag array**, not scale values (a UI caption showing the corresponding scales was requested) |

`[VERIFY]` points: `np.unique` after `astype(int)` makes the effective number of scales smaller than `n_lags` (many duplicates at small s); `astype(int)` truncates whereas the package rounds; the engine must pass/consume the *returned* `lag`; the UI `lag end` default (log10 = 4.6 ≈ 39 811) can exceed N/4 for short signals; whether any scale above N/4 is permitted.

### 5.4 Slope fitting and fit quality
- `h(q)` = linear regression slope of `ln F_q(s)` against `ln s` over `[fit_start:fit_end]`, same range for every q.
- Order of operations matters: **slice, then log** (`np.log(dfa_mf[fit_start:fit_end, i])`), otherwise invalid values outside the fit range still trigger warnings (a fix that was applied; confirm both `compute_hq` and `fit_dfa_exponent`).
- R² per q from the same regression; the page reports the **minimum R² across all q** (not the R² of the 6 plotted curves).
- The multi-q plot shows 6 representative q values (−5, −2, −1, 1, 2, 5) with legend h values; all q are computed in the background.

### 5.5 Spectrum and statistics
```
τ(q) = q·h(q) − 1
α    = np.gradient(τ, q)                 # coordinate array supplied, so non-uniform spacing around the q gap is handled
f(α) = q·α − τ
```
- **Δα (raw)** = max α − min α over all kept q.
- **Δα (robust)** = width after trimming fragile extreme-q tips via `q_width_max` (a previously pasted review described it as using only |q| ≤ 4), optional `positive_q_only`, and `f_floor` (drop points with f below a floor) `[VERIFY exact defaults and rule]`. The app also reports the relative difference between robust and raw widths.
- Also reported: `spec_range` (α min–max, raw and robust), `α_peak` (α at maximum f; with q = 0 removed, the maximum is ~0.99 rather than 1 `[VERIFY definition]`), **asymmetry** (raw and robust; sign convention described in the UI as ">0 toward the rough side, <0 toward the smooth side") `[VERIFY: formula, normalisation, and that it does not depend on q-grid density]`, and min R².
- Per trial exports: Δα raw, Δα robust, asymmetry, α peak, surrogate p-value, min R².

### 5.6 What the plots are supposed to show
Fluctuation functions (log–log, one line per q; parallel ⇒ monofractal, fanning ⇒ multifractal), h(q) vs q (flat ⇒ monofractal), τ(q) vs q (linear ⇒ monofractal), f(α) vs α (point ⇒ monofractal, arc ⇒ multifractal).

---

## 6. Upstream preprocessing (outside the app) and the hazards it creates for MFDFA `[SPEC]`

The app reads a clean one-column CSV; preprocessing is deliberately **outside** the app (reproducibility, defensibility). Steps per puzzle window:

1. Load the Gazepoint export; check sampling regularity (`TIME`, `CNT`), regrid so dropped records become NaN rows.
2. Slice the window: RETURN key-down → SPACE key-down (`KB`, `KBS == 1`), with a check that the number of RETURN presses between SPACEs matches the protocol.
3. Mask bad samples: `BPOGV != 1`, `BKID != 0` (+ a few samples of padding around blinks), coordinates outside [0,1] or (0,0).
4. Trim leading/trailing bad samples (never flat-fill them); interpolate interior gaps linearly; cap the gap length.
5. `v = np.hypot(np.diff(x), np.diff(y))` (N samples give N−1 displacements; the first sample simply has none; no padding with 0 or NaN).
6. Write `y` to CSV, plus a QC row (N, masked fraction, longest gap, zero fraction, longest zero run, max/median speed).

**Hazards for MFDFA validity (review these assumptions):**
- **Zero runs.** Held/quantised tracker positions give exact-zero displacement runs. A window lying entirely inside a zero run has F² = 0; for q < 0 this gives `0^{q/2}` = inf. The engine's `s_min = max(order+2, zero_run+1)` guards against exact-zero runs.
- **Constant-velocity runs from interpolation `[TESTED]`.** Linear interpolation of x and y produces a **constant speed** across the gap. A segment lying inside it has a perfectly linear profile, which order-1 detrending removes exactly ⇒ F² ≈ 0, the same failure as a zero run, **but the `zero_run` guard does not see it** (the values are non-zero constants). Test: a spiky noise-like series (gamma-distributed, N = 6000) with 20 gaps of 15 samples (5 % of samples) replaced by constant values: `h(q=−4)` rose from **0.637 to 0.818**, `h(−2)` from 0.590 to 0.670, `h(+4)` barely moved (0.512 → 0.548), and `F` at the smallest scale for q = −4 collapsed to 0.0. Negative-q h(q) values > 1 on a noise-like input are therefore a warning sign to rule out before interpreting them as strong small-fluctuation persistence `[OPEN]`.
  - Mitigations: cap interpolated gap length below the smallest fitted scale (or start the fit above it), exclude trials with longer gaps, and/or extend the guard to the longest constant-velocity/interpolated run.
- **Edge fill** (`bfill/ffill`, or `interpolate()` without `limit_area="inside"`) creates constant runs at the ends; the preprocessing was changed to trim instead.
- **Non-uniform sampling** (dropped records) breaks the assumption that adjacent samples are one step apart.
- **Blink padding adds to gap length** (2 × pad samples per blink).

---

## 7. Surrogate (shuffle) test `[SPEC — verify]`

**Purpose:** separate multifractality that comes from the *temporal ordering* of the signal from multifractality that comes only from its *value distribution* (heavy tails, many near-zeros, a few big spikes). Kantelhardt et al. (2002) identify two sources: broad probability density of the values, and different long-range correlations of small vs large fluctuations. Shuffling destroys the correlations and keeps the distribution.

**Procedure (intended):**
1. Compute Δα (the **robust** width) for the real signal.
2. Repeat `n = 100` times: `np.random.permutation(signal)`, run the *identical* pipeline, compute Δα_robust.
3. Report real Δα, surrogate mean, median, std, the 2.5–97.5 percentile interval (called "95 % CI" in the UI; strictly a surrogate/percentile interval, not a confidence interval), and the p-value.
4. **p-value:** `p = (1 + Σ(Δα_surr ≥ Δα_real)) / (n + 1)` (Phipson & Smyth 2010; never exactly 0). With n = 100 the minimum is 1/101 ≈ 0.0099. A previous operator-precedence bug (`1 + sum/len + 1` instead of `(1 + sum)/(len + 1)`) produced p = 2.0 and was fixed.
5. Interpretation: real Δα above the upper bound / small p ⇒ the width is not explained by the value distribution alone ⇒ temporal structure contributes. This is **one-sided** for p (surrogates ≥ real) while the percentile interval is two-sided; both give the same reject decision for "broader than surrogate".

**What the test does not show:** a plain shuffle destroys *all* temporal structure including linear autocorrelation, so it cannot separate linear correlation from nonlinear (cascade-like) structure. Phase-randomised/IAAFT surrogates would, and are **not implemented** (to be stated as a limitation).

**`[VERIFY]` correctness conditions for the surrogate test:**
- Same `q` list, same `order`, same fit range, same width definition and trimming for real and surrogate signals.
- **The same `lag` array for all.** If the engine recomputes `s_min` from `zero_run` per signal, a shuffled signal has a different longest zero run (shuffling scatters runs) ⇒ different `lag` ⇒ not like-for-like. Use the real signal's `lag` for every surrogate.
- The same NaN/inf handling for surrogates (negative q on shuffled data should not produce inf).
- Seed handling / reproducibility; computation time for n = 100 (it is an optional button in the UI).

---

## 8. Validation experiments and baselines a correct pipeline gives `[TESTED]`

All numbers below were produced with the code in Appendix B (LRydin 0.4.3 with the same kind of pipeline the app uses: scales log-spaced from 10 to N/4, 40 scales, fit range `[lag.size//8 : lag.size/1.5]`, `q = linspace(−5, 5, 101)` after the package's |q|>0.1 filter, `α = np.gradient(τ, q)`). Different fit ranges change the widths.

### 8.1 Independent reference implementation vs package
Appendix A's from-scratch implementation reproduces the package's F_q(s) to a maximum relative difference of **2.9e−16**. So the package follows the published algorithm (both-ends segmentation, polynomial detrending, F_q as above).

### 8.2 Monofractal ground truth: fGn, H = 0.7
| N | h(q) at q = −4, −2, 2, 4 (mean of 8 seeds) | sd |
|---|---|---|
| 2¹⁴ | 0.701, 0.701, 0.703, 0.702 | 0.015–0.028 |

**Spurious width of a monofractal (true Δα = 0)** with the full pipeline:

| N | raw Δα (mean ± sd, 6 seeds) | Δα with \|q\| ≤ 4 |
|---|---|---|
| 2¹⁴ | 0.051 ± 0.018 | 0.040 |
| 2¹⁶ | 0.028 ± 0.020 | 0.021 |

The author's fOU validation reported Δα ≈ 0.02 (monofractal verdict), consistent with this baseline.

### 8.3 Multifractal ground truth: binomial cascade (Kantelhardt 2002)
Series `x_k = a^{n(k−1)} (1−a)^{n_max − n(k−1)}`, `N = 2^{n_max}`, `n(k)` = number of 1-bits of k. Theory: `τ(q) = −log2(a^q + (1−a)^q)`, `h(q) = (1 + τ(q))/q`, asymptotic width `Δα∞ = log2(max(a,1−a) / min(a,1−a))`. (The app's generator multiplies halves by p and 1−p recursively; this is the same series up to a ↔ 1−a `[VERIFY with allclose(sorted(...))]`.)

| a | q = −4, −2, 2, 4: h(q) measured | h(q) theory |
|---|---|---|
| 0.3 (N = 2¹⁴) | 1.498, 1.343, 0.835, 0.708 | 1.499, 1.359, 0.893, 0.753 |
| 0.4 (N = 2¹⁴) | 1.130, 1.073, 0.917, 0.830 | 1.137, 1.087, 0.972, 0.922 |

Negative q is accurate to ~0.01–0.02; **positive q is biased low by ~0.05–0.09** at N = 2¹⁴.

### 8.4 The width-vs-theory comparison used in the app (p = 0.55)
The app compares the empirical width with (i) the asymptotic formula and (ii) a **finite-q theoretical spectrum** evaluated on the *same q list and the same trimming*:

```python
tau_th   = -np.log2(p**q + (1 - p)**q)
alpha_th = np.gradient(tau_th, q)
f_th     = q * alpha_th - tau_th
rel_err  = abs(emp - theory) / theory * 100     # theory in the denominator
```

Last observed app output (screenshot; p inferred as 0.55 from Δα∞ = 0.2895, N not confirmed `[VERIFY]`):

| | empirical | theory (finite q) | relative error |
|---|---|---|---|
| Δα raw | 0.2123 | 0.1330 | 59.6 % |
| Δα robust | 0.1720 | 0.1103 | 55.9 % |
| vs asymptotic 0.2895 | raw 26.7 %, robust 40.6 % | | |

`[TESTED]` the same quantities from the independent pipeline:

| N | raw: empirical / theory (ratio) | \|q\| ≤ 4: empirical / theory (ratio) |
|---|---|---|
| 2¹⁴ | 0.3349 / 0.1330 (2.52) | 0.3025 / 0.1103 (2.74) |
| 2¹⁶ | **0.2071 / 0.1330 (1.56)** | **0.1753 / 0.1103 (1.59)** |
| 2¹⁸ | 0.2241 / 0.1330 (1.68) | 0.1909 / 0.1103 (1.73) |

At N ≈ 2¹⁶ the independent pipeline reproduces the app's numbers (0.207/0.175 vs 0.212/0.172). **Conclusion for the reviewer:** the large relative width error at p = 0.55 is what a *correct* implementation produces; it is estimator bias, not (necessarily) an implementation error. The width does not converge monotonically to the finite-q theoretical value even at N = 2¹⁸. Mechanism: α = h + q·h′ is a *derivative*, so small, systematic h(q) errors (here up to 0.044 at N = 2¹⁶: `max |h_emp − h_theory| = 0.0436`, h_emp range 0.929–1.035 vs theory 0.972–1.042) are amplified into the width. Therefore relative width error is a **poor correctness criterion**; judge validation primarily on **h(q)/τ(q) agreement** and on the **monofractal width baseline** (8.2). Whether the app's validation page should show those instead is a reviewer recommendation worth making `[OPEN]`.

### 8.5 Sensitivity checks the reviewer may want
- Δα vs the number of q values (e.g. 21, 51, 101): finite-difference α amplifies noise in τ(q) as the q step shrinks.
- Δα vs fit range (the width is sensitive to it).
- `np.gradient` uses first-order one-sided differences at the two end points by default (`edge_order=1`), and α_min/α_max are exactly the end points ⇒ raw Δα depends on the least accurate derivative estimates; "robust" trimming mitigates this.

---

## 9. Reviewer checklist

**A. Input and call**
1. Signal is a 1-D `float64` NumPy array (not a Series), no NaN/inf, evenly sampled; length N recorded and shown.
2. The raw noise-like signal is passed; the app does **not** integrate it first (the package integrates internally). `modified` stays `False`.
3. The time axis is never passed as `lag` or as data.
4. Uploaded signals: no `H = slope − 1` correction; fOU path only. If the multifractal pipeline runs on the fOU path, `h(q) − 1` is used before `τ = q·h − 1`.
5. DFA/slope diagnostic: slope > 1 on an upload triggers a clear warning (integrated input).

**B. Scales (`lag`)**
6. The app uses the **returned** `lag`, and `lag` is integer, unique, ≥ order + 2, ≤ ~N/4.
7. `s_min` guard covers exact-zero runs **and** interpolated/constant runs (Section 6), or such runs are prevented upstream.
8. The number of effective scales after `np.unique` is shown/checked (≥ ~10 inside the fit range).
9. Surrogates use the real signal's `lag`.

**C. q handling**
10. The q values used downstream are **exactly the q kept by the package** (|q| ≤ 0.1 removed, float effects included). With the default grid there are 99 kept values, asymmetric around 0. Check there is no misalignment between `f` columns and the q array, and no hidden crash for other `q_num`.
11. The q = 2 column used for DFA/H is selected robustly (`np.isclose`, and present after filtering).
12. Consider whether an even `q_num` (symmetric removal of ±0.0505 for 100 points) is preferable to odd counts that give an asymmetric kept set.
13. Non-finite F values (zero-variance segments) are detected and reported; no silent NaN in h(q).

**D. Fit**
14. Slice-then-log in every slope computation; same range for all q; indices vs scales displayed consistently.
15. R² formula is the standard coefficient of determination of the log–log regression; "min R² across q" uses all kept q.
16. Slope stability: h(q) should barely change when the fit range is nudged (a reporting recommendation).

**E. Spectrum and statistics**
17. `τ = q·h − 1`, `α = gradient(τ, q)`, `f = qα − τ`; compare with `singspect` on identical inputs and with the independent implementation (Appendix A).
18. Definition and defaults of Δα robust (`q_width_max`, `positive_q_only`, `f_floor`), α_peak, asymmetry (formula, sign, normalisation).
19. Whether raw Δα depends strongly on q density/end-point derivatives (8.5).

**F. Surrogate test (Section 7)**
20. Identical settings; same lag; p-value formula `(1 + k)/(n + 1)`; interval percentiles `[2.5, 97.5]`; labelling as "surrogate interval"; limitation stated (shuffle ≠ IAAFT); seed/reproducibility.

**G. Validation**
21. fOU: monofractal verdict with Δα near the baseline in 8.2; H recovered after the −1 correction.
22. Cascade: compare h(q)/τ(q), not only width; theoretical reference uses the same q list and trimming; denominator = theory.
23. Add (or confirm) a baseline: width of an fGn/shuffled series of the same N.

**H. Data-quality interface (preprocessing → app)**
24. QC numbers exist per trial (N, masked fraction, longest gap/zero run, max/median speed) and exclusion thresholds were fixed before looking at spectra.
25. Anisotropy of normalised x/y (Section 2) is decided and reported.

---

## 10. Open methodological questions (for reviewer judgement)

1. **Short signals:** per-puzzle N may be only 10³–10⁴. Is any multifractal claim defensible at that length, and how many usable scales remain? (Being discussed with the supervisor.)
2. **Negative-q reliability on spiky, zero-heavy, partly interpolated data:** values of h(q) > 1 on the negative-q side of a noise-like input need to be separated from interpolation/quantisation artefacts (Section 6) before interpretation.
3. **Width as the headline statistic:** it is derivative-based, sensitive to fit range, q density and end-point handling; the robust variant needs a documented, theory-independent justification of its trimming rule.
4. **Validation criterion:** relative width error vs theory is dominated by estimator bias (8.4); recommend h(q)/τ(q)-level and baseline-width criteria.
5. **Surrogate scope:** shuffle only; phase-randomised surrogates would test linear-vs-nonlinear structure.
6. **Fit range policy across participants:** one fixed rule (e.g. fixed scale limits in samples or seconds) vs per-trial manual choice; group comparisons need identical settings.
7. **Unit/anisotropy** of the displacement signal.

---

## Appendix A — Independent reference implementation (matches LRydin to 3e-16)

```python
import numpy as np

def mfdfa_ref(x, scales, q, order=1):
    """Plain-loop MFDFA following Kantelhardt et al. (2002). q must not contain 0."""
    x = np.asarray(x, float)
    Y = np.cumsum(x - x.mean())                          # profile
    N = len(Y); q = np.asarray(q, float)
    Fq = np.empty((len(scales), len(q)))
    for a, s in enumerate(scales):
        ns = N // s
        segs = [Y[:ns*s].reshape(ns, s),                 # from the start
                Y[N - ns*s:].reshape(ns, s)]             # from the end
        t = np.arange(1, s + 1)
        F2 = []
        for S in segs:
            for seg in S:
                coef = np.polyfit(t, seg, order)
                F2.append(np.mean((seg - np.polyval(coef, t))**2))   # F²(ν, s)
        F2 = np.array(F2)
        for b, qq in enumerate(q):
            Fq[a, b] = np.mean(F2 ** (qq / 2)) ** (1 / qq)
    return Fq
```

Slope / spectrum helpers used for the checks:

```python
def slopes(F, scales, lo, hi):
    return np.array([np.polyfit(np.log(scales[lo:hi]), np.log(F[lo:hi, i]), 1)[0]
                     for i in range(F.shape[1])])

def spectrum(q, h):
    tau = q * h - 1
    alpha = np.gradient(tau, q)
    return tau, alpha, q * alpha - tau

def width(q, tau, qmax=None):
    alpha = np.gradient(tau, q)
    m = np.ones_like(q, bool) if qmax is None else (np.abs(q) <= qmax)
    return alpha[m].max() - alpha[m].min()
```

## Appendix B — Reproducible checks

```python
# pip install MFDFA==0.4.3
import numpy as np, warnings
from MFDFA import MFDFA, fgn
warnings.filterwarnings("ignore")

# B1. What the package's q-filter keeps for the app's default grid
q_req = np.linspace(-5, 5, 101)
q = q_req[(q_req < -.1) + (q_req > .1)]
print(q.size, q[q < 0][-1], q[q > 0][0])             # 99, -0.1999..., 0.1000...005

# B2. Package vs reference
x = np.random.default_rng(3).standard_normal(4000)
scales = np.unique(np.logspace(1, 3, 15).astype(int))
qq = np.array([-4., -2., 2., 4.])
_, F_pkg = MFDFA(x, lag=scales, q=qq, order=1)
print(np.max(np.abs(F_pkg - mfdfa_ref(x, scales, qq)) / F_pkg))        # ~1e-16

# B3. Binomial cascade (Kantelhardt 2002) and the app-style pipeline
def cascade(a, nmax):
    k = np.arange(2**nmax); n1 = np.array([bin(i).count("1") for i in k])
    return a**n1 * (1 - a)**(nmax - n1)

def pipeline(x, nlag=40):
    N = x.size
    lag = np.unique(np.logspace(np.log10(10), np.log10(N//4), nlag).astype(int))
    _, F = MFDFA(x, lag=lag, q=q_req, order=1)
    lo, hi = len(lag)//8, int(len(lag)/1.5)
    h = slopes(F, lag, lo, hi)
    return h, q * h - 1

p = 0.55
h, tau = pipeline(cascade(p, 16))
tau_th = -np.log2(p**q + (1 - p)**q)
print(width(q, tau), width(q, tau_th))                 # ≈ 0.207 vs 0.133
print(width(q, tau, 4.0), width(q, tau_th, 4.0))       # ≈ 0.175 vs 0.110

# B4. Monofractal width baseline (true width 0)
for N in (2**14, 2**16):
    w = []
    for seed in range(6):
        np.random.seed(seed); h, tau = pipeline(fgn(N, 0.7)); w.append(width(q, tau))
    print(N, np.mean(w), np.std(w))                    # ≈ 0.051 / 0.028

# B5. Negative-q damage from constant (interpolated) runs
rng = np.random.default_rng(1)
N = 6000
base = rng.gamma(shape=0.6, scale=0.02, size=N)
gap = base.copy()
for s0 in rng.choice(np.arange(100, N - 100, 250), 20, replace=False):
    gap[s0:s0 + 15] = gap[s0]                          # 15-sample constant-speed run
qt = np.array([-4., -2., 2., 4.])
lag = np.unique(np.logspace(1, np.log10(N // 4), 25).astype(int))
for name, sig in (("clean", base), ("with gaps", gap)):
    _, F = MFDFA(sig, lag=lag, q=qt, order=1)
    print(name, np.round(slopes(F, lag, 3, 20), 3))    # h(-4): 0.637 -> 0.818
```

## Appendix C — Notation map (the notation collision is real)

| Symbol | Meaning in this project |
|---|---|
| slope of DFA log–log line (q = 2), written α in the DFA part of the app text | scaling exponent of the *signal*; equals H for noise-like input, H + 1 for walk-like input |
| `h(q)` | generalised Hurst exponent: slope of `ln F_q(s)` vs `ln s` for each q (the slope **is** h(q)) |
| `H` | classical Hurst exponent; `h(2)` for noise-like input |
| `τ(q)` | mass exponent, `q·h(q) − 1` |
| `α` (spectrum) | singularity strength / Hölder exponent, `dτ/dq`; **different from the DFA slope α** |
| `f(α)` | singularity spectrum, `q·α − τ` |
| `Δα` | spectrum width, `α_max − α_min` (raw or robust) |
| `F²(ν,s)` | variance of the detrended residuals of segment ν at scale s |
| `F_q(s)` | q-th order fluctuation function at scale s |
