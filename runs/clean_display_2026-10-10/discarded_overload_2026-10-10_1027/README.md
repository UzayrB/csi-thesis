# Discarded: the first render attempt, stopped for overload (10 October 2026)

**Stopped at 10:27:29 SAST (clock read), on the Mastermind's instruction.** The machine was overloaded: load 21.7 at
10:26 with 15 heavy processes on 10 cores (6 look replays, 6 real-time renders, and Third overall's 2 CPU and 1 GPU).

**Why the renders were not at lower priority:** the render driver itself ran under nice 19 and started each replay with
`nice -n 19` on top of that, and nice adds up. So the renders ran at 20, the same as the looks (whose driver was niced
10 and its replays 10 more).

**What is here:** the six partial A3 videos (started 10:22:38, under five minutes of real time each; three are empty
headers of 261 bytes) and the render logs. No replay log was written: `semi_disp-K1gf_causal_realtime_screen` did not
exist yet, and RENDERS.json was not written. Nothing here is used. The renders are re-run after the semi looks,
`nopress` and `fullcheck`, at most 3 at a time, with the load average recorded beside the ACCEPTANCE.
