"""Backfill translation_status: untranslated into existing non-English regulation files.

Targets KR (Korean) and JP (Japanese) files that don't already have translation_status set.
Skips files where translation_status is already present.

Usage:
    python scripts/backfill_translation.py [--dry-run]
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"

NON_ENGLISH_PREFIXES = {"kr", "jp"}


def backfill(dry_run: bool = False) -> int:
    updated = 0
    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        prefix = path.stem.split("-")[0].lower()
        if prefix not in NON_ENGLISH_PREFIXES:
            continue

        post = frontmatter.load(path)
        if post.metadata.get("translation_status"):
            continue  # already set

        if dry_run:
            print(f"[dry-run] would set translation_status=untranslated on {path.name}")
            updated += 1
            continue

        post.metadata["translation_status"] = "untranslated"
        path.write_text(frontmatter.dumps(post), encoding="utf-8")
        print(f"OK {path.name}")
        updated += 1

    print(f"\n{'[dry-run] ' if dry_run else ''}{updated} file(s) updated.")
    return updated


def main() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Backfill translation_status into non-English regulation files.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
