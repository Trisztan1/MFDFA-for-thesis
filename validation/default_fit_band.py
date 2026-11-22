"""Default fit band s >= 10 (engine-review F4) + fOU default-band check (F8).

Pre-registered expectations:
  * negative control: the page's own cascade demo (14 levels, p=0.25,
    seed 0), on the default MF-DFA grid, is BLOCKED by the fit gate when
    the band starts at the first scale (fit_start = 0);
  * the default band (utils.pages_logic.default_fit_start: first scale
    >= 10) passes the same gate;
  * the fOU demo keeps |H - 0.7| < 0.15 on the app-default DFA band
    (FOU_TOL from validation/fou_subtract_one.py);
  * fGn upload-path sanity keeps |H - 0.7| < 0.10 (FGN_TOL).

The before/after numbers (fit_start=0 vs default band) are printed for the
demo signals and, when present, two real gaze series under docs/sample_data/
(reporting only; the section is skipped cleanly when the local data is
absent, so the script stays exit-0 on a fresh clone).

No Streamlit runtime is needed: only the pure helpers
default_fit_start / get_valid_fitting_range are called.
"""
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import (  # noqa: E402
    Check,
    engine,
    hq_and_spectrum,
    print_header,
)
from utils import pages_logic as pl  # noqa: E402
from MFDFA import fgn  # noqa: E402

H_TRUE = 0.7
SEEDS = (0, 1, 2)
FOU_TOL = 0.15  # same criterion as validation/fou_subtract_one.py:38
FGN_TOL = 0.10  # validation/fou_subtract_one.py:39

# The interactive pages' widget defaults (utils/pages_logic.py).
# Any-typed like _common.standard_params: the widgets pass untyped values.
APP_MF: dict[str, Any] = dict(lag_start=0.5, lag_stop=3.6, lag_num=100,
                              q_start=-5.0, q_stop=5.0, q_num=101, order=1)
APP_DFA: dict[str, Any] = dict(lag_start=0.5, lag_stop=3.0, lag_num=100)

SAMPLE_ROOT = Path(__file__).resolve().parent.parent / "docs" / "sample_data"
SAMPLE_SERIES = [("2_v.sz.", "puzzle_03"), ("3_v.sz.", "puzzle_03")]


def default_start(lag_mf):
    return pl.default_fit_start(lag_mf, max(0, len(lag_mf) - 5))


def mf_line(label, lag_mf, dfa_mf, q_list, fit_start, fit_end):
    if fit_start >= fit_end:
        return f"{label}: skipped (fit_start={fit_start} >= fit_end={fit_end})"
    valid = pl.get_valid_fitting_range(dfa_mf, fit_start, fit_end)
    sp = hq_and_spectrum({"lag_mf": lag_mf, "dfa_mf": dfa_mf,
                          "q_list": q_list,
                          "fit_start": fit_start, "fit_end": fit_end})
    hq = sp["hq"]

    def h_at(qv):
        return float(hq[int(np.argmin(np.abs(q_list - qv)))])

    r2 = np.asarray(sp["r2"], dtype=float)
    r2_min = float(np.nanmin(r2)) if np.isfinite(r2).any() else float("nan")
    band = f"s={lag_mf[fit_start]:.0f}->{lag_mf[fit_end - 1]:.0f}"
    return (f"{label}: band {band} | gate={'OK' if valid else 'BLOCKED'} | "
            f"h(-4)={h_at(-4):.3f} h(-2)={h_at(-2):.3f} "
            f"h(2)={h_at(2):.3f} h(4)={h_at(4):.3f} | "
            f"width raw={sp['width_raw']:.3f} robust={sp['width_robust']:.3f} | "
            f"min R2={r2_min:.3f}")


def dfa_line(label, lag_mf, dfa, fit_start, fit_end, subtract_one):
    if fit_start >= fit_end:
        return f"{label}: skipped (fit_start={fit_start} >= fit_end={fit_end})"
    slope, _, H, r2 = engine.fit_dfa_exponent(
        lag_mf=lag_mf, dfa=dfa, fit_start=fit_start, fit_end=fit_end,
        subtract_one=subtract_one)
    band = f"s={lag_mf[fit_start]:.0f}->{lag_mf[fit_end - 1]:.0f}"
    return f"{label}: band {band} | H={H:.3f} slope={slope:.3f} R2={r2:.4f}"


def mf_rows(tag, signal):
    lag_mf, dfa_mf, q_list = engine.run_mfdfa(signal, **APP_MF)
    fit_end = len(lag_mf) - 1
    return [mf_line(f"{tag} [old]", lag_mf, dfa_mf, q_list, 0, fit_end),
            mf_line(f"{tag} [new]", lag_mf, dfa_mf, q_list,
                    default_start(lag_mf), fit_end)]


def dfa_rows(tag, signal, subtract_one):
    lag_mf, dfa_mf, q_list = engine.run_mfdfa(signal, **APP_DFA)
    dfa = engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)
    fit_end = len(lag_mf) - 1
    return [dfa_line(f"{tag} [old]", lag_mf, dfa, 0, fit_end, subtract_one),
            dfa_line(f"{tag} [new]", lag_mf, dfa, default_start(lag_mf),
                     fit_end, subtract_one)]


