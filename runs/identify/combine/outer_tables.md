| configuration | Z (minus v4 [95 %]) | D (minus v4 [95 %]) | guard | verdict |
|---|---|---|---|---|
| v4 | 25.56 (+0.00 [+0.00, +0.00]) | 27.59 (+0.00 [+0.00, +0.00]) | holds | reference |
| F3 (primary) | 24.17 (-1.39 [-8.89, +9.17]) | 28.01 (+0.42 [-2.58, +3.60]) | holds | NOT BETTER (confirmatory (the primary, fixed on A1, A2 and B1 before any look)) |
| F7 | 27.22 (+1.67 [-2.22, +5.56]) | 31.11 (+3.52 [+0.67, +6.76]) | holds | HIGHER, NOT SEPARABLE (chosen on A3 and B2, 7 configurations tried) |
| CNN | 24.17 (-1.39 [-5.56, +2.50]) | 28.17 (+0.57 [-4.28, +5.97]) | FAILS | NOT BETTER (chosen on A3 and B2, 7 configurations tried) |
| NP | 24.44 (-1.11 [-5.56, +3.33]) | 29.12 (+1.53 [-3.67, +7.27]) | FAILS | NOT BETTER (chosen on A3 and B2, 7 configurations tried) |
| F4 | 27.50 (+1.94 [-5.56, +9.17]) | 28.34 (+0.74 [-1.64, +3.09]) | holds | HIGHER, NOT SEPARABLE (chosen on A3 and B2, 7 configurations tried) |
| F5 | 23.89 (-1.67 [-6.39, +2.50]) | 27.03 (-0.56 [-1.44, +0.35]) | holds | NOT BETTER (chosen on A3 and B2, 7 configurations tried) |
| F3+F7+NP+F4+F5 | 25.28 (-0.28 [-5.00, +4.44]) | 29.29 (+1.70 [-3.82, +7.52]) | FAILS | NOT BETTER (chosen on A3 and B2, 7 configurations tried) |

**v4**

| group | cell | walks | new | v4 | S0 | new minus v4 |
|---|---|---|---|---|---|---|
| zero-shot | xr_A B2 path | 120 | 23.33 [15.00, 32.50] | 23.33 | 20.83 | +0.00 [+0.00, +0.00] not separable |
| zero-shot | xr_A B2 natural | 60 | 23.33 [10.00, 36.67] | 23.33 | 23.33 | +0.00 [+0.00, +0.00] not separable |
| zero-shot | xr_B1 A3 path | 120 | 30.00 [16.67, 46.67] | 30.00 | 44.17 | +0.00 [+0.00, +0.00] not separable |
| cross-day | loso * natural | 180 | 37.78 [23.33, 53.33] | 37.78 | 38.33 | +0.00 [+0.00, +0.00] not separable |
| cross-day | loso * path | 600 | 30.67 [21.67, 39.17] | 30.67 | 30.17 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_AB A3 path | 120 | 30.00 [20.00, 40.00] | 30.00 | 42.50 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_AB B2 path | 120 | 22.50 [10.00, 36.67] | 22.50 | 23.33 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_AB B2 natural | 60 | 25.00 [3.33, 48.33] | 25.00 | 25.00 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_A A3 path | 120 | 23.33 [14.17, 33.33] | 23.33 | 38.33 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_B1 B2 path | 120 | 22.50 [13.33, 30.83] | 22.50 | 35.00 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_B1 B2 natural | 60 | 28.33 [13.29, 45.00] | 28.33 | 30.00 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_ABtrk A3 path | 120 | 25.00 [20.00, 29.17] | 25.00 | 39.17 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_ABtrk B2 path | 120 | 30.83 [21.67, 44.17] | 30.83 | 20.83 | +0.00 [+0.00, +0.00] not separable |
| guard | loso * slow | 120 | 29.17 [6.67, 54.17] | 29.17 | 17.50 | +0.00 [+0.00, +0.00] not separable |
| guard | loso * fast | 119 | 30.25 [20.34, 42.02] | 30.25 | 16.81 | +0.00 [+0.00, +0.00] not separable |
| extra | xr_A B2 slow | 60 | 18.33 [8.33, 28.33] | 18.33 | 16.67 | +0.00 [+0.00, +0.00] not separable |
| extra | xr_A B2 fast | 59 | 33.90 [15.52, 53.33] | 33.90 | 20.34 | +0.00 [+0.00, +0.00] not separable |
| ranking | top2 (loso natural) | 180 | 62.78 [48.89, 76.67] | 62.78 |  | +0.00 [+0.00, +0.00] not separable |
| ranking | group2 (loso natural) | 180 | 72.33 [60.56, 82.89] | 72.33 |  | +0.00 [+0.00, +0.00] not separable |

