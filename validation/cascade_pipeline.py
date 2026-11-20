"""Multifractal ground truth: binomial cascade vs closed-form theory.

Reference: docs/references/mfdfa_app_review_reference.md sections 8.3-8.4, B3.
Theory (Kantelhardt 2002): tau(q) = -log2(p^q + (1-p)^q), h(q) = (1 + tau)/q,
compared against the engine's empirical tau = q*h - 1 and the engine's own
finite-q theoretical spectrum (cascade_theoretical_spectrum) with the same
trimming as the app (q_width_max=4, f_floor=0.0).

Two generators, two roles (measured with the app's engine, seeds 0..5/7):

1. DETERMINISTIC cascade (the B3 known-answer signal) — asserted tightly.
   Through the engine pipeline it reproduces the feature.md priors exactly:
   p=0.3, 14 levels: max|dh| = 0.038, robust ratio = 0.965.
   Thresholds: max|dh| < 0.1 (2.6x margin), ratio in [0.85, 1.15].

2. The ENGINE'S OWN randomized cascade (binomial_cascade — what the app's
   MF-DFA page actually generates) — asserted with measurement-based
   bounds. Same value distribution as the deterministic cascade, but a
   different spatial arrangement: at p=0.3, N=2^14 the negative-q estimator
   is noisy (h(-4) 1.331..1.724 vs theory 1.499 across seeds; max|dh|
   0.053..0.184 over seeds 0..5, 0.240 at seed 7; robust ratio
   0.648..1.266). Thresholds from the protocol (mean + 3 sd / >= 2x
   observed): mean max|dh| < 0.25 (measured 0.108 +/- 0.049), every
   max|dh| < 0.30 (max observed 0.184), every ratio in [0.55, 1.35]
   (observed 0.648..1.225), mean ratio in [0.80, 1.25] (observed 1.03).

3. p=0.55 INFORMATIONAL ONLY for both generators (14 and 16 levels) —
   never assert on it: its true width is small, so estimator bias
   dominates the ratio (deterministic priors: 2.74 @ 14 levels, 1.59 @ 16;
   the engine's randomized cascade lands elsewhere: 0.92 / 1.14).
"""
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import (  # noqa: E402
    ROBUST_KW,
    Check,
    engine,
    hq_and_spectrum,
    print_header,
    standard_run,
)


def det_cascade(a: float, nmax: int) -> np.ndarray:
    """Deterministic binomial cascade (Kantelhardt 2002), as in B3."""
    k = np.arange(2 ** nmax)
    n1 = np.array([bin(i).count("1") for i in k])
    return a ** n1 * (1 - a) ** (nmax - n1)


def measure(signal) -> tuple[dict[str, Any], dict[str, Any]]:
    run = standard_run(signal)
    sp = hq_and_spectrum(run)
    return run, sp


def theory_comparison(p: float, run: dict[str, Any], sp: dict[str, Any]) -> dict[str, Any]:
    q_list = run["q_list"]
    tau_th = engine.cascade_theoretical_spectrum(p, q_list)[0]
    h_th = (1.0 + tau_th) / q_list
    _, t_alpha, t_f = engine.cascade_theoretical_spectrum(p, q_list)
    _, _, t_width, _, _ = engine.spectrum_width_robust(
        alpha=t_alpha, f_alpha=t_f, q_list=q_list, **ROBUST_KW
    )
    return {
        "q_list": q_list, "h_th": h_th, "tau_th": tau_th, "t_width": t_width,
        "max_dh": float(np.max(np.abs(sp["hq"] - h_th))),
        "max_dtau": float(np.max(np.abs(sp["tau"] - tau_th))),
        "ratio": float(sp["width_robust"] / t_width),
    }


def report(p: float, label: str, run: dict[str, Any], sp: dict[str, Any], t: dict[str, Any]) -> None:
    print(f"{label}: p={p}, N={run['N']}")
    for qv in (-4.0, -2.0, 2.0, 4.0):
        i = int(np.argmin(np.abs(t["q_list"] - qv)))
        print(f"  h({qv:>4.0f}): emp {sp['hq'][i]:.3f} vs theory {t['h_th'][i]:.3f} "
              f"| tau: emp {sp['tau'][i]:.3f} vs theory {t['tau_th'][i]:.3f}")
    print(f"  max|dh|={t['max_dh']:.3f}, max|dtau|={t['max_dtau']:.3f}, "
          f"robust width emp {sp['width_robust']:.3f} vs finite-q theory "
          f"{t['t_width']:.3f} (ratio {t['ratio']:.3f})")


