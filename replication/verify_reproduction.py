#!/usr/bin/env python3
"""Verify scientific results, public scope, metadata, and generated assets."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from file_inventory import FIGURE_NAMES, PUBLIC_FILES, RESULT_NAMES, TABLE_NAMES

ROOT = Path(__file__).resolve().parents[1]
sys.set_int_max_str_digits(0)
SOURCE_DATE_EPOCH = 1786968000
TEXT_SUFFIXES = {
    "",
    ".bib",
    ".cff",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yml",
    ".yaml",
    ".tex",
}
FORBIDDEN_TERM_DIGESTS = {
    "85c5264188683fb774bb88f3ab468c46ee9a774e458c9bc5ae6e9c91c11f9ef3": "private control-system phrase",
    "c71195a843a9800d80ec75e501dcbfedc276f5c208097a31d84d8cc1fe12ac9b": "internal project label",
    "0eee3a0bb608847ca1ac05a7689e07f625d04045c0146025136a545ec9ccbc09": "internal execution label",
    "2ab8c63a63b208bd8731b8b32ef3126e9b8bc67469661b3d2621bad70ddc9522": "internal execution label",
    "d72402872e7206336d53a939ac29891f9eac2d157c568fe48d3f6e13ee88fe43": "internal outcome label",
    "98e6206d2525468430321a5e4f24b486f5f82c6ba2d0f05250bb0a95d24b82d6": "internal design word",
    "52563f898870e6ce7817b3ffbd430df2104719a74fc408cbe24eb9f481078ce4": "internal design word",
    "ffb304816a1090313e833215c08dae3d209cfad1ffd1f674f0909a2ae99e1394": "internal design word",
    "da7f739f627198465eeab537a6f7a435dc4a0c332f9e4a8462293eb3f4ab7ee0": "internal design word",
}
PATH_COMPONENTS = tuple(
    "".join(chr(value) for value in values)
    for values in ((85, 115, 101, 114, 115), (86, 111, 108, 117, 109, 101, 115))
)
CREDENTIAL_PREFIXES = tuple(
    "".join(chr(value) for value in values)
    for values in (
        (103, 104, 112, 95),
        (103, 105, 116, 104, 117, 98, 95, 112, 97, 116, 95),
        (115, 107, 45),
        (65, 75, 73, 65),
    )
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(relative: str) -> dict:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"missing, invalid, or symlinked JSON file: {relative}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON root is not an object: {relative}")
    return payload


def scan_public_text(text: str, label: str) -> None:
    tokens = re.findall(r"[a-z0-9_]+", text.casefold())
    candidates = tokens + [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]
    for candidate in candidates:
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        if digest in FORBIDDEN_TERM_DIGESTS:
            raise SystemExit(
                f"{FORBIDDEN_TERM_DIGESTS[digest]} in public material: {label}"
            )
    if any(f"/{component}/" in text for component in PATH_COMPONENTS):
        raise SystemExit(f"private absolute path in public material: {label}")
    if re.search(r"\b019f[a-f0-9-]{20,}\b", text):
        raise SystemExit(f"private task identifier in public material: {label}")
    if any(prefix in text for prefix in CREDENTIAL_PREFIXES):
        raise SystemExit(f"credential-like prefix in public material: {label}")


def require_exact_names(folder: str, expected: set[str]) -> None:
    path = ROOT / folder
    if path.is_symlink() or not path.is_dir():
        raise SystemExit(f"missing, invalid, or symlinked directory: {folder}")
    observed = {item.name for item in path.iterdir() if item.is_file()}
    if observed != expected:
        raise SystemExit(
            f"unexpected {folder} file set: missing={sorted(expected - observed)} extra={sorted(observed - expected)}"
        )
    if any(item.is_symlink() or not item.is_file() for item in path.iterdir()):
        raise SystemExit(f"non-regular entry in {folder}")


def check_environment() -> dict[str, str]:
    expected = {
        "numpy": "2.2.6",
        "matplotlib": "3.9.2",
        "sympy": "1.13.1",
        "mpmath": "1.3.0",
    }
    observed = {name: importlib.metadata.version(name) for name in expected}
    if observed != expected:
        raise SystemExit(f"reference package version mismatch: {observed}")
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(f"Python 3.12 required; observed {sys.version.split()[0]}")
    return observed


def check_science() -> dict[str, int]:
    require_exact_names("results", RESULT_NAMES)
    stability = load_json("results/stability_grid.json")
    if stability.get("schema") != "learning-from-prices-stability-grid-v1":
        raise SystemExit("stability-grid schema mismatch")
    if stability.get("counts") != {"BOUNDARY": 0, "STABLE": 6267, "UNSTABLE": 1833}:
        raise SystemExit("stability-grid count mismatch")
    if stability.get("finite_horizon_limiting_objects_at_k1000") != {
        "NONZERO_FIXED_POINT": 6267,
        "SINGULAR_BOUNDARY_LIMIT": 1833,
    }:
        raise SystemExit("stability-grid limiting-object mismatch")
    source = stability.get("source_sweep", {})
    if source.get("counts") != {"BOUNDARY": 0, "STABLE": 61, "UNSTABLE": 39}:
        raise SystemExit("source-sweep count mismatch")
    if len(stability.get("cells", [])) != 8100 or len(source.get("cells", [])) != 100:
        raise SystemExit("stability-grid cell count mismatch")
    for cell in stability["cells"] + source["cells"]:
        if set(cell.get("errors", {})) != {"1", "2", "3", "10", "99", "100"}:
            raise SystemExit("stability-grid horizon set mismatch")
        if set(cell.get("persistent_entry", {})) != {"0.05", "0.01", "0.001", "0.0001"}:
            raise SystemExit("stability-grid persistence-band set mismatch")

    horizon = load_json("results/finite_horizon_sensitivity.json")
    if horizon.get("schema") != "learning-from-prices-finite-horizon-v1":
        raise SystemExit("finite-horizon schema mismatch")
    expected_branches = {
        "article_updater_H",
        "deposited_D",
        "partial_revelation_benchmark",
    }
    if set(horizon.get("branches", {})) != expected_branches:
        raise SystemExit("finite-horizon branch set mismatch")
    if (
        horizon["branches"]["partial_revelation_benchmark"]["persistent_entry"]["0.01"][
            "coefficient"
        ]
        != 10
    ):
        raise SystemExit("partial 1-percent horizon mismatch")
    if {
        horizon["branches"][branch]["persistent_entry"]["0.01"]["coefficient"]
        for branch in ("article_updater_H", "deposited_D")
    } != {20}:
        raise SystemExit("private 1-percent horizon mismatch")

    starts = load_json("results/starting_value_sensitivity.json")
    if starts.get("schema") != "learning-from-prices-starting-values-v1":
        raise SystemExit("starting-value schema mismatch")
    if (
        set(starts.get("branches", {})) != expected_branches
        or len(starts.get("private_scalar_starts", {})) != 7
    ):
        raise SystemExit("starting-value case set mismatch")
    for row in starts["private_scalar_starts"].values():
        if row.get("full_vector_completion") != "SCALAR_REDUCTION_ONLY":
            raise SystemExit("starting-value scope mismatch")
        if row.get("coefficient_error", {}).get("status") != "NOT_APPLICABLE":
            raise SystemExit("starting-value coefficient applicability mismatch")

    boundary = load_json("results/boundary_pole_diagnostics.json")
    if boundary.get("schema") != "learning-from-prices-boundary-pole-v1":
        raise SystemExit("boundary-and-pole schema mismatch")
    if (
        len(boundary.get("boundary_cases", [])) != 17
        or len(boundary.get("pole_preimage_cases", [])) != 85
    ):
        raise SystemExit("boundary-and-pole case count mismatch")
    zero_cases = [
        case
        for case in boundary["pole_preimage_cases"]
        if case["offset"]["numerator"] == 0
    ]
    observed_poles = [
        (case["preimage_power"], case["status"], case["terminal_k"])
        for case in zero_cases
    ]
    if observed_poles != [
        (1, "EXACT_POLE", 0),
        (2, "EXACT_POLE", 1),
        (3, "EXACT_POLE", 2),
        (4, "EXACT_POLE", 3),
        (5, "EXACT_POLE", 4),
    ]:
        raise SystemExit("boundary-and-pole indexing mismatch")

    price_gap = load_json("results/price_gap_grid.json")
    if price_gap.get("schema") != "learning-from-prices-price-gap-v1":
        raise SystemExit("price-gap schema mismatch")
    if (
        price_gap.get("relative_normalization")
        != "article_updater_H_fixed_price_sup_norm"
    ):
        raise SystemExit("price-gap normalization mismatch")
    exact_first = price_gap["finite_paths"]["1"]["exact_rational_metrics"][
        "relative_sup"
    ]["rational"]
    if exact_first != "750000/3204433":
        raise SystemExit("price-gap exact first-update value mismatch")

    pole_guard = load_json("results/finite_pole_certificate.json")
    if pole_guard.get("schema") != "learning-from-prices-finite-pole-certificate-v1":
        raise SystemExit("finite-pole certificate schema mismatch")
    if pole_guard.get("status") != "PASS" or pole_guard.get("exact_finite_poles") != 0:
        raise SystemExit("finite-pole certificate result mismatch")
    if (
        pole_guard.get("deposited_sweep_cells_checked") != 100
        or pole_guard.get("prespecified_grid_cells_checked") != 8100
    ):
        raise SystemExit("finite-pole certificate coverage mismatch")
    if pole_guard.get("maximum_monotone_crossing_exponent_checked") != 416:
        raise SystemExit("finite-pole diagnostic exponent mismatch")

    persistence = load_json("results/persistence_certificate.json")
    if (
        persistence.get("schema") != "learning-from-prices-persistence-certificate-v1"
        or persistence.get("status") != "PASS"
    ):
        raise SystemExit("persistence certificate status mismatch")
    if set(persistence.get("surfaces", {})) != {"deposited_sweep", "prespecified_grid"}:
        raise SystemExit("persistence certificate surface mismatch")
    for name, stable, unstable, checks in (
        ("deposited_sweep", 61, 39, 244),
        ("prespecified_grid", 6267, 1833, 25068),
    ):
        row = persistence["surfaces"][name]
        if (
            row.get("stable_cells"),
            row.get("unstable_cells"),
            row.get("stable_cell_band_checks"),
        ) != (stable, unstable, checks):
            raise SystemExit(f"persistence certificate count mismatch: {name}")
        if (
            row.get("stable_delta_greater_or_equal_one") != 0
            or row.get("persistent_classifier_mismatches") != 0
        ):
            raise SystemExit(f"persistence certificate proof-domain mismatch: {name}")
        if row.get("unstable_k1000_above_largest_band") != unstable:
            raise SystemExit(
                f"persistence certificate unstable endpoint mismatch: {name}"
            )

    with (ROOT / "results/stability_grid_cells.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        if sum(1 for _ in csv.reader(handle)) != 8101:
            raise SystemExit("stability-grid CSV row count mismatch")
    with (ROOT / "results/source_sweep_cells.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        if sum(1 for _ in csv.reader(handle)) != 101:
            raise SystemExit("source-sweep CSV row count mismatch")

    manifest = load_json("results/RESULTS_MANIFEST.json")
    if manifest.get("schema") != "learning-from-prices-results-manifest-v1":
        raise SystemExit("result manifest schema mismatch")
    expected_payloads = RESULT_NAMES - {"RESULTS_MANIFEST.json"}
    if set(manifest.get("files", {})) != expected_payloads:
        raise SystemExit("result manifest file set mismatch")
    for name, expected in manifest["files"].items():
        if sha256(ROOT / "results" / name) != expected:
            raise SystemExit(f"result manifest digest mismatch: {name}")

    return {
        "stable_grid_cells": 6267,
        "unstable_grid_cells": 1833,
        "source_sweep_unstable": 39,
        "finite_poles": 0,
        "persistence_checks": 25312,
    }


def check_tables() -> None:
    require_exact_names("tables", TABLE_NAMES)
    custody = load_json("provenance/recorded_source_checks.json")
    if custody.get("status") != "RECORDED_NOT_REGENERATED":
        raise SystemExit("recorded source-check status mismatch")
    if (
        custody.get("source_execution", {}).get("repeated_by_this_repository")
        is not False
    ):
        raise SystemExit("recorded source-check execution boundary mismatch")
    for number, stem, expected_rows in (
        (1, "source_custody", 5),
        (2, "private_identities", 7),
        (3, "stability_horizon", 8),
        (4, "claim_boundary", 5),
    ):
        csv_path = ROOT / f"tables/table{number}_{stem}.csv"
        tex_path = ROOT / f"tables/table{number}_{stem}.tex"
        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        if len(rows) != expected_rows + 1:
            raise SystemExit(f"table {number} row count mismatch")
        tex = tex_path.read_text(encoding="utf-8")
        for cell in (cell for row in rows for cell in row):
            if cell not in tex:
                raise SystemExit(f"table {number} CSV/TeX mismatch: {cell}")
        if number == 1 and rows[1:] != custody.get("table_rows"):
            raise SystemExit("table 1 differs from recorded source-check rows")
    table2 = (ROOT / "tables/table2_private_identities.csv").read_text(encoding="utf-8")
    for exact in ("125000/3544233", "125000/751233", "168773/35773", "603/103"):
        if exact not in table2:
            raise SystemExit(f"table 2 exact value missing: {exact}")


def check_figures() -> None:
    require_exact_names("figures", FIGURE_NAMES)
    for name in sorted(FIGURE_NAMES):
        path = ROOT / "figures" / name
        data = path.read_bytes()
        decoded = data.decode("latin-1", errors="ignore")
        scan_public_text(decoded, f"figure metadata: {name}")
        if path.suffix == ".pdf":
            qpdf = subprocess.run(
                ["qpdf", "--check", str(path)], capture_output=True, text=True
            )
            if qpdf.returncode:
                raise SystemExit(f"qpdf check failed: {name}: {qpdf.stderr.strip()}")
            fonts = subprocess.run(
                ["pdffonts", str(path)], capture_output=True, text=True
            )
            if fonts.returncode:
                raise SystemExit(f"pdffonts failed: {name}")
            rows = [
                line.split() for line in fonts.stdout.splitlines()[2:] if line.strip()
            ]
            if not rows or any(
                len(row) < 7 or row[-5:-2] != ["yes", "yes", "yes"] for row in rows
            ):
                raise SystemExit(
                    f"figure PDF font embedding/subsetting/Unicode failure: {name}"
                )
            metadata = subprocess.run(
                ["pdfinfo", str(path)], capture_output=True, text=True, check=True
            ).stdout
            expected_date = datetime.fromtimestamp(
                SOURCE_DATE_EPOCH, tz=timezone.utc
            ).strftime("%a %b %d %H:%M:%S %Y UTC")
            if f"CreationDate:    {expected_date}" not in metadata:
                raise SystemExit(
                    f"figure PDF creation date is not deterministic: {name}"
                )
    descriptions = (ROOT / "docs/FIGURE_DESCRIPTIONS.md").read_text(encoding="utf-8")
    if (
        sum(1 for line in descriptions.splitlines() if line.startswith("## Figure "))
        != 4
    ):
        raise SystemExit("figure-description count mismatch")


def observed_public_files() -> set[str]:
    observed: set[str] = set()
    ignored_roots = {".git", ".mplconfig", ".venv", "dist", "__pycache__"}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in ignored_roots for part in relative.parts):
            continue
        if path.is_symlink():
            raise SystemExit(f"symlink in public repository: {relative.as_posix()}")
        if path.is_file():
            observed.add(relative.as_posix())
    return observed


def check_public_scope() -> dict[str, int]:
    observed = observed_public_files()
    if observed != PUBLIC_FILES:
        raise SystemExit(
            f"public file-set mismatch: missing={sorted(PUBLIC_FILES - observed)} extra={sorted(observed - PUBLIC_FILES)}"
        )
    prohibited_suffixes = {
        ".m",
        ".mat",
        ".fig",
        ".mlx",
        ".mex",
        ".pptx",
        ".docx",
        ".zip",
    }
    prohibited_directories = {
        "manuscript",
        "supplement",
        "cover_letter",
        "reviews",
        "presentation",
    }
    text_files = 0
    for relative in sorted(observed):
        path = ROOT / relative
        if path.suffix.lower() in prohibited_suffixes:
            raise SystemExit(f"prohibited file format in public repository: {relative}")
        if any(part in prohibited_directories for part in Path(relative).parts):
            raise SystemExit(
                f"prohibited publication directory in public repository: {relative}"
            )
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"LICENSE", "Makefile"}:
            text = path.read_text(encoding="utf-8")
            text_files += 1
            scan_public_text(text, relative)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.split())
    for phrase in (
        "supplementary research and technical aids",
        "programming syntax and package use",
        "secondary and adversarial checks",
        "accepts full responsibility",
    ):
        if phrase not in normalized_readme:
            raise SystemExit(f"generative-AI disclosure phrase missing: {phrase}")
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    for field in (
        'family-names: "Bodon"',
        'given-names: "Mateo"',
        'orcid: "https://orcid.org/0009-0004-5012-835X"',
        'license: "BSD-3-Clause"',
        'version: "1.0.2"',
        'repository-code: "https://github.com/MateoBodon/learning-from-prices-reproduction"',
    ):
        if field not in cff:
            raise SystemExit(f"CITATION.cff field missing: {field}")
    if (
        not (ROOT / "LICENSE")
        .read_text(encoding="utf-8")
        .startswith("BSD 3-Clause License")
    ):
        raise SystemExit("BSD 3-Clause license text missing")

    release_manifest = load_json("RELEASE_MANIFEST.json")
    if (
        release_manifest.get("status") != "PASS"
        or release_manifest.get("license") != "BSD-3-Clause"
    ):
        raise SystemExit("public release manifest status or license mismatch")
    rows = release_manifest.get("entries", [])
    expected = PUBLIC_FILES - {"RELEASE_MANIFEST.json"}
    if {row.get("path") for row in rows} != expected or len(rows) != len(expected):
        raise SystemExit("public release manifest file set mismatch")
    for row in rows:
        path = ROOT / row["path"]
        if row.get("sha256") != sha256(path) or row.get("bytes") != path.stat().st_size:
            raise SystemExit(f"public release manifest digest mismatch: {row['path']}")
    return {"files": len(observed), "text_files_scanned": text_files}


def verify() -> dict:
    environment = check_environment()
    science = check_science()
    check_tables()
    check_figures()
    scope = check_public_scope()
    return {
        "schema": "learning-from-prices-public-verification-v1",
        "status": "PASS",
        "environment": environment,
        "science": science,
        "public_scope": scope,
        "network_used": False,
        "matlab_invoked": False,
        "third_party_source_included": False,
        "manuscript_included": False,
    }


def main() -> None:
    print(json.dumps(verify(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
