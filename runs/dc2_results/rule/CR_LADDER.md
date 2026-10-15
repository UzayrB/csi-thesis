# The ablation ladder on the rotations, before and with the clean start-of-walk readers

Display lock, configuration A; objective = weighted mean of committed + lock (B1 x2); each gain against the step before, paired, 95 percent interval.

| step | objective before | objective clean | gain before | gain clean | clean B1 c/l | clean A2 c/l | clean A1 c/l |
|---|---|---|---|---|---|---|---|
| D0 baseline: the pooled per-link recipe, shipped decode | 76.04 | 74.38 |  |  | 37.50/18.33 | 74.17/45.00 | 38.33/28.33 |
| + D2 augmentation + relative RSSI | 85.83 | 85.42 | +9.79 [3.54, 16.25] | +11.04 [4.79, 17.71] | 40.00/15.83 | 77.50/62.50 | 54.17/35.83 |
| + D3 relative motion gate | 100.21 | 99.58 | +14.38 [9.38, 19.79] | +14.17 [9.17, 19.79] | 53.33/28.33 | 77.50/62.50 | 57.50/37.50 |
| + D4 shared encoder, learned fusion | 122.50 | 121.46 | +22.29 [14.37, 30.83] | +21.88 [13.95, 30.42] | 59.17/39.17 | 94.17/72.50 | 70.83/51.67 |

D0 to final: before +46.46 [37.49, 55.62]; clean +47.08 [38.33, 56.04].
