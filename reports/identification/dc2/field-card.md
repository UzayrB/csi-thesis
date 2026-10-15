# DC2 identification: field card (version d)

**SEAT:** (-1.0, 0.5), fixed for all of DC2, with the laptop and a powered hub. Keep still while
recording.
**RX2:** home at (-0.5, 2.5) facing east. Identification spot at **(2.0, -0.5)**, or (1.5, -0.5) as
set at the rehearsal, facing north. 4 m cable. Align with the tape and arrow, photograph at every
move, and note the time.

**PATH:** line A (`A_fwd`), from (2.5, 0) to (2.5, 5), walking AWAY from the TX. Press at **every
metre, 0 m to 5 m, six presses per pass**. Stand still 5 s at the start before each pass; stop just
before RX1; walk back around the outside with no press.

**SLOT**, per person. Every command starts `PYTHONPATH=. python3 -m pipeline.identify.capture_idpath`.

1. RX2 to the spot, facing north, then `--empty --position idspot --participant <code> --day <d> --move-time HH:MM` (30 s, nobody in the grid)
2. Walks. Day 1: `--participant <code> --day 1 --block natural` (10 passes).
   Day 2: `--block natural` (5), then `--block slow` and `--block fast` (5 each). Odd codes slow
   first, even codes fast first.
   Add `--shoes "..." --clothing "..." --nothing-carried`.
3. RX2 home, facing east, then `--empty --position home --participant <code> --day <d> --move-time HH:MM`
4. Tracking, per the tracking protocol.

**ORDER:** day 1 runs P1 to P6, day 2 runs P6 to P1 (`--plan-day --day <d>`).

**IF A BLOCK ENDS SHORT:** `--participant <code> --day <d> --block <b> --amend-count-reason "why"`.
