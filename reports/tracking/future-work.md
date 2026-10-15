# Future work: tracking

Started 30 September 2026, 09:09 SAST. These are notes for a later version of the tracker. None of them
changes the 15:39 model.

## 1. V2, a lock-time corner term (stopped; not adopted)

**Where it is recorded:** `reports/V2_DEVELOPMENT_2026-09-30.md` and `runs/dc2_results/rule/V2_PREREG.md`.
Uzayr accepted the stop on 30 September. There is no new option and no re-tuning.

- **Option 3,** the start readers on the final recipe: +2.29 [-0.21, 5.00]. The interval reaches below
  0, so it was not adopted.
- **Option 4,** a lock-time corner term (w4 0.5): +6.25 [2.71, 9.79], and corner-pair lock errors
  61 -> 41. But E_row5's lock fell from 10 to 5 of 18: the NW corner was over-corrected towards D_fwd, and
  the edge guard failed.
- **For a later version:** a corner term that treats the NW corner differently would be a new,
  pre-registered option, judged on the rotations.

## 2. The time-step units

**Where it is recorded:** `reports/DT_MISMATCH_2026-09-30.md`.

- **For the 15:39 model: disclosed.** The late-entry reach and cost, the minimum transit windows and the
  transit clock are in 1 s units inside the 0.5 s decoder. They change none of 360 decisions on the
  rotations.
- **For any later version: fix them.** Put all three in 0.5 s units, clock 16, as V2-B did.
