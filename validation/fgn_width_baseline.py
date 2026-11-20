"""Monofractal ground truth: fGn H=0.7 — spurious-width baseline (true DA = 0).

Priors (feature.md): package pipeline, 12 seeds, N=4096: raw width
0.070 +/- 0.031 (max 0.124); robust (|q|<=4, f>=0) 0.056 +/- 0.024
(max 0.101). Reference section 8.2: N=2^14 raw 0.051 +/- 0.018 — the width
shrinks with N, so N=4096 is the conservative case.

Thresholds (user-approved): mean raw and robust width < 0.12 (~1.7x the
prior mean, above mean+3sd). Engine re-measurement recorded in the header
after the first run (see summary in the conversation).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import (  # noqa: E402
    Check,
    h_at,
    hq_and_spectrum,
    print_header,
    standard_run,
)
from MFDFA import fgn


def main() -> None:
    print_header("fgn_width_baseline")
    H, N = 0.7, 4096
    seeds = list(range(12))
    print(f"fGn H={H}, N={N}, np.random.seed per fgn, seeds {seeds[0]}..{seeds[-1]}")

    raws, robs, h2s = [], [], []
    for s in seeds:
        np.random.seed(s)
        y = fgn(N, H)
        run = standard_run(y)
        sp = hq_and_spectrum(run)
        raws.append(sp["width_raw"])
        robs.append(sp["width_robust"])
        h2s.append(h_at(sp, run["q_list"], 2.0))
    raws = np.array(raws)
    robs = np.array(robs)

    print(f"h(2): mean {np.mean(h2s):.3f} +/- {np.std(h2s):.3f} (expected ~0.7)")
    print(f"raw width:    mean {raws.mean():.3f} +/- {raws.std():.3f}, max {raws.max():.3f}")
    print(f"robust width: mean {robs.mean():.3f} +/- {robs.std():.3f}, max {robs.max():.3f}")

    c = Check("fgn_width_baseline")
    c.ok("mean raw width < 0.12 (true width is 0)", raws.mean() < 0.12,
         f"mean {raws.mean():.3f}")
    c.ok("mean robust width < 0.12 (true width is 0)", robs.mean() < 0.12,
         f"mean {robs.mean():.3f}")
    c.ok("every h(2) within 0.7 +/- 0.15",
         all(abs(h - H) < 0.15 for h in h2s),
         f"h(2) range {min(h2s):.3f}..{max(h2s):.3f}")
    c.finish()


if __name__ == "__main__":
    main()
