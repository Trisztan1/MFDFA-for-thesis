# Engine-freeze review (R0–R4) — 2026-11-22

Reviewer: stats-reviewer (Claude Sonnet 5.5, openrouter/anthropic/claude-sonnet-5.5). Read-only; the only file written is this report.
Scope: `git diff` of `mfdfa_engine.py`, `utils/pages_logic.py`, `validation/iaaft_test.py`; new `validation/default_fit_band.py`, `validation/iaaft_protocol.json`, `validation/_protocol.py`, `validation/protocol_check.py`, `docs/results/2026-11-22-engine-freeze.md`; `feature.md` as spec. Skill files and other .md files not read.
Run: all 11 harness scripts (exit 0 each, final line PASS) and `.venv/bin/basedpyright mfdfa_engine.py pages/ validation/ --level error` (19 errors, exit 1). `git tag` was denied by permissions, so the tag was not verified.

## 1. Verdict (5 lines)

1. **Approved as the frozen state, with one blocking follow-up:** the recorded `engine_commit` is the pre-change HEAD and the freeze changes are still uncommitted — the provenance stamp does not yet identify the frozen code. Commit, rerun `protocol_check.py`, update the two hash lines in the results file, then tag `v0.2-engine-frozen`. Until then the freeze is not in force.
2. R1 is reporting-only as claimed: iteration and RNG order untouched, and the byte-exact regression holds — fGn p `0.8387096774193549` (k=25), cascade p `0.03225806451612903` (k=0), all six width statistics match the pinned pre-change reprs; shuffle pins unchanged (0.9032/27, 0.0323/0).
3. The new diagnostics do their job: the cascade now shows mean relative spectral error **0.122** (max 0.134, 30/30 stopped on "tolerance") where the old readout printed 6.712e-05 absolute — IAAFT review F1 is now visible in every run.
4. R2 moves the app default to the validated s ≥ 10 exactly as specified; the pre-registered cascade check passes and matches my own independent probe from 2026-11-21 number-for-number (h(−4)=1.781, robust 1.623, raw 1.640, min R² 0.979).
5. Everything else is unchanged: 11/11 scripts pass, typecheck is exactly the 19-error baseline (same 8 engine implicit-Optional errors, now at lines 102/120/409/424).

## 2. Requirement verdicts

| Req | Verdict | Evidence |
|---|---|---|
| R0 baseline recorded | OK | results file §R0 matches my own 2026-11-21 runs: 9/9 PASS, 19 errors (8 engine, 4 dfa, 7 mf_dfa); key numbers identical (package_vs_ref 3.135e-16, fGn widths 0.070/0.056, cascade ratio 1.030, h(−4) 0.948) |
| R1.1 new return payload | OK | `_iaaft_generate` returns `(surrogate, iterations, rel_spectral_error, stop_reason)` (engine:339-341); `rel = final_error / mean(target_amp²)` (engine:284, 339) exactly as specified; rank fixed point checked before tolerance (engine:331-334) |
| R1.2 diagnostics 7-tuple | OK | `(mean_iterations, max_iterations_used, mean_rel, max_rel, stop_counts)` with `stop_counts=(n_rank, n_tol, n_cap)` (engine:377-385) |
| R1.3 n_capped counts only "cap" | OK | `int(sum(r == "cap" ...))` (engine:380); harness proves the edge: `max_iter=51` (the pinned convergence iteration) → reason `tolerance`, not capped; `max_iter=10` → `cap` (iaaft_test lines 125-133, PASS in my run) |
| R1.4 no change to iteration/RNG/loop/p-value/shuffle | OK | engine diff touches only return payloads and diagnostics; `_surrogate_widths` (engine:189-258) untouched; my runs reproduce both IAAFT and shuffle pins exactly |
| R1.5 byte-exact regression | OK | `EXPECTED_FGN`/`EXPECTED_CASCADE` full-precision reprs asserted (iaaft_test:50-58); my run: "reprs match" PASS for both; values equal my independent pre-change run of 2026-11-21 (mean 0.0504…, p 0.8387; cascade mean 0.9795…, p 0.0323) |
| R1.6 iaaft_test updated | OK | stop-rule checks, F5 edge case, rel-error pin (8.212e-07 < 1e-5), determinism over all four fields — all PASS in my run; cascade diagnostic assertion `mean rel err > 0.05` pins F1 visibly |
| R2.1 `default_fit_start` | OK | pure helper (pages_logic.py:11-21); first index `lag_mf >= 10`, falls back to 0 when the grid never reaches 10, clamped to `max_index` |
| R2.2 slider default only | OK | `value=default_fit_start(lag_mf, max_index)` in both sidebars (pages_logic.py:218, 349); min/max and fit_end default unchanged; Hungarian warning when `lag_mf[-1] < 10` (pages_logic.py:228-232, 359-363) |
| R2.3 Hungarian help/caption | OK | help text + caption state the s ≥ 10 validated band in both sections |
| R2.4 `default_fit_band.py` | OK | pre-registered cascade check PASS (old band BLOCKED, default band OK — matches my 2026-11-21 probe exactly); fOU H 0.682/0.704/0.676 within ±0.15; fGn H 0.742/0.755/0.719 within ±0.10; before/after tables cover demo + both real series (N=17224, N=3804); skip logic for absent sample data present (default_fit_band.py:183-189) |
| R3.1 protocol JSON | OK | all 11 required fields; frozen values match the harness standard (`_common.standard_params` + `ROBUST_KW`: lag 10..N/4, 40 lags, q −5..5/101, band `[size//8 : int(size/1.5)]`, order 1, robust 4/False/0.0, max_iter 500, tol 1e-6, n_surrogates 39); `role` + `app_defaults` difference declared |
| R3.2 `_protocol.py` | OK | sha256 of file bytes + `git rev-parse HEAD` (_protocol.py:45-54); rejects missing fields with a Hungarian error |
| R3.3 `protocol_check.py` | OK | PASS in my run; sha256 `cef635c4…da6dabc`, commit `e5822e4…` printed |
| R3.4 tag | UNVERIFIABLE | `git tag` denied by permissions; spec makes tagging the owner's action — must be done after the commit (see finding 1) |
| R4 results file | OK with a provenance gap | `docs/results/2026-11-22-engine-freeze.md`: versions, seeds, hashes, R0 baseline, pre-change reprs, before/after tables, per-change explanations; see finding 1 for the commit stamp |

