# Pre-registration addendum, 2026-09-24: the DC2 day design, and three pipeline corrections

**Written on 2026-09-24, begun at 17:24 SAST and revised at 17:30 after the identification session's
review, both read from the clock. No Room B data existed: `data/room_B` did not exist, checked at 17:24:18
and 17:29:56.** The decisions in section 1 are Uzayr's, made in
conversation on 2026-09-24. This file amends `PREREG_DC2_crossroom_2026-09-22.md` (tracking) and
`PREREG_ID_DC2_2026-09-23.md` with its addenda B, C and D (identification) without editing them: every
one is pinned. **Where this file and those disagree on how DC2 is captured, this file governs. It changes
no analysis, no model and no constant.** Freeze 23h and its addenda are untouched and still verify.

## 1. The day, as decided

| | decided | replaces |
|---|---|---|
| blocks | **one block per person per day: tracking first, then identification** | the tracking checklist's "at least two separated blocks per person"; the identification sheet's identification-first order |
| receivers | **RX1, RX2, RX3 only.** No RX4. RX2 moves to the identification spot for identification and home for tracking | the checklist's fifth-receiver section |
| static recordings | **none**: no grid sweep (`ground_truth --mode walk`), no per-person standing block, no 60 s standing, no 60 s empty room for tracking | the checklist's calibration block rows 1 and 2, and its standing and off-path rows |
| kept | the reaction-time calibration; **the calibration walks, every day**; identification's two 30 s empty rooms per person | |
| tracking passes | **20 per person per day, Room A's composition** (8 centre directed lines twice, 4 edge lines once) | the checklist's "20 to 30, edge lines over-sampled" |
| identification path | **line A in both directions**: each cycle is one pass away from the TX (`A_fwd`) and one back towards it (`A_rev`), six presses each | "walk back around the outside with no press" |
| identification blocks | **day 1: natural 10, slow 5, fast 5 cycles; day 2: natural 5, slow 5, fast 5.** Natural first, then the participant's pace order by P-code parity (odd P codes slow first), on both days; day 2's order is therefore as sheet 23d had it | day 1 natural only |
| RX2 within a block | **30 s empty room with RX2 at home (-0.5, 2.5) facing east; tracking; RX2 to the identification spot, facing north; 30 s empty room there; the identification walks; RX2 back home.** Two moves per person, as before, each photographed and timed. The home empty room OPENS the block, so, as under sheet 23d, it is recorded with the placement that person then tracks in, immediately before their tracking, and the first person of each day has one | the identification-first order |
| slot order | **unchanged: day 1 P1 to P6, day 2 P6 to P1** (addendum B section 1; `capture_idboth --plan-day`) | |
| folders | tracking in `data/room_B/session_B1` (day 1) and `session_B2` (day 2); identification in `data/room_B/identification/session_01` and `session_02`; nothing is ever written to `data/room_A` | `data/room_B/session_0<day>` for identification |

**Why 20 tracking passes and not more.** The DC2 figure is compared with Room A's 62.50, measured on
this composition. Edge lines are the hardest (every one lost walks on the ONE lattice), so extra edge
passes would pull the pooled Room B figure down against Room A for a reason that is not the room.
The gain is small (12 passes per edge line over DC2 at 20, 24 at 24: a per-line interval of about
28 points narrowing to about 20), and it would need new tracking capture code two days before DC2.

## 2. Tracking: three corrections, found before any data

Found on 2026-09-24 by reading `dc2_pipeline.py` and `dc2_run.py` against the real layout. Both are
pinned and hashed by 23h, so neither is edited: `pipeline/constrained/dc2b.py` replaces the two
functions at fault at call time. **The DC2 commands are now**

    python3 -m pipeline.constrained.dc2b_pipeline --room room_B
    python3 -m pipeline.constrained.dc2b_scorerlock --room room_B

| | the fault | now |
|---|---|---|
| 1 | a Room B folder named `session_01` or `session_02` was silently replaced in the view by Room A's own session of that name, so DC2 would have scored Room A's training data as Room B. **Reproduced** | REFUSED; Room B sessions are `B1` and `B2` |
| 2 | calibration and aborted pass ids were per SESSION and applied to every recording in it; pass ids restart at 1, so a calibration recording's passes 1 to 8 also took passes 1 to 8 of every participant as calibration | the manifest names calibration RECORDINGS and aborted passes per recording (`dc2b_manifest`); the per-session form is refused on real data |
| 3 | an identification recording inside a tracking session was scored as tracking | REFUSED; identification has its own folder |

**Verified before any data.** The stand-in (Room A session 03 dressed as Room B, from raw files) run
through the corrected command equals the shipped decisions **72 of 72, EXACT**, and its fusion
plumbing **72 of 72, EXACT** (2026-09-24 17:14, `runs/constrained/fh/dc2_pipeline_standin/`). The
per-recording form, run on the same stand-in with one participant's recording as the calibration
recording, equals them on every one of the other five recordings' passes, **100 of 100, EXACT**, fusion
plumbing 100 of 100 (2026-09-24 17:21, `runs/constrained/fh/dc2_pipeline_standin_bycal/`). No file
under `data/room_A` was written by either run. Tests: `tests/test_dc2b.py`, each fault
reproduced on the frozen code first, every refusal killed by a mutant.

**What the day design does to the tracking analyses.** Nothing in sections 10 to 13 changes.

- **The calibration block** is one recording per day, participant code `CAL`, `--mode walk`: the first
  8 passes of the default shuffled plan, then `q` straight after the eighth pass's sixth press. Its lines
  are recorded in the manifest. It replaces "2 passes on each of 4 named lines", which the capture tool
  cannot plan without editing `pipeline/io/`. It is walked by a helper, or by the first participant
  before their own tracking, and is never scored.
