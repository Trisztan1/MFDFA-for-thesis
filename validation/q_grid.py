"""Engine q-grid alignment (reference section 9, checklist items C10-C11).

The installed package silently drops |q| < 0.1 (MFDFA.py:150) and the engine
pre-filters with the same predicate (mfdfa_engine.py:85), so the q array used
downstream must have exactly as many entries as the F matrix has columns.

Default grid: linspace(-5, 5, 101) keeps 99 values, asymmetric around 0
(floating point: the -0.1 entry fails `q < -0.1`, the +0.1 entry passes
`q > 0.1`; nearest kept: -0.2 negative side, +0.1 positive side).
Even q_num=100 keeps 98, symmetric (both +/-0.0505 dropped).

Also verifies that get_dfa slices the true q=2 column, by comparing against
a direct q=[2] package run on the same lag array.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import Check, engine, print_header  # noqa: E402
from MFDFA import MFDFA, fgn


def main() -> None:
    print_header("q_grid")
    seed, N, H = 0, 4096, 0.7
    np.random.seed(seed)  # fgn uses the legacy global RNG (fgn.py:60)
    y = fgn(N, H)
    print(f"signal: fGn N={N}, H={H}, np.random.seed({seed})")

    c = Check("q_grid")

    # Case A: default q grid (-5..5, 101 points), engine defaults otherwise
    lag_mf, dfa_mf, q_list = engine.run_mfdfa(y)
    q_neg_max = q_list[q_list < 0].max()
    q_pos_min = q_list[q_list > 0].min()
    c.ok("default grid keeps exactly 99 q values", q_list.size == 99,
         f"got {q_list.size}")
    c.ok("kept grid asymmetric: nearest negative q ~ -0.2, nearest positive ~ +0.1",
         np.isclose(q_neg_max, -0.2, atol=1e-9) and np.isclose(q_pos_min, 0.1, atol=1e-9),
         f"nearest kept: {q_neg_max:.6f} / {q_pos_min:.6f}")
    c.ok("F matrix columns == len(q_list) after the package's own filter",
         dfa_mf.shape[1] == q_list.size,
         f"dfa_mf {dfa_mf.shape} vs q_list {q_list.size}")

    dfa = engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)
    _, f_q2 = MFDFA(y, lag=lag_mf, q=np.array([2.0]), order=1)
    i2 = int(np.argmin(np.abs(q_list - 2)))
    c.ok("get_dfa slices the true q=2 column",
         np.allclose(dfa, f_q2[:, 0], rtol=1e-12),
         f"q used: {q_list[i2]:.6f}, max |diff| {np.max(np.abs(dfa - f_q2[:, 0])):.2e}")

    # Case B: even q_num — the asymmetric-removal case must not misalign
    _, dfa_mf2, q_list2 = engine.run_mfdfa(y, q_num=100)
    c.ok("even q_num=100 keeps 98 (symmetric), columns still aligned",
         q_list2.size == 98 and dfa_mf2.shape[1] == q_list2.size,
         f"kept {q_list2.size}, dfa_mf2 cols {dfa_mf2.shape[1]}")

    c.finish()


if __name__ == "__main__":
    main()
