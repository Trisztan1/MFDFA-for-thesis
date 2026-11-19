# Code Review Report

**Document:** Gaze Processor Data Summary for the MF-DFA Project

## 1. Review Metadata

- **Date:** 2026-11-19
- **Purpose:** Concise, self-contained reference for agents in the separate MF-DFA repository that consume gaze-processor exports.
- **Basis:** Current `PLAN.md`, `AGENTS.md`, `architecture.md`, the archived QC feature specification, and the previously completed review/verification reports.
- **Status of this summary:** Documentation synthesis. No new code execution was performed for this document; numerical statements come from the completed project verification records.

## 2. Executive Summary

The `gaze_processor` project is a single-user Streamlit utility for a psychology master's thesis. It converts Gazepoint eye-tracker recordings of participants solving nine chess puzzles into one ordered gaze-displacement series per puzzle for later MF-DFA analysis. MF-DFA itself is performed in the separate project.

### 2.1 Processing workflow

```text
Gazepoint CSV
  -> identify thinking phases from keyboard markers
  -> retain valid, non-blink, numeric gaze coordinates
  -> calculate displacement between consecutive retained coordinates
  -> show a per-puzzle QC table
  -> save one puzzle_NN.csv per puzzle plus qc.csv
```

The owner processes one participant recording at a time, manually assigns the participant folder name, checks that exactly nine non-empty `puzzle_NN.csv` files were produced, and excludes participants without nine valid files. Puzzle identity is recorded in the owner's notebook; it is not present in Gazepoint or the exported CSVs.

### 2.2 Required input fields

| Column | Meaning | Use |
|---|---|---|
| `BPOGX`, `BPOGY` | Binocular-average normalized gaze coordinates, documented as 0–1 | Coordinates used to calculate displacement |
| `BPOGV` | Gaze-validity flag | A sample is retained only when `BPOGV == 1` |
| `BKID` | Blink flag/identifier | A sample is retained only when `BKID == 0` |
| `KB` | Keyboard marker name | Compared with exact strings `RETURN`, `SPACE`, and `BACK` |
| `KBS` | Keyboard state | Only `KBS == 1` key-down events drive chunking |

### 2.3 Thinking-phase chunking

Only keyboard-down events (`KBS == 1`) are considered:

- `RETURN` opens a thinking phase at that row.
- A repeated `RETURN` does not replace the first start; rows between the presses remain included.
- `SPACE` closes the phase. The SPACE-down row itself is **excluded**.
- `BACK` before SPACE discards the unfinished phase.
- An unmatched SPACE is ignored.
- A phase still open at end-of-file is discarded.

Each completed chunk therefore includes its RETURN-down row and all subsequent rows up to, but not including, SPACE-down. Execution-phase data after SPACE is not processed. Chunks remain in chronological order.

### 2.4 Exact preprocessing sequence

For each chunk:

1. `BPOGX` and `BPOGY` are converted with `pd.to_numeric(..., errors="coerce")`.
2. Rows failing `(BPOGV == 1) & (BKID == 0)` are removed.
3. Rows with missing/coerced-to-NaN X or Y are removed.
4. Consecutive retained coordinates are differenced.
5. Displacement is calculated as:

```text
d_i = hypot(x_i - x_(i-1), y_i - y_(i-1))
    = sqrt((x_i - x_(i-1))^2 + (y_i - y_(i-1))^2)
```

6. The first undefined distance is dropped. With `N` retained coordinates, one series has `N-1` displacement values.

The operation is a **displacement**, not a velocity: it is not divided by time.

### 2.5 Zero displacements

Zero-length steps are intentionally retained. Two consecutive identical retained coordinates produce `distance = 0.0`. Downstream MF-DFA code must accept zero values and must not remove them as invalid.

### 2.6 Invalid samples and temporal gaps

Filtering occurs before differencing. If invalid or blink rows lie between two retained coordinates, the next displacement is calculated directly between those retained endpoints. The removed rows' duration and sample count are not represented.

Example:

```text
Raw:                 A (valid) -> B (blink) -> C (invalid) -> D (valid)
Retained:            A -----------------------------> D
Exported value:      distance(A, D)
```

No timestamps, sample indices, resampling, interpolation, or gap durations are exported. Zero values do not create extra gaps because they remain in the series.

**Critical MF-DFA consequence:** exported row order is meaningful, but row number is an observation index, not elapsed time. Exported rows must not be assumed to represent uniformly spaced time intervals. An MF-DFA scale expressed in exported rows is a number of retained displacement observations, not seconds.

## 3. Findings

### Informational — Exported rows are not guaranteed to be uniformly time-spaced

- **Severity:** Informational
- **Confidence:** Confirmed by documented implementation behavior
- **Location:** Processing and export contract
- **Evidence:** Invalid/blink samples are removed before differencing, only distance values are saved, and timestamps/sample indices are omitted.
- **Problem/impact:** A displacement may span multiple original Gazepoint samples. Treating all rows as fixed-time observations can change the interpretation of MF-DFA scales.
- **Recommended handling:** Preserve row order and document that scales are measured in retained displacement observations. Do not reconstruct timestamps or interpolate without a separate owner decision.

