### CR_D3b_relgate+abstain_vs_ref: d1sp@CR.relgate+abstain against d1sp@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 56.67 | 40.00 | +40.83 (+23 / +26 passes) |
| A2 | x1 | 74.17 | 45.00 | 53.33 | 24.17 | -41.67 (-25 / -25 passes) |
| A1 | x1 | 38.33 | 28.33 | 40.83 | 26.67 | +0.83 (+3 / -2 passes) |

Objective (weighted mean of committed + lock): base 74.38, arm 84.58.
Paired gain +10.21 points, 95% interval [3.33, 17.92], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 67 / 61 / 61 / 17
- lock: base 50 / 33 / 28 / 22; arm 33 / 28 / 17 / 22
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 33.33333333333333, 'arm': 16.666666666666664}]

**Decision: KEEP BASE.**
