"""B2: the installed MFDFA package vs an independent reference implementation.

Reference: docs/references/mfdfa_app_review_reference.md Appendix A/B (B2).
Prior measurement: max relative error 2.9e-16. Threshold set to 1e-10 for
cross-build (numpy/BLAS) headroom, per feature.md.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import Check, print_header  # noqa: E402
from MFDFA import MFDFA


def mfdfa_ref(x, scales, q, order=1):
    """Plain-loop MFDFA following Kantelhardt et al. (2002); q must not contain 0."""
    x = np.asarray(x, float)
    Y = np.cumsum(x - x.mean())
    N = len(Y)
    q = np.asarray(q, float)
    Fq = np.empty((len(scales), len(q)))
    for a, s in enumerate(scales):
        ns = N // s
        segs = [Y[: ns * s].reshape(ns, s), Y[N - ns * s:].reshape(ns, s)]
        t = np.arange(1, s + 1)
        f2 = []
        for S in segs:
            for seg in S:
                coef = np.polyfit(t, seg, order)
                f2.append(np.mean((seg - np.polyval(coef, t)) ** 2))
        f2 = np.array(f2)
        for b, qq in enumerate(q):
            Fq[a, b] = np.mean(f2 ** (qq / 2)) ** (1 / qq)
    return Fq


def main() -> None:
    print_header("package_vs_ref")
    seed, N = 3, 4000
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(N)
    scales = np.unique(np.logspace(1, 3, 15).astype(int))
    q = np.array([-4.0, -2.0, 2.0, 4.0])
    print(
        f"signal: standard_normal N={N}, default_rng({seed}) | "
        f"lags {scales[0]}..{scales[-1]} ({scales.size} unique) | q={q.tolist()}"
    )

    _, f_pkg = MFDFA(x, lag=scales, q=q, order=1)
    f_ref = mfdfa_ref(x, scales, q)
    rel = float(np.max(np.abs(f_pkg - f_ref) / f_pkg))
    print(f"max relative error = {rel:.3e} (threshold 1e-10; prior 2.9e-16)")

    c = Check("package_vs_ref")
    c.ok("package matches the independent reference implementation",
         rel < 1e-10, f"max rel err {rel:.3e}")
    c.finish()


if __name__ == "__main__":
    main()
