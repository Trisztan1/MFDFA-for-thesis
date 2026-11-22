# Data processing

How the gaze processor turns a Gazepoint recording into one distance series
per puzzle. Only the data path is described here; the app's UI is out of
scope.

```
Gazepoint CSV
  -> 1. chunk the thinking phases (keyboard markers)
  -> 2. filter samples (validity, blink, on-screen bounds)
  -> 3. compute displacements between consecutive retained samples
  -> 4. summarise per chunk (QC table)
  -> 5. save puzzle_NN.csv (+ qc.csv)
```

## Input

Relevant columns of the Gazepoint export:

| Column | Meaning |
|---|---|
| `BPOGX`, `BPOGY` | Binocular-average gaze coordinates, normalized to the screen (documented 0–1) |
| `BPOGV` | Gaze validity flag: `1` = valid |
| `BKID` | Blink flag: `0` = no blink |
| `KB` | Keyboard marker name: `RETURN`, `SPACE`, `BACK` |
| `KBS` | Keyboard state: `1` = pressed (down), `2` = released, otherwise idle |

Timestamps (`CNT`, `TIME(...)`, `TIMETICK(...)`) are read but never used or
saved. The file is read as a plain DataFrame; original row order and index
are preserved throughout.

## Stage 1 — Chunking the thinking phase

Only key-down events (`KBS == 1`) are examined, in row order:

- `RETURN` opens a thinking phase at that row.
- `SPACE` closes it. The chunk is `df.iloc[start:stop]`: the RETURN-down row
  is **included**, the SPACE-down row is **excluded**.
- `BACK` before the SPACE discards the unfinished phase (a missing SPACE must
  not merge two puzzles).
- A doubled RETURN keeps the **first** press as the start; the rows between
  the presses stay in the chunk. The number of doubled RETURNs is counted
  separately and only feeds a UI warning.
- An unmatched SPACE is ignored; a phase still open at end-of-file is
  discarded.

Output: a chronological list of chunk DataFrames with all columns and
original indices. A normal recording yields nine chunks; the app warns when
it sees a different number but still processes what it finds.

## Stage 2 — Sample filter

Within each chunk, a row is retained only when **all four** conditions hold:

1. `BPOGV == 1` — gaze point valid;
2. `BKID == 0` — no blink in progress;
3. `0 <= BPOGX <= 1` — normalized X on screen (edges inclusive);
4. `0 <= BPOGY <= 1` — normalized Y on screen (edges inclusive).

Coordinates are coerced with `pd.to_numeric(errors="coerce")` first, so
non-numeric or null values become NaN and fail the bounds check; they are
dropped.

Why the bounds: `BPOGV == 1` does **not** guarantee on-screen coordinates.
When the participant looks away from the screen, the tracker still reports
"valid" while extrapolating the gaze ray to the screen plane; on the pilot,
flagged-valid Y values reach ±6.5 screen heights. Such rows are impossible
as on-screen gaze positions and would inject displacements larger than the
screen diagonal into the series. They are removed and collapsed like
invalid/blink rows.

The surviving rows keep their original order and index. Gaps are **not**
repaired: if removed rows lay between two retained samples, the next
displacement is computed directly between those two retained coordinates,
and the removed rows' duration and count are not represented in the output.

## Stage 3 — Displacement series

For each chunk, with the retained coordinates in order:

```
distance_i = hypot(x_i - x_(i-1), y_i - y_(i-1))
           = sqrt((x_i - x_(i-1))^2 + (y_i - y_(i-1))^2)
```

- The first value is undefined (no predecessor) and is dropped; N retained
  coordinates therefore produce N − 1 distances.
- Zero-length steps are **retained**. A `0.0` means the two consecutive
  retained coordinates were exactly equal (fixation-like), not missing data.
- Values are Euclidean displacements in normalized screen units: no division
  by time, no aspect-ratio correction, no interpolation, no resampling.

