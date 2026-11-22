"""IAAFT surrogate behaviour (implementation-findings section 7).

1. Unit checks on engine.iaaft_surrogate (fGn H=0.7, N=4096):
   - exact value multiset preserved (zero tolerance);
   - relative spectral error below the pinned threshold;
   - determinism: same seed -> identical surrogate, iterations, error, reason;
   - non-finite input raises ValueError;
   - iteration count within [1, max_iter];
   - stop reason is the true mechanism: seed 3 converges at the pinned
     iteration on "tolerance"; a tighter cap gives "cap";
   - the F5 edge case: max_iter set exactly to the pinned convergence
     iteration must count as the stopping rule, not as capped.
2. Behavioural checks via engine.iaaft_surrogate_test (n=30, seed=5,
   standard harness pipeline):
   - the six width statistics are byte-identical to the pre-change values
     (captured before the diagnostics change; p fGn=25/31, cascade=1/31);
   - fGn H=0.7 (a linear process) is NOT significant;
   - cascade p=0.3, 14 levels IS significant;
   - diagnostics are informative: fGn converges with a tiny relative
     spectral error, the cascade stops on the tolerance plateau with a
     large one (IAAFT review F1) -- pinned so the difference stays visible.
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

# Pinned from the first measured run with the diagnostics change
# (2026-11-22): fGn H=0.7 N=4096, seed 3 converges at iteration 51 on the
# "tolerance" rule with relative spectral error 8.2e-7. Threshold = 1e-5
# (~12x margin).
MAX_REL_SPECTRAL_ERROR = 1e-5
CONVERGENCE_ITER = 51
CONVERGENCE_REASON = "tolerance"

# Full-precision reprs captured from the engine BEFORE the R1 diagnostics
# change (same seeds, standard harness pipeline). The diagnostics change is
# reporting-only, so these must stay byte-identical.
EXPECTED_FGN = [
    "0.05039092604199815", "0.04875894232227118", "0.022067784905532743",
    "0.019880355787205147", "0.09579943724456229", "0.8387096774193549",
]
EXPECTED_CASCADE = [
    "0.9794787437834299", "0.9806385251246499", "0.16273502432347575",
    "0.7091116593288517", "1.260941173591316", "0.03225806451612903",
]


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


def print_diagnostics(label: str, diag, n: int) -> None:
    n_rank, n_tol, n_cap = diag[4]
    print(f"{label} IAAFT diagnostics: mean iterations={diag[0]:.2f}, "
          f"max iterations={diag[1]}, mean rel. spectral error={diag[2]:.3e}, "
          f"max rel. spectral error={diag[3]:.3e}, stop counts "
          f"rank_fixed_point={n_rank}, tolerance={n_tol}, capped={n_cap}/{n}")


def main() -> None:
    print_header("iaaft_test")
    c = Check("iaaft_test")

    # --- unit checks on the generator ---
    np.random.seed(11)
    y = fgn(4096, 0.7)
    surr, iterations, rel_err, reason = engine.iaaft_surrogate(y, seed=IAAFT_SEED)
    print(f"fGn H=0.7 N=4096: IAAFT surrogate -> iterations={iterations}, "
          f"relative spectral error={rel_err:.3e}, stop reason={reason}")
    c.ok("exact value multiset preserved (zero tolerance)",
         np.array_equal(np.sort(surr), np.sort(y)),
         f"max|diff|={np.max(np.abs(np.sort(surr) - np.sort(y))):.3e}")
    c.ok("relative spectral error below pinned threshold",
         rel_err < MAX_REL_SPECTRAL_ERROR,
         f"rel err={rel_err:.3e} (threshold {MAX_REL_SPECTRAL_ERROR:.0e})")
    surr2, iterations2, rel_err2, reason2 = engine.iaaft_surrogate(y, seed=IAAFT_SEED)
    c.ok("deterministic: same seed -> identical surrogate, error and reason",
         np.array_equal(surr, surr2) and iterations == iterations2
         and rel_err == rel_err2 and reason == reason2,
         f"iterations {iterations} vs {iterations2}, reasons {reason} vs {reason2}")
    c.ok("iteration count within [1, max_iter]",
         1 <= iterations <= 500, f"iterations={iterations}, cap=500")
    c.ok("stop reason is the pinned stopping rule (not cap)",
         iterations == CONVERGENCE_ITER and reason == CONVERGENCE_REASON,
         f"iterations={iterations} (pinned {CONVERGENCE_ITER}), "
         f"reason={reason} (pinned {CONVERGENCE_REASON})")
    _, capped_iter, _, capped_reason = engine.iaaft_surrogate(
        y, seed=IAAFT_SEED, max_iter=10)
    c.ok("a tighter cap stops on 'cap'",
         capped_iter == 10 and capped_reason == "cap",
         f"iterations={capped_iter}, reason={capped_reason}")
    _, edge_iter, edge_rel, edge_reason = engine.iaaft_surrogate(
        y, seed=IAAFT_SEED, max_iter=CONVERGENCE_ITER)
    c.ok("F5 edge: converging exactly at max_iter is NOT counted as capped",
         edge_iter == CONVERGENCE_ITER and edge_reason == CONVERGENCE_REASON,
         f"iterations={edge_iter} == max_iter, reason={edge_reason}")
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
    print_diagnostics("fGn", diag, N_SURROGATES)
    got = [repr(float(v)) for v in res[:6]]
    c.ok("fGn: six width statistics byte-identical to the pre-change values",
         got == EXPECTED_FGN,
         "reprs match" if got == EXPECTED_FGN else f"got {got}")
    k = p_form_ok(c, "fGn", p, N_SURROGATES)
    c.ok("fGn (linear process) is NOT significant", p > 0.05,
         f"p={p:.4f} (k={k}, threshold 0.05)")
    c.ok("fGn diagnostics: no capped surrogates",
         diag[4][2] == 0 and sum(diag[4]) == N_SURROGATES,
         f"stop counts {diag[4]}")
    c.ok("fGn diagnostics: tiny relative spectral error",
         diag[2] < MAX_REL_SPECTRAL_ERROR,
         f"mean rel err={diag[2]:.3e}, max={diag[3]:.3e}")

    # --- behavioural: cascade (nonlinear ordering) must be significant ---
    _, measure = engine.binomial_cascade(n_levels=14, p=0.3, seed=7)
    run_c, sp_c, res_c, dt_cas = run_iaaft_test(measure, N_SURROGATES, SURROGATE_SEED)
    mean_c, median_c, std_c, lo_c, hi_c, p_c, diag_c = res_c
    print(f"cascade p=0.3, 14 levels (N={run_c['N']}): observed robust "
          f"DA={sp_c['width_robust']:.4f} | surrogate mean={mean_c:.4f} "
          f"95% interval=[{lo_c:.4f}, {hi_c:.4f}] p={p_c:.4f}")
    print_diagnostics("cascade", diag_c, N_SURROGATES)
    got_c = [repr(float(v)) for v in res_c[:6]]
    c.ok("cascade: six width statistics byte-identical to the pre-change values",
         got_c == EXPECTED_CASCADE,
         "reprs match" if got_c == EXPECTED_CASCADE else f"got {got_c}")
    k_c = p_form_ok(c, "cascade", p_c, N_SURROGATES)
    c.ok("cascade p=0.3 IS significant", p_c <= 0.05,
         f"p={p_c:.4f} (k={k_c}, threshold 0.05)")
    c.ok("cascade diagnostics: large relative spectral error (IAAFT F1)",
         diag_c[2] > 0.05,
         f"mean rel err={diag_c[2]:.3f}, max={diag_c[3]:.3f} -- the stopping "
         "rules accept a plateau far from the target spectrum")

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
