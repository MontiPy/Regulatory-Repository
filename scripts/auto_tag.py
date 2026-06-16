"""Automated LLM tagging using the Anthropic Messages Batch API.

Classifies all untagged regulations against the taxonomy (commodities, systems,
vehicle_categories) and writes results back into the .md frontmatter.

Usage:
    # Tag all untagged regulations
    ANTHROPIC_API_KEY=sk-ant-... python scripts/auto_tag.py

    # Tag only one region
    python scripts/auto_tag.py --region US

    # Dry-run: print prompts without sending
    python scripts/auto_tag.py --dry-run

    # Resume polling for an already-submitted batch
    python scripts/auto_tag.py --poll msgbatch_xxxxxxxxxxxxxxxx

    # Re-tag records that are already tagged
    python scripts/auto_tag.py --retag
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"
TAXONOMY_PATH = ROOT / "taxonomy.yaml"

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 512
BODY_TRUNCATE = 5000
POLL_INTERVAL = 30  # seconds between status checks
OPEN_TAGS_CAP = 12


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_taxonomy() -> dict[str, list[str]]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return {
        "commodities": list(raw.get("commodities", [])),
        "systems": list(raw.get("systems", [])),
        "vehicle_categories": list(raw.get("vehicle_categories", [])),
    }


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
            "path": str(path),
            "region": meta.get("region", ""),
            "citation": meta.get("citation", ""),
            "title": meta.get("title", ""),
            "body": body,
        })
    return records


def build_prompt(reg: dict, taxonomy: dict[str, list[str]]) -> str:
    commodities = "\n".join(f"  - {v}" for v in taxonomy["commodities"])
    systems = "\n".join(f"  - {v}" for v in taxonomy["systems"])
    vehicle_categories = "\n".join(f"  - {v}" for v in taxonomy["vehicle_categories"])
    return f"""\
You are classifying an automotive regulation against a controlled taxonomy.
Return ONLY a JSON object — no prose, no markdown fences.

## Regulation
Title: {reg["title"]}
Citation: {reg["citation"]}
Region: {reg["region"]}

## Content
{reg["body"][:BODY_TRUNCATE]}

## Task
Select ONLY values that appear verbatim in the lists below.
If a facet does not clearly apply, return an empty array — do not guess.

## Valid commodities
{commodities}

## Valid systems
{systems}

## Valid vehicle_categories
{vehicle_categories}

