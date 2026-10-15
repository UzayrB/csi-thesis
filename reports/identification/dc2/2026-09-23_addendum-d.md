# Pre-registration addendum D: DC2 identification, an erratum to addendum B

**Written on 2026-09-24 at 09:04 SAST, read from the clock.** No DC2 data existed at the time of
writing: `data/room_B` did not exist, checked at 09:03:50. Its SHA-256 is recorded in
`runs/IDENTIFICATION_FROZEN_2026-09-23g.json`, which references the 23f freeze and supersedes
nothing. The erratum was approved by Uzayr.

**This addendum changes no analysis.** Every configuration, analysis, statistic, verdict rule and
expectation in the pre-registration and addenda B and C stands exactly as frozen. The scorers
(`id29_dc2_score.py`, `idgp_dc2_score.py`) and every earlier pre-registration file are unchanged.
This file corrects a record of WHEN addendum B was edited. It does not change WHAT addendum B says.

## The error

Addendum B states that it was written at 18:48 SAST, and that P2, P3 and P6 were amended at 19:20,
19:35 and 19:55 SAST "before freezing". It also stamps four sections with times:

- P2's single-link note, "added at 19:35";
- P2's two-version note, "added at 19:20; figures corrected at 19:45";
- P3's reading notes, "added at 19:20";
- P6, "amended at 19:55".

These amendment times were estimated, not read from the clock. **They cannot be right**, because
addendum B's SHA-256 was frozen in `runs/IDENTIFICATION_FROZEN_2026-09-23e.json` at 19:08:10, and
that hash matches the file today.

## The correct times

**Sources.** The session that wrote addendum B logs every tool call with a UTC timestamp (Claude Code
session log `201c1360`, converted to SAST, UTC+2). The file's modification time on disk (19:05:45)
and the 23e freeze's `frozen_at` (19:08:10) agree with it.

**Git cannot establish them.** The file's first commit is the cleanup snapshot `3c3c779`, on
2026-09-24 at 05:39, so no earlier version of it exists in git or at the tag `pre-cleanup`.

| what addendum B says | time stated | time established | what the edit did |
|---|---|---|---|
| written | 18:48 | **18:48:42** (whole file), rewritten at **18:50:59** | the first text |
| P2 two-version note and P3 reading notes | 19:20 | **18:53:42** | added the segment-length finding, the full-length and fixed-length P2 rows, and the P3 notes |
| P2 single-link note | 19:35 | **18:55:51** | added the single-link extraction |
| P2 figures corrected | 19:45 | **18:58:59** | corrected the leak figures (25 to 33 and 17 to 29 percent) and softened the P3 note |
| P6 single-link | 19:55 | **19:05:44** | made P6 single-link on TX-RX3, and updated the header |
| frozen | | **19:08:10** | 23e freeze written |

**Every amendment was made before the 23e freeze, and the order stated in addendum B is right.**
Only the clock times are wrong: each is between 26 and 49 minutes late. The content addendum B
froze is the content scored.