Output: one ordered `pd.Series` per chunk, including empty series (a chunk
with 0 or 1 retained coordinates yields an empty series).

## Stage 4 — QC table

One row per chunk, chronological. `puzzle` is the position (1…n), **not** a
puzzle ID; the notebook maps positions to actual puzzles.

| Column | Definition |
|---|---|
| `raw_rows` | `len(chunk)`: RETURN-down row included, SPACE-down row excluded |
| `retained_rows` | `len(series) + 1`; `NaN` for an empty series (0 and 1 retained rows cannot be distinguished) |
| `removed_pct` | `100 × (1 − retained_rows / raw_rows)`, one decimal; `NaN` for an empty series |
| `distances` | `len(series)` — rows that enter MF-DFA |
| `zero_pct` | share of distances exactly `0.0`, one decimal; `NaN` for an empty series |
| `longest_zero_run` | longest constant run whose value is `0` |
| `longest_nonzero_const_run` | longest constant run whose value is not `0` |
| `longest_const_run` | longest constant run of any value |

A **constant run** is consecutive rows with exactly equal values
(`x[i] == x[i-1]`); its length is counted in rows, a lone row is a run of 1,
and an empty series gives 0. Every constant run has a single value, so
`longest_const_run == max(longest_zero_run, longest_nonzero_const_run)`.

The MF-DFA fit-start guard uses `longest_const_run` only: a detrended window
that falls entirely inside a constant stretch has zero variance whatever the
constant's value. The QC table is human-facing; the MF-DFA engine computes
its own statistics and does not read these columns.

## Stage 5 — Output files

Under `saved_files/{participant}/` (resolved next to the app file):

- `puzzle_NN.csv` — one per non-empty series, single column `distance`, no
  index, no timestamps. Numbering is contiguous over **saved** chunks, so on
  an incomplete recording it follows the surviving order.
- `qc.csv` — the QC table, written next to the puzzle files. Its name never
  starts with `puzzle_`, so a `puzzle_*.csv` glob never picks it up.

Empty series are not saved. Files are overwritten on each save.

## Constraints and gotchas

- **No timestamps in the output.** Row order is meaningful; row number is an
  observation index, not elapsed time. MF-DFA scales are counted in retained
  observations, not seconds.
- **Gaps are invisible.** A displacement can span several original sample
  intervals when invalid, blink, or off-screen rows were removed. Zero steps
  do not create gaps because they are retained.
- **Off-screen is not "invalid" in the export.** Flagged-valid rows outside
  `[0, 1]` are filtered out, not flagged; the output records them only
  indirectly through `removed_pct`.
- **Puzzle position ≠ puzzle ID.** The notebook maps `puzzle_NN` to the
  actual puzzle.
- **Incomplete recordings.** A missing SPACE drops that phase; the app warns
  when the chunk count differs from 9 but does not block processing.
- **Idle `KB` is a literal space** (`' '`), not `""` or NaN — the marker walk
  uses `KBS == 1` down-events and exact strings.
- **Old exports are stale.** Files generated before the on-screen filter
  (2026-11-22) have different counts and may contain super-diagonal
  displacements; regenerate before analysis.

## Pilot reference (`data/User 0_all_gaze.csv`)

- 114,646 rows × 60 columns; 54 keyboard event rows (9 puzzles × 3 keys ×
  down/up); all nine RETURN-down rows are valid and non-blink.
- 9 chunks; 56,380 raw rows; 52,379 retained coordinates; **52,370
  distances**; 4,647 zeros (8.9 %); 7.1 % of rows removed (245 of them
  off-screen).
- Per-puzzle distances: 714, 5,378, 17,224, 10,076, 6,919, 3,402, 2,793,
  3,483, 2,381. Maximum displacement 0.552 (≤ screen diagonal √2).
- The full expected per-puzzle table is the verification checklist in
  `PLAN.md`.