## Required output format (JSON only)
{{"commodities": [...], "systems": [...], "vehicle_categories": [...]}}"""


def write_tags_to_file(path: str, tags: dict) -> None:
    p = Path(path)
    post = frontmatter.load(p)
    for field in ("commodities", "systems", "vehicle_categories"):
        post[field] = tags.get(field, [])
    post["tagging_status"] = "llm-tagged"
    post["tagged_at"] = _now_iso()
    p.write_text(frontmatter.dumps(post), encoding="utf-8")


def _clean_open_tags(raw: object) -> list[str]:
    """Free-form tags: strings only, trimmed, deduped case-insensitively, capped."""
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        tag = item.strip()
        if not tag:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(tag)
        if len(cleaned) >= OPEN_TAGS_CAP:
            break
    return cleaned


def parse_tags(text: str, taxonomy: dict[str, list[str]]) -> dict:
    text = text.strip()
    # Strip markdown fences if the model included them
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    empty = {"commodities": [], "systems": [], "vehicle_categories": [], "open_tags": []}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return empty

    result = {}
    for field, valid_values in taxonomy.items():
        valid_set = set(valid_values)
        raw = data.get(field, [])
        if not isinstance(raw, list):
            raw = []
        result[field] = [v for v in raw if v in valid_set]
    result["open_tags"] = _clean_open_tags(data.get("open_tags", []))
    return result


def custom_id_for(reg_id: str) -> str:
    """Map a record id to a valid Anthropic Batch API custom_id.

    The Batch API requires custom_id to match ^[a-zA-Z0-9_-]{1,64}$. Record ids are
    kebab-case slugs but some exceed 64 chars, so long ids are deterministically
    shortened to a readable prefix plus a hash suffix (unique, reproducible across
    runs so --poll can rebuild the same mapping).
    """
    if len(reg_id) <= 64:
        return reg_id
    digest = hashlib.sha1(reg_id.encode("utf-8")).hexdigest()[:12]
    return f"{reg_id[:50]}-{digest}"  # 50 + 1 + 12 = 63 chars


def run_batch(regulations: list[dict], taxonomy: dict[str, list[str]], dry_run: bool) -> str | None:
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    requests = []
    for reg in regulations:
        prompt = build_prompt(reg, taxonomy)
        if dry_run:
            print(f"\n{'='*60}\n[DRY RUN] {reg['citation']} ({reg['id']})")
            print(prompt[:300] + "...")
            continue
        requests.append({
            "custom_id": custom_id_for(reg["id"]),
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": "You are a precise automotive regulation classifier. Return only valid JSON.",
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    if dry_run:
        print(f"\n[DRY RUN] Would send {len(regulations)} regulation(s) to Anthropic Batch API.")
        return None

    client = anthropic.Anthropic(api_key=api_key)
    print(f"Submitting {len(requests)} request(s) to Anthropic Batch API ...")
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")
    return batch.id


def poll_and_import(batch_id: str, regulations: list[dict], taxonomy: dict[str, list[str]]) -> None:
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    path_by_cid = {custom_id_for(reg["id"]): reg["path"] for reg in regulations}

    print(f"Polling batch {batch_id} ...")
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(
            f"  Status: {batch.processing_status} | "
            f"succeeded={counts.succeeded} processing={counts.processing} "
            f"errored={counts.errored} canceled={counts.canceled}"
        )
        if batch.processing_status == "ended":
            break
        time.sleep(POLL_INTERVAL)

    print("Batch complete. Importing results ...")
    ok = err = skip = 0
    for result in client.messages.batches.results(batch_id):
        reg_id = result.custom_id
        if result.result.type != "succeeded":
            print(f"  SKIP {reg_id}: result type={result.result.type}")
            skip += 1
            continue
        text = result.result.message.content[0].text
        tags = parse_tags(text, taxonomy)
        file_path = path_by_cid.get(reg_id)
        if not file_path:
            print(f"  WARN {reg_id}: no matching file found")
            skip += 1
            continue
        try:
            write_tags_to_file(file_path, tags)
            ok += 1
        except Exception as exc:
            print(f"  ERROR {reg_id}: {exc}")
            err += 1

    print(f"\nImport complete: {ok} tagged, {skip} skipped, {err} errors.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-tag regulations using the Anthropic Batch API.")
    parser.add_argument("--region", help="Tag only this region (e.g. US, EU).")
    parser.add_argument("--retag", action="store_true", help="Re-tag already-tagged records.")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling the API.")
    parser.add_argument("--poll", metavar="BATCH_ID", help="Resume polling for an existing batch ID.")
    args = parser.parse_args()

    taxonomy = load_taxonomy()
    regulations = load_regulations(args.region, args.retag)

    if not regulations and not args.poll:
        print("No untagged regulations found. Use --retag to re-tag all.")
        return 0

    if args.poll:
        if not regulations:
            # Load all regulations for the path lookup when polling without retag context
            regulations = load_regulations(args.region, retag=True)
        poll_and_import(args.poll, regulations, taxonomy)
        return 0

    print(f"Found {len(regulations)} regulation(s) to tag.")
    batch_id = run_batch(regulations, taxonomy, args.dry_run)

    if batch_id and not args.dry_run:
        print(f"\nBatch ID saved. To poll for results later, run:")
        print(f"  python scripts/auto_tag.py --poll {batch_id}")
        print("\nPolling now ...")
        poll_and_import(batch_id, regulations, taxonomy)

    return 0


if __name__ == "__main__":
    sys.exit(main())
