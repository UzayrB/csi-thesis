# DC2 addendum 2026-09-28 (relabel): PA5's day 1 labels, and PA1's day 1 baseline. POST HOC

**Written 2026-09-28 from 07:51 SAST, read from the clock.** Both days of Room B data exist, so both
changes below are POST HOC, in those words. No model had been run on Room B and no Room B figure
existed when they were made. Both are Uzayr's decisions of 2026-09-28. No model, constant, arm or
CSI file changes.

## 1. PA5, day 1 (B1): one extra press removed from the ground truth

**What happened.** During PA5's tracking walk the operator pressed space a second time at the
end of pass 9, 0.988 s after its last press (t_mono 771902.2665, laptop clock 13:11:36.8), with
PA5 still standing there. The capture tool has no minimum gap between presses and closes a pass
on its sixth press, so every later pass closed one mark early. Passes 10 to 20 each held the
previous pass's real 5 m press followed by their own real 0 to 4 m presses. The tool flagged all 11
("anchors 1->2 ... implies a SPURIOUS press"). The recording stopped on the 120th press, which was
pass 20's real 4 m mark, so pass 20's real 5 m press was never recorded.

**The evidence**, from press times only; the radio was not examined:
- In all 32 walk recordings of Room A and Room B, a first press within 3 s of the previous pass's
  last press occurs only here, on all 11 passes.
- That gap equals one mark interval of the line just walked: about 1.1 s after a diagonal (1.41 m
  between marks) and 0.85 s after a straight line (1 m).
- After the relabel, her pace is 1.17 to 1.34 m/s and her gaps between passes 7.6 to 17.8 s,
  matching her own passes 1 to 8 (1.20 to 1.31 m/s; 9.3 to 15.4 s).

**The rule.** Delete the one extra press (recorded as pass 10's first press), then regroup the
remaining presses in sixes, in order:
- passes 1 to 9 are unchanged;
- passes 10 to 19 get their six real presses;
- pass 20 gets its five real presses (0 to 4 m) and an ESTIMATED 5 m mark: the 4 m press plus the
  median of its own four intervals, 0.828 s. No radio exists at that time, because the recording
  ends 0.06 s after the 4 m press. The estimate therefore labels no window's position; it sets
  only the pass's end time. Pass 20 is kept, so PA5 has 20 passes as pre-registered.

Only `anchor_times`, `t_start`, `t_end`, `flagged` and `flags` of passes 10 to 20 changed, and
`n_flagged` went from 11 to 0. Every re-grouped pass passes the capture tool's own `validate_pass`.
The file name, the JSON layout (2-space indent, no trailing newline) and every other field are
unchanged.

**One judgement call.** The extra press is taken as the press 0.99 s after pass 9 ended, which keeps
pass 9 exactly as captured and as the tool validated it. The only other candidate, pass 9's own
first press, gives pass 9 the same pace (1.59 m/s, her fastest pass that day), so the press times
cannot separate the two.

**The files.**

| | sha256 |
|---|---|
| original, kept at `data/room_B/aborted/pa5_d1_gt_before_relabel/participant_PA5_walk.gt.json` | `b91337c64e397f66287f243864068bf13421830a93f1aaef48c0bba54c019807` |
| relabelled, at `data/room_B/session_B1/participant_PA5_walk.gt.json` | `35aeb15ad66d857ac9488c058f0d88f2aecc004e6d814fc7dc9b5411b2c889b0` |

The three CSI files and the run record are byte-identical to before. After the change
`python3 -m tools.dc2_day_check --day 1 --final` reports PA5 at 20 passes and 0 flagged. Its only
remaining problem is the cross-day manifest false alarm (`tools/dc2_day_check.py:76` hands the
manifest check this day's session alone), which is separate from this change.

## 2. PA1, day 1 (B1): PA2's baseline is accepted

PA1's own 11:54 baseline lost RX2 and was moved to `data/room_B/aborted/pa1_d1_no_rx2/`. His
tracking recording (12:09) names PA2's baseline `20260926-110249`, taken 66 minutes earlier with
RX2 at home. That baseline is used as recorded, and this is disclosed beside every Room B figure.
Between the two, RX2 was moved to the identification spot and back.

## 3. For every report

Any Room B tracking figure states both changes. PA5's passes 10 to 20 are evaluated on the
relabelled times. A reader can reproduce the original labelling from the preserved file above.
