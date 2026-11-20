"""Shared helpers for the MF-DFA validation harness (validation/*.py).

Standard harness pipeline, matching the app-style pipeline in
docs/references/mfdfa_app_review_reference.md (section 8 / Appendix B):

    lags   : 10 .. N//4, 40 log-spaced ints (np.unique'd), order 1
    q      : linspace(-5, 5, 101) after the engine's |q| <= 0.1 filter
    fit    : [lag.size // 8 : int(lag.size / 1.5)]   (indices into lag)
    robust : spectrum_width_robust(q_width_max=4, positive_q_only=False, f_floor=0.0)

Rules: fixed seeds; print seeds/versions/sizes; exit 0 on pass, 1 on fail;
import only compute-layer functions — importing mfdfa_engine pulls in
streamlit, which is harmless outside a Streamlit runtime, but the plot_*
functions are NEVER called from these scripts.
"""
import importlib.metadata as _md
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

warnings.filterwarnings("ignore")  # MFDFA docstring SyntaxWarnings etc.
import mfdfa_engine as engine  # noqa: E402


def print_header(name: str) -> None:
    print(f"== {name} ==")
    print(
        f"python {sys.version.split()[0]} | numpy {np.__version__} "
        f"| MFDFA {_md.version('MFDFA')} | streamlit {_md.version('streamlit')}"
    )


def standard_params(N: int, n_lag: int = 40) -> dict[str, Any]:
    return {
        "lag_start": 1.0,  # 10**1 = 10 samples
        "lag_stop": float(np.log10(N // 4)),
        "lag_num": n_lag,
        "q_start": -5.0,
        "q_stop": 5.0,
        "q_num": 101,
        "order": 1,
    }


def standard_run(y, n_lag: int = 40) -> dict[str, Any]:
    """Run the engine pipeline with the standard harness parameters."""
    y = np.asarray(y)
    p = standard_params(y.size, n_lag)
    lag_mf, dfa_mf, q_list = engine.run_mfdfa(y, **p)
    fit_start = lag_mf.size // 8
    fit_end = int(lag_mf.size / 1.5)
    return {
        "y": y, "N": y.size, "params": p, "lag_mf": lag_mf,
        "dfa_mf": dfa_mf, "q_list": q_list,
        "fit_start": fit_start, "fit_end": fit_end,
    }


ROBUST_KW = {"q_width_max": 4, "positive_q_only": False, "f_floor": 0.0}


def hq_and_spectrum(run: dict[str, Any]) -> dict[str, Any]:
    hq, r2 = engine.compute_hq(
        run["lag_mf"], run["dfa_mf"], run["q_list"], run["fit_start"], run["fit_end"]
    )
    tau, alpha, f_alpha = engine.spectrum(hq=hq, q_list=run["q_list"])
    _, _, width_raw, alpha_peak, asym = engine.spectrum_stats(alpha=alpha, f_alpha=f_alpha)
    _, _, width_robust, _, _ = engine.spectrum_width_robust(
        alpha=alpha, f_alpha=f_alpha, q_list=run["q_list"], **ROBUST_KW
    )
    return {
        "hq": hq, "r2": r2, "tau": tau, "alpha": alpha, "f_alpha": f_alpha,
        "width_raw": width_raw, "width_robust": width_robust,
        "alpha_peak": alpha_peak, "asymmetry": asym,
    }


def h_at(sp: dict[str, Any], q_list, qv: float) -> float:
    """h(q) at the grid value closest to qv."""
    return float(sp["hq"][int(np.argmin(np.abs(np.asarray(q_list) - qv)))])


class Check:
    """Collects PASS/FAIL results; exit code 1 if anything failed."""

    def __init__(self, script: str):
        self.script = script
        self.failures: list[str] = []

    def ok(self, label: str, cond: bool, detail: str = "") -> None:
        line = f"[{'PASS' if cond else 'FAIL'}] {label}"
        if detail:
            line += f" — {detail}"
        print(line)
        if not cond:
            self.failures.append(label)

    def finish(self) -> None:
        verdict = "PASS" if not self.failures else f"FAIL ({len(self.failures)} failed)"
        print(f"{self.script}: {verdict}")
        sys.exit(0 if not self.failures else 1)
