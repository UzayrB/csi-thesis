### D2_mix: d2p_mix against d2p_base (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 25.83 | 12.50 | 29.17 | 15.00 | +5.83 (+4 / +3 passes) |
| A2 | x1 | 70.00 | 37.50 | 66.67 | 43.33 | +2.50 (-4 / +7 passes) |
| A1 | x1 | 26.67 | 19.17 | 36.67 | 22.50 | +13.33 (+12 / +4 passes) |

Objective (weighted mean of committed + lock): base 57.50, arm 64.38.
Paired gain +6.88 points, 95% interval [-0.21, 13.54], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 50 / 44 / 83 / 39; arm 39 / 39 / 78 / 17
- lock: base 11 / 22 / 33 / 11; arm 39 / 39 / 28 / 6
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 38.88888888888889, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row5', 'base': 11.11111111111111, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
