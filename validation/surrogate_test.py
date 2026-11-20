"""Surrogate (shuffle) test behaviour (reference section 7).

1. p-value form, verified behaviourally: the engine computes
   p = (1 + k) / (n + 1) with k = #{surrogate widths >= observed}
   (mfdfa_engine.py:235). From a real engine run, k recovered as
   p*(n+1) - 1 must be an exact integer in [0, n], and p must equal
   (1+k)/(n+1) to floating point. A previous operator-precedence bug
   produced p ~ 2.0 (reference section 7) — this check catches that class.
2. Fixed seed, n=30 surrogates: fGn H=0.7 (monofractal) must NOT come out
   significant; the cascade p=0.3, 14 levels (true multifractality from
   temporal ordering) MUST (expected k=0 -> p = 1/31 ~ 0.032).
"""
import sys
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


def p_form_ok(c: "Check", label: str, p: float, n: int) -> int:
    k = p * (n + 1) - 1
    ok_int = bool(abs(k - round(k)) < 1e-9 and 0 <= round(k) <= n)
    ok_exact = bool(np.isclose((1 + round(k)) / (n + 1), p, rtol=0, atol=1e-12))
    c.ok(f"{label}: p has the (1+k)/(n+1) form",
         ok_int and ok_exact, f"p={p:.4f}, recovered k={round(k)}, n={n}")
    return int(round(k))


def run_surrogate(signal, n, seed):
    """Observed robust width + engine surrogate test under the standard pipeline."""
    run = standard_run(signal)
    sp = hq_and_spectrum(run)
    pp = run["params"]
    mfdfa_params = (pp["lag_start"], pp["lag_stop"], pp["lag_num"],
                    pp["q_start"], pp["q_stop"], pp["q_num"], pp["order"])
    res = engine.shuffled_surrogate_test(
        signal, n, sp["width_robust"], mfdfa_params,
        run["fit_start"], run["fit_end"], seed=seed,
    )
    return run, sp, res


def main() -> None:
    print_header("surrogate_test")
    print(f"n_surrogates={N_SURROGATES}, surrogate seed={SURROGATE_SEED} | "
          f"identity: (1+0)/(100+1) = {(1 + 0) / (100 + 1):.6f} (= 1/101)")
    c = Check("surrogate_test")

    # --- fGn: monofractal; width is finite-sample noise -> not significant ---
    np.random.seed(11)
    y = fgn(4096, 0.7)
    run, sp, res = run_surrogate(y, N_SURROGATES, SURROGATE_SEED)
    mean, median, std, lo, hi, p = res
    print(f"fGn H=0.7 N=4096: observed robust DA={sp['width_robust']:.4f} | "
          f"surrogate mean={mean:.4f} median={median:.4f} std={std:.4f} "
          f"95% interval=[{lo:.4f}, {hi:.4f}] p={p:.4f}")
    k = p_form_ok(c, "fGn", p, N_SURROGATES)
    c.ok("fGn (monofractal) is NOT significant", p > 0.05,
         f"p={p:.4f} (k={k}, threshold 0.05)")

    # --- cascade p=0.3: temporal ordering carries the multifractality ---
    _, measure = engine.binomial_cascade(n_levels=14, p=0.3, seed=7)
    run_c, sp_c, res_c = run_surrogate(measure, N_SURROGATES, SURROGATE_SEED)
    mean_c, median_c, std_c, lo_c, hi_c, p_c = res_c
    print(f"cascade p=0.3, 14 levels (N={run_c['N']}): observed robust "
          f"DA={sp_c['width_robust']:.4f} | surrogate mean={mean_c:.4f} "
          f"95% interval=[{lo_c:.4f}, {hi_c:.4f}] p={p_c:.4f}")
    k_c = p_form_ok(c, "cascade", p_c, N_SURROGATES)
    c.ok("cascade p=0.3 IS significant", p_c <= 0.05,
         f"p={p_c:.4f} (k={k_c}, threshold 0.05)")

    c.finish()


if __name__ == "__main__":
    main()