**F3** (primary)

| group | cell | walks | new | v4 | S0 | new minus v4 |
|---|---|---|---|---|---|---|
| zero-shot | xr_A B2 path | 120 | 25.83 [5.00, 52.50] | 23.33 | 20.83 | +2.50 [-14.17, +26.67] not separable |
| zero-shot | xr_A B2 natural | 60 | 20.00 [3.33, 40.00] | 23.33 | 23.33 | -3.33 [-13.33, +6.67] not separable |
| zero-shot | xr_B1 A3 path | 120 | 26.67 [10.00, 46.67] | 30.00 | 44.17 | -3.33 [-7.50, +0.83] not separable |
| cross-day | loso * natural | 180 | 37.78 [20.00, 57.78] | 37.78 | 38.33 | +0.00 [-5.56, +5.56] not separable |
| cross-day | loso * path | 600 | 28.17 [21.17, 34.67] | 30.67 | 30.17 | -2.50 [-5.33, +0.33] not separable |
| cross-day | xr_AB A3 path | 120 | 29.17 [13.33, 46.67] | 30.00 | 42.50 | -0.83 [-7.50, +8.33] not separable |
| cross-day | xr_AB B2 path | 120 | 28.33 [18.33, 38.33] | 22.50 | 23.33 | +5.83 [-5.00, +22.50] not separable |
| cross-day | xr_AB B2 natural | 60 | 26.67 [5.00, 50.00] | 25.00 | 25.00 | +1.67 [+0.00, +5.00] not separable |
| cross-day | xr_A A3 path | 120 | 27.50 [19.17, 36.67] | 23.33 | 38.33 | +4.17 [-0.83, +9.17] not separable |
| cross-day | xr_B1 B2 path | 120 | 23.33 [12.50, 31.67] | 22.50 | 35.00 | +0.83 [-3.33, +5.00] not separable |
| cross-day | xr_B1 B2 natural | 60 | 26.67 [11.67, 43.33] | 28.33 | 30.00 | -1.67 [-5.00, +0.00] not separable |
| cross-day | xr_ABtrk A3 path | 120 | 21.67 [10.00, 31.67] | 25.00 | 39.17 | -3.33 [-10.83, +5.00] not separable |
| cross-day | xr_ABtrk B2 path | 120 | 30.83 [17.50, 45.00] | 30.83 | 20.83 | +0.00 [-12.50, +13.33] not separable |
| guard | loso * slow | 120 | 28.33 [6.67, 53.33] | 29.17 | 17.50 | -0.83 [-5.83, +4.17] not separable |
| guard | loso * fast | 119 | 31.93 [18.97, 43.70] | 30.25 | 16.81 | +1.68 [-6.78, +10.92] not separable |
| extra | xr_A B2 slow | 60 | 18.33 [6.67, 30.00] | 18.33 | 16.67 | +0.00 [-5.00, +5.00] not separable |
| extra | xr_A B2 fast | 59 | 33.90 [6.78, 61.07] | 33.90 | 20.34 | +0.00 [-13.79, +11.86] not separable |
| ranking | top2 (loso natural) | 180 | 62.22 [41.67, 81.11] | 62.78 |  | -0.56 [-7.22, +5.56] not separable |
| ranking | group2 (loso natural) | 180 | 71.22 [55.11, 84.89] | 72.33 |  | -1.11 [-5.22, +2.56] not separable |

**F7**