- **The gate's still level.** The frozen code takes it from `idle` windows, which are the time between
  passes, and never read a standing block as such; the re-anchored gate is confined to [0.20, 0.60],
  Room A's flat region, or falls back to 0.431. Dropping the standing recording therefore changes
  nothing the code does. The null, the constant that matters, is re-anchored on the calibration walks,
  which are kept.
- **One block per person.** Any per-person tracking figure, and the within-DC2 within-day split, are
  confounded with the block and are labelled so. The primary figure pools passes and is unaffected.

## 3. Identification: the pre-registered analyses read exactly what they read before

**P1 to P6 (addendum B) and P1-GP (addendum C) are unchanged and read the same data:** the `A_fwd`
passes of day 1 natural (10 per person) and day 2 natural, slow and fast (5 each), and the empty rooms.
They are scored by the FROZEN `id29_dc2_score` and `idgp_dc2_score`, unchanged, on a view
(`pipeline/identify/idboth_view.py`) that holds only those recordings, with only their `A_fwd` passes.
**On synthetic data, every figure the frozen scorer returns through the view is identical to the 23e
layout's on the same `A_fwd` data** (`tests/test_idboth_view.py`), and a view that let `A_rev` passes
through fails that test.

Capture: `pipeline/identify/capture_idboth.py`, which reuses the frozen wrapper's rules by import.

**The view keeps every refusal the frozen scorers make.** It carries every pre-registered recording
and nothing else, so a missing recording is still missing and the scorer still refuses; the `A_fwd`
passes keep their own times, so the 1.5 to 12 s duration check still applies; the empty rooms are the
captured files, so the 25 s check still applies; and each count is restated for `A_fwd` against the
23e plan, COMPLETE only if it matches, carrying a reason only if `--amend-count-reason` logged one.
The frozen scorers are always run with `--data-root runs/identify/dc2_view/room_B`. Run on
`data/room_B` itself they REFUSE at discovery (the day 1 pace blocks are unexpected recordings, and
the `A_rev` passes are not on `A_fwd`); they never score the new layout by accident.

**The `A_rev` passes and the day 1 slow and fast blocks are outside P1 to P6 and P1-GP**, and the view
excludes them.

**What changes around the `A_fwd` passes, stated so it is not discovered later.**

- The walker reaches the 0 m mark by walking back down line A and turning, then stands 5 s as before;
  before, they came round the outside. The `A_fwd` segment itself, 0 m press to 5 m press, is as
  registered.
- Identification now follows about 7 minutes of tracking walks, on both days alike, so the cross-day
  comparison stays matched.
- After the 5 m press the walker stops, turns and stands 5 s before walking back; before, they stopped and
  walked round the outside. If P1-GP's cadence margin (0 or 0.5 s, chosen by the day 1 ICC, addendum C)
  is 0.5 s, the half second after the 5 m press now covers the stop and turn. The 0 m side is the 5 s
  stand, as before.
- Day 2's slow and fast blocks are no longer the participants' first walks at those paces: they walked
  both on day 1. P3's reading still rests on S0's drop, which is its manipulation check.
- Addendum C section 3 says P1-GP trains on `A_fwd` "by necessity" because DC2 walks only `A_fwd`. That
  is no longer the reason: **P1-GP trains on `A_fwd` because it was pre-registered so, and `A_rev` is
  never added to its training.**

**Secondary analyses, pre-registered now, before any data.** Neither is part of P1's claim or its
family; each reports addendum B's statistics (accuracy, n, chance 16.67, a 95 percent bootstrap over
participants, 1000 draws, and the within-day permutation p). Their scoring code does not exist yet: it
is written and tested on synthetic data, and hashed into a further identification freeze that
references `runs/IDENTIFICATION_FROZEN_2026-09-24.json`, before any identification figure is computed.
It reuses the frozen features and heads.

- **P1-REV.** P1 exactly (PRIMARY, SECONDARY and S0, all three links) on the `A_rev` passes: train on
  day 1 natural `A_rev`, test on day 2 natural `A_rev`. The moved RX2 link has the same geometry
  factor in both directions (0.981 at the primary spot). **It neither replaces nor rescues P1**, and
  any figure pooling `A_fwd` and `A_rev` is exploratory.
- **P7, pace-matched cross-day.** PRIMARY and S0 on `A_fwd`: train on day 1 slow, test on day 2
  slow; the same for fast. It asks whether identity crosses days when pace is held.

**Everything else on the `A_rev` passes or the day 1 pace blocks is EXPLORATORY** unless a further
addendum registers it before any identification figure is computed.

## 4. What does not change

The model, the heads, the decoder, every constant and every arm of freeze 23h. The chance levels. The
ship rule. Calibration passes are never scored. A pass is excluded only if aborted at capture time,
never for scoring badly. Node geometry is Room A's, except RX2 at the identification spot during
identification, as addendum B has it. The operator seat is (-1.0, 0.5).

## 5. The freezes

This addendum and the code it names are hashed in `runs/TRACKING_FROZEN_2026-09-24.json` (the `dc2b`
files; it references 23h and its addenda) and `runs/IDENTIFICATION_FROZEN_2026-09-24.json`
(`capture_idboth.py` and `idboth_view.py`, since the view decides what the frozen scorers read; it
references 23g), and re-hashed by `tests/test_freeze_2026_09_24.py`. The hardware rehearsal may still
find a fault in the capture code. Any change before Room B data exists gets a new dated freeze that
supersedes these, never an edit of them; any change after is POST HOC and says so.
