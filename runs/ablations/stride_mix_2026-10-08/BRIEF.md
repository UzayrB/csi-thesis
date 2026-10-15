# Brief (Uzayr, 8 October 2026), verbatim

Message with the brief, about 13:33 SAST: "the machine is yours for now, i am havinng lunch. start this monitor, caffeinate and everything"

```text
Brief (tracking, stride ablation): does the five-head pool's stride mix matter?

Arms, all on the final recipe (shared encoder, relative RSSI, augmentation, 24 epochs):
- MIX: the shipped mix, 1 head at a 0.5 s training stride + 3 seeds at 1 s + g100 at 1 s
- ALL05: all five heads at a 0.5 s stride (4 seeds of 25 cells + g100)
- ALL1: all five heads at a 1 s stride (4 seeds of 25 cells + g100)
All arms are applied to the same press-aligned 2 s windows at a 0.5 s stride, and decoded with the shipped decode (variant relgateU+abstain+a2w0.25, semi mode).

Data: the three training rotations only (A1+A2 to B1, A1+B1 to A2, A2+B1 to A1), the existing d1sp_* cells. Never touch A3 or B2. Three seed sets per arm.

First, before any training:
1. Read the dwell ablation (runs/ablations/dwell_aid_2026-10-06/: PLAN.md, train_one.py, run.py, REPRODUCE.md) and reuse its machinery.
2. Check whether the d1sp_* heads are the final recipe and can serve as MIX seed set 0. Check that B1's window arrays exist at both strides (re-cut from data/ if not).
3. Write a dated plan (time read from the clock) in runs/ablations/stride_mix_<date>/PLAN.md, with the primary measure (pooled committed-line error, arm minus MIX, mean over seed sets with an interval) fixed in advance. Commit and push it, then wait for my go-ahead before training.

Rules: one GPU job at a time under the watchdog, nohup for long jobs, no caffeinate unless I ask, never overwrite outputs, commit named paths only. Nothing in the shipped model changes, whatever the result.

Report: committed and lock for each arm and rotation, with intervals and the edge lines (E_col1, E_col5, E_row1, E_row5) beside every pooled figure, labelled "development evaluation, all data seen". Say plainly whether the stride mix matters.
```

The same message asks for caffeinate and for the run to be started and monitored, which this run takes as the go-ahead of
step 3 given in advance: the plan is committed and pushed first, and training starts after that without a further wait.
