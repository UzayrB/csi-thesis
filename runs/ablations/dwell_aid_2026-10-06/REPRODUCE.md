# How to reproduce the dwell ablation

The result is in `RESULTS.md` and `results.json`; the design and the decision rule are in `PLAN.md` and `BRIEF.md`.
Every run's own evaluation (`runs/<arm>_k<k>/eval_fin_A3.json`, `eval_fin_B2.json`), training summaries and logs are
kept. The 198 trained model files (`runs/<arm>_k<k>/{art,train}_<head>/models/*.pt`, 71 MB) are not needed to read the
result. They are in git at commit `2efed00d` (6 Oct 2026), so they can be restored without retraining:

    git checkout 2efed00d -- runs/ablations/dwell_aid_2026-10-06/runs

## From scratch

From the repository root, with `PY=/opt/anaconda3/bin/python3` and `OMP_NUM_THREADS=1 PYTHONPATH=.`.

1. **B1's 1 s windows.** Training the 1 s heads needs `runs/constrained/windows_s1.0_dc2/room_B/session_B1/*.npz`.
   If they are missing, re-cut them into a scratch folder and accept them only if every new `meta.json` equals the
   one already at that path, byte for byte (PLAN.md, "Rebuilt input"); then put the `.npz` files back at that path:

       $PY -m pipeline.io.windows --data data --out <scratch> --stride 1.0 --sessions B1

   The cut takes about 1.5 min and writes 2,622 windows (`logs/b1_cut.log`).
2. **Train and decode.** `run.py` trains W and W+D for seed sets 0, 1 and 2 (five heads each, one GPU job at a time
   under its memory watchdog), then decodes `fin_A3` and `fin_B2` for every run on the CPU. A finished head or decode
   is skipped, so a stopped run can be restarted. It holds `caffeinate` for its own lifetime.

       $PY runs/ablations/dwell_aid_2026-10-06/run.py

   On 6 October one seed set of W+D took about 76 min to train, and each decode 28 to 35 min.
3. **Score.** `score.py` reads the twelve `eval_*.json` files and writes `results.json` and `RESULTS.md`.

       $PY runs/ablations/dwell_aid_2026-10-06/score.py

## The shipped-model check

`shipped_check/` is the shipped tracker decoded on B2 by the same evaluator. It reproduced the record exactly
(93.33 committed, 72.50 lock, 0 of 120 decisions changed), which shows the ablation's decode path equals the live
app's. No shipped file was modified: on 6 Oct 2026 every file on `runs/live/models/final.json` (454) and
`zeroshot.json` (218) and on the four hash lists in `runs/dc2_results/final/` re-hashed clean.
