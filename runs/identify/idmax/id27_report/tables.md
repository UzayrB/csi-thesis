## Headline table

| row | nested accuracy % | 95% interval | chance % | permutation p | cohort |
|---|---|---|---|---|---|
| cross-day LOSO (headline) | 15.83 | [10.28, 21.67] | 16.67 | 0.7063 | 6 |
| cross-day, nine pairings pooled (mean of pairings 19.26, median 19.17) | 19.26 | [15.83, 22.96] | 16.67 | 0.0330 | 6 |
| WITHIN-DAY temporal split | 32.64 | [23.59, 40.97] | 16.67 | 0.0010 | 6 |
| WITHIN-DAY leave-one-line-out | 33.33 | [28.45, 37.95] | 16.67 | 0.0010 | 6 |
| identification path, cross-day, nested choice (c) | 13.33 | [3.23, 25.81] | 16.67 | 0.7153 | 6 |
| identification path, cross-day, E_row1 by geometry (d) | 16.67 | [0.00, 33.33] | 16.67 | 0.5724 | 6 |
| identification path, WITHIN-DAY, centre lines (see table P) | see P | | 16.67 | | 6 |
| RECORDING-SIGNATURE REFERENCE, cross-day LOSO | 20.28 | [6.66, 36.67] | 16.67 | 0.1938 | 6 |
| RECORDING-SIGNATURE REFERENCE, WITHIN-DAY temporal | 91.67 | [86.11, 97.22] | 16.67 | 0.0010 | 6 |
| SESSION-ID CONTROL (3 classes, new people, 20 splits) | 36.81 | [35.44, 38.14] | 33.33 | 0.0010 | 3 of 6 |
| S0 oracle speed, cross-day LOSO (a control) | 32.50 | [23.89, 42.50] | 16.67 | 0.0030 | 6 |
| S0 oracle speed, WITHIN-DAY temporal (a control) | 34.03 | [18.75, 49.32] | 16.67 | 0.0040 | 6 |

Within-day rows: WITHIN-DAY: same recording, learns the session and the recording as well as the person.

## Cohort size

| scope | k | chance | mean | min | max | subsets |
|---|---|---|---|---|---|---|
| LOSO | 2 | 50.0 | 49.33 | 40.83 | 57.5 | 15 |
| LOSO | 3 | 33.33 | 32.44 | 26.67 | 38.89 | 20 |
| LOSO | 4 | 25.0 | 23.5 | 19.58 | 28.33 | 15 |
| LOSO | 5 | 20.0 | 18.83 | 15.33 | 20.33 | 6 |
| LOSO | 6 | 16.67 | 15.83 | 15.83 | 15.83 | 1 |
| LOSO | largest k with mean above 50 | | None | | | |
| WD_temporal | 2 | 50.0 | 62.5 | 50.0 | 72.92 | 15 |
| WD_temporal | 3 | 33.33 | 46.94 | 36.11 | 55.56 | 20 |
| WD_temporal | 4 | 25.0 | 40.56 | 36.46 | 44.79 | 15 |
| WD_temporal | 5 | 20.0 | 36.39 | 30.0 | 40.83 | 6 |
| WD_temporal | 6 | 16.67 | 32.64 | 32.64 | 32.64 | 1 |
| WD_temporal | largest k with mean above 50 | | 2 | | | |

## Section 8 sweep, ranked by nested cross-day LOSO accuracy

