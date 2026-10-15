# Addendum A to `reports/PREREG_ID_2026-09-23.md`

**Written 2026-09-23 01:25 SAST, during the tracking gate. NO CSI HAS BEEN READ BY THIS RUN, and no
identification number of any kind exists yet, on a corridor or otherwise.** This addendum changes a
pre-registered rule, so it is written now rather than after the numbers, and the change is
disclosed in those words.

Evidence: `pipeline/identify/id15_factor_map.py`, `runs/identify/id15_geometry/results.json`, and
figures F17 and F17b. All of it is geometry. It reads the taped line coordinates from the
ground-truth sidecars and the fixed node positions, and nothing else.

---

## 1. What was found

The pre-registered corridor gate (section 5 of the pre-registration) strikes out any line on which
**any link spends more than 25 percent of its length below F = 0.3**.

**All twelve taped lines in Room A are struck out by that gate.**

| line | length | mean F | min-link mean F | worst link | fraction below F = 0.3 |
|---|---|---|---|---|---|
| E_row1 | 5.00 | 0.474 | 0.458 | RX2 | 42 % |
| E_row5 | 5.00 | 0.410 | 0.386 | RX2 | 35 % |
| C, D (all four diagonals) | 7.07 | 0.451 | 0.368 | RX1 | 43 % |
| B_fwd, B_rev | 5.00 | 0.455 | 0.363 | RX1 | 38 % |
| E_col1, E_col5 | 5.00 | 0.337 | 0.142 | RX1 | 91 % |
| **A_fwd, A_rev** | 5.00 | 0.333 | **0.000** | RX1 | **100 %** |

**Line A is pathological and it is exact, not approximate.** A runs from (2.5, 0) to (2.5, 5); the
TX sits at (2.5, -0.5) and RX1 at (2.5, 5.5). The walk is therefore straight along the TX-RX1 sight
line, where the two unit rays are anti-parallel and cancel, so **F is identically zero for the whole
pass on that link**. A person walking line A produces no RX1 path-rate content at any speed.

**And it is not a matter of choosing a better line.** A search over every straight directed segment
of 7 m, 5 m and 4 m that fits inside the room, at 36 angles and a 0.25 m origin spacing, returns
**no compliant corridor at any length**. The best achievable anywhere in Room A is a mean F of about
0.52 with the worst link still below F = 0.3 for 38 percent of the path.

## 2. The rule change, and its narrow scope

**For the Room A corridor pilot only, the strike-out rule is suspended and replaced by ranking.**
Candidates are ranked by min-link mean F, then by M1, M3, M4 and M5 as already registered, and the
bad fraction is reported beside every candidate. **No candidate is removed**, because applying the
rule as written leaves zero candidates and the pilot could not run at all.

**The strike-out rule remains binding for DC2 and is not weakened there.** It moves from being a
corridor-selection rule to being a **node-placement** rule, per section 3.

**R5 is unchanged and now carries more weight, not less.** The corridor result on Room A data is a
pilot, it supports no claim on its own, and it is now known in advance to be running on geometry
that cannot meet the standard. **Any corridor pilot result, positive or negative, is therefore
confounded with a geometry that was never suitable, and the report must say so in those words.**

## 3. What this hands DC2, which is the useful part

A search over 543,004 node layouts on a 5 by 5 room perimeter, scoring the 7.07 m diagonal:

| nodes spread over | best min-link mean F | worst link below F = 0.3 | verdict |
|---|---|---|---|
| **2 walls** (clustered at the corridor's origin corner) | **0.938** | **0 %** | **passes** |
| 1 wall | 0.835 | 5 % | passes |
| 3 walls | 0.456 | 32 % | struck out |
| 4 walls | 0.456 | 32 % | struck out |
| **4 walls, the current Room A layout** | **0.373** | **43 %** | struck out |

**No layout that spreads the four nodes over three or more walls passes the gate.** The trade-off is
hard, not gradual, and the crossover sits between two and three walls.

**The physical reason.** F is near 1 when both rays are roughly parallel to the walk, which happens
when the nodes sit ahead of or behind the walker along the walk axis. That is the doorway geometry
WiWho and Gate-ID use, and it is why they work. Spreading nodes around the perimeter, which is what
multilateration wants, guarantees that some link is near-anti-parallel to the walk over part of its
length, and that link contributes a flat spectrogram.

**This is a direct conflict between the two branches of this project, and it is Uzayr's decision,
not this run's.** Tracking wants spatial diversity. Gait Doppler wants the nodes gathered near one
end of the walk. The current rig is configured for tracking, and **the projected Doppler factor on
the best Room A line is 2.5 times lower than a gait-first layout would give.** It is recorded here
as a measured trade-off so that the DC2 layout is decided with the number in hand.

## 4. What does NOT change

Nothing else in the pre-registration moves. The feature groups, the heads, the nine pairings, the
speed policy, the validation gate, R1 to R4, R6 and R7, and the three outcomes all stand exactly as
registered. This addendum touches the corridor gate and nothing else.
