"""IAAFT surrogate behaviour (implementation-findings section 7).

1. Unit checks on engine.iaaft_surrogate (fGn H=0.7, N=4096):
   - exact value multiset preserved (zero tolerance);
   - final spectral error below the pinned threshold;
   - determinism: same seed -> identical surrogate and iteration count;
   - non-finite input raises ValueError;
   - iteration count within [1, max_iter].
2. Behavioural checks via engine.iaaft_surrogate_test (n=30, seed=5,
   standard harness pipeline):
   - p has the (1+k)/(n+1) form;
   - fGn H=0.7 (a linear process) is NOT significant;
   - cascade p=0.3, 14 levels IS significant -- its width comes from the
     nonlinear temporal ordering that IAAFT destroys while keeping the
     value multiset and (approximately) the linear spectrum.
3. Cost: wall time per surrogate, compared with one run_mfdfa call.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import (  # noqa: E402
    Check,
    engine,
    hq_and_spectrum,
    print_header,
    standard_run,
)
from MFDFA import fgn

N_SURROGATES = 30
SURROGATE_SEED = 5
IAAFT_SEED = 3

# Pinned from the first measured run (2026-11-21): fGn H=0.7 N=4096 converges
# to ~2.8e-8 .. 3.0e-8 mean squared amplitude error across seeds 3..42, in
# 37..66 iterations. Threshold = 1e-6 (~33x margin).
MAX_SPECTRAL_ERROR = 1e-6


def p_form_ok(c: "Check", label: str, p: float, n: int) -> int:
    k = p * (n + 1) - 1
    ok_int = bool(abs(k - round(k)) < 1e-9 and 0 <= round(k) <= n)
    ok_exact = bool(np.isclose((1 + round(k)) / (n + 1), p, rtol=0, atol=1e-12))
    c.ok(f"{label}: p has the (1+k)/(n+1) form",
         ok_int and ok_exact, f"p={p:.4f}, recovered k={round(k)}, n={n}")
    return int(round(k))


def run_iaaft_test(signal, n, seed):
    """Observed robust width + engine IAAFT test under the standard pipeline."""
    run = standard_run(signal)
    sp = hq_and_spectrum(run)
    pp = run["params"]
    mfdfa_params = (pp["lag_start"], pp["lag_stop"], pp["lag_num"],
                    pp["q_start"], pp["q_stop"], pp["q_num"], pp["order"])
    t0 = time.perf_counter()
    res = engine.iaaft_surrogate_test(
        signal, n, sp["width_robust"], mfdfa_params,
        run["fit_start"], run["fit_end"], seed=seed,
    )
    elapsed = time.perf_counter() - t0
    return run, sp, res, elapsed


def main() -> None:
    print_header("iaaft_test")
    c = Check("iaaft_test")

    # --- unit checks on the generator ---
    np.random.seed(11)
    y = fgn(4096, 0.7)
    surr, iterations, err = engine.iaaft_surrogate(y, seed=IAAFT_SEED)
    print(f"fGn H=0.7 N=4096: IAAFT surrogate -> iterations={iterations}, "
          f"final spectral error={err:.3e}")
    c.ok("exact value multiset preserved (zero tolerance)",
         np.array_equal(np.sort(surr), np.sort(y)),
         f"max|diff|={np.max(np.abs(np.sort(surr) - np.sort(y))):.3e}")
    c.ok("final spectral error below pinned threshold",
         err < MAX_SPECTRAL_ERROR,
         f"err={err:.3e} (threshold {MAX_SPECTRAL_ERROR:.0e})")
    surr2, iterations2, _ = engine.iaaft_surrogate(y, seed=IAAFT_SEED)
    c.ok("deterministic: same seed -> identical surrogate",
         np.array_equal(surr, surr2) and iterations == iterations2,
         f"iterations {iterations} vs {iterations2}")
    c.ok("iteration count within [1, max_iter]",
         1 <= iterations <= 500, f"iterations={iterations}, cap=500")
    raised_msg = None
    try:
        engine.iaaft_surrogate(np.array([1.0, np.nan, 2.0]), seed=IAAFT_SEED)
    except ValueError as e:
        raised_msg = str(e)
    c.ok("non-finite input raises ValueError", raised_msg is not None,
         repr(raised_msg) if raised_msg else "no exception raised")
    if raised_msg is not None:
        print(f"NaN input -> ValueError: {raised_msg}")

    # --- behavioural: fGn (linear process) must NOT be significant ---
    run, sp, res, dt_fgn = run_iaaft_test(y, N_SURROGATES, SURROGATE_SEED)
    mean, median, std, lo, hi, p, diag = res
    print(f"fGn H=0.7 N=4096: observed robust DA={sp['width_robust']:.4f} | "
          f"surrogate mean={mean:.4f} median={median:.4f} std={std:.4f} "
          f"95% interval=[{lo:.4f}, {hi:.4f}] p={p:.4f}")
    print(f"fGn IAAFT diagnostics: mean iterations={diag[0]:.2f}, "
          f"max iterations={diag[1]}, mean spectral error={diag[2]:.3e}, "
          f"capped={diag[3]}/{N_SURROGATES}")
    k = p_form_ok(c, "fGn", p, N_SURROGATES)
    c.ok("fGn (linear process) is NOT significant", p > 0.05,
         f"p={p:.4f} (k={k}, threshold 0.05)")

    # --- behavioural: cascade (nonlinear ordering) must be significant ---
    _, measure = engine.binomial_cascade(n_levels=14, p=0.3, seed=7)
    run_c, sp_c, res_c, dt_cas = run_iaaft_test(measure, N_SURROGATES, SURROGATE_SEED)
    mean_c, median_c, std_c, lo_c, hi_c, p_c, diag_c = res_c
    print(f"cascade p=0.3, 14 levels (N={run_c['N']}): observed robust "
          f"DA={sp_c['width_robust']:.4f} | surrogate mean={mean_c:.4f} "
          f"95% interval=[{lo_c:.4f}, {hi_c:.4f}] p={p_c:.4f}")
    print(f"cascade IAAFT diagnostics: mean iterations={diag_c[0]:.2f}, "
          f"max iterations={diag_c[1]}, mean spectral error={diag_c[2]:.3e}, "
          f"capped={diag_c[3]}/{N_SURROGATES}")
    k_c = p_form_ok(c, "cascade", p_c, N_SURROGATES)
    c.ok("cascade p=0.3 IS significant", p_c <= 0.05,
         f"p={p_c:.4f} (k={k_c}, threshold 0.05)")

    # --- cost: IAAFT test vs the MF-DFA pipeline it runs per surrogate ---
    pp = run["params"]
    t0 = time.perf_counter()
    engine.run_mfdfa(y, pp["lag_start"], pp["lag_stop"], pp["lag_num"],
                     pp["q_start"], pp["q_stop"], pp["q_num"], pp["order"])
    dt_run = time.perf_counter() - t0
    print(f"cost: IAAFT test {dt_fgn:.1f} s / {N_SURROGATES} surrogates = "
          f"{dt_fgn / N_SURROGATES:.2f} s per surrogate "
          f"(cascade {dt_cas / N_SURROGATES:.2f} s) | "
          f"one run_mfdfa = {dt_run:.2f} s")

    c.finish()


if __name__ == "__main__":
    main()
