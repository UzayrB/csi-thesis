# Claude Code prompt: re-derive the motion-gate threshold from the six participants without static dwells

You are working in the TDR-03 code repository (`Code/`).

## Why

The final tracker's motion gate uses threshold 0.431. It was set on 11 September by balanced accuracy between A1's standing-sweep (static dwell) windows and A1's walking windows, from all eight participants, including the two removed on 14 September. It was then checked on A2.

Uzayr's report must say the final system uses only the six-participant cohort and no static dwells. That is only true if the gate is re-derived. **Do not change any text, configuration or result. This task establishes the facts.**

## Ground rules

- **Read-only.** Do not change `runs/dc2_results/rule/FINAL_CONFIG.md`, `pipeline/live/final_model.py`, the frozen networks, or any existing result. Work in `runs/gate_six_2026-10-08/` and write `reports/tracking/2026-10-08_gate-six.md`.
- **Data.**
  - Use only the six cohort participants (PA1 to PA6; names are fine in code).
  - Use no standing-sweep (dwell) windows.
  - Use no data from the two removed participants.
- **No accuracy is scored on A3 or B2.** Read no labels from them, decode nothing on them, and compute no committed-line, lock or dot figure on them.

## Steps

1. **Trace every gate value, not only the threshold.** The scaled statistic is band energy × max(1, G0 / g_rec), with G0 = 0.7542 (deployed). For each of the following, report the file, function, sessions, participants and window types it was computed from, and say whether it touched dwells or the two removed participants:
   - the threshold 0.431, and the rule used to choose it (balanced accuracy, plus any tie rule);
   - G0 for the deployed model;
   - G0 for the zero-shot model (A1 + A2);
   - g_rec: confirm it comes only from each recording's own idle windows.

   Any value that touched dwells or the removed participants joins the re-derivation. If G0 is clean, say so and leave it.

2. **Choose a still class without dwells.** From the six participants' recordings in A1 (and A2 for the check), identify windows that are reliably not walking:
   - the idle windows before each recording's first start press;
   - standing between passes;
   - or another source you can justify from the protocol.

   Report the source and the window counts, and explain why each window is reliably still.
   - **Walking class:** labelled walking windows inside passes, six participants only.
   - **Tie rule:** use the original derivation's tie rule. If it had none, use the midpoint of the flat range of maximal balanced accuracy.
   - **Pre-registration.** Write the still-class source, the walking class, the rule and the tie rule into `PREREG.md`, then hash and commit it before computing anything.

3. **Re-derive.**
   - Apply the pre-registered rule on A1 (six participants, no dwells), with the same statistic and scaling.
   - Check on A2, as the original was checked.
   - Report the new threshold (and the new G0 if step 1 required one), the balanced accuracy on A1 and on A2, and the curve, with 0.431 marked on it.

4. **Equivalence check.** This decides whether anything downstream changes.
   - For every window of every session either model decodes (deployed: A1, A2, B1, A3, B2; zero-shot: B2; calibration recordings included), compute the scaled gate statistic under the old values and under the new ones. Count the windows whose still or walking decision differs.
   - This reads no labels and scores nothing. It only compares two settings' decisions on the same statistic.
   - Split the flips by where they fall: before the start press, from the press to the walk end, and after the walk end.
   - From the code, confirm whether a gate decision before the press or after the walk end can reach any output (the lock, the position track, the committed line, or the switch).
   - Report the counts per session, per model and per span.

5. **Outcome.**
   - **No flip can reach an output** (zero flips, or flips only in spans the code shows cannot affect an output). The final system's outputs are identical under the new values. Record that, and draft the exact thesis sentence. Do not change FINAL_CONFIG. Uzayr will approve the swap to the new value separately, so that the number in the thesis matches the code.
   - **Any flip can reach an output.** STOP. Report the counts and which sessions and models are affected. Do not re-decode anything. Uzayr decides between:
     - adopting the new values, which would mean re-decoding the test sessions and changing the headline figures;
     - or keeping 0.431 and disclosing its origin.

## Report back

1. The provenance of the threshold, G0 (deployed and zero-shot) and g_rec, as found.
2. The still-class source and its counts.
3. The PREREG hash.
4. The new values, the A1 and A2 balanced accuracies, and the curve.
5. The flip counts per session, model and span, and what the code shows about which spans reach an output.
6. The outcome, and the exact sentence the thesis may use.
