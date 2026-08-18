"""Exact file inventory for the public reproduction repository and release."""

RELEASE_VERSION = "1.0.2"
RELEASE_TAG = f"v{RELEASE_VERSION}"
ARCHIVE_STEM = f"learning-from-prices-reproduction-{RELEASE_TAG}"

RESULT_NAMES = {
    "RESULTS_MANIFEST.json",
    "boundary_pole_diagnostics.json",
    "finite_horizon_sensitivity.json",
    "finite_pole_certificate.json",
    "persistence_certificate.json",
    "price_gap_grid.json",
    "source_sweep_cells.csv",
    "stability_grid.json",
    "stability_grid_cells.csv",
    "starting_value_sensitivity.json",
}

FIGURE_NAMES = {
    "Fig1_stability_regions.pdf",
    "Fig1_stability_regions.png",
    "Fig2_finite_iteration_error.pdf",
    "Fig2_finite_iteration_error.png",
    "Fig3_pole_geometry.pdf",
    "Fig3_pole_geometry.png",
    "Fig4_private_map_paths.pdf",
    "Fig4_private_map_paths.png",
}

TABLE_NAMES = {
    f"table{number}_{stem}.{suffix}"
    for number, stem in (
        (1, "source_custody"),
        (2, "private_identities"),
        (3, "stability_horizon"),
        (4, "claim_boundary"),
    )
    for suffix in ("csv", "tex")
}

STATIC_FILES = {
    ".github/workflows/reproduce.yml",
    ".gitignore",
    ".python-version",
    "CITATION.cff",
    "ENVIRONMENT.md",
    "LICENSE",
    "Makefile",
    "NOTICE.md",
    "PROVENANCE.md",
    "README.md",
    "RESULTS.md",
    "docs/FIGURE_DESCRIPTIONS.md",
    "provenance/recorded_source_checks.json",
    "references.bib",
    "replication/build_release.py",
    "replication/check_theory.py",
    "replication/clean_generated.py",
    "replication/file_inventory.py",
    "replication/render_assets.py",
    "replication/run_analysis.py",
    "replication/verify_release.py",
    "replication/verify_reproduction.py",
    "requirements.txt",
}

GENERATED_FILES = (
    {f"results/{name}" for name in RESULT_NAMES}
    | {f"figures/{name}" for name in FIGURE_NAMES}
    | {f"tables/{name}" for name in TABLE_NAMES}
)

PUBLIC_FILES = STATIC_FILES | GENERATED_FILES | {"RELEASE_MANIFEST.json"}
RELEASE_MEMBERS = PUBLIC_FILES - {"RELEASE_MANIFEST.json"}
