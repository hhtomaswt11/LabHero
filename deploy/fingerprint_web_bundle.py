#!/usr/bin/env python3
"""Fingerprint Pygbag's heavy archive so browsers can cache it safely.

Pygbag 0.9.3 emits a fixed ``src.tar.gz`` name and references that name from
``index.html``.  A long HTTP cache lifetime on that fixed URL would risk
serving an old game after a deployment.  This build-time helper renames the
archive using a content hash and rewrites the generated HTML accordingly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

_HASH_LENGTH = 16
_VERSIONED_ARCHIVE_RE = re.compile(r"src\.[0-9a-f]{16}\.tar\.gz")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_web_bundle(web_dir: Path) -> Path:
    """Rename ``src.tar.gz`` to a content-hashed name and patch index.html.

    Returns the final archive path.  The operation is idempotent for an
    already-fingerprinted build directory, which makes local diagnostics less
    surprising if the helper is run twice.
    """

    web_dir = Path(web_dir)
    index_path = web_dir / "index.html"
    source_archive = web_dir / "src.tar.gz"

    if not index_path.is_file():
        raise FileNotFoundError(f"Pygbag index not found: {index_path}")

    html = index_path.read_text(encoding="utf-8")

    if not source_archive.is_file():
        matches = sorted(set(_VERSIONED_ARCHIVE_RE.findall(html)))
        if len(matches) == 1:
            existing = web_dir / matches[0]
            if existing.is_file():
                return existing
        raise FileNotFoundError(f"Pygbag archive not found: {source_archive}")

    if "src.tar.gz" not in html:
        raise RuntimeError(
            "Pygbag index.html does not reference src.tar.gz; refusing to "
            "rename the archive without a matching HTML reference."
        )

    short_hash = _sha256(source_archive)[:_HASH_LENGTH]
    versioned_name = f"src.{short_hash}.tar.gz"
    versioned_archive = web_dir / versioned_name

    if versioned_archive.exists():
        raise FileExistsError(f"Versioned archive already exists: {versioned_archive}")

    source_archive.rename(versioned_archive)
    patched_html = html.replace("src.tar.gz", versioned_name)
    index_path.write_text(patched_html, encoding="utf-8")

    return versioned_archive


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {Path(argv[0]).name} <pygbag-web-directory>", file=sys.stderr)
        return 2

    final_archive = fingerprint_web_bundle(Path(argv[1]))
    print(f"[LabHero] Fingerprinted browser archive: {final_archive.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
