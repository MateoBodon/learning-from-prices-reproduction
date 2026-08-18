#!/usr/bin/env python3
"""Verify the deterministic public ZIP, manifest, and checksum sidecar."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

from file_inventory import ARCHIVE_STEM, RELEASE_MEMBERS, RELEASE_TAG, RELEASE_VERSION

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    archive = DIST / f"{ARCHIVE_STEM}.zip"
    sidecar = DIST / f"{archive.name}.sha256"
    root_manifest = ROOT / "RELEASE_MANIFEST.json"
    dist_manifest = DIST / "RELEASE_MANIFEST.json"
    for path in (archive, sidecar, root_manifest, dist_manifest):
        if path.is_symlink() or not path.is_file():
            raise SystemExit(
                f"missing, invalid, or symlinked release file: {path.name}"
            )

    manifest_data = root_manifest.read_bytes()
    if dist_manifest.read_bytes() != manifest_data:
        raise SystemExit("root and release manifest bytes differ")
    manifest = json.loads(manifest_data)
    if manifest.get("status") != "PASS" or manifest.get("version") != RELEASE_VERSION:
        raise SystemExit("release manifest status or version mismatch")
    if manifest.get("tag") != RELEASE_TAG or manifest.get("license") != "BSD-3-Clause":
        raise SystemExit("release manifest tag or license mismatch")
    rows = manifest.get("entries", [])
    if {row.get("path") for row in rows} != RELEASE_MEMBERS or len(rows) != len(
        RELEASE_MEMBERS
    ):
        raise SystemExit("release manifest member set mismatch")
    for row in rows:
        data = (ROOT / row["path"]).read_bytes()
        if row.get("sha256") != sha256(data) or row.get("bytes") != len(data):
            raise SystemExit(f"release manifest byte mismatch: {row['path']}")

    archive_digest = sha256(archive.read_bytes())
    expected_sidecar = f"{archive_digest}  {archive.name}\n"
    if sidecar.read_text(encoding="utf-8") != expected_sidecar:
        raise SystemExit("release SHA-256 sidecar mismatch")

    prefix = f"{ARCHIVE_STEM}/"
    expected_names = [prefix + name for name in sorted(RELEASE_MEMBERS)] + [
        prefix + "RELEASE_MANIFEST.json"
    ]
    expected_names.sort()
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        if names != expected_names:
            raise SystemExit("release ZIP member order or set mismatch")
        for info in zf.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or info.is_dir():
                raise SystemExit(f"unsafe release ZIP path: {info.filename}")
            if info.date_time != (2026, 8, 17, 12, 0, 0):
                raise SystemExit(f"non-deterministic ZIP timestamp: {info.filename}")
            relative = info.filename.removeprefix(prefix)
            expected = (
                manifest_data
                if relative == "RELEASE_MANIFEST.json"
                else (ROOT / relative).read_bytes()
            )
            if zf.read(info) != expected:
                raise SystemExit(f"release ZIP captured-byte mismatch: {relative}")
            if re.search(
                r"(?i)(^|/)(manuscript|supplement|cover_letter|reviews?|presentation)(/|$)",
                relative,
            ):
                raise SystemExit(
                    f"prohibited publication material in release: {relative}"
                )
            if Path(relative).suffix.lower() in {
                ".m",
                ".mat",
                ".fig",
                ".mlx",
                ".mex",
                ".pptx",
                ".docx",
            }:
                raise SystemExit(
                    f"prohibited third-party or presentation format in release: {relative}"
                )

    print(
        json.dumps(
            {
                "status": "PASS",
                "archive": archive.name,
                "sha256": archive_digest,
                "members": len(expected_names),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