| block | LOSO % | interval | p | nine pairings, mean | median |
|---|---|---|---|---|---|
| A1_conditioning | 21.67 | [16.39, 27.22] | 0.019 | 20.74 | 20.83 |
| B_features | 18.61 | [15.0, 22.78] | 0.1818 | 19.63 | 20.0 |
| A2_subcarriers | 18.06 | [13.61, 22.78] | 0.2757 | 17.31 | 16.67 |
| A4_segmentation | 18.06 | [13.05, 23.61] | 0.2388 | 18.89 | 19.17 |
| A3_bands | 17.22 | [13.06, 21.94] | 0.4236 | 19.26 | 20.0 |
| E_perline_z | 16.94 | [13.61, 20.83] | 0.4815 | 20.0 | 18.33 |
| F_links | 14.72 | [12.22, 17.5] | 0.8292 | 16.67 | 17.5 |
| UNION (every block, the run's nested search) | 15.83 | [10.28, 21.67] | 0.7063 | 19.26 | 19.17 |
| D learned models (nested architecture, 5-seed ensemble) | 27.22 | [21.11, 33.61] | 0.001 | seed mean 23.06, sd 2.65 | |

| model (nested alone over the UNION shortlist) | LOSO % |
|---|---|
| gb | 21.11 |
| logreg_C0.1 | 20.56 |
| rbfsvm_C1 | 18.61 |
| knn_1 | 18.61 |
| knn_7 | 18.61 |
| knn_15 | 18.61 |
| latefuse_w | 18.33 |
| et | 17.78 |
| dtw1nn_tpl | 17.78 |
| linsvm_C0.1 | 17.22 |
| rbfsvm_C10 | 16.94 |
| rf | 16.39 |
| lda | 16.11 |
| logreg_C0.01 | 15.56 |
| stack | 15.28 |
| logreg_C1 | 15.0 |
| linsvm_C0.01 | 15.0 |
| latefuse | 15.0 |

## Table P: the identification path

| path | cross-day LOSO % | interval | n | within-day % | within-day n |
|---|---|---|---|---|---|
| A_fwd | 13.89 | [2.78, 27.78] | 36 | 27.78 | 18 |
| A_rev | 19.44 | [5.56, 33.33] | 36 | 33.33 | 18 |
| B_fwd | 13.89 | [2.78, 27.78] | 36 | 22.22 | 18 |
| B_rev | 13.89 | [5.56, 25.0] | 36 | 27.78 | 18 |
| C_fwd | 16.67 | [5.56, 27.78] | 36 | 16.67 | 18 |
| C_rev | 16.67 | [5.56, 30.56] | 36 | 33.33 | 18 |
| D_fwd | 11.11 | [2.78, 22.22] | 36 | 16.67 | 18 |
| D_rev | 19.44 | [5.56, 36.11] | 36 | 22.22 | 18 |
| E_col1 | 27.78 | [5.56, 50.0] | 18 | none | 0 |
| E_col5 | 16.67 | [0.0, 33.33] | 18 | none | 0 |
| E_row1 | 16.67 | [0.0, 33.33] | 18 | none | 0 |
| E_row5 | 22.22 | [5.56, 44.44] | 18 | none | 0 |
| A both directions, invariant features | 16.67 | [8.33, 27.78] | 72 | | |
| A both directions, direction as flag | 16.67 | [8.33, 25.0] | 72 | | |
| B both directions, invariant features | 16.67 | [9.72, 23.61] | 72 | | |
| B both directions, direction as flag | 12.5 | [5.56, 22.22] | 72 | | |
| C both directions, invariant features | 19.44 | [11.11, 29.17] | 72 | | |
| C both directions, direction as flag | 22.22 | [8.33, 37.5] | 72 | | |
| D both directions, invariant features | 22.22 | [12.5, 33.33] | 72 | | |
| D both directions, direction as flag | 13.89 | [6.94, 20.83] | 72 | | |

## Voting (soft, calibrated) and alignment

| arm | mode | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|---|
| UNION | across_paths | 15.83 | 14.39 | 13.67 | 12.47 | 12.42 |
| UNION | same_path | 15.83 | 13.89 | - | - | - |
| S0_ORACLE_SPEED | across_paths | 32.5 | 33.48 | 34.42 | 33.97 | 36.11 |
| S0_ORACLE_SPEED | same_path | 32.5 | 33.33 | - | - | - |
| REF_RECSIG | across_paths | 20.28 | 21.35 | 21.28 | 21.36 | 20.17 |
| REF_RECSIG | same_path | 20.28 | 19.44 | - | - | - |
| TRANSDUCTIVE perSession_z | single pass | 15.56 [11.67, 20.56] | | | | |
| TRANSDUCTIVE rank | single pass | 15.0 [9.44, 21.94] | | | | |
| TRANSDUCTIVE coral | single pass | 15.0 [10.56, 20.0] | | | | |

## Speed diagnostic (reported, not a gate)

```
{
 "configuration": "steady_raw/U_all_gait/mean@b08_35/all/pc1-3/perline_z|rf",
 "speed_residualised_LOSO": {
  "acc_pct": 27.5,
  "ci95_pct": [
   21.94,
   33.33
  ],
  "perm_p": 0.005
 },
 "linear_probe_R2_speed_from_features": [
  0.143,
  0.187,
  -0.042
 ],
 "linear_probe_R2_mean": 0.096
}
```

## POST-HOC CEILING: selected on the test data, not a result

| configuration | model | LOSO % |
|---|---|---|
| walk_edge_hampel/B5_doppler/mean@b08_35/all/pc1-3/none | rf | 28.33 |
| walk_edge_hampel/B5_doppler/pca@b08_35/all/pc1-3/none | rf | 28.33 |
| steady_hampel/B5_doppler/mean@b08_35/all/pc1-3/none | rf | 26.94 |
| steady_hampel/B5_doppler/pca@b08_35/all/pc1-3/none | rf | 26.94 |
| steady_runmean/B5_doppler/mean@b08_35/all/pc1-3/none | rf | 26.67 |
| steady_runmean/B5_doppler/pca@b08_35/all/pc1-3/none | rf | 26.67 |
| steady_raw/B5_doppler/mean@b08_35/noRX3/pc1-3/none | rf | 26.39 |
| steady_hampel/B5_doppler/mean@b08_35/all/pc1-3/none | logreg_C0.1 | 25.28 |
| steady_hampel/B5_doppler/pca@b08_35/all/pc1-3/none | logreg_C0.1 | 25.28 |
| steady_hampel/B5_doppler/mean@b08_35/all/pc1-3/none | lda | 25.0 |
| median over all 696 scored | | 17.78 |