def main() -> None:
    print_header("cascade_pipeline")
    c = Check("cascade_pipeline")

    # --- 1. deterministic cascade: pipeline ground truth (asserted tightly) ---
    run_d, sp_d = measure(det_cascade(0.3, 14))
    t_d = theory_comparison(0.3, run_d, sp_d)
    report(0.3, "deterministic cascade (B3), 14 levels", run_d, sp_d, t_d)
    c.ok("deterministic p=0.3: max|h_emp - h_theory| < 0.1",
         t_d["max_dh"] < 0.1, f"{t_d['max_dh']:.3f} (prior 0.038)")
    c.ok("deterministic p=0.3: robust width within +/-15% of finite-q theory",
         0.85 <= t_d["ratio"] <= 1.15, f"ratio {t_d['ratio']:.3f} (prior 0.96)")

    # --- 2. the app's own randomized cascade (asserted with measured bounds) ---
    dhs, ratios = [], []
    for s in range(6):
        _, m = engine.binomial_cascade(n_levels=14, p=0.3, seed=s)
        run_r, sp_r = measure(m)
        t_r = theory_comparison(0.3, run_r, sp_r)
        dhs.append(t_r["max_dh"])
        ratios.append(t_r["ratio"])
        print(f"engine cascade seed {s}: max|dh|={t_r['max_dh']:.3f}, ratio={t_r['ratio']:.3f}")
    dhs, ratios = np.array(dhs), np.array(ratios)
    print(f"engine cascade, 6 seeds: max|dh| mean {dhs.mean():.3f} +/- {dhs.std():.3f} "
          f"(max {dhs.max():.3f}); ratio mean {ratios.mean():.3f} "
          f"(range {ratios.min():.3f}..{ratios.max():.3f})")
    c.ok("engine cascade p=0.3: mean max|dh| < 0.25 (measured 0.108 +/- 0.049)",
         dhs.mean() < 0.25, f"mean {dhs.mean():.3f}")
    c.ok("engine cascade p=0.3: every max|dh| < 0.30 (max observed 0.184)",
         bool((dhs < 0.30).all()), f"max {dhs.max():.3f}")
    c.ok("engine cascade p=0.3: every robust ratio in [0.55, 1.35] "
         "(observed 0.648..1.225)",
         bool(((ratios >= 0.55) & (ratios <= 1.35)).all()),
         f"range {ratios.min():.3f}..{ratios.max():.3f}")
    c.ok("engine cascade p=0.3: mean robust ratio in [0.80, 1.25] (observed 1.03)",
         0.80 <= ratios.mean() <= 1.25, f"mean {ratios.mean():.3f}")

    # --- 3. p=0.55: informational only, both generators ---
    for label, sig, n_levels in (
        ("deterministic", det_cascade(0.55, 14), 14),
        ("deterministic", det_cascade(0.55, 16), 16),
    ):
        run55, sp55 = measure(sig)
        t55 = theory_comparison(0.55, run55, sp55)
        print(f"p=0.55 {label}, {n_levels} levels (INFORMATIONAL, no assert): "
              f"max|dh|={t55['max_dh']:.3f}, ratio={t55['ratio']:.2f} "
              f"(priors 2.74 @ 14, 1.59 @ 16)")
    for n_levels in (14, 16):
        _, m = engine.binomial_cascade(n_levels=n_levels, p=0.55, seed=7)
        run55, sp55 = measure(m)
        t55 = theory_comparison(0.55, run55, sp55)
        print(f"p=0.55 engine cascade seed 7, {n_levels} levels (INFORMATIONAL, "
              f"no assert): max|dh|={t55['max_dh']:.3f}, ratio={t55['ratio']:.2f}")

    c.finish()


if __name__ == "__main__":
    main()