| group | cell | walks | new | v4 | S0 | new minus v4 |
|---|---|---|---|---|---|---|
| zero-shot | xr_A B2 path | 120 | 23.33 [11.67, 35.83] | 23.33 | 20.83 | +0.00 [-3.33, +3.33] not separable |
| zero-shot | xr_A B2 natural | 60 | 26.67 [10.00, 45.00] | 23.33 | 23.33 | +3.33 [-8.33, +15.00] not separable |
| zero-shot | xr_B1 A3 path | 120 | 31.67 [18.33, 47.50] | 30.00 | 44.17 | +1.67 [-1.67, +5.83] not separable |
| cross-day | loso * natural | 180 | 37.78 [22.78, 55.56] | 37.78 | 38.33 | +0.00 [-5.00, +5.56] not separable |
| cross-day | loso * path | 600 | 29.17 [21.67, 35.33] | 30.67 | 30.17 | -1.50 [-4.00, +0.50] not separable |
| cross-day | xr_AB A3 path | 120 | 34.17 [21.67, 46.67] | 30.00 | 42.50 | +4.17 [+0.00, +8.33] not separable |
| cross-day | xr_AB B2 path | 120 | 31.67 [18.33, 45.00] | 22.50 | 23.33 | +9.17 [+4.17, +15.00] separable gain |
| cross-day | xr_AB B2 natural | 60 | 30.00 [11.67, 48.33] | 25.00 | 25.00 | +5.00 [-8.33, +21.67] not separable |
| cross-day | xr_A A3 path | 120 | 32.50 [24.17, 40.83] | 23.33 | 38.33 | +9.17 [+4.17, +14.17] separable gain |
| cross-day | xr_B1 B2 path | 120 | 30.00 [22.50, 37.50] | 22.50 | 35.00 | +7.50 [+4.17, +11.67] separable gain |
| cross-day | xr_B1 B2 natural | 60 | 25.00 [16.67, 33.33] | 28.33 | 30.00 | -3.33 [-13.33, +6.67] not separable |
| cross-day | xr_ABtrk A3 path | 120 | 24.17 [17.50, 29.17] | 25.00 | 39.17 | -0.83 [-9.17, +4.17] not separable |
| cross-day | xr_ABtrk B2 path | 120 | 36.67 [25.00, 51.67] | 30.83 | 20.83 | +5.83 [-0.83, +12.50] not separable |
| guard | loso * slow | 120 | 29.17 [11.67, 51.67] | 29.17 | 17.50 | +0.00 [-6.67, +5.83] not separable |
| guard | loso * fast | 119 | 31.09 [20.17, 42.86] | 30.25 | 16.81 | +0.84 [-5.00, +5.98] not separable |
| extra | xr_A B2 slow | 60 | 30.00 [10.00, 50.00] | 18.33 | 16.67 | +11.67 [+1.67, +21.67] separable gain |
| extra | xr_A B2 fast | 59 | 28.81 [3.51, 55.00] | 33.90 | 20.34 | -5.08 [-13.79, +6.67] not separable |
| ranking | top2 (loso natural) | 180 | 60.56 [41.67, 77.22] | 62.78 |  | -2.22 [-10.00, +5.56] not separable |
| ranking | group2 (loso natural) | 180 | 73.33 [63.78, 83.11] | 72.33 |  | +1.00 [-2.33, +4.44] not separable |

**CNN**