## 3. Findings

**1. The freeze's provenance stamp does not yet identify the frozen code (blocking for the calibration feature). Confidence: high.**
`git status` shows the freeze changes uncommitted; `protocol_hashes()` recorded `e5822e4…` = HEAD *before* the changes (results file line 11 admits this and instructs rerunning `protocol_check.py` after commit). As it stands, a later reader cannot map a results row to the frozen engine: the sha256 covers only the JSON, and the commit hash points at pre-R1/R2 code. Required sequence before any calibration run: commit the freeze → rerun `validation/protocol_check.py` → replace the two hash lines in the results file → create the tag. Severity: changes the meaning of every future "attributable to exact code" claim; not a numerical defect.

**2. Caption change goes beyond the letter of R2 (positive deviation; report it). Class (b). Confidence: high.**
R2 asked only for the moved default, warning and help text. The captions also changed from `lag_mf[fit_end]` to `lag_mf[fit_end - 1]` (pages_logic.py:234-236, 365-367) — this fixes engine-review F1's display half: the caption now names the last scale actually *used* by the exclusive slice. Correct and welcome, but it is an unrequested UI change inside a feature whose constraints say "only the default value moved"; it must be mentioned in the completion summary. The plot half of F1 remains: `add_vrect` still spans to `lag_mf[min(fit_end, len(lag_mf)-1)]` (mfdfa_engine.py:451-454), so the gray band on the fluctuation plot still shows the excluded end scale. Cosmetic, explicitly out of scope here.

**3. `default_fit_start` can silently start below s = 10 when clamped. Cosmetic. Confidence: high (code reading; not triggered by any current path).**
The helper clamps to `max_index` (pages_logic.py:21). If the first index with s ≥ 10 lies beyond the slider maximum, the default starts at a scale < 10 without the warning firing — the warning only covers `lag_mf[-1] < 10` (pages_logic.py:228). Needs a very short or narrow lag grid; the current app grids (min `len(lag_mf)-5` with 85-90 lags) never hit it. Worth a sentence in the docs, nothing more.

**4. "Fails before / passes after" is satisfied only weakly. Cosmetic. Confidence: high.**
On pre-change code `default_fit_band.py` dies with `AttributeError` (`pl.default_fit_start` does not exist) before any assertion runs, so the pre-registered cascade check never actually *fails* on the old code — the negative control (old band BLOCKED) is demonstrated inside the post-change run instead (default_fit_band.py:115-124). Acceptable reading of the spec, but the acceptance criterion "fails on the pre-change code" is technically unmet; the results file states this honestly ("the helper did not exist").

**5. The app default band is not the protocol band, and on fGn they differ measurably. Class (b) — already covered by the `role` declaration, keep it visible. Confidence: high.**
On the new default DFA band (s=10→943) fGn H comes out 0.742/0.755/0.719 — a +0.02..+0.055 upward bias vs true 0.7, honestly recorded in the results file, while the frozen protocol band (10..N/4, fit `[size//8 : int(size/1.5)]`) gave 0.698/0.687/0.745 in `fou_subtract_one.py`'s fGn check. Same estimator, different band, ~0.04 shift. The protocol's `role` field and `app_defaults` note handle this correctly (app numbers are exploratory); the thesis must quote only protocol-pipeline numbers. This is the exact trap the freeze is designed to close — it is closed on paper, and the calibration feature must keep quoting the protocol band.

