### CR_D3b_relgate+abstain_vs_ref: d1sp@CR.relgate+abstain against d1sp@CR.ref (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 56.67 | 44.17 | +45.00 (+23 / +31 passes) |
| A2 | x1 | 74.17 | 50.83 | 53.33 | 30.00 | -41.67 (-25 / -25 passes) |
| A1 | x1 | 38.33 | 29.17 | 40.83 | 27.50 | +0.83 (+3 / -2 passes) |

Objective (weighted mean of committed + lock): base 76.04, arm 88.33.
Paired gain +12.29 points, 95% interval [5.41, 19.79], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 67 / 61 / 61 / 17
- lock: base 50 / 33 / 28 / 17; arm 33 / 28 / 17 / 22
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 33.33333333333333, 'arm': 16.666666666666664}]

**Decision: KEEP BASE.**
