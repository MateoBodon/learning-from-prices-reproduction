# Learning-from-prices reproduction materials

This repository contains Mateo Bodon's independent reproduction code and
derived numerical materials for the accompanying manuscript, “Equilibrium
Consistency and Finite-Iteration Dynamics in Learning from Prices.” The
manuscript itself is not distributed here.

The code checks equilibrium identities, compares two denominator conventions,
derives the reduced private-map recurrence, and reproduces the finite-horizon,
stability, boundary, and price-gap results reported in the manuscript. Exact
rational arithmetic determines identities and classifications; floating-point
values are used only for display where the result records say so.

## Scope

The repository regenerates the independent results, figures, and tables in
`results/`, `figures/`, and `tables/`. It does not contain or execute the
third-party MATLAB source associated with the published article. Recorded
checks from one retained source execution are isolated in
`provenance/recorded_source_checks.json` and are labeled
`RECORDED_NOT_REGENERATED` wherever they are used.

Two distinctions are important:

- `168773/35773` is the ratio of the two horizon-specific normalized price
  gaps. `603/103` is the separate ratio of the raw coefficient gaps.
- The 1,833 unstable paths in the 8,100-cell census approach a
  branch-dependent singular boundary. That boundary is not a fixed point,
  equilibrium, attractor, or selected economic outcome.

## Rebuild

The reference environment is Python 3.12.2 with the exact package versions in
`requirements.txt`. Poppler's `pdffonts` utility is used for the optional
embedded-font check.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
make rebuild
```

`make rebuild` removes only enumerated generated files, reruns the symbolic
checks and independent analysis, redraws the figures and tables, creates a
checksum manifest, and runs the complete verifier. It neither uses the network
nor invokes MATLAB.

To build and verify the deterministic versioned archive:

```bash
make release
```

The release command writes a ZIP, a SHA-256 sidecar, and a copy of the release
manifest under `dist/`. Archive members are sorted and use fixed timestamps and
file modes.

## Results and provenance

- `RESULTS.md` summarizes the main reproduced quantities.
- `PROVENANCE.md` identifies the external article, appendix, and public source
  record without redistributing their files.
- `docs/FIGURE_DESCRIPTIONS.md` supplies text descriptions for the four
  figures.
- `RELEASE_MANIFEST.json` binds every distributed file to its SHA-256 digest.

## Use of generative AI tools

Generative-AI tools served as supplementary research and technical aids during
literature review, for assistance with programming syntax and package use
during code development, and for secondary and adversarial checks of
mathematical derivations, code, and reproducibility materials. Mateo Bodon
determined the research questions, methods, mathematical arguments,
implementation, interpretation, and final wording; independently reviewed the
cited sources and every reported equation, result, figure, table, code file,
and statement; and accepts full responsibility for the work. A final personal
reading and analysis of the exact manuscript submission files remains required
before submission.

## Citation and license

Citation metadata are in `CITATION.cff`. Mateo Bodon's original repository
contents are licensed under the BSD 3-Clause License. The cited third-party
research materials are not included or relicensed; see `NOTICE.md`.
