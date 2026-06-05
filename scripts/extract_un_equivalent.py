"""Deterministically extract grounded UN R citations from regulation bodies.

For every non-ECE record, scan the body text for explicit UN/ECE regulation
citations and write the canonical UN R numbers to the ``un_equivalent``
frontmatter field. ECE records are skipped (their UN number is their identity,
so a self-reference would be meaningless). No network calls.

Usage:
    python scripts/extract_un_equivalent.py            # all records
    python scripts/extract_un_equivalent.py --dry-run  # report, write nothing
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"

try:
    from scripts.un_refs import ece_id_to_un, scan_grounded_un
except ImportError:
    from un_refs import ece_id_to_un, scan_grounded_un


def extract_for_record(path: Path, dry_run: bool = False) -> bool:
    """Write grounded un_equivalent for one record. Returns True if changed."""
    post = frontmatter.load(path)
    rid = post.get("id", path.stem)
    if ece_id_to_un(rid):           # ECE record — skip self-reference
        return False
    found = scan_grounded_un(post.content or "")
    current = list(post.get("un_equivalent", []) or [])
    if found == current:
        return False
    if not dry_run:
        post["un_equivalent"] = found
        path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract grounded UN equivalents.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    changed = 0
    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        post = frontmatter.load(path)
        rid = post.get("id", path.stem)
        if ece_id_to_un(rid):
            continue
        found = scan_grounded_un(post.content or "")
        current = list(post.get("un_equivalent", []) or [])
        if found == current:
            continue
        changed += 1
        if args.dry_run:
            print(f"  [dry] {path.stem}: {found}")
        else:
            post["un_equivalent"] = found
            path.write_text(frontmatter.dumps(post), encoding="utf-8")
            print(f"  {path.stem}: {found}")
    print(f"\n{changed} record(s) {'would change' if args.dry_run else 'updated'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
