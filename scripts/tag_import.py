"""Stage 2c — Import classifier results JSONL back into .md frontmatter."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"
TAGGING_BATCHES_DIR = ROOT / "tagging_batches"
DONE_DIR = TAGGING_BATCHES_DIR / "_done"
TAXONOMY_PATH = ROOT / "taxonomy.yaml"
TAG_REPORT_PATH = ROOT / ".tag_report.txt"


def load_taxonomy() -> dict[str, set]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return {
        "commodities": set(raw.get("commodities", [])),
        "systems": set(raw.get("systems", [])),
        "vehicle_categories": set(raw.get("vehicle_categories", [])),
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def import_result(result: dict, taxonomy: dict[str, set], dry_run: bool) -> tuple[bool, list[str]]:
    record_id = result.get("id", "").strip()
    if not record_id:
        return False, ["missing id in result"]

    md_path = REGULATIONS_DIR / f"{record_id}.md"
    if not md_path.exists():
        return False, [f"{record_id}: .md file not found"]

    discarded: list[str] = []
    updates: dict[str, list] = {}

    for field in ("commodities", "systems", "vehicle_categories"):
        raw_vals = result.get(field, []) or []
        valid = [v for v in raw_vals if v in taxonomy[field]]
        bad = [v for v in raw_vals if v not in taxonomy[field]]
        updates[field] = valid
        for v in bad:
            discarded.append(f"{record_id}.{field}: '{v}' not in taxonomy")

    if dry_run:
        print(f"  [dry-run] {record_id}: {updates}")
        return True, discarded

    post = frontmatter.load(md_path)
    for field, values in updates.items():
        post[field] = values
    post["tagging_status"] = "llm-tagged"
    post["tagged_at"] = now_iso()
    md_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return True, discarded


def find_result_files(batch: str | None) -> list[Path]:
    if batch:
        p = TAGGING_BATCHES_DIR / f"batch_{batch}_results.jsonl"
        return [p] if p.exists() else []
    return sorted(TAGGING_BATCHES_DIR.glob("batch_*_results.jsonl"))


def move_to_done(result_path: Path) -> None:
    DONE_DIR.mkdir(exist_ok=True)
    stem = result_path.stem.replace("_results", "")
    input_path = TAGGING_BATCHES_DIR / f"{stem}.jsonl"
    shutil.move(result_path, DONE_DIR / result_path.name)
    if input_path.exists():
        shutil.move(input_path, DONE_DIR / input_path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import tagging results into .md frontmatter.")
    parser.add_argument("--batch", help="Import only batch_NNN_results.jsonl (e.g. '001').")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change; write nothing.")
    args = parser.parse_args()

    taxonomy = load_taxonomy()
    result_files = find_result_files(args.batch)

    if not result_files:
        print("No *_results.jsonl files found in tagging_batches/.")
        return 0

    total_records = 0
    total_discarded: list[str] = []

    for rfile in result_files:
        with rfile.open("r", encoding="utf-8") as fh:
            lines = [line.strip() for line in fh if line.strip()]

        for line in lines:
            try:
                result = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  WARN: could not parse line in {rfile.name}: {exc}")
                continue

            ok, discarded = import_result(result, taxonomy, args.dry_run)
            if ok:
                total_records += 1
            total_discarded.extend(discarded)

        if not args.dry_run:
            move_to_done(rfile)

    report_lines = total_discarded or ["No discarded values."]
    TAG_REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        f"Imported {total_records} records across {len(result_files)} batch(es). "
        f"{len(total_discarded)} facet value(s) discarded as out-of-vocab "
        f"(see .tag_report.txt)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