| group | cell | walks | new | v4 | S0 | new minus v4 |
|---|---|---|---|---|---|---|
| zero-shot | xr_A B2 path | 120 | 25.83 [18.33, 32.50] | 23.33 | 20.83 | +2.50 [-4.17, +9.17] not separable |
| zero-shot | xr_A B2 natural | 60 | 23.33 [8.33, 43.33] | 23.33 | 23.33 | +0.00 [-13.33, +11.67] not separable |
| zero-shot | xr_B1 A3 path | 120 | 23.33 [8.33, 40.83] | 30.00 | 44.17 | -6.67 [-8.33, -5.00] separable cost |
| cross-day | loso * natural | 180 | 30.00 [13.89, 52.78] | 37.78 | 38.33 | -7.78 [-23.33, +4.44] not separable |
| cross-day | loso * path | 600 | 26.67 [16.67, 35.50] | 30.67 | 30.17 | -4.00 [-9.67, +1.83] not separable |
| cross-day | xr_AB A3 path | 120 | 32.50 [20.00, 45.00] | 30.00 | 42.50 | +2.50 [-4.17, +8.33] not separable |
| cross-day | xr_AB B2 path | 120 | 24.17 [12.50, 35.83] | 22.50 | 23.33 | +1.67 [-13.33, +18.33] not separable |
| cross-day | xr_AB B2 natural | 60 | 30.00 [15.00, 48.33] | 25.00 | 25.00 | +5.00 [-13.33, +18.33] not separable |
| cross-day | xr_A A3 path | 120 | 37.50 [28.33, 48.33] | 23.33 | 38.33 | +14.17 [+1.67, +25.00] separable gain |
| cross-day | xr_B1 B2 path | 120 | 24.17 [10.00, 41.67] | 22.50 | 35.00 | +1.67 [-12.50, +19.17] not separable |
| cross-day | xr_B1 B2 natural | 60 | 26.67 [13.33, 43.33] | 28.33 | 30.00 | -1.67 [-15.00, +10.00] not separable |
| cross-day | xr_ABtrk A3 path | 120 | 24.17 [14.17, 32.50] | 25.00 | 39.17 | -0.83 [-8.33, +5.83] not separable |
| cross-day | xr_ABtrk B2 path | 120 | 25.83 [20.00, 32.50] | 30.83 | 20.83 | -5.00 [-13.33, +3.33] not separable |
| guard | loso * slow | 120 | 21.67 [0.83, 45.83] | 29.17 | 17.50 | -7.50 [-16.67, -0.83] separable cost |
| guard | loso * fast | 119 | 26.89 [16.81, 38.33] | 30.25 | 16.81 | -3.36 [-10.92, +4.20] not separable |
| extra | xr_A B2 slow | 60 | 20.00 [1.67, 40.00] | 18.33 | 16.67 | +1.67 [-13.33, +16.67] not separable |
| extra | xr_A B2 fast | 59 | 18.64 [3.51, 35.00] | 33.90 | 20.34 | -15.25 [-21.67, -10.17] separable cost |
| ranking | top2 (loso natural) | 180 | 52.78 [37.22, 71.67] | 62.78 |  | -10.00 [-25.00, +3.33] not separable |
| ranking | group2 (loso natural) | 180 | 67.11 [56.44, 80.33] | 72.33 |  | -5.22 [-16.11, +4.89] not separable |

**NP**

