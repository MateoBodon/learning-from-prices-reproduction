#!/usr/bin/env python3
"""Build the checksum manifest and deterministic public release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

from file_inventory import ARCHIVE_STEM, RELEASE_MEMBERS, RELEASE_TAG, RELEASE_VERSION

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
MANIFEST_PATH = ROOT / "RELEASE_MANIFEST.json"
FIXED_ZIP_TIME = (2026, 8, 12, 12, 0, 0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_member(relative: str) -> bytes:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"missing, invalid, or symlinked release member: {relative}")
    return path.read_bytes()


def build_manifest() -> bytes:
    entries = []
    for relative in sorted(RELEASE_MEMBERS):
        data = read_member(relative)
        entries.append(
            {"path": relative, "sha256": sha256_bytes(data), "bytes": len(data)}
        )
    payload = {
        "schema": "learning-from-prices-public-release-manifest-v1",
        "status": "PASS",
        "version": RELEASE_VERSION,
        "tag": RELEASE_TAG,
        "release_date": "2026-08-12",
        "creator": {
            "name": "Mateo Bodon",
            "orcid": "https://orcid.org/0009-0004-5012-835X",
        },
        "license": "BSD-3-Clause",
        "scope": "independent code, documentation, and lawful derived results; no manuscript or third-party source files",
        "entries": entries,
    }
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    MANIFEST_PATH.write_bytes(data)
    return data


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.flag_bits = 0x800
    return info


def build_archive(manifest_data: bytes) -> tuple[Path, str]:
    if DIST.is_symlink():
        raise SystemExit("refusing symlinked release directory")
    DIST.mkdir(exist_ok=True)
    archive = DIST / f"{ARCHIVE_STEM}.zip"
    prefix = f"{ARCHIVE_STEM}/"
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        for relative in sorted(RELEASE_MEMBERS | {"RELEASE_MANIFEST.json"}):
            data = (
                manifest_data
                if relative == "RELEASE_MANIFEST.json"
                else read_member(relative)
            )
            zf.writestr(zip_info(prefix + relative), data, compresslevel=9)
    digest = sha256_bytes(archive.read_bytes())
    sidecar = DIST / f"{archive.name}.sha256"
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    (DIST / "RELEASE_MANIFEST.json").write_bytes(manifest_data)
    return archive, digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    manifest_data = build_manifest()
    if args.manifest_only:
        print(
            json.dumps(
                {"status": "PASS", "manifest_entries": len(RELEASE_MEMBERS)},
                sort_keys=True,
            )
        )
        return
    archive, digest = build_archive(manifest_data)
    print(
        json.dumps(
            {
                "status": "PASS",
                "archive": archive.name,
                "sha256": digest,
                "members": len(RELEASE_MEMBERS) + 1,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
