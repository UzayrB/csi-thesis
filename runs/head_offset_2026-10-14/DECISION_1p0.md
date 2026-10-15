# Uzayr's decision: ship the 1.0 s head offset over the rule's winner (14 Oct 2026)

**Received in Agent1's own chat at or before 12:35:39 SAST, 14 Oct 2026** (the prompt "Mastermind: ship the 1.0 s head
offset (Uzayr's decision, 14 Oct 2026)", pasted by Uzayr; given first to the Mastermind, which paused the 0.875 s A3/B2
decode at 12:32:19 so that no more test data was decoded while it reached this chat). Recorded here at 12:38. Written
AFTER the development-rotation results (`SELECTION.json`, c7bb0985) were seen. It overrides the choice the committed
rules made (0.875 s). No rule file is edited: `PREREG.md` and its two addenda stand as the record of what the rules chose.

**State when it was made:** the rules had chosen 0.875 s; the A3/B2 decode with 0.875 s had started at 12:23:01 and was
paused at 12:32:19 with 4 of 6 A3 recordings and 1 of 6 B2 recordings complete and logged, none scored or read.

## The decision, as written (section 1 of the prompt, verbatim)

> Uzayr chooses the **1.0 s head offset** over the rule's winner of 0.875 s. Record it in the run's record and in the
> Decisions Log, with this reason and disclosure:
>
> - **Why:** each position is drawn at its own window's centre, the moment it describes. The marker therefore sits level
>   with the truth: mean signed offset −0.039 m [−0.102, +0.021] against −0.347 m shipped, with the lowest median,
>   0.311 m. This removes the 0.25 s lag and the start glide, which simplifies the whole display.
> - **The rule it overrides:** the pre-fixed display-only guard. On one walk of the A2 rotation, the drawn line made a
>   switch it did not make before. The lock and the committed line were unchanged on that walk and on every other walk.
> - **Disclosure:** chosen after the development-rotation results were seen, against a guard fixed beforehand. This is
>   the third such decision, after the two of 12 Oct. A3 and B2 had not been decoded with any new arm when it was made.