| group | cell | walks | new | v4 | S0 | new minus v4 |
|---|---|---|---|---|---|---|
| zero-shot | xr_A B2 path | 120 | 27.50 [21.67, 32.50] | 23.33 | 20.83 | +4.17 [-2.50, +10.00] not separable |
| zero-shot | xr_A B2 natural | 60 | 21.67 [8.33, 41.67] | 23.33 | 23.33 | -1.67 [-15.00, +10.00] not separable |
| zero-shot | xr_B1 A3 path | 120 | 24.17 [8.33, 43.33] | 30.00 | 44.17 | -5.83 [-8.33, -3.33] separable cost |
| cross-day | loso * natural | 180 | 30.56 [15.00, 53.89] | 37.78 | 38.33 | -7.22 [-20.56, +4.44] not separable |
| cross-day | loso * path | 600 | 29.00 [19.67, 37.83] | 30.67 | 30.17 | -1.67 [-6.83, +3.50] not separable |
| cross-day | xr_AB A3 path | 120 | 33.33 [21.67, 45.00] | 30.00 | 42.50 | +3.33 [-4.17, +10.00] not separable |
| cross-day | xr_AB B2 path | 120 | 24.17 [12.50, 35.00] | 22.50 | 23.33 | +1.67 [-13.33, +18.33] not separable |
| cross-day | xr_AB B2 natural | 60 | 31.67 [13.33, 53.33] | 25.00 | 25.00 | +6.67 [-13.33, +21.67] not separable |
| cross-day | xr_A A3 path | 120 | 36.67 [28.33, 45.83] | 23.33 | 38.33 | +13.33 [+1.67, +23.33] separable gain |
| cross-day | xr_B1 B2 path | 120 | 24.17 [10.83, 40.00] | 22.50 | 35.00 | +1.67 [-10.83, +16.67] not separable |
| cross-day | xr_B1 B2 natural | 60 | 28.33 [15.00, 43.33] | 28.33 | 30.00 | +0.00 [-10.00, +10.00] not separable |
| cross-day | xr_ABtrk A3 path | 120 | 26.67 [15.83, 35.83] | 25.00 | 39.17 | +1.67 [-5.00, +8.33] not separable |
| cross-day | xr_ABtrk B2 path | 120 | 26.67 [20.00, 35.00] | 30.83 | 20.83 | -4.17 [-12.50, +3.33] not separable |
| guard | loso * slow | 120 | 23.33 [1.67, 46.67] | 29.17 | 17.50 | -5.83 [-14.17, +0.83] not separable |
| guard | loso * fast | 119 | 26.89 [17.09, 38.33] | 30.25 | 16.81 | -3.36 [-10.00, +3.33] not separable |
| extra | xr_A B2 slow | 60 | 21.67 [3.33, 41.67] | 18.33 | 16.67 | +3.33 [-11.67, +18.33] not separable |
| extra | xr_A B2 fast | 59 | 20.34 [3.51, 40.00] | 33.90 | 20.34 | -13.56 [-21.67, -6.67] separable cost |
| ranking | top2 (loso natural) | 180 | 54.44 [39.44, 71.11] | 62.78 |  | -8.33 [-20.00, +3.33] not separable |
| ranking | group2 (loso natural) | 180 | 68.00 [57.22, 80.33] | 72.33 |  | -4.33 [-13.11, +4.44] not separable |

