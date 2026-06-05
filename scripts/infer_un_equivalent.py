"""Infer cross-market UN equivalents with the Anthropic Batch API (Haiku).

For each non-ECE record, ask which UN R number(s) it is the cross-market
equivalent of, constrained to the UN regulations present in the corpus.
Results are written to the SEPARATE ``un_equivalent_ai`` frontmatter field
(never commingled with grounded ``un_equivalent``) and surfaced in the reader
as "AI-suggested — verify against source".

Usage (mirrors auto_tag.py):
    python scripts/infer_un_equivalent.py
    python scripts/infer_un_equivalent.py --dry-run
    python scripts/infer_un_equivalent.py --poll msgbatch_xxx
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"

try:
    from scripts.un_refs import ece_id_to_un, normalize_un
    from scripts.auto_tag import custom_id_for
except ImportError:
    from un_refs import ece_id_to_un, normalize_un
    from auto_tag import custom_id_for

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 256
BODY_TRUNCATE = 4000
POLL_INTERVAL = 30
MAX_AI = 2


def build_valid_targets() -> dict[str, str]:
    """Canonical UN R number -> ECE record title, for every ECE record."""
    targets: dict[str, str] = {}
    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        un = ece_id_to_un(path.stem)
        if un:
            post = frontmatter.load(path)
            targets[un] = str(post.get("title", path.stem))
    return targets


def load_candidates() -> list[dict]:
    """Non-ECE records to check for an AI equivalent."""
    out = []
    for path in sorted(REGULATIONS_DIR.glob("*.md")):
        if ece_id_to_un(path.stem):
            continue
        post = frontmatter.load(path)
        body = (post.content or "")[:BODY_TRUNCATE]
        out.append({
            "id": post.get("id", path.stem),
            "path": str(path),
            "region": post.get("region", ""),
            "citation": post.get("citation", ""),
            "title": post.get("title", ""),
            "body": body,
            "grounded": list(post.get("un_equivalent", []) or []),
        })
    return out


def build_prompt(reg: dict, valid_targets: dict[str, str]) -> str:
    catalog = "\n".join(f"  - {un}: {title}" for un, title in sorted(valid_targets.items()))
    return f"""\
You map an automotive regulation to its cross-market UN (ECE) equivalent.
Return ONLY a JSON object - no prose, no markdown fences.

## Regulation
Title: {reg["title"]}
Citation: {reg["citation"]}
Region: {reg["region"]}

## Content (truncated)
{reg["body"]}

## Task
From the catalog below, pick the UN regulation(s) this regulation is the
cross-market equivalent of (covers the same subject / test). MOST regulations
have NO UN equivalent - returning an empty list is expected and correct. Do not
guess. Return at most {MAX_AI} of the strongest matches, only if confident.

## Valid UN regulations (choose ONLY from these exact strings)
{catalog}

## Required output (JSON only)
{{"un_equivalent_ai": ["UN R##", ...]}}"""


def parse_ai_equiv(text: str, valid_targets: dict[str, str], grounded: list[str]) -> list[str]:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    raw = data.get("un_equivalent_ai", [])
    if not isinstance(raw, list):
        return []
    grounded_canon = {normalize_un(g) for g in grounded}
    out: list[str] = []
    for value in raw:
        canon = normalize_un(value) if isinstance(value, str) else None
        if canon and canon in valid_targets and canon not in grounded_canon and canon not in out:
            out.append(canon)
        if len(out) >= MAX_AI:
            break
    return out


def write_ai_to_file(path: str, values: list[str]) -> None:
    p = Path(path)
    post = frontmatter.load(p)
    if values:
        post["un_equivalent_ai"] = values
    elif "un_equivalent_ai" in post:
        del post["un_equivalent_ai"]
    p.write_text(frontmatter.dumps(post), encoding="utf-8")


def run_batch(candidates: list[dict], valid_targets: dict[str, str], dry_run: bool) -> str | None:
    if dry_run:
        print(f"\n[DRY RUN] {len(candidates)} non-ECE candidate(s) would be sent to Anthropic Batch API.")
        for reg in candidates[:2]:
            prompt = build_prompt(reg, valid_targets)
            print(f"\n{'='*60}\n[DRY RUN] {reg['citation']} ({reg['id']})")
            print(prompt[:300] + "...")
        return None

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
    for reg in candidates:
        prompt = build_prompt(reg, valid_targets)
        requests.append({
            "custom_id": custom_id_for(reg["id"]),
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": "You map automotive regulations to UN/ECE equivalents. Return only valid JSON.",
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    client = anthropic.Anthropic(api_key=api_key)
    print(f"Submitting {len(requests)} request(s) to Anthropic Batch API ...")
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")
    return batch.id


def poll_and_import(batch_id: str, candidates: list[dict], valid_targets: dict[str, str]) -> None:
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
    cand_by_cid = {custom_id_for(c["id"]): c for c in candidates}

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
    with_suggestion = empty = 0
    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type != "succeeded":
            print(f"  SKIP {cid}: result type={result.result.type}")
            skip += 1
            continue
        cand = cand_by_cid.get(cid)
        if not cand:
            print(f"  WARN {cid}: no matching candidate found")
            skip += 1
            continue
        text = result.result.message.content[0].text
        values = parse_ai_equiv(text, valid_targets, cand["grounded"])
        try:
            write_ai_to_file(cand["path"], values)
            ok += 1
            if values:
                with_suggestion += 1
            else:
                empty += 1
        except Exception as exc:
            print(f"  ERROR {cid}: {exc}")
            err += 1

    print(f"\nImport complete: {ok} written ({with_suggestion} with AI suggestion, {empty} empty), {skip} skipped, {err} errors.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Infer UN equivalents using the Anthropic Batch API.")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling the API.")
    parser.add_argument("--poll", metavar="BATCH_ID", help="Resume polling for an existing batch ID.")
    args = parser.parse_args()

    valid_targets = build_valid_targets()
    candidates = load_candidates()

    if args.dry_run:
        run_batch(candidates, valid_targets, dry_run=True)
        return 0

    if args.poll:
        poll_and_import(args.poll, candidates, valid_targets)
        return 0

    if not candidates:
        print("No non-ECE candidates found.")
        return 0

    print(f"Found {len(candidates)} non-ECE candidate(s) to infer UN equivalents for.")
    batch_id = run_batch(candidates, valid_targets, dry_run=False)

    if batch_id:
        print(f"\nBatch ID saved. To poll for results later, run:")
        print(f"  python scripts/infer_un_equivalent.py --poll {batch_id}")
        print("\nPolling now ...")
        poll_and_import(batch_id, candidates, valid_targets)

    return 0


if __name__ == "__main__":
    sys.exit(main())