**A correction to the disclosure's last sentence, for the record (it does not change the decision):** when the decision
was made, A3 and B2 HAD begun to be decoded with the 0.875 s arm (12:23:01 to the pause at 12:32:19: A3's PA5, PA1,
PA2 and PA3 recordings and B2's PA5 recording complete and logged). No result of that decode was scored or read
by anyone. The 1.0 s arm had not touched A3 or B2.

## The rest of the prompt (steps 2 to 8), verbatim

> ## 2. Stop the 0.875 s test decode
>
> If the A3 and B2 decode with 0.875 s has not finished, stop it and discard its partial outputs. If it has finished, keep
> its record, count its looks, and report them. It does not ship.
>
> ## 3. Explain the one changed switch
>
> Report, for that A2-rotation walk:
> - the walk ID and its true line;
> - the lock, the drawn line before and after, and the switch's timing under each setting;
> - whether the new switch moved the marker onto the true line or off it;
> - the mechanism. Most likely the switch's 1.5 m radius condition reads the marker's drawn position, which the head
>   offset moves, but confirm it from the code rather than assuming.
>
> Also count how many switches change between 0.75 s and 1.0 s on A3 and B2 in step 4.
>
> ## 4. A3 and B2, once each, with 1.0 s against the shipped 0.75 s
>
> This is A3's eighth look and B2's sixth. Decode the deployed model on A3 and B2 and the zero-shot model on B2, the same
> cells as the 10 Oct record (`f05_A3`, `f05_B2`, `z05_B2`). For each, report paired against 0.75 s on the same walks:
> - **dot error:** median from the press, on correct-lock walks and on all walks, with 95 % CIs and the paired
>   difference;
> - **mean signed offset,** with a 95 % CI;
> - **share within 0.5 m;**
> - **switches** that changed, and whether each helped or hurt;
> - **confirmation** that the lock and the committed line are identical on every walk;
> - **render rules,** especially 2a: the first frame exactly on the locked line's entry, now that the anchor span is
>   zero;
> - **the causal margin and the draw lag** on the stream clock, against today's worst of 0.153 s.
>
> If the lock or the committed line moves on any walk, or a render rule or the causality check fails, stop before step 5
> and report.
>
> ## 5. Ship it in the live app
>
> - **Add a new display profile:** the clean display with `head_offset_s = 1.0` and everything else unchanged. Make it
>   the default.
> - **Keep the old profiles reproducible:** "pre_clean" and the 0.75 s clean display must still reproduce their shipped
>   outputs exactly.
> - **Confirm the 1.0 s handling:**
>   - `display.py` handles the empty anchor span (`t_dec0` equal to `park_until`) with no division or ordering edge case;
>   - the glide code path is now inert, not erroring.
> - **Tests:** the live suite passes, and the pre-flight replay equals the offline decode row for row.
> - **Commit** code and records in the Code repository as usual. Hash the shipped files before and after, as on 10 Oct.
>
> ## 6. Re-render the twelve demonstration videos
>
> - One per participant for A3 and for B2, at real-time pace, semi-constrained, with the new default profile.
> - Each video's log must equal its full-speed replay row for row.
> - Report per video: lock and committed line (expected unchanged), dot median on all walks and on correct-lock walks,
>   render-rule failures, switches, and the draw lag.
> - Keep the old renders, renamed, until Uzayr has seen the new ones.
> - This is heavy, so run it when the machine is quiet, and extend the keep-awake past the current caffeinate (PID 44825,
>   until about 15:23) to cover it.
>
> ## 7. Editor list, not applied
>
> - **Methodology:**
>   - the position-track sentence, which becomes simpler: each position drawn at its window's centre, one stride ahead,
>     with no glide (confirm whether any glide remains);
>   - `fig:lock-timing`'s screen row;
>   - the display settings anywhere they are listed;
>   - the switch paragraph, if the mechanism in step 3 needs a clause.
> - **Results:**
>   - the dot figures and signed offset in §4.3 and the A3 statement and footnote;
>   - the per-video figures in §4.5;
>   - the draw lag;
>   - the disclosure sentence for this decision.
> - **Ledger:** a row for the head-offset selection, all three arms, with the override.
> - **Discussion and Recommendations:** the 0.25 s lag no longer exists, so remove any recommendation to extend the grid.
>
> ## 8. Limits
>
> - Display only. Do not touch the networks, the readers, the lock's or the committed answer's settings, `engine.py` or
>   identification.
> - Report back with the record, the step 3 explanation, the step 4 table, the step 5 checks, the step 6 table and the
>   Editor list. Stop at whichever step fails.

## Uzayr's answer on rule 2a for the 1.0 s display (in Agent1's chat, 14 Oct, at or before 12:46:11 SAST, before any A3/B2 decode with 1.0 s)

The question: at 1.0 s there is no glide, so the first frame at press + 2.0 s is the first decoded position. On the 360
rotation walks it is always on the locked line (largest distance off it 2.2e-16 m) but exactly at its entry on only 32
(within 0.15 m on 209; median 0.116 m, largest 1.144 m). Step 4 stops before step 5 if a render rule fails and lists rule
2a as "the first frame exactly on the locked line's entry". How should rule 2a apply?

**His answer: "Retire 2a for 1.0 s"**, the option worded: "No anchor span means no anchor rule (as in addendum 1). Report
the first frame's distance from the entry and that it is on the line; step 4 stops only on lock, committed line, other
render rules or causality."

So in step 4 rule 2a is reported (each walk's first frame at or after press + 2.0 s: its distance from the locked line's
entry and from the line), and is not a stop condition. The park, together, one-lock and at-most-one-switch rules, the lock,
the committed line and the causal margin remain stop conditions.

## Uzayr's decisions after seeing the A3 and B2 results (in Agent1's chat, 14 Oct, at or before 13:12:48 SAST)

Made by Uzayr after step 4's A3 and B2 results (`STEP4_RESULT.json`, 26c0daec) were reported to him at about 13:07. His
words: "Go ahead with step 5 onwards using 1.0 s. This is my decision, and it covers each of these, so record them all in
the record and the Decisions Log as made by me after seeing the A3 and B2 results:"

> Rule 2a is retired at 1.0 s. The marker now first appears on the locked line at its first decoded position, a median
> of about 0.1 m and at most about 1.1 m from the entry, instead of exactly on it.
> The slight lead is accepted: about +0.05 m mean signed offset, and +0.061 m [+0.004, +0.115] on B2.
> The two lost corrective switches on B2 are accepted: PA4 walk 5 (true D_fwd, locked E_row5) and PA6 walk 5 (true D_rev,
> locked B_rev). Confirm the mechanism for these two and for the A2-rotation walk from the code, and put it in the record.
> The guard override from the development selection stands as already recorded.
>
> Then do steps 5 to 7 as written: the new default profile with the old ones still reproducible, the tests, the
> pre-flight, the hashes, and the twelve re-rendered videos with their logs equal to the replay. In the Editor list, also
> include:
>
> replacing the PA6 B2 showcase in Results §4.5, because walk 5 no longer shows a corrected lock (say which video, if
> any, now shows a switch correcting a wrong lock);
> the new dot figures from step 4, measured from the first decoded frame.
>
> Don't touch the report repository. Stop at whichever step fails.

**Recorded as four decisions, each made after the A3 and B2 results were seen:**
1. Rule 2a retired at 1.0 s (the first frame is the first decoded position on the locked line: median about 0.1 m, at
   most about 1.1 m from the entry; on the line within 2.2e-16 m).
2. The slight lead accepted: mean signed offset about +0.05 m on correct-lock walks (A3 +0.041 [-0.027, +0.111], B2
   +0.061 [+0.004, +0.115], zero-shot B2 +0.058 [-0.004, +0.118]), where Uzayr's prompt of 09:43 had preferred a slight
   lag to a lead.
3. The two lost corrective switches on B2 accepted (PA4, PA4, walk 5; PA6, PA6, walk 5).
4. The guard override of the development selection stands (section 1 above).

## Uzayr's go after the CORRECTED step 4 (in Agent1's chat, 14 Oct, at or before 13:58:53 SAST)

Step 4 as first run (STEP4_RESULT.json) ran its networks on the GPU and is invalid (STEP4_INVALID.md, 87dee341). Uzayr chose
the corrected re-run on the CPU ("1"); it reproduced the shipped 0.75 s replay row for row first (STEP4_CPU_CHECK.json)
and then decoded A3 and B2 with 1.0 s on the CPU (STEP4_CPU_RESULT.json, 3cfc6c6d). The corrected figures were reported
to him, with the note that decision 3 above named two lost switches where the corrected run loses one. His answer: **"Go
ahead"**, for step 5 onwards on the corrected figures.

**The four decisions, as they stand on the corrected figures (each made after the A3 and B2 results were seen):**
1. Rule 2a retired at 1.0 s: the first frame is the first decoded position on the locked line, a median of 0.09 to 0.13 m
   and at most 1.15 m from the entry (exactly on it on 5 to 9 of 120 walks per test).
2. The slight lead accepted: mean signed offset on correct-lock walks A3 +0.037 [-0.030, +0.106], B2 +0.063
   [+0.006, +0.117], zero-shot B2 +0.058 [-0.004, +0.118].
3. **CORRECTED: one lost corrective switch on B2, accepted:** PA6 (PA6), walk 5 (true D_rev, locked B_rev). PA4's
   (PA4) walk 5 keeps its switch on the CPU; its loss in the first run was the GPU's. A3 and zero-shot B2: no switch
   changes.
4. The guard override of the development selection stands.

**Looks:** the corrected run is a re-decode of A3 and B2 with the same 1.0 s configuration, after a first run on the GPU;
recorded as the corrected A3 eighth and B2 sixth looks (Uzayr's count), with the GPU run disclosed beside them.
