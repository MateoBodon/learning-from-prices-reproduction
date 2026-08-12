#!/usr/bin/env python3
"""Remove only the enumerated files created by the public build."""

from __future__ import annotations

import re
from pathlib import Path

from file_inventory import ARCHIVE_STEM, GENERATED_FILES

ROOT = Path(__file__).resolve().parents[1]


def remove_file(relative: str) -> None:
    path = ROOT / relative
    if path.is_symlink():
        raise SystemExit(f"refusing symlinked generated path: {relative}")
    if path.exists() and not path.is_file():
        raise SystemExit(f"generated path is not a regular file: {relative}")
    if path.is_file():
        path.unlink()


for name in sorted(GENERATED_FILES | {"RELEASE_MANIFEST.json"}):
    remove_file(name)

for folder in (ROOT / "results", ROOT / "figures", ROOT / "tables"):
    if folder.is_symlink():
        raise SystemExit(f"refusing symlinked output directory: {folder.name}")
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()

dist = ROOT / "dist"
if dist.is_symlink():
    raise SystemExit("refusing symlinked release directory")
if dist.exists() and not dist.is_dir():
    raise SystemExit("release location is not a directory")
for name in (
    f"{ARCHIVE_STEM}.zip",
    f"{ARCHIVE_STEM}.zip.sha256",
    "RELEASE_MANIFEST.json",
):
    remove_file(f"dist/{name}")
if dist.is_dir() and not any(dist.iterdir()):
    dist.rmdir()

mpl_dir = ROOT / ".mplconfig"
if mpl_dir.is_symlink():
    raise SystemExit("refusing symlinked Matplotlib cache directory")
if mpl_dir.is_dir():
    for path in sorted(mpl_dir.iterdir()):
        if not path.is_file() or not re.fullmatch(r"fontlist-v\d+\.json", path.name):
            raise SystemExit(f"unexpected Matplotlib cache entry: {path.name}")
        path.unlink()
    mpl_dir.rmdir()

cache = ROOT / "replication" / "__pycache__"
if cache.is_symlink():
    raise SystemExit("refusing symlinked Python cache directory")
if cache.is_dir():
    pattern = re.compile(r"[A-Za-z0-9_]+\.cpython-\d+(?:\.opt-\d+)?\.pyc")
    for path in sorted(cache.iterdir()):
        if not path.is_file() or not pattern.fullmatch(path.name):
            raise SystemExit(f"unexpected Python cache entry: {path.name}")
        path.unlink()
    cache.rmdir()
