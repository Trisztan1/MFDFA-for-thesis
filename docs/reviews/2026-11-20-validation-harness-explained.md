# The `validation/` harness, explained simply

Written for you (the owner), 2026-11-20. This is not a review report — it is a plain-language guide to the eight `.py` files I created under `validation/`, based on `feature.md`. If you want the exact thresholds and rules, read `feature.md`; if you want the short version of *why each file exists and what it proved*, read this.

## The big idea

Your app does a deep piece of math (MF-DFA) on time series. A scary thing about math code is that it can break *silently*: nobody notices until a thesis number is wrong. So I built a set of small scripts that work like a **teacher with an answer key**:

1. Each script builds a test signal whose **correct answer is already known** (from theory, or from an independent calculation).
2. It pushes that signal through the app's **own math functions** (`run_mfdfa`, `compute_hq`, `spectrum`, and friends from `mfdfa_engine.py`) — not through a copy of them.
3. It compares the app's numbers with the known answers.
4. It prints everything it measured, and exits with code **0** (all good) or **1** (something failed).

Because the exit code is 0/1, a machine can judge the result too — you (or a reviewer agent) can run all of them after any change and immediately see if the math survived.

**What is a "seed"?** Computers make "random" numbers from a starting value called a seed. Fix the seed, and the "random" signal is the same every time — like writing down your dice throws in advance. That is why a PASS today means the same thing tomorrow, and why every script prints its seeds.

**How to run one** (from the project folder):

```sh
.venv/bin/python validation/q_grid.py
```

All of them take seconds, except `surrogate_test.py`, which takes about a minute.

---

## `_common.py` — the shared toolbox

Not a test itself. It does the boring parts once, so all seven scripts can reuse them:

- Finds the project folder, so the scripts can import your app's engine (yes, importing the engine also loads streamlit — that is expected and harmless here; the scripts only ever call the *math* functions, never the plotting ones).
- Holds the **"standard recipe"** that matches the pipeline your reference measurements came from: look at window sizes 10 to N/4 (40 of them), q from −5 to 5 with the near-zero values removed, and fit the line over the middle portion of the points.
- Prints which Python / numpy / MFDFA versions are running, so anyone can reproduce your results later.
- A tiny scorekeeper that collects PASS/FAIL lines and sets the exit code.

Two words you will see everywhere:

- **scale (lag)**: MF-DFA measures roughness at many window sizes — small, medium, large. The lag list is those sizes.
- **q**: a dial. Negative q makes the math focus on *small* fluctuations, positive q on *big* ones. Near q = 0 the formula explodes, so those values are always removed.

---

## `q_grid.py` — counting the seats

The MFDFA package silently throws away q values too close to zero (the formula does not settle there). Your engine removes them too, *before* calling the package. Two filters, one list — if they ever disagreed, the columns of the results table would line up with the wrong q labels, and everything downstream would be quietly wrong.

This script checks the counting, like checking that a spreadsheet has exactly as many columns as its header promises:

- The default grid (−5 to 5, 101 points) keeps exactly **99** q values — and the kept set is lopsided: the closest kept negative is **−0.2**, the closest kept positive is **+0.1**. (Computers store 0.1 imperfectly; one side slips under the cutoff, the other just barely doesn't. Not a bug — just arithmetic at the limit.)
- The results table has exactly as many columns as the q list has entries. Aligned.
- The column the app uses for the simple (monofractal) DFA really is the **q = 2** column — proven by re-running the package with *only* q = 2 and comparing: the difference was exactly 0.
- A different grid size (100 points instead of 101) also stays aligned (98 kept).

**Result:** PASS, everything exact.

---

## `package_vs_ref.py` — two students, the same exam

The package (LRydin's MFDFA) is a fast, optimized black box. To trust it, I wrote a second MF-DFA **from scratch** inside this script — deliberately slow, plain loops, exactly the textbook recipe (Kantelhardt 2002). Then both computed the same signal.

If a fast optimized version and a slow honest version agree, both followed the recipe.

**Measured:** biggest relative difference **3.1e-16** — that is 0.0000000000000003, i.e. agreement to the 16th decimal place.
**Threshold:** 1e-10. Why so much looser than the measurement? Because a different numpy/BLAS build on another machine can wobble a little, and the test should not fail because of that.

---

## `fgn_width_baseline.py` — weighing the empty box

fGn with H = 0.7 is *boring by design*: one single kind of roughness everywhere. For such a signal the true multifractal width is exactly **0**. But a healthy pipeline, fed finite, noisy data, still shows a small width — like a scale that shows 0.02 kg when you weigh nothing. You need to know your scale's own error.

So this script measures **how much fake width a healthy pipeline produces**, 12 different seeded signals:

- raw width: **0.070 ± 0.031** (worst 0.124)
- robust width: **0.056 ± 0.024** (worst 0.101)
- and as a bonus: the fitted h(2) came out **0.703 ± 0.023** — we put H = 0.7 in, the pipeline gave 0.7 back.

**Threshold:** the *mean* width must stay below 0.12.

Nice detail: these numbers matched your own earlier measurements (you wrote 0.070 / 0.056 in the plan) **exactly** — strong evidence the harness is running the very same pipeline you measured with.

---

## `cascade_pipeline.py` — the cake with a known recipe

A **binomial cascade** is built by repeatedly splitting the signal in two and handing out mass with fixed fractions p and 1−p. For it, theory knows the answer for *every* q, exactly:

- τ(q) = −log2(p^q + (1−p)^q), and h(q) = (1 + τ(q))/q.

So this script does not just check one summary number — it compares the app's h(q) against theory, point by point.

**Two tiers, because there are two cascades:**

1. **The textbook (deterministic) cascade** — the one your reference measurements came from. Through the app's pipeline it recovers h(q) with a maximum error of **0.038**, and the robust width lands within 4% of theory (ratio 0.965). PASS with your exact thresholds (error < 0.1, ratio within ±15%).
2. **The app's own generator** (`binomial_cascade` — the randomized one your MF-DFA page actually creates when you click). Same values, different arrangement. Surprise: it **wobbles more on the negative-q side** — error 0.05–0.24 depending on the seed, width ratio 0.65–1.27. This is not a bug; a random cake simply lands differently than the textbook cake. So these thresholds are based on six measured seeds with generous margin, instead of pretending the textbook numbers apply.

**p = 0.55 is printed but never judged**, on purpose. Its true width is so small that noise and bias dominate (the textbook cascade at 14 levels shows a ratio of 2.74!). Judging correctness by that number would punish a perfectly correct implementation — your reference doc says the same.

**The story behind your priors:** your earlier numbers (0.038, ratio 0.96) came from the deterministic cascade — and indeed the deterministic one through the app's pipeline reproduces them exactly. The app's randomized one behaves differently. Both facts are now written down where future readers will find them.

---

## `negative_q_damage.py` — poking holes on purpose

Real eye-tracker data can go bad in two ways:

- a long run of **exact zeros** (the gaze is not moving), or
- a long run of **constant values** (a gap that was filled in by interpolation → constant speed).

Negative q stares at the *smallest* fluctuations. Inside a flat stretch, the "variance after trend removal" collapses to exactly 0 — and zero with a negative power is like 1/0: it explodes. So flat stretches poison the negative-q results.

**What I verified while writing this (and wrote into the script):** your reference doc says the engine has a guard against zero-runs (`s_min = max(order+2, zero_run+1)`). **That guard does not exist** — not in `mfdfa_engine.py`, not in the package. What actually protects you:

- **Zero-runs:** the variance becomes exactly 0 → the negative-q results become exactly 0 → your page-level "is this fit band valid?" check (`get_valid_fitting_range`) notices and **blocks the analysis**. The script asserts this. PASS — the defense works.
- **Constant-runs:** the values are not zero, so *nothing* notices. h(−4) silently drifts from **0.643 to 0.948**. The script measures and prints this but does not judge it, because it is a known hazard (your B5 note measured 0.637 → 0.818), not a new bug.

The open decision (recorded in `feature.md`): add a real guard one day, or trust that your gaze processor removes gaps before the data ever reaches the app.

---

## `surrogate_test.py` — shuffling the deck

The question: does the "multifractality" live in the **order** of the values, or just in the **values themselves** (a few big spikes, many tiny ones — no order needed)?

The test: shuffle the signal like a deck of cards, 30 times. Same values, order destroyed. Recompute the width after every shuffle. If the real signal's width beats all the shuffled ones, the *order* is what matters.

- **fGn** (boring signal): p = **0.90** — nowhere near significant. Correct.
- **Cascade** (truly structured): p = **0.032 = 1/31** — every single shuffle was weaker than the real signal. Correct.

The script also checks the **p-value formula itself**. The engine computes p = (1 + k) / (n + 1), where k is the number of shuffled widths at least as big as the real one. From a real run you can recover k backwards (k = p·(n+1) − 1) and demand that it comes out as a whole number, and that the formula reproduces p exactly. This matters because an earlier version of the engine had a bracket mistake that produced p ≈ 2.0 — impossible for a probability — and this check would have caught it instantly.

---

## `fou_subtract_one.py` — checking the minus-one rule

The app has a rule about the DFA slope:

- its own **generated** signal (fOU, a random-walk-like thing) has slope ≈ H + 1, so it **subtracts 1**;
- **uploaded** signals (noise-like, e.g. your velocity series) have slope ≈ H directly, so it must **not** subtract.

Getting this backwards would flip every Hurst exponent in your thesis by 1. The script checks all sides of it:

- fOU **with** the subtraction recovers the H we put in: 0.678, 0.705, 0.677 (input was 0.7);
- fGn **without** the subtraction recovers its true H: 0.698, 0.687, 0.745;
- if you *wrongly* subtracted 1 from fGn, you would get about **−0.3** — obviously impossible for a Hurst exponent, outside (0, 1);
- finally it reads `pages/dfa.py` and confirms the upload branch passes `subtract_one=False` exactly once, and the generated branch relies on the default `True`.

**Result:** PASS on all four.

---

## The two honest discoveries, in one place

1. **The missing guard.** The reference doc promised a zero-run guard in the engine; there is none. The app's real zero-run defense is the page-level validity check, which works (asserted). Constant-run damage is caught by *nothing* — measured and printed, decision left to you.
2. **Two cascades, two behaviors.** Your validation priors belong to the deterministic cascade (reproduced exactly). The app's own randomized cascade is noisier at negative q and *better* at p = 0.55. Not a bug — but it means the app's validation page is noisier at p = 0.3 than the reference doc's table suggests.

And one reassuring fact: every place where your own prior measurements applied (fGn width, deterministic cascade), the harness reproduced your numbers **exactly**.

## Where to look next

- `feature.md` — the exact thresholds, and the rules used to pick them.
- The docstring at the top of each `validation/*.py` — the same story as this file, one paragraph per script.
- Run any script yourself with `.venv/bin/python validation/<name>.py` — it prints everything it does.
