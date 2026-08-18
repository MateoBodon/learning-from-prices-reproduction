# Reproduced results

The clean build verifies the following exact or certified quantities:

- Article/updater-H private root:
  `(304/581, 277/581, 80/581, -4432/14525)`.
- Deposited-D mean-supply loading: `11080/116781`.
- Mean-supply market-clearing residual at the deposited-system root:
  `5000/116781`.
- Original normalized fixed-point price gap: `125000/3544233`.
- Original normalized first-update price gap: `125000/751233`.
- Ratio of those normalized gaps: `168773/35773`.
- Separate unnormalized constant-coefficient-gap ratio: `603/103`.
- Deposited 100-point variance sweep: 61 stable and 39 unstable cases.
- Prespecified 8,100-cell variance grid: 6,267 stable and 1,833 unstable
  cases, with no boundary cells.
- Closest stable grid value: `epsilon = 625/626`.
- Exact finite-pole scan: zero finite poles across the 100 source-sweep paths
  and 8,100 grid paths.
- Persistence checks: 244 source-sweep and 25,068 grid cell-by-band checks,
  with zero mismatches; every unstable path remains above the largest reported
  error band at iteration 1,000.

The build preserves undefined states as typed outcomes rather than converting
them to numerical zeros or dropping them. The detailed exact values, decimal
display records, path classifications, and per-cell results are in `results/`.
