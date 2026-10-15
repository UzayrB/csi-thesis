### CR_D2_rrel: d2p_rrel@CR.ref against d2p_base@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 25.83 | 12.50 | 35.83 | 18.33 | +15.83 (+12 / +7 passes) |
| A2 | x1 | 70.83 | 37.50 | 65.83 | 47.50 | +5.00 (-6 / +12 passes) |
| A1 | x1 | 21.67 | 19.17 | 37.50 | 19.17 | +15.83 (+19 / +0 passes) |

Objective (weighted mean of committed + lock): base 56.46, arm 69.58.
Paired gain +13.13 points, 95% interval [4.38, 20.42], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 50 / 44 / 89 / 39; arm 50 / 67 / 94 / 33
- lock: base 11 / 22 / 33 / 11; arm 44 / 44 / 39 / 0
- guard FAILS: [{'what': 'lock', 'line': 'E_row5', 'base': 11.11111111111111, 'arm': 0.0}]

**Decision: KEEP BASE.**
