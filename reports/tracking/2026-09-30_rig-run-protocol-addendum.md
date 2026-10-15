# Rig run protocol, addendum of 30 September 2026: one press per walk

**What it amends.** `reports/RIG_RUN_PROTOCOL_2026-09-29.md`, section 3, items 2 and 4. Everything else
there stands, including the idle period before the first walk and the 5 s of stillness between walks.

**Why.** Since 30 September the live app is the tracking model (Uzayr: one model, and it is the live
app). Its headline mode is SEMI-CONSTRAINED, the mode every reported figure uses. In that mode the app
is given one press per walk and nothing else.

## 1. The command

As before. The rig now runs the semi-constrained mode by default:

```bash
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live rig --baseline "$BASE" --minutes 20
```

**The fully constrained mode** (start and end presses; an upper bound, never the headline) is
available for a comparison run:

```bash
OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.final_model rig --baseline "$BASE" --minutes 20 --mode full
```

**At start,** the rig prints its mode and what SPACE means in it.

## 2. Each walk: ONE press (replaces item 2)

**The walk:** unchanged.
- The participant walks one of the 12 taped lines, in its direction, at their natural pace.
- They start a step or two before the start tape.

**SPACE, once:** at the moment the walker crosses the line's start tape (0 m).
- **There is no end press.** Do not press at the end tape. A second SPACE would start a new walk.
- **The app ends each walk itself:** at its own causal exit, or at the next start press, whichever
  comes first.

**Order:** unchanged. Any lines, in any order.

## 3. What the screen shows (replaces item 4)

**The dot and the lock:**
- the dot, 2.0 s behind real time;
- the room centre until 2.0 s after the press; then the dot is at the locked line's entry, and it
  stays there until the first decoded position, 0.6 s later;
- the lock, 2.0 s after each press. It never changes afterwards, except by at most one marked mid-walk
  switch.

**At the walk's end, the banner** "committed at the causal exit", naming the app's committed line. Live
there is no ground truth, so it says NO GROUND TRUTH.

**The summary** in `runs/live/rig/` now also records the mode, the first lock of each walk and any lock
change after it (there should be none).

## 4. Figures to expect

**Unchanged until the app's own figures exist.** They will be in `reports/LIVE_APP_MODEL_2026-09-30.md`,
from replays of the recorded sessions through this same app, one press per walk.