def main() -> None:
    print_header("default_fit_band")
    c = Check("default_fit_band")

    # --- pre-registered: the page's own cascade demo ---
    _, measure = engine.binomial_cascade(n_levels=14, p=0.25, seed=0)
    lag_mf, dfa_mf, q_list = engine.run_mfdfa(measure, **APP_MF)
    fit_end = len(lag_mf) - 1
    start = default_start(lag_mf)
    old_valid = bool(pl.get_valid_fitting_range(dfa_mf, 0, fit_end))
    new_valid = bool(pl.get_valid_fitting_range(dfa_mf, start, fit_end))
    print(f"cascade demo (14 levels, p=0.25, seed 0): {len(lag_mf)} lags, "
          f"max lag {lag_mf[-1]}, first lag >= 10 at index {start} "
          f"(s={lag_mf[start]})")
    print(f"  fit_start=0      -> gate {'OK' if old_valid else 'BLOCKED'}")
    print(f"  default (idx {start:2d})  -> gate {'OK' if new_valid else 'BLOCKED'}")
    c.ok("negative control: the old default band (fit_start=0) is blocked",
         not old_valid,
         "gate BLOCKED at fit_start=0 - documents engine F4")
    c.ok("default band (first scale >= 10) passes the fit gate",
         new_valid, f"fit_start={start}, fit_end={fit_end}")
    c.ok("default start is the first scale >= 10",
         bool(lag_mf[start] >= 10 and (start == 0 or lag_mf[start - 1] < 10)),
         f"index {start} -> s={lag_mf[start]}")

    # --- fOU default-band check (engine F8) ---
    fou_h = []
    for seed in SEEDS:
        np.random.seed(seed)
        _, y = engine.generate_fou(t_final=20, delta_t=0.001, theta=0.3,
                                   sigma=0.1, H=H_TRUE)
        lag_mf, dfa_mf, q_list = engine.run_mfdfa(y, **APP_DFA)
        start = default_start(lag_mf)
        fit_end = len(lag_mf) - 1
        dfa = engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)
        slope, _, h_fit, r2 = engine.fit_dfa_exponent(
            lag_mf=lag_mf, dfa=dfa, fit_start=start, fit_end=fit_end,
            subtract_one=True)
        fou_h.append(h_fit)
        print(f"fOU seed={seed}: band s={lag_mf[start]:.0f}->"
              f"{lag_mf[fit_end - 1]:.0f}, H=slope-1={h_fit:.3f}, R2={r2:.4f}")
    c.ok(f"fOU keeps H={H_TRUE} within +/-{FOU_TOL} on the app-default band",
         all(abs(h - H_TRUE) < FOU_TOL for h in fou_h),
         f"H values {np.round(fou_h, 3).tolist()}")

    # --- fGn upload-path sanity ---
    fgn_h = []
    for seed in SEEDS:
        np.random.seed(seed)
        y = fgn(4096, H_TRUE)
        lag_mf, dfa_mf, q_list = engine.run_mfdfa(y, **APP_DFA)
        start = default_start(lag_mf)
        fit_end = len(lag_mf) - 1
        dfa = engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)
        slope, _, h_fit, r2 = engine.fit_dfa_exponent(
            lag_mf=lag_mf, dfa=dfa, fit_start=start, fit_end=fit_end,
            subtract_one=False)
        fgn_h.append(h_fit)
        print(f"fGn seed={seed}: band s={lag_mf[start]:.0f}->"
              f"{lag_mf[fit_end - 1]:.0f}, H={h_fit:.3f}, R2={r2:.4f}")
    c.ok(f"fGn upload-path keeps H={H_TRUE} within +/-{FGN_TOL} on the app-default band",
         all(abs(h - H_TRUE) < FGN_TOL for h in fgn_h),
         f"H values {np.round(fgn_h, 3).tolist()}")

    # --- before/after numbers (reporting only) ---
    print("\n-- before/after: fit_start=0 vs default band (app grids) --")
    np.random.seed(11)
    demo_fgn = fgn(4096, H_TRUE)
    for tag, sig in (("cascade demo", measure), ("fGn H=0.7", demo_fgn)):
        for row in mf_rows(tag, sig):
            print(row)
        for row in dfa_rows(tag, sig, subtract_one=False):
            print(row)

    print("\n-- real series (reporting only; skipped when absent) --")
    for participant, puzzle in SAMPLE_SERIES:
        path = SAMPLE_ROOT / participant / f"{puzzle}.csv"
        if not path.exists():
            print(f"{participant}/{puzzle}.csv: absent -> skipped")
            continue
        df = pd.read_csv(path)
        if df.shape[1] != 1 or len(df) < 8:
            print(f"{participant}/{puzzle}.csv: not a single usable column -> skipped")
            continue
        signal = df.to_numpy().astype(float).ravel()
        print(f"\n{participant}{puzzle}.csv (N={signal.size})")
        for row in mf_rows("  MF-DFA", signal):
            print(row)
        for row in dfa_rows("  DFA", signal, subtract_one=False):
            print(row)

    c.finish()


if __name__ == "__main__":
    main()
