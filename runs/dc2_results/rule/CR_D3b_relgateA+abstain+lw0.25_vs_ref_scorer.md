### CR_D3b_relgateA+abstain+lw0.25_vs_ref: d1sp@CR.relgateA+abstain+lw0.25 against d1sp@CR.ref (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 56.67 | 44.17 | +45.00 (+23 / +31 passes) |
| A2 | x1 | 74.17 | 50.83 | 60.00 | 45.83 | -19.17 (-17 / -6 passes) |
| A1 | x1 | 38.33 | 29.17 | 44.17 | 32.50 | +9.17 (+7 / +4 passes) |

Objective (weighted mean of committed + lock): base 76.04, arm 96.04.
Paired gain +20.00 points, 95% interval [12.49, 27.71], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 61 / 61 / 83 / 33
- lock: base 50 / 33 / 28 / 17; arm 28 / 28 / 11 / 6
- guard FAILS: [{'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row5', 'base': 16.666666666666664, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
