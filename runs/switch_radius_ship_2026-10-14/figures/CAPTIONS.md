# Queue 15 (a): the two redrawn Results figures, for the Editors through the Mastermind (NOT APPLIED)

PA codes only. The PDFs are `results_dot_cdf.pdf` and `results_decode_example.pdf` in this folder, each the same page size as
the report's current PDF, in Times New Roman, in the current PDFs' colours, line widths and dash patterns. The current
report PDFs are kept here as `*_previous.pdf` for rollback. Every figure is from the shipped profile's replays
(`Code/runs/switch_radius_a3b2_2026-10-14/R0/`), scored with app_score.score_recording from the first decoded frame
against the truth 2.0 s earlier (`FIGURES.json`). Development evaluation, all data seen. This replaces E10 and E11 of
`../EDITOR_LIST.md`: both figures are redrawn, so E11's "keeping the figure" option falls away.

## E10, fig:error-cdf (`Figures/results_dot_cdf.pdf`)

- **Panel (a), all walks, changes.** Within 0.5 m: B2 deployed 60.0 to 65.9 %, A3 58.5 to 65.0 %, B2 zero-shot 50.1 to
  55.5 %, as E3 to E13 give them in the text.
- **Panel (b), correct-lock walks, is unchanged.** Its frames were asserted equal to the `clean_1s` replays' (the display
  the current PDF drew) for all three curves.
- **The caption has no number that changes and stands as it is.**
- Evidence comment for the Editors: `% UPDATED 14 Oct 2026 (the switch's radius removed; redrawn from the shipped profile's
  replays). Evidence: Code/runs/switch_radius_ship_2026-10-14/figures/ (results_figures.py, FIGURES.json); panel (b)
  asserted equal to the 1.0 s display's`.

## E11, fig:decode-example (`Figures/results_decode_example.pdf`)

The same two walks as now, chosen by the figure's own rule and asserted to be its walks: (a) recording 3 of 6, pass 2
(PA2); (b) recording 1 of 6, pass 3 (PA5). The current PDF was drawn on 11 October from the 0.75 s display, and its numbers
(0.18 and 2.35 m, 1.15 and 1.03 s) reproduce from that replay. **Panel (a) changes too, because of the 1.0 s head offset
shipped on 14 October and not because of the radius:** its rows are identical under `clean_1s` and the shipped display. The
first frame is no longer exactly at the line's start (rule 2a is retired at 1.0 s), and the median is 0.22 m.
**Panel (b)** now switches from E_col1 to C_fwd 5.5 s after the press (the hollow diamond), and the dot slides across to
C_fwd. Its title reads `(b) Lock E_col1, switch to C_fwd`, and the legend gains `Switch, press + 5.5 s`.

Caption, Results.tex:468 to 477:
- Old: `Two B2 walks on C\_fwd decoded by the deployed model, trained on A1, A2 and B1, semi-constrained, on the floor plan of the grid.`
- New: `Two B2 walks on C\_fwd decoded by the deployed model, trained on A1, A2 and B1, semi-constrained, with the live app's display, on the floor plan of the grid.`
- Old: `(a) The lock and the committed line are both C\_fwd, and the dot, drawn every 0.1~s from its first frame at the line's start, stays a median 0.18~m from where the walker was 2.0~s earlier.`
- New: `(a) The lock and the committed line are both C\_fwd, and the dot, drawn every 0.1~s from its first frame 0.06~m from the line's start, stays a median 0.22~m from where the walker was 2.0~s earlier.`
- Old: `(b) The lock goes to E\_col1, which starts beside the same corner, so the dot runs up E\_col1 whilst the walker crosses the diagonal, a median 2.35~m away, yet the committed line, announced 1.03~s after the walk's end, is C\_fwd.`
- New: `(b) The lock goes to E\_col1, which starts beside the same corner, so the dot runs up E\_col1 whilst the walker crosses the diagonal, until 5.5~s after the press the display switches to C\_fwd and the dot slides across to it, which keeps it a median 0.63~m from the walker. The committed line, announced 1.03~s after the walk's end, is C\_fwd.`
- Unchanged: `Each is the first walk of its kind in the replay's file order.`

Evidence comment for the Editors (replacing the 11 Oct one above the figure): `% UPDATED 14 Oct 2026 (the live app's
display: head offset 1.0 s and the switch without its radius condition; redrawn by the Code agent). Two B2 C_fwd walks of the
deployed model, the first in sorted log order of each kind: (a) recording 3 of 6, pass 2, dot median 0.22 m, first frame
0.06 m from the entry, announced 1.15 s after the walk's last anchor; (b) recording 1 of 6, pass 3, locked E_col1, switch
to C_fwd at press + 5.5 s, dot median 0.63 m, announced 1.03 s after it. Evidence:
Code/runs/switch_radius_ship_2026-10-14/figures/ (results_figures.py, FIGURES.json), from
Code/runs/switch_radius_a3b2_2026-10-14/R0/final/ (the shipped profile's replays)`.