**6. Minor notes.** (i) `n_surrogates=39` in the protocol vs 30 in the harness is intended (calibration resolution p=1/40); no script asserts 39 anywhere except `protocol_check` — fine. (ii) The results file quotes "1246 warnings" for basedpyright; I ran `--level error` and verified only the 19-error count, not the warning count. (iii) The real-series rows in the results file are derived summary statistics per the owner's stated policy (results file lines 125-128); the script itself writes nothing and only reads `docs/sample_data/`.

## 4. Cross-checks against my earlier reviews

- IAAFT review F1 (invisible plateau): fixed by R1 — cascade mean rel err 0.122/max 0.134, 30/30 "tolerance"; matches my measured 0.1292 (seed 1, 2026-11-21).
- IAAFT review F5 (n_capped edge): fixed — converging exactly at `max_iter` counts under its rule.
- Engine review F4 (default fit band s=3): fixed by R2; the fix reproduces my probe numbers exactly.
- Engine review F8 (fOU on the app-default band): now measured — H 0.682/0.704/0.676 within ±0.15.
- Engine review F3 (NaN width): was already fixed; `surrogate_test.py` asserts it (PASS in my run).
- Still open by owner decision, correctly listed in the results file: engine F2 (constant-run guard; upstream, QC evidence cited), F6 (raw-width edges), F7, F9, the 8 implicit-Optional errors.
- Still open from the IAAFT review and *not* addressed by this feature (correctly out of scope): the calibration question itself — type-I error on heavy-tailed correlated data (my probe: 82.5 % reject under a true null) and the cascade's unmatched spectrum. The freeze is the precondition for measuring these; they are the next feature's job.

## 5. Harness results (all exit 0, final line PASS)

- `q_grid`: 99 kept, (85, 99) aligned, q=2 diff 0.
- `package_vs_ref`: 3.135e-16.
- `fgn_width_baseline`: h(2) 0.703±0.023; raw 0.070±0.031; robust 0.056±0.024.
- `negative_q_damage`: zero-run BLOCK, h(−4) nan; constant-runs ALLOW, h(−4) 0.643→0.948 (unchanged, per owner decision).
- `fou_subtract_one`: fOU H 0.678/0.705/0.677; fGn 0.698/0.687/0.745; subtract_one wiring correct.
- `cascade_pipeline`: deterministic max|dh| 0.038, ratio 0.965; engine seeds 0-5 ratio mean 1.030 (0.648..1.225); p=0.55 2.74@14 / 1.59@16.
- `hq_fit_quality`: lengths 99/99/99; degenerate columns → NaN R².
- `surrogate_test`: fGn p=0.9032 (k=27), cascade p=0.0323 (k=0), NaN raises.
- `iaaft_test`: reprs match pre-change pins; fGn rel err 7.991e-07, stops (20 rank, 10 tol, 0 cap); cascade rel err 0.122/0.134, stops (0, 30, 0); F5 edge PASS.
- `default_fit_band`: cascade old BLOCKED / default OK (index 7, s=10); fOU 0.682/0.704/0.676; fGn 0.742/0.755/0.719; real series 2_v.sz. N=17224 and 3_v.sz. N=3804 rows printed, gates and widths as in the results file.
- `protocol_check`: 11/11 fields, frozen settings, sha256 `cef635c4d30f64432103f996617b211f27af92487325626c7868b5584da6dabc`, commit `e5822e4ed785c9644faaaa422aea3090ff9a74a5`.
- `basedpyright --level error`: 19 errors, exit 1 — identical count and distribution to the R0 baseline; no new errors from the new files.

## 6. Could not verify

- The tag `v0.2-engine-frozen`: `git tag` was denied; per spec it is the owner's action after the final commit.
- The post-commit engine hash (the changes are uncommitted; see finding 1).
- The basedpyright *warning* count quoted in the results file (1246); I ran error-level only.
- Streamlit runtime behaviour of the two changed sidebar functions (no UI check possible here; the pure helper and gate logic are covered by `default_fit_band.py`).
- The pre-change failure of `default_fit_band.py` (finding 4) — by construction it cannot be re-run on pre-change code without reverting.

## 7. Next steps (owner actions, in order)

1. Commit the freeze; rerun `validation/protocol_check.py`; update the `engine_commit` (and, if the JSON changed, sha256) lines in `docs/results/2026-11-22-engine-freeze.md`; then tag `v0.2-engine-frozen`. This is the only blocking item.
2. In the completion summary, name the unrequested caption change (finding 2) so the feature record matches the diff.
3. Keep quoting only protocol-band numbers in the thesis; the app default band measurably differs (finding 5).
4. Next feature (already planned): Phase 0 instrument verification + the size study — my standing numbers to beat: 82.5 % reject under a true IAAFT null on lognormal-of-fGn (40 realizations, n=19); cascade relative spectral error ~0.13.
