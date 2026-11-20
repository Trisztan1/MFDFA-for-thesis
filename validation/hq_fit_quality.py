"""Test for the compute_hq R² append bug (mfdfa_engine.py:129).

R1-A — Normal inputs: must PASS on both buggy and fixed code.
R1-B — Degenerate columns: must FAIL (exit 1) on the buggy code
       (conditional expression discards NaN instead of appending it);
       must PASS (exit 0) on the fixed code.

R1-B uses the real lag_mf, q_list, fit_start and fit_end from the A(i) fGn
run, replacing only the F matrix with a controlled one containing three
degenerate columns (constant, NaN, zero) alongside healthy power-law columns.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import Check, engine, print_header, standard_run
from MFDFA import fgn

# Fixed seeds (printed in the output per harness convention)
SEED_FGN = 3        # np.random.seed for fgn (legacy global RNG, fgn.py:60)
SEED_CASCADE = 7    # binomial_cascade seed
SEED_CTRL = 42      # default_rng for the controlled F matrix

# Column indices in the controlled F matrix (must not collide)
COL_CONSTANT = 2    # zero-variance log-log line
COL_NAN = 3         # NaN input
COL_ZERO = 4        # 0.0 → log(0) = -inf
COL_HEALTHY = (0, 1, 5)  # spot-checked healthy columns


def main() -> None:
    print_header("hq_fit_quality")
    print(f"seeds: fgn={SEED_FGN} (np.random.seed), cascade={SEED_CASCADE}, "
          f"controlled-F={SEED_CTRL} (default_rng)")
    c = Check("hq_fit_quality")

    # ---- A. Normal inputs (PASS on both buggy and fixed code) ----

    # A(i): fGn H=0.7, N=4096
    np.random.seed(SEED_FGN)
    y_fgn = fgn(4096, 0.7)
    run_fgn = standard_run(y_fgn)
    hq_fgn, r2_fgn = engine.compute_hq(
        run_fgn["lag_mf"], run_fgn["dfa_mf"], run_fgn["q_list"],
        run_fgn["fit_start"], run_fgn["fit_end"],
    )
    n_q = len(run_fgn["q_list"])
    print(f"fGn H=0.7 N=4096: len(hq)={len(hq_fgn)}, len(r2)={len(r2_fgn)}, len(q)={n_q}")
    print(f"  R² range: {np.nanmin(r2_fgn):.4f}..{np.nanmax(r2_fgn):.4f}")
    c.ok("fGn: len(hq) == len(q_list)", len(hq_fgn) == n_q,
         f"{len(hq_fgn)} vs {n_q}")
    c.ok("fGn: len(r2) == len(q_list)", len(r2_fgn) == n_q,
         f"{len(r2_fgn)} vs {n_q}")
    c.ok("fGn: all R² finite and in (0, 1+1e-12]",
         bool(np.all(np.isfinite(r2_fgn)) and np.all(r2_fgn > 0)
              and np.all(r2_fgn <= 1 + 1e-12)),
         f"R² range [{np.nanmin(r2_fgn):.4f}, {np.nanmax(r2_fgn):.4f}]")

    # A(ii): binomial cascade p=0.3, 14 levels
    _, measure = engine.binomial_cascade(n_levels=14, p=0.3, seed=SEED_CASCADE)
    run_cas = standard_run(measure)
    hq_cas, r2_cas = engine.compute_hq(
        run_cas["lag_mf"], run_cas["dfa_mf"], run_cas["q_list"],
        run_cas["fit_start"], run_cas["fit_end"],
    )
    print(f"cascade p=0.3, 14 levels: len(hq)={len(hq_cas)}, len(r2)={len(r2_cas)}, "
          f"len(q)={len(run_cas['q_list'])}")
    print(f"  R² range: {np.nanmin(r2_cas):.4f}..{np.nanmax(r2_cas):.4f}")
    c.ok("cascade: len(hq) == len(q_list)", len(hq_cas) == len(run_cas["q_list"]),
         f"{len(hq_cas)} vs {len(run_cas['q_list'])}")
    c.ok("cascade: len(r2) == len(q_list)", len(r2_cas) == len(run_cas["q_list"]),
         f"{len(r2_cas)} vs {len(run_cas['q_list'])}")
    c.ok("cascade: all R² finite and in (0, 1+1e-12]",
         bool(np.all(np.isfinite(r2_cas)) and np.all(r2_cas > 0)
              and np.all(r2_cas <= 1 + 1e-12)),
         f"R² range [{np.nanmin(r2_cas):.4f}, {np.nanmax(r2_cas):.4f}]")

    # ---- B. Degenerate columns (the bug catchment) ----
    # Uses the REAL lag_mf, q_list, fit_start, fit_end from the A(i) fGn run;
    # replaces only the F matrix with a controlled one.
    n_rows, n_cols = run_fgn["dfa_mf"].shape
    rng = np.random.default_rng(SEED_CTRL)

    # Healthy columns: clean power law (slope ~0.7) with ±2% noise → high R²
    F_ctrl = np.empty((n_rows, n_cols))
    healthy_mask = np.ones(n_cols, dtype=bool)
    healthy_mask[[COL_CONSTANT, COL_NAN, COL_ZERO]] = False
    for i in np.where(healthy_mask)[0]:
        F_ctrl[:, i] = (run_fgn["lag_mf"] ** 0.7
                        * rng.uniform(0.98, 1.02, size=n_rows))

    # Degenerate columns
    F_ctrl[:, COL_CONSTANT] = 0.75     # constant: zero variance in log
    F_ctrl[:, COL_NAN] = np.nan        # NaN input
    F_ctrl[:, COL_ZERO] = 0.0          # log(0) = -inf

    hq_ctrl, r2_ctrl = engine.compute_hq(
        run_fgn["lag_mf"], F_ctrl, run_fgn["q_list"],
        run_fgn["fit_start"], run_fgn["fit_end"],
    )

    print(f"\ncontrolled F ({n_rows} scales x {n_cols} q), "
          f"real lag_mf/q_list from the fGn run, "
          f"fit band [{run_fgn['fit_start']}:{run_fgn['fit_end']}]")
    print(f"  len(hq)={len(hq_ctrl)}, len(r2)={len(r2_ctrl)}, len(q)={n_q}")
    print(f"  degenerate columns: {COL_CONSTANT}=constant, {COL_NAN}=NaN, {COL_ZERO}=zero")

    # Length assertions — these FAIL on buggy code and gate the column checks
    len_ok = len(r2_ctrl) == n_q
    c.ok("controlled: len(hq) == len(q_list)", len(hq_ctrl) == n_q,
         f"{len(hq_ctrl)} vs {n_q}")
    c.ok("controlled: len(r2) == len(q_list)", len_ok,
         f"{len(r2_ctrl)} vs {n_q}")

    if not len_ok:
        # Buggy code: the length mismatch already proves the bug.
        # Print the surviving r2 vector so the failure is visible, then
        # exit cleanly (no IndexError crash).
        print(f"  BUG: r2 has {len(r2_ctrl)} entries but q_list has {n_q} "
              f"— {n_q - len(r2_ctrl)} silently dropped")
        print(f"  r2  = {np.round(r2_ctrl, 4).tolist()}")
        print(f"  NaN count in surviving r2: {int(np.isnan(r2_ctrl).sum())}")
        c.finish()
        return

    # Column-level assertions — only reached when lengths match (fixed code)
    c.ok(f"col {COL_CONSTANT} (constant): R² is NaN",
         bool(np.isnan(r2_ctrl[COL_CONSTANT])),
         f"r2[{COL_CONSTANT}]={r2_ctrl[COL_CONSTANT]}")
    c.ok(f"col {COL_NAN} (NaN input): hq is NaN",
         bool(np.isnan(hq_ctrl[COL_NAN])),
         f"hq[{COL_NAN}]={hq_ctrl[COL_NAN]}")
    c.ok(f"col {COL_NAN} (NaN input): R² is NaN",
         bool(np.isnan(r2_ctrl[COL_NAN])),
         f"r2[{COL_NAN}]={r2_ctrl[COL_NAN]}")
    c.ok(f"col {COL_ZERO} (zero): R² is NaN",
         bool(np.isnan(r2_ctrl[COL_ZERO])),
         f"r2[{COL_ZERO}]={r2_ctrl[COL_ZERO]}")

    # Healthy columns: spot-check that they give normal finite R²
    for idx in COL_HEALTHY:
        val = r2_ctrl[idx]
        ok = bool(np.isfinite(val) and val > 0 and val <= 1 + 1e-12)
        c.ok(f"col {idx} (healthy): R² is normal finite", ok,
             f"r2[{idx}]={val:.4f}")

    # Last column (high index) — confirms no off-by-one at the array end
    idx = n_cols - 1
    val = r2_ctrl[idx]
    ok = bool(np.isfinite(val) and val > 0 and val <= 1 + 1e-12)
    c.ok(f"col {idx} (healthy, last): R² is normal finite", ok,
         f"r2[{idx}]={val:.4f}")

    c.finish()


if __name__ == "__main__":
    main()
