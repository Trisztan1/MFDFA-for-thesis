# Engine freeze for IAAFT calibration — results record

Date: 2026-11-22. Feature: `feature.md` (R0–R4), archived at `/complete`.

## Provenance stamps

| Item | Value |
|---|---|
| Protocol | `validation/iaaft_protocol.json` |
| Protocol sha256 | `cef635c4d30f64432103f996617b211f27af92487325626c7868b5584da6dabc` |
| Engine commit | `4a95b9491b2c10678a6179f85f2ef5f643175d94` |
| Versions | python 3.12.13, numpy 2.4.6, MFDFA 0.4.3, streamlit 1.58.0 |
| Seeds | R1: `np.random.seed(11)` (fGn), cascade seed 7, surrogate seeds 3 (unit) and 5 (test); R2: cascade 14 levels / p=0.25 / seed 0, fOU and fGn `np.random.seed(0, 1, 2)`, demo fGn `np.random.seed(11)` |

Full raw outputs of the 9 baseline scripts (2,121 lines) were captured during
implementation; they are deterministic and reproduced by running the scripts
today. The values that matter for later comparison are recorded below.

## R0 — pre-flight baseline (before any edit)

| Script | Verdict | Key numbers |
|---|---|---|
| q_grid | PASS | 99 kept; nearest −0.2/+0.1; `dfa_mf (85, 99)`; q=2 diff 0 |
| package_vs_ref | PASS | max rel err 3.135e-16 |
| fgn_width_baseline | PASS | raw 0.070±0.031, robust 0.056±0.024, h(2) 0.672..0.745 |
| negative_q_damage | PASS | zero-run gate BLOCK; constant-runs gate ALLOW, h(−4) 0.948 |
| fou_subtract_one | PASS | fOU H 0.678/0.705/0.677; fGn H 0.698/0.687/0.745 |
| cascade_pipeline | PASS | deterministic max|dh| 0.038; engine ratio mean 1.030 |
| hq_fit_quality | PASS | len(hq)=len(r2)=len(q)=99; zero column R² NaN |
| surrogate_test | PASS | fGn p=0.9032/k=27; cascade p=0.0323/k=0; NaN raises |
| iaaft_test | PASS | fGn p=0.8387/k=25; cascade p=0.0323/k=0 |
| basedpyright | 19 errors | 8 engine, 4 pages/dfa.py, 7 pages/mf_dfa.py (1246 warnings) |

## R1 — IAAFT diagnostics (reporting only)

**Pre-change capture** (before the edit; n=30, seed 5, standard pipeline):

- fGn: mean `0.05039092604199815`, median `0.04875894232227118`,
  std `0.022067784905532743`, lo `0.019880355787205147`,
  hi `0.09579943724456229`, p `0.8387096774193549`
  (diag: 45.73 iterations, max 63, abs err 2.954e-08, capped 0)
- cascade: mean `0.9794787437834299`, median `0.9806385251246499`,
  std `0.16273502432347575`, lo `0.7091116593288517`,
  hi `1.260941173591316`, p `0.03225806451612903`
  (diag: 34.57 iterations, max 62, abs err 6.712e-05, capped 0)

**Post-change verification:** all six statistics for both signals are
byte-identical (`repr` comparison, enforced by `validation/iaaft_test.py`).

**New diagnostics** (the point of the change):

| Signal | mean rel. spectral err | max rel. spectral err | stop counts (rank_fixed_point, tolerance, cap) |
|---|---|---|---|
| fGn H=0.7 | 7.991e-07 | 9.009e-07 | (20, 10, 0) |
| cascade p=0.3 | **0.1224** | **0.1341** | (0, 30, 0) |

The cascade line is IAAFT review F1 made visible: every surrogate stops on
the tolerance plateau with ~12–13% of the power unmatched, whereas the old
absolute-error readout showed "6.712e-05" (which looked superb).

**F5 edge fix:** a surrogate converging exactly at `max_iter` now counts
under its stopping rule. Demonstrated in the harness: fGn seed 3 converges
at iteration 51 (`reason="tolerance"`); `max_iter=51` gives the same result
and is not capped; `max_iter=10` gives `reason="cap"`.

## R2 — default fit band s ≥ 10 (engine F4)

Pre-registered check (fails on the pre-change code — the helper did not
exist and the old default band is blocked; passes after):

```
cascade demo (14 levels, p=0.25, seed 0): 90 lags, max lag 3981, first lag >= 10 at index 7 (s=10)
  fit_start=0      -> gate BLOCKED
  default (idx  7)  -> gate OK
```

fOU default-band check (engine F8, tolerance 0.15 as pinned in
`fou_subtract_one.py`): band s=10→943, H = 0.682 / 0.704 / 0.676 → PASS.
fGn upload-path sanity (tolerance 0.10): H = 0.742 / 0.755 / 0.719 → PASS
(note the +0.04..+0.055 upward bias on this band; within the pinned
tolerance, recorded for honesty).