**F4**; flags: xr_B1_v4: F4 needs two training days; dropped (v4's columns) on this one-day model

| group | cell | walks | new | v4 | S0 | new minus v4 |
|---|---|---|---|---|---|---|
| zero-shot | xr_A B2 path | 120 | 30.83 [24.17, 38.33] | 23.33 | 20.83 | +7.50 [+1.67, +14.17] separable gain |
| zero-shot | xr_A B2 natural | 60 | 21.67 [1.67, 45.00] | 23.33 | 23.33 | -1.67 [-20.00, +16.67] not separable |
| zero-shot | xr_B1 A3 path | 120 | 30.00 [16.67, 46.67] | 30.00 | 44.17 | +0.00 [+0.00, +0.00] not separable |
| cross-day | loso * natural | 180 | 35.56 [20.00, 54.44] | 37.78 | 38.33 | -2.22 [-10.00, +3.89] not separable |
| cross-day | loso * path | 600 | 27.83 [19.17, 35.33] | 30.67 | 30.17 | -2.83 [-5.17, -0.17] separable cost |
| cross-day | xr_AB A3 path | 120 | 27.50 [18.33, 36.67] | 30.00 | 42.50 | -2.50 [-5.00, +0.83] not separable |
| cross-day | xr_AB B2 path | 120 | 30.00 [20.83, 38.33] | 22.50 | 23.33 | +7.50 [-0.83, +15.00] not separable |
| cross-day | xr_AB B2 natural | 60 | 28.33 [16.67, 40.00] | 25.00 | 25.00 | +3.33 [-11.67, +16.67] not separable |
| cross-day | xr_A A3 path | 120 | 27.50 [17.50, 34.17] | 23.33 | 38.33 | +4.17 [-6.67, +14.17] not separable |
| cross-day | xr_B1 B2 path | 120 | 22.50 [13.33, 30.83] | 22.50 | 35.00 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_B1 B2 natural | 60 | 28.33 [13.29, 45.00] | 28.33 | 30.00 | +0.00 [+0.00, +0.00] not separable |
| cross-day | xr_ABtrk A3 path | 120 | 27.50 [20.83, 33.33] | 25.00 | 39.17 | +2.50 [-3.33, +8.33] not separable |
| cross-day | xr_ABtrk B2 path | 120 | 28.33 [20.00, 36.67] | 30.83 | 20.83 | -2.50 [-10.00, +5.83] not separable |
| guard | loso * slow | 120 | 24.17 [5.00, 46.67] | 29.17 | 17.50 | -5.00 [-10.00, -0.83] separable cost |
| guard | loso * fast | 119 | 26.89 [14.65, 39.50] | 30.25 | 16.81 | -3.36 [-8.40, +2.52] not separable |
| extra | xr_A B2 slow | 60 | 21.67 [5.00, 40.00] | 18.33 | 16.67 | +3.33 [-6.67, +15.00] not separable |
| extra | xr_A B2 fast | 59 | 22.03 [10.17, 35.00] | 33.90 | 20.34 | -11.86 [-23.73, -3.39] separable cost |
| ranking | top2 (loso natural) | 180 | 55.56 [40.00, 73.33] | 62.78 |  | -7.22 [-17.78, +2.78] not separable |
| ranking | group2 (loso natural) | 180 | 69.89 [59.22, 80.78] | 72.33 |  | -2.44 [-7.33, +2.11] not separable |

**F5**

| group | cell | walks | new | v4 | S0 | new minus v4 |
|---|---|---|---|---|---|---|
| zero-shot | xr_A B2 path | 120 | 27.50 [20.83, 33.33] | 23.33 | 20.83 | +4.17 [+0.00, +7.50] not separable |
| zero-shot | xr_A B2 natural | 60 | 20.00 [3.33, 40.00] | 23.33 | 23.33 | -3.33 [-20.00, +10.00] not separable |
| zero-shot | xr_B1 A3 path | 120 | 24.17 [10.83, 40.00] | 30.00 | 44.17 | -5.83 [-8.33, -3.33] separable cost |
| cross-day | loso * natural | 180 | 35.00 [20.00, 52.78] | 37.78 | 38.33 | -2.78 [-7.78, +1.67] not separable |
| cross-day | loso * path | 600 | 28.67 [21.67, 37.00] | 30.67 | 30.17 | -2.00 [-5.33, +1.67] not separable |
| cross-day | xr_AB A3 path | 120 | 28.33 [21.67, 35.00] | 30.00 | 42.50 | -1.67 [-8.33, +4.17] not separable |
| cross-day | xr_AB B2 path | 120 | 20.83 [11.67, 31.67] | 22.50 | 23.33 | -1.67 [-5.83, +1.67] not separable |
| cross-day | xr_AB B2 natural | 60 | 23.33 [8.33, 41.67] | 25.00 | 25.00 | -1.67 [-15.00, +10.00] not separable |
| cross-day | xr_A A3 path | 120 | 27.50 [19.17, 37.50] | 23.33 | 38.33 | +4.17 [-1.67, +10.00] not separable |
| cross-day | xr_B1 B2 path | 120 | 22.50 [15.00, 30.00] | 22.50 | 35.00 | +0.00 [-4.17, +3.33] not separable |
| cross-day | xr_B1 B2 natural | 60 | 28.33 [11.67, 48.33] | 28.33 | 30.00 | +0.00 [-5.00, +5.00] not separable |
| cross-day | xr_ABtrk A3 path | 120 | 26.67 [21.67, 31.67] | 25.00 | 39.17 | +1.67 [-2.50, +5.83] not separable |
| cross-day | xr_ABtrk B2 path | 120 | 29.17 [18.33, 41.67] | 30.83 | 20.83 | -1.67 [-4.17, +1.67] not separable |
| guard | loso * slow | 120 | 27.50 [4.17, 53.33] | 29.17 | 17.50 | -1.67 [-5.83, +1.67] not separable |
| guard | loso * fast | 119 | 26.05 [12.61, 42.50] | 30.25 | 16.81 | -4.20 [-10.00, +0.85] not separable |
| extra | xr_A B2 slow | 60 | 11.67 [1.67, 21.67] | 18.33 | 16.67 | -6.67 [-16.67, +0.00] not separable |
| extra | xr_A B2 fast | 59 | 22.03 [8.47, 36.67] | 33.90 | 20.34 | -11.86 [-20.00, -5.26] separable cost |
| ranking | top2 (loso natural) | 180 | 57.78 [42.78, 73.33] | 62.78 |  | -5.00 [-11.67, +1.11] not separable |
| ranking | group2 (loso natural) | 180 | 68.44 [54.89, 80.56] | 72.33 |  | -3.89 [-7.67, -0.44] separable cost |

**F3+F7+NP+F4+F5**; flags: xr_B1_v4: F4 needs two training days; dropped (v4's columns) on this one-day model

| group | cell | walks | new | v4 | S0 | new minus v4 |
|---|---|---|---|---|---|---|
| zero-shot | xr_A B2 path | 120 | 27.50 [20.00, 33.33] | 23.33 | 20.83 | +4.17 [-2.50, +10.00] not separable |
| zero-shot | xr_A B2 natural | 60 | 21.67 [8.33, 41.67] | 23.33 | 23.33 | -1.67 [-15.00, +10.00] not separable |
| zero-shot | xr_B1 A3 path | 120 | 26.67 [10.00, 46.69] | 30.00 | 44.17 | -3.33 [-6.67, +0.83] not separable |
| cross-day | loso * natural | 180 | 31.11 [14.44, 54.44] | 37.78 | 38.33 | -6.67 [-21.67, +5.56] not separable |
| cross-day | loso * path | 600 | 27.67 [17.67, 36.50] | 30.67 | 30.17 | -3.00 [-8.50, +2.50] not separable |
| cross-day | xr_AB A3 path | 120 | 34.17 [20.83, 47.50] | 30.00 | 42.50 | +4.17 [-3.33, +10.83] not separable |
| cross-day | xr_AB B2 path | 120 | 25.83 [12.50, 39.17] | 22.50 | 23.33 | +3.33 [-12.50, +20.83] not separable |
| cross-day | xr_AB B2 natural | 60 | 30.00 [15.00, 48.33] | 25.00 | 25.00 | +5.00 [-13.33, +18.33] not separable |
| cross-day | xr_A A3 path | 120 | 38.33 [28.33, 48.33] | 23.33 | 38.33 | +15.00 [+3.33, +25.00] separable gain |
| cross-day | xr_B1 B2 path | 120 | 24.17 [10.83, 39.17] | 22.50 | 35.00 | +1.67 [-11.67, +16.67] not separable |
| cross-day | xr_B1 B2 natural | 60 | 28.33 [13.33, 48.33] | 28.33 | 30.00 | +0.00 [-13.33, +11.67] not separable |
| cross-day | xr_ABtrk A3 path | 120 | 24.17 [13.33, 34.17] | 25.00 | 39.17 | -0.83 [-10.00, +7.50] not separable |
| cross-day | xr_ABtrk B2 path | 120 | 29.17 [23.33, 35.83] | 30.83 | 20.83 | -1.67 [-9.17, +5.83] not separable |
| guard | loso * slow | 120 | 23.33 [1.67, 46.67] | 29.17 | 17.50 | -5.83 [-14.17, +0.83] not separable |
| guard | loso * fast | 119 | 26.89 [15.97, 40.00] | 30.25 | 16.81 | -3.36 [-10.92, +5.04] not separable |
| extra | xr_A B2 slow | 60 | 21.67 [3.33, 41.67] | 18.33 | 16.67 | +3.33 [-11.67, +18.33] not separable |
| extra | xr_A B2 fast | 59 | 22.03 [3.51, 45.00] | 33.90 | 20.34 | -11.86 [-21.67, -1.67] separable cost |
| ranking | top2 (loso natural) | 180 | 52.78 [35.00, 71.67] | 62.78 |  | -10.00 [-24.44, +3.33] not separable |
| ranking | group2 (loso natural) | 180 | 67.11 [55.66, 80.22] | 72.33 |  | -5.22 [-14.89, +3.67] not separable |