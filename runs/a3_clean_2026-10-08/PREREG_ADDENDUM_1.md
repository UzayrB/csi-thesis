# PREREG addendum 1, 8 October 2026, 19:33 SAST (clock read): A1's remaining arms on four processes

**Compute only.** The arms, data, objective, selection order, rules, the committed-lines gate and the plumbing gate of
`PREREG.md` (SHA-256 bf0284de...) are unchanged.

**Why.** Uzayr asked both jobs to push while the machine was quiet. At about 19:30 the primary chat allowed A1's remaining
arms to be split across up to 4 niced CPU processes, under three conditions:
- disjoint arm subsets;
- no shared in-progress folder;
- B1's lane left to finish its running arm.
This replaces section 8's "at most 2 processes" for A1 only.

**What was done.**
- **B1 and A2 had finished** (A2 exit 0 at 19:18; B1 exit 0 at 19:26). Both plumbing gates had passed EXACT (A2 17:15,
  B1 17:16).
- **A1's lane passed its plumbing gate.** It started at 19:26 and wrote the shipped arm `sd4.5_soft_w1.0` at 19:32:31: EXACT
  against DT0, 120/120 committed, display lock and scorer lock.
- **That process was then stopped,** at 19:32:31 (PID 27985, started by this run; its command line was checked first). Its
  lane logged "A1 EXIT 241".
- **It had just created the next arm's folder,** `lock/decodes/A1/sd2.5_soft_w1.0`. The folder was empty, with no outputs,
  and was removed.
- **The 31 remaining arms run on four processes** (`run_lock_a1.sh`), in disjoint round-robin subsets of `lock_side.GRID`
  order, recorded in `lock/logs/A1_split.txt` (8, 8, 8, 7 arms). Each process fits its own readers, fresh, as in section 1.
  The driver is unchanged (its `--arms` option).
- **Limits unchanged:** CPU only, one thread and `nice -n 10` per process, writes only in this folder, pause below 25 %
  system free memory.

**No result had been read** when this was written. The only figures seen were the per-arm log lines (committed lines changed:
0 on every arm; the count of display locks changed) on B1 and A2, and no selection had been computed.