**Before/after tables** (app-default grids; `fit_start=0` vs default band):

| Signal | Band | Gate | h(−4) | h(−2) | h(2) | h(4) | width raw | width robust | min R² |
|---|---|---|---|---|---|---|---|---|---|
| cascade demo [old] | s=3→3704 | BLOCKED | nan | nan | 0.833 | 0.642 | nan | 0.724 | 0.984 |
| cascade demo [new] | s=10→3704 | OK | 1.781 | 1.584 | 0.830 | 0.636 | 1.640 | 1.623 | 0.979 |
| fGn H=0.7 [old] | s=3→3704 | OK | 0.800 | 0.755 | 0.686 | 0.670 | 0.268 | 0.237 | 0.917 |
| fGn H=0.7 [new] | s=10→3704 | OK | 0.719 | 0.705 | 0.677 | 0.665 | 0.132 | 0.108 | 0.991 |
| 2_v.sz. p03 [old] | s=3→3704 | OK | 0.926 | 0.844 | 0.601 | 0.482 | 0.775 | 0.737 | 0.847 |
| 2_v.sz. p03 [new] | s=10→3704 | OK | 0.783 | 0.740 | 0.580 | 0.475 | 0.572 | 0.535 | 0.959 |
| 3_v.sz. p03 [old] | s=3→3704 | BLOCKED | nan | nan | 0.618 | 0.509 | nan | 0.374 | 0.988 |
| 3_v.sz. p03 [new] | s=10→3704 | OK | 0.794 | 0.735 | 0.607 | 0.510 | 0.647 | 0.578 | 0.985 |

| Signal | Band | H | R² |
|---|---|---|---|
| cascade demo [old] | s=3→943 | 0.827 | 0.9970 |
| cascade demo [new] | s=10→943 | 0.822 | 0.9960 |
| fGn H=0.7 [old] | s=3→943 | 0.715 | 0.9987 |
| fGn H=0.7 [new] | s=10→943 | 0.711 | 0.9988 |
| 2_v.sz. p03 [old] | s=3→943 | 0.588 | 0.9861 |
| 2_v.sz. p03 [new] | s=10→943 | 0.549 | 0.9952 |
| 3_v.sz. p03 [old] | s=3→943 | 0.632 | 0.9969 |
| 3_v.sz. p03 [new] | s=10→943 | 0.618 | 0.9975 |

Explanations (unexplained change = defect):

- **Gate BLOCKED → OK** on the cascade demo and 3_v.sz. p03: windows of
  size 3 on discrete/quantized data have degenerate fluctuations (engine
  F4; the review's probe showed the same), so the old default band could
  not be fitted at all.
- **h(q<0) and the widths shrink** when s=3..9 are dropped: those tiny
  windows are dominated by near-collinear profile segments (zeros,
  interpolated stretches), which inflate the negative-q moments — the
  mechanism documented in the engine review (F2) and visible in
  `negative_q_damage.py`.
- **min R² rises** because the small scales are the worst-fitting ones.
- **fGn h(−4): 0.800 → 0.719**, moving toward the true 0.7 — consistent
  with the review's finding that the s=3 scales bias the negative-q arm.
- **DFA H shifts by −0.01..−0.04** (0.715→0.711 fGn; 0.588→0.549 and
  0.632→0.618 on the real series): the excluded small scales carry a mild
  upward bias; R² improves on every signal.

Note: the app-default numbers above are demo/exploratory by design
(protocol `role`); the thesis numbers come from the frozen protocol
pipeline. The real-series rows are derived summary statistics (committed
per owner decision); the raw series stay gitignored in `docs/sample_data/`.

## R3 — freeze

`validation/protocol_check.py`: PASS — 11/11 required fields, frozen IAAFT
settings (n_surrogates 39, max_iter 500, tol 1e-6), harness fit-band rule
intact, role + `app_defaults` difference recorded.

Protocol sha256: `cef635c4d30f64432103f996617b211f27af92487325626c7868b5584da6dabc`
Engine commit: `4a95b9491b2c10678a6179f85f2ef5f643175d94`

## End state

- All 11 runnable harness scripts pass (9 baseline + `default_fit_band.py`
  + `protocol_check.py`); the real-series section of `default_fit_band.py`
  skips cleanly when `docs/sample_data/` is absent.
- Typecheck: 19 errors — exactly the baseline (8 engine, 4 dfa, 7 mf_dfa).
- Deliberately not fixed here: engine F2 (constant-run guard — upstream
  decision stands; worst nonzero const run = 2 samples on the 18 series),
  engine F6 (raw-width edges; the study measures robust width), F7/F9
  (cosmetic), the 8 engine implicit-Optional type errors (baseline).
- Not verified here: the reviewer's probe numbers (82.5% false alarm,
  13% cascade relative error) are not re-measured — that is the
  calibration feature (Phase 0 + size study), which runs on this frozen
  state.