### Informational — Puzzle numbers are chronological positions, not puzzle IDs

- **Severity:** Informational
- **Confidence:** Confirmed
- **Location:** Output filenames and QC table
- **Evidence:** Files are named in processed-chunk order; the owner maps positions to actual puzzles using a notebook.
- **Problem/impact:** Gazepoint and the CSVs contain no puzzle identifier.
- **Recommended handling:** Use the owner's notebook mapping. For accepted participants, the nine saved files represent the nine chronological thinking phases.

### Informational — `qc.csv` is quality-control metadata, not an MF-DFA input

- **Severity:** Informational
- **Confidence:** Confirmed
- **Location:** `saved_files/{participant}/qc.csv`
- **Evidence:** The QC table describes each chunk; the displacement series remain the analysis inputs.
- **Problem/impact:** Treating QC columns as part of a distance series would be incorrect.
- **Recommended handling:** Read `qc.csv` separately, join it by chronological `puzzle` position if needed, and never include it in a `puzzle_*.csv` glob or displacement array.

No code defect is claimed by this summary.

## 4. Diagnostic Investigation

No failure was investigated for this document. The relevant established behavior is:

- A lone retained coordinate produces an empty series.
- A chunk with no valid coordinates produces no puzzle CSV.
- Accepted participants are manually required to have nine non-empty puzzle files.
- `qc.csv` is written next to the puzzle files on Save and does not match `puzzle_*.csv`.

## 5. Architectural Observations

The processing functions are separated as:

- `file_chunking(df)` — marker-based segmentation only.
- `process_file(chunks)` — filtering, differencing, displacement calculation.
- `qc_table(chunks, processed)` — pure per-chunk QC summary.
- `save_processed_file(..., qc=None)` — writes puzzle series and `qc.csv`.

All output is written under the gaze-processor application directory:

```text
src/gaze_processor/saved_files/{participant}/
  puzzle_01.csv
  ...
  puzzle_09.csv
  qc.csv
```

The participant folder name is manually supplied and is the external participant identifier.

## 6. Output Contract and QC Table

### 6.1 Puzzle CSV schema

Each `puzzle_NN.csv` has exactly one column:

```csv
distance
0.0
0.012264098010045459
...
```

- One numeric displacement per consecutive retained coordinate pair.
- Non-negative values; exact zeros are valid and retained.
- No timestamps, sample indices, absolute coordinates, flags, puzzle IDs, or participant metadata.
- Empty series are not saved.
- For an accepted participant, exactly nine non-empty puzzle files are expected.

### 6.2 `qc.csv` schema

One row per detected chunk, in chronological order:

| Column | Meaning |
|---|---|
| `puzzle` | Chronological position 1…n, not a puzzle ID |
| `raw_rows` | Rows from RETURN-down included to SPACE-down excluded |
| `retained_rows` | Retained coordinates, inferred as `distances + 1`; NaN for an empty series |
| `removed_pct` | Percentage of raw thinking-phase rows removed by validity/blink/numeric filtering |
| `distances` | Number of exported displacement rows for that puzzle |
| `zero_pct` | Percentage of exported distances exactly equal to `0.0` |
| `longest_zero_run` | Longest consecutive run of exact-zero distances, in exported rows |

`removed_pct` describes removed raw rows, not removed distances. `longest_zero_run` is intended for human cross-checking against the MF-DFA smallest-scale guard; it is not itself an analysis input.

On the documented pilot recording, the process produced 56,380 thinking-phase raw rows and 52,615 distances, including 4,679 zeros (8.9%); 6.7% of thinking-phase rows were removed overall. `longest_zero_run` was 1 for every pilot puzzle.

## 7. Recommended Action Order for MF-DFA Agents

1. Treat each `puzzle_NN.csv` as one ordered displacement series.
2. Read the single `distance` column numerically and preserve row order.
3. Accept and retain `0.0`; do not require strictly positive values.
4. Never interpret row index as time or assume uniform temporal spacing.
5. Do not interpolate, resample, or remove zeros without an explicit methodological decision.
6. For accepted participants, require nine non-empty puzzle files and map `puzzle_01`…`puzzle_09` through the owner's notebook mapping.
7. Read `qc.csv` separately for quality control; never include it in puzzle-series globs.
8. Interpret values as Euclidean displacements in normalized Gazepoint coordinate units, not physical distance, visual angle, or velocity.

## 8. Remaining Uncertainties

- Whether MF-DFA scales should be interpreted over retained displacement observations or require gap-aware processing from original recordings remains an owner/supervisor methodological decision.
- No coordinate aspect-ratio correction or physical-unit conversion is performed.
- The pilot `longest_zero_run` values are sample-specific and should not be assumed for other participants.
- Existing exports created before the zero-retention change may be zero-free and may lack `qc.csv`; analysis inputs should be generated with the current pipeline.
- The exclusion cutoff based on `removed_pct` is not implemented; it remains a later supervisor decision.
