# BRIEF: presence detection, a propagation investigation, and the free-form baseline lookup. Received 1 October 2026

**Uzayr's instruction, verbatim below.** Work from this file, never from memory of it. The status of each item is in
`QUEUE.md`, section "PRESENCE, PROPAGATION, FREE-FORM (1 OCT)".

---

Tracking only. Two measurements on existing recordings for the thesis, plus one lookup. No model, setting or figure changes; nothing is adopted.

1. Presence detection (the brief asks for "detecting human presence").
   Use the live app's own motion-gate statistic (band energy 0.3 to 2 Hz), both raw and as the app scales it. In every session (A1, A2, A3, B1, B2), compare three states:
   - the empty-room baseline captures;
   - a person standing still (idle windows before the first press, plus Room A's standing block);
   - a person walking (labelled walk windows).
   Report per session and room:
   - the statistic's distribution in each state;
   - AUROC for empty against occupied (still plus walking), empty against walking, and still against walking;
   - accuracy at the app's existing threshold, unchanged.
   If an empty-against-occupied threshold is needed, fix it on A1+A2+B1 and report it on A3 and B2.
   Write reports/PRESENCE_2026-10-01.md.

2. A propagation investigation (the brief's GA4 wording: "the physical signal propagation characteristics").
   From every session's labelled walk windows, measure each link's response as a function of the walker's perpendicular distance from that link's line, and of position along it. Use two response measures:
   - the RSSI dip relative to the recording's idle mean;
   - the CSI-shape change against the empty-room baseline.
   Compare the fall-off with the first Fresnel-zone half-width at the crossing point (link 1 about 0.43 m at mid-link; links 2 and 3 about 0.36 m). Report the measured response half-width per link and room, say whether the RX1 bistatic-factor finding still holds, and include figures.
   Write reports/PROPAGATION_2026-10-01.md.

3. Lookup, no re-run: find Room A's free-form 2D position result (the mid-September regressor, about 1.5 m median against 2.0 m for guessing the centre). Report which report it is in, the model, the train/test partition and the exact figures, so the thesis can use it to justify the twelve-line formulation.

Report back with one table: item, result, files written, commit.

Storage: put each item's raw numbers (JSON or CSV) and figures (PNG) in runs/dc2_results/presence/ and runs/dc2_results/propagation/, and write item 3's answer to reports/FREEFORM_BASELINE_2026-10-01.md. Commit the reports and the small result files by name; leave anything large git-ignored, as the other run outputs are.
