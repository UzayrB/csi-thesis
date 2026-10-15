# Geometry audit, 2026-09-20. Read only, nothing changed.

> **Terminology corrected 2026-09-23 (batch 23c):** g100 is a 100-cell REGION posterior head ("g" is the grid kind, 100 the cell count), not a motion gate. Earlier text here called it "the gate head" and has been corrected; the JSON keys `gate_head_g100` and `g100_gate` are kept as identifiers and mean the same region head.

Written for sanity-checking by someone who wants to be sure no axis is swapped, no line mirrored
and no direction reversed anywhere between the tape on the floor and the dot on the screen.

## 1. The room, the nodes and the coordinate convention

The room is 5 x 5 m. Coordinates are metres, **x to the right, y upwards**, origin at one corner,
so the room spans (0, 0) to (5, 5) and its centre is (2.5, 2.5). The same convention is used in the
labels, the chains, the emission grid and the render; there is no transform anywhere between them.

The **room centre (2.5, 2.5) is also the decoded position of the NULL state**, which is why the dot
parks there between walks: that is not a drawing convention, it is where the decoder says the
person is when it says they are not on a line.

The emission grid is **5 by 5 cells** over the same square, so cell k spans
`x in [ (k mod 5), (k mod 5) + 1 ]`, `y in [ floor(k/5), floor(k/5) + 1 ]` in metres. The g100 region head
uses a 10 by 10 grid and is summed four cells to one onto this same 5 by 5 grid, which is a pure
sum of probabilities over each block with no interpolation.

## 2. The twelve lines, read from the chain states themselves

These are not copied from the protocol sheet; they are the first and last state of each chain in
`st.xy`, which is what the decoder and the render both use.

| line | start | end | length | direction |
|---|---|---|---|---|
| A_fwd | (2.50, 0.00) | (2.50, 5.00) | 5.00 m | +y |
| A_rev | (2.50, 5.00) | (2.50, 0.00) | 5.00 m | -y |
| B_fwd | (0.00, 2.50) | (5.00, 2.50) | 5.00 m | +x |
| B_rev | (5.00, 2.50) | (0.00, 2.50) | 5.00 m | -x |
| C_fwd | (0.00, 0.00) | (5.00, 5.00) | 7.07 m | +x +y |
| C_rev | (5.00, 5.00) | (0.00, 0.00) | 7.07 m | -x -y |
| D_fwd | (0.00, 5.00) | (5.00, 0.00) | 7.07 m | +x -y |
| D_rev | (5.00, 0.00) | (0.00, 5.00) | 7.07 m | -x +y |
| E_col1 | (0.50, 0.00) | (0.50, 5.00) | 5.00 m | +y |
| E_col5 | (4.50, 0.00) | (4.50, 5.00) | 5.00 m | +y |
| E_row1 | (0.00, 0.50) | (5.00, 0.50) | 5.00 m | +x |
| E_row5 | (0.00, 4.50) | (5.00, 4.50) | 5.00 m | +x |

Each is a separate CHAIN of states spaced **0.25 m** apart in arc length, so a 5 m line is 21
states and a diagonal is 29. The six A/B/C/D pairs are the same tape walked in both directions and
are separate chains, because direction is part of what the decoder must decide.

**The E lines are the parallel siblings.** A_fwd, E_col1 and E_col5 are three parallel vertical
lines 0.5 m, 2.5 m and 4.5 m across; B_fwd, E_row1 and E_row5 are the horizontal three. Those two
families are the known confusion limit.

## 3. Where each representation is used

| | |
|---|---|
| labelling | anchor presses give `t_end` and the pass's line name; positions are interpolated between anchors and written per window as `rec.xy`, only on `walk`-mode windows |
| chains | `st.xy` above, `st.s_of` the arc length of each state, `st.slice_of[name]` the state range |
| emissions | a posterior over the 25 cells per window, converted to a score per chain state by the cell the state falls in |
| render | `decoded_xy(state)` returns `st.xy[state]` directly, and the null state returns (2.5, 2.5) |

There is no axis swap or scaling at any boundary: the render plots `st.xy` and the truth in the
same frame.

## 4. Check one, the round trip. PASSES.

For every labelled truth point on every pass, the distance from that point to the nearest state of
**its own** chain was measured.

| | |
|---|---|
| labelled truth points checked | 1089 |
| worst distance to its own chain | **0.125 m** |
| state spacing | 0.250 m |

0.125 m is exactly half the state spacing, which is the largest a quantisation error can be. **So
every labelled position lies on its own chain to within quantisation: no axis swap, no mirror and
no reversed direction anywhere between the anchors, the chains and the rendered coordinates.**

## 5. Check two, the confusion matrix. Errors are NOT concentrated on the parallel siblings.

Demonstration pairing, true line against locked line at a 1.5 s wait under the strict causal rule.
120 passes, 44 wrong, 37 percent.

| error type | count | share | chance share | reading |
|---|---|---|---|---|
| parallel sibling | 5 | 11 % | 18 % | **below chance**, so siblings are not the problem |
| mirror across the centre | 6 | 14 % | 9 % | slightly above chance, not a systematic flip |
| same line reversed | 8 | **18 %** | 9 % | **twice chance**, the most structured pattern |
| none of these | 25 | 57 % | | |

Top confusions: `D_rev -> E_col5` (8), `A_rev -> A_fwd` (4), `B_fwd -> E_row1` (4),
`A_fwd -> E_row1` (3), `B_rev -> E_col5` (3).

**There is no flip.** A mirror share of 14 percent against a chance share of 9 is not evidence of a
systematic reflection, and check one rules it out independently.

**The known parallel-sibling limit is not what is binding here.** At 11 percent it is below its own
chance share.

Two patterns are real. **Direction reversal at twice chance**: `A_rev -> A_fwd` and friends, the
same tape walked the other way. And the single largest confusion, `D_rev -> E_col5`, is a pair
whose STARTS are 0.5 m apart, (5.00, 0.00) against (4.50, 0.00): a shared starting corner rather
than a parallel line.

## 6. Check three, progress on wrongly locked passes. Progress does NOT survive a wrong line.

For the 44 wrongly locked passes, the distance the person actually walked against the arc the
decoder advanced along the line it locked to:

| | |
|---|---|
| true distance walked, median | 4.63 m |
| decoded along-chain progress, median | 3.00 m |
| correlation | **+0.235** |
| median absolute difference | **3.01 m** |

**So the decoder is not reading progress correctly and merely choosing the wrong parallel line.**
On a wrong line it is lost in both respects. That is consistent with section 5: only 5 of the 44
errors are parallel siblings, and the rest are lines that share no geometry with the truth, where
there is no reason for progress to transfer.

The brief's third check was framed for the parallel-sibling case specifically. **There are only
five such passes, which is too few to conclude anything**, and that is reported rather than
computed into a number that would look like evidence.

## 7. What this audit rules in and out

- **Ruled out**: axis swap, mirroring, reversed chain direction, and any transform between
  labelling, chains, emissions and render. Check one is exact to quantisation over 1089 points.
- **Ruled out**: that the line errors are mostly the known parallel-sibling limit. They are below
  chance for that category.
- **Ruled in, and worth attention**: direction reversal at twice its chance share, and confusions
  between lines that share a starting corner.
