"""Stage 2a — Export untagged regulations to JSONL batches for classification."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import frontmatter
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"
TAGGING_BATCHES_DIR = ROOT / "tagging_batches"
TAXONOMY_PATH = ROOT / "taxonomy.yaml"
VOCAB_PATH = TAGGING_BATCHES_DIR / "_vocab.md"
CLASSIFIER_PROMPT_PATH = ROOT / "prompts" / "tag_classifier.md"

DEFAULT_BATCH_SIZE = 15
BODY_TRUNCATE = 6000


def load_taxonomy() -> dict:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_regulations(region: str | None, retag: bool) -> list[dict]:
    records = []
    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        post = frontmatter.load(path)
        meta = dict(post.metadata)

        if region and meta.get("region") != region:
            continue

        if not retag and meta.get("tagging_status") != "untagged":
            continue

        body = post.content or ""
        if len(body) > BODY_TRUNCATE:
            body = body[:BODY_TRUNCATE]

        records.append({
            "id": meta.get("id", path.stem),
            "region": meta.get("region", ""),
            "citation": meta.get("citation", ""),
            "title": meta.get("title", ""),
            "body": body,
        })
    return records


def find_next_batch_num(existing: list[Path]) -> int:
    nums = []
    for p in existing:
        try:
            n = int(p.stem.split("_")[1])
            nums.append(n)
        except (IndexError, ValueError):
            pass
    return max(nums, default=0) + 1


def write_batches(records: list[dict], batch_size: int) -> list[Path]:
    TAGGING_BATCHES_DIR.mkdir(exist_ok=True)

    existing = sorted(TAGGING_BATCHES_DIR.glob("batch_*.jsonl"))
    start_num = find_next_batch_num(existing)

    paths: list[Path] = []
    for i in range(0, len(records), batch_size if batch_size > 0 else len(records)):
        chunk = records[i : i + batch_size] if batch_size > 0 else records
        num = start_num + (i // batch_size if batch_size > 0 else 0)
        path = TAGGING_BATCHES_DIR / f"batch_{num:03d}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for record in chunk:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        paths.append(path)
        if batch_size == 0:
            break
    return paths


def write_vocab(taxonomy: dict) -> None:
    TAGGING_BATCHES_DIR.mkdir(exist_ok=True)
    prompt = ""
    if CLASSIFIER_PROMPT_PATH.exists():
        prompt = CLASSIFIER_PROMPT_PATH.read_text(encoding="utf-8")

    lines = [
        "# Tagging Vocabulary and Instructions\n",
        prompt,
        "\n## Current Controlled Vocabulary\n",
        "\n### Commodities\n",
    ]
    for item in taxonomy.get("commodities", []):
        lines.append(f"- {item}")
    lines.append("\n### Systems\n")
    for item in taxonomy.get("systems", []):
        lines.append(f"- {item}")
    lines.append("\n### Vehicle Categories\n")
    for item in taxonomy.get("vehicle_categories", []):
        lines.append(f"- {item}")

    VOCAB_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export untagged records to JSONL batches.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help="Records per batch (0 = single batch).")
    parser.add_argument("--region", help="Export only this region.")
    parser.add_argument("--retag", action="store_true", help="Re-export all (not just untagged).")
    args = parser.parse_args()

    taxonomy = load_taxonomy()
    records = load_regulations(args.region, args.retag)

    if not records:
        print("No untagged records found. Use --retag to re-export all.")
        return 0

    batch_paths = write_batches(records, args.batch_size)
    write_vocab(taxonomy)

    batch_count = len(batch_paths)
    print(
        f"Wrote {batch_count} batch(es) ({len(records)} records) to tagging_batches/. "
        "Next: open Claude Code or Codex and follow tagging_batches/_vocab.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
