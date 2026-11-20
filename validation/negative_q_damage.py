"""Negative-q behaviour on damaged signals (reference section 6, B5).

VERIFIED 2026-11-19: the reference doc (section 6) states the engine has an
s_min = max(order+2, zero_run+1) guard against exact-zero runs. No such guard
exists — mfdfa_engine.run_mfdfa (mfdfa_engine.py:74-90) contains no zero-run
logic and the installed package enforces only lag > order+1
(MFDFA.py:125-127). Until that changes:

  - clean spiky baseline (gamma-distributed, like B5) — asserted sane;
  - exact-zero run (held tracker positions): the profile is linear inside
    the run, order-1 detrending removes it exactly, F^2 collapses to
    exactly 0 and the negative-q F columns become 0.0 in the fit band —
    h(-4)/h(-2) are NaN. The app's actual defense line, the page-level
    fit-band gate (utils.pages_logic.get_valid_fitting_range), blocks
    this deterministically — ASSERTED;
  - constant-value runs (linear interpolation of coordinates -> constant
    speed): same failure mode, but the values are non-zero, F stays
    finite and positive, and the gate does NOT see it — measured and
    printed, no assert (B5 prior: h(-4) 0.637 -> 0.818).
"""
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import (  # noqa: E402
    Check,
    hq_and_spectrum,
    print_header,
    standard_run,
)
from utils.pages_logic import get_valid_fitting_range


def report(name: str, sp: dict[str, Any], run: dict[str, Any]):
    sel = run["dfa_mf"][run["fit_start"]:run["fit_end"], :]
    finite = bool(np.isfinite(sel).all())
    positive = bool((sel > 0).all())
    hs = {qv: sp["hq"][int(np.argmin(np.abs(run["q_list"] - qv)))]
          for qv in (-4.0, -2.0, 2.0, 4.0)}
    print(f"{name}: F finite={finite}, F>0={positive} | "
          + " | ".join(f"h({qv:>4.0f})={hs[qv]:.3f}" for qv in (-4.0, -2.0, 2.0, 4.0)))
    return finite, positive, hs


def main() -> None:
    print_header("negative_q_damage")
    N = 6000
    rng = np.random.default_rng(1)  # same construction as reference B5
    base = rng.gamma(shape=0.6, scale=0.02, size=N)
    print(f"signal: gamma(shape=0.6, scale=0.02), N={N}, default_rng(1)")
    print("guard status: NO s_min/zero-run guard exists in the engine "
          "(mfdfa_engine.py:74-90) or the package (MFDFA.py:125-127); "
          "the app's only defense is the page-level fit-band validity gate.")

    c = Check("negative_q_damage")

    # --- clean baseline: asserted ---
    run0 = standard_run(base)
    sp0 = hq_and_spectrum(run0)
    f0, p0, h0 = report("clean baseline", sp0, run0)
    c.ok("clean baseline: F finite in the fit band", f0)
    c.ok("clean baseline: F > 0 in the fit band", p0)
    c.ok("clean baseline: 0 < h(q) < 1.5 at q=-4,-2,2,4",
         all(0.0 < h0[qv] < 1.5 for qv in h0))

    # --- exact-zero run (held positions): damage is real, but the app's
    # page-level fit-band gate blocks it deterministically (the profile is
    # linear inside the run, order-1 detrending removes it exactly, F^2 is
    # exactly 0, so the negative-q F columns collapse to 0.0 in the fit
    # band). This is the app's actual zero-run defense — asserted.
    zero = base.copy()
    zero[2000:2500] = 0.0
    run_z = standard_run(zero)
    sp_z = hq_and_spectrum(run_z)
    report("zero-run (500 samples)", sp_z, run_z)
    gate_z = get_valid_fitting_range(run_z["dfa_mf"], run_z["fit_start"], run_z["fit_end"])
    h_z_m4 = sp_z["hq"][int(np.argmin(np.abs(run_z["q_list"] + 4)))]
    c.ok("zero-run: the app's fit-band gate BLOCKS the signal "
         "(negative-q F collapses to 0, h(-4) not finite)",
         (not gate_z) and not np.isfinite(h_z_m4),
         f"gate={'BLOCK' if not gate_z else 'ALLOW'}, h(-4)={h_z_m4}")

    # --- constant-value runs (interpolated-like): measured, not asserted ---
    const = base.copy()
    pos = rng.choice(np.arange(100, N - 100, 250), 20, replace=False)
    for s0 in pos:
        const[s0:s0 + 15] = const[s0]
    run_c = standard_run(const)
    sp_c = hq_and_spectrum(run_c)
    report("constant-runs (20 x 15 samples)", sp_c, run_c)
    gate_c = get_valid_fitting_range(run_c["dfa_mf"], run_c["fit_start"], run_c["fit_end"])
    h_c_m4 = sp_c["hq"][int(np.argmin(np.abs(run_c["q_list"] + 4)))]
    print(f"  app fit-band gate would {'BLOCK' if not gate_c else 'ALLOW'} this signal "
          f"(B5 prior: h(-4) 0.637 -> 0.818; measured here: "
          f"{h0[-4.0]:.3f} -> {h_c_m4:.3f})")

    c.finish()


if __name__ == "__main__":
    main()
