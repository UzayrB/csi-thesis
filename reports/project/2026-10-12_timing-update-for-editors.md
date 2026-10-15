# Timing update for the report: parallel window extraction kept (12 October 2026)

Written by the Mastermind at 2026-10-12 11:50 SAST (clock read), for the next Editor session of the report repository. Both Editor sessions had closed when this was ready, so it could not be sent by message. **Every accuracy figure is unchanged. Only identification's timing changes.** Uzayr gave the go for this job in the identification chat (Agent1). An Editor whose rule needs his go in its own chat should ask him.

## What changed, and the proof that no decision moved

The live app now extracts each walk's three windows (0, 0.15 and 0.30 s after the press) in parallel, in a warm pool of three worker processes made at app start, instead of one after another. Each worker runs the engine's own extraction on a frozen copy of the data, and `engine.py` is unchanged.

The change is timing only:
- all 897 windows of B2 are bitwise identical, pool against serial;
- the live app is bit-identical to the serial app on all 299 B2 decisions (CPU);
- on the GPU, 299 of 299 decisions equal the v5 replay, with ensemble difference 0.

**Sources:**
- `Code/reports/identification/2026-10-12_parallel-extraction.md` (commit 03952698). Section 6 is its own Editor list.
- The run: `Code/runs/identify/v5/rig_timing_confirm_par2.json` and `rig/rig_timing_confirm_par2_20261012_104115.npz`: B2's whole day streamed at 1x through the real serial parser, on the GPU, 12 Oct 10:41 to 11:46. The Mastermind recomputed every figure below from these files.
- Code: commit 5e4193a6 (re-adopted in d5cd118b).

## Chapter 3 (Section 3.6 and Figure 3.4)

| figure | was (serial, 11 Oct) | now (parallel, 12 Oct) |
|---|---|---|
| decision after t0 + 4.0 s, median | 1.05 s | **0.71 s** (0.714) |
| decision after t0 + 4.0 s, at most | 1.32 s | **0.81 s** (0.813) |
| within the cap of t0 + 5.30 s | 298 of 299, one miss of 0.015 s | **all 299** (the one-miss clause goes) |
| from the last window's data to the decision | (not stated) | median 0.39 s, at most 0.48 s |

- Still true: the calibration after each decision, never waited for, and the CPU sentence.
- Add one clause to 3.5 or 3.6, in the Editor's wording: the three windows are extracted in parallel worker processes, which changes the timing only, never a decision.

## Results (Section 4.5, `tab:latency`, `tab:compliance`)

| figure | was | now |
|---|---|---|
| decision after t0 + 4.0 s, median / at most | 1.05 / 1.32 s | **0.71 / 0.81 s** |
| within the cap | 298 of 299 | **299 of 299** |
| classification of the three windows, median / at most | 0.140 / 0.167 s | 0.139 / 0.167 s (classification alone; the extraction now runs in the workers, each window a median 0.33 s, in parallel) |
| calibration after each decision, median / at most | 0.29 / 0.55 s | 0.26 / 0.51 s (still never waited for) |
| the stream's lag at a press, at most | 0.01 s | 0.01 s |
| the run's date | 11 Oct | 12 Oct |
| compliance, Latency row, from the last window's data to the decision | 0.718 / 0.980 s, Met Y / N | **0.387 / 0.484 s, Met Y / Y** (all 287 decisions made during the stream within 0.5 s; the 12 closing-poll decisions trivially) |

- Section 4.6's sentence that "tracking meets its timing targets" needs revisiting. Identification now meets the latency target too, though not the update interval, since it decides once per walk.

## Not for the report

Memory is not mentioned anywhere in the report (Uzayr's rule). The memory rule for this run was redefined by Uzayr after a first run on 12 Oct had been reverted, and fixed before the second run. The Code report documents this (`2026-10-12_parallel-extraction.md`).
