"""Slope conventions: subtract_one on the fOU (generated) path vs the upload path.

The engine's fOU (generate_fou) is walk-like on the analysed scales (the
mean-reversion crossover 1/theta sits far above the fit band), so its DFA
slope is ~H+1 and the fOU path uses subtract_one=True. fGn models the
uploaded (increment-like) series: slope ~ H, no subtraction.

Checks:
  1. fOU path with subtract_one=True recovers the generated H (3 seeds).
  2. fGn with subtract_one=False recovers its true H (3 seeds).
  3. Applying -1 to the fGn slope lands OUTSIDE (0,1) — the practical guard
     that separates the two conventions.
  4. Source-level contract: pages/dfa.py passes subtract_one=False exactly
     once (upload branch, pages/dfa.py:85) and the generated branch relies
     on the engine default (True).

fOU parameters are shrunk (t_final=20, delta_t=0.001 -> N=20000) so the run
stays fast; the fit band (largest fitted lag ~600 samples) is well inside the
walk-like regime (crossover 1/theta = 3.33 time units = 3333 samples).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import (  # noqa: E402
    REPO_ROOT,
    Check,
    engine,
    print_header,
    standard_run,
)
from MFDFA import fgn

H_TRUE = 0.7
SEEDS = (0, 1, 2)
FOU_TOL = 0.15  # adjusted after engine re-measurement; see script output
FGN_TOL = 0.10


def main() -> None:
    print_header("fou_subtract_one")
    c = Check("fou_subtract_one")

    # --- fOU: generated-signal path (subtract_one=True) ---
    fou_h = []
    for s in SEEDS:
        np.random.seed(s)  # generate_fou draws fgn (legacy global RNG)
        _, y = engine.generate_fou(
            t_final=20, delta_t=0.001, theta=0.3, sigma=0.1, H=H_TRUE
        )
        run = standard_run(y)
        dfa = engine.get_dfa(dfa_mf=run["dfa_mf"], q_list=run["q_list"])
        slope, _, h_fit, r2 = engine.fit_dfa_exponent(
            lag_mf=run["lag_mf"], dfa=dfa,
            fit_start=run["fit_start"], fit_end=run["fit_end"], subtract_one=True,
        )
        fou_h.append(h_fit)
        print(f"fOU seed={s}: N={run['N']}, slope={slope:.3f} (~H+1), "
              f"H=slope-1={h_fit:.3f}, R2={r2:.4f}")
    c.ok(f"fOU path (subtract_one=True) recovers H={H_TRUE} within +/-{FOU_TOL}",
         all(abs(h - H_TRUE) < FOU_TOL for h in fou_h),
         f"H values {np.round(fou_h, 3).tolist()}")

    # --- fGn: upload-like path (subtract_one=False) ---
    fgn_h, fgn_wrong = [], []
    for s in SEEDS:
        np.random.seed(s)
        y = fgn(4096, H_TRUE)
        run = standard_run(y)
        dfa = engine.get_dfa(dfa_mf=run["dfa_mf"], q_list=run["q_list"])
        slope, _, h_fit, _ = engine.fit_dfa_exponent(
            lag_mf=run["lag_mf"], dfa=dfa,
            fit_start=run["fit_start"], fit_end=run["fit_end"], subtract_one=False,
        )
        _, _, h_wrong, _ = engine.fit_dfa_exponent(
            lag_mf=run["lag_mf"], dfa=dfa,
            fit_start=run["fit_start"], fit_end=run["fit_end"], subtract_one=True,
        )
        fgn_h.append(h_fit)
        fgn_wrong.append(h_wrong)
        print(f"fGn seed={s}: slope={slope:.3f} (~H), H={h_fit:.3f} "
              f"(no correction), wrongly corrected H={h_wrong:.3f}")
    c.ok(f"upload-like fGn (subtract_one=False) recovers H={H_TRUE} within +/-{FGN_TOL}",
         all(abs(h - H_TRUE) < FGN_TOL for h in fgn_h),
         f"H values {np.round(fgn_h, 3).tolist()}")
    c.ok("applying -1 to the fGn slope lands outside (0,1)",
         all(not (0.0 < h < 1.0) for h in fgn_wrong),
         f"wrongly corrected H {np.round(fgn_wrong, 3).tolist()}")

    # --- source-level contract: pages/dfa.py ---
    src = (REPO_ROOT / "pages" / "dfa.py").read_text()
    n_false = src.count("subtract_one=False")
    n_any = src.count("subtract_one")
    c.ok("pages/dfa.py: upload branch passes subtract_one=False; generated branch uses default True",
         n_false == 1 and n_any == 1,
         f"'subtract_one' occurrences: {n_any}, 'subtract_one=False': {n_false} "
         "(expected 1 and 1)")
    if not (n_false == 1 and n_any == 1):
        for i, line in enumerate(src.splitlines(), start=1):
            if "subtract_one" in line:
                print(f"  pages/dfa.py:{i}: {line.strip()}", file=sys.stderr)

    c.finish()


if __name__ == "__main__":
    main()
