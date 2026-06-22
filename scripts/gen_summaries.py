"""Generate plain-language AI summaries for regulations via the Anthropic Batch API.

Writes a 1-2 sentence summary into each regulation's .md frontmatter as
``summary``, alongside ``summary_hash`` (SHA-1 of the cleaned body it was made
from) and ``summary_generated_at``. The build (scripts/build.py) prefers this
summary on the card and flags it "out of date" when the body hash no longer
matches.

Usage:
    # Summarize every regulation that has no summary yet
    ANTHROPIC_API_KEY=sk-ant-... python scripts/gen_summaries.py

    # Only one region
    python scripts/gen_summaries.py --region AU

    # Re-summarize only regulations whose body changed since the summary
    python scripts/gen_summaries.py --stale-only

    # Re-summarize everything
    python scripts/gen_summaries.py --regen

    # Print prompts without calling the API
    python scripts/gen_summaries.py --dry-run

    # Resume polling an already-submitted batch
    python scripts/gen_summaries.py --poll msgbatch_xxxxxxxxxxxxxxxx
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

# Validate TLS against the OS trust store so corporate TLS-interception proxies
# don't break the API connection. No-op if truststore isn't installed.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

try:
    from scripts._fsutil import list_md_files
except ImportError:
    from _fsutil import list_md_files

try:
    from scripts.build import _body_hash, clean_body
except ImportError:
    from build import _body_hash, clean_body

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 256
BODY_TRUNCATE = 5000
SUMMARY_CAP = 320
POLL_INTERVAL = 30  # seconds between status checks


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def should_process(meta: dict, current_hash: str, regen: bool, stale_only: bool) -> bool:
    """Decide whether a regulation needs (re)summarizing for this run."""
    if regen:
        return True
    has_summary = bool(meta.get("summary"))
    if stale_only:
        return has_summary and str(meta.get("summary_hash") or "") != current_hash
    return not has_summary


def load_regulations(region: str | None, regen: bool, stale_only: bool) -> list[dict]:
    records = []
    for path in list_md_files(REGULATIONS_DIR):
        post = frontmatter.load(path)
        meta = dict(post.metadata)
        if region and meta.get("region") != region:
            continue
        cleaned = clean_body(post.content or "", str(meta.get("source_api") or ""))
        current_hash = _body_hash(cleaned)
        if not should_process(meta, current_hash, regen, stale_only):
            continue
        records.append({
            "id": meta.get("id", path.stem),
            "path": str(path),
            "region": meta.get("region", ""),
            "citation": meta.get("citation", ""),
            "title": meta.get("title", ""),
            "cleaned_body": cleaned,
            "body_hash": current_hash,
        })
    return records


def build_prompt(reg: dict) -> str:
    return f"""\
You are summarizing an automotive regulation for a reference catalog.
Write a 1-2 sentence, plain-language summary of what this regulation covers and
what it requires or mandates.

Rules:
- Summarize ONLY what the provided text states. Do NOT add outside knowledge,
  history, or interpretation. If the text is too sparse to summarize, describe
  only what it plainly establishes.
- Lead with the subject (what is regulated), then what it requires.
- Return the summary sentence(s) ONLY — no preamble, no "This regulation...",
  no markdown, no surrounding quotes.

## Regulation
Title: {reg["title"]}
Citation: {reg["citation"]}
Region: {reg["region"]}

## Text
{reg["cleaned_body"][:BODY_TRUNCATE]}"""


def parse_summary(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:\w+)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip('“"”').strip()
    if len(text) > SUMMARY_CAP:
        cut = text.rfind(" ", 0, SUMMARY_CAP)
        text = text[: cut if cut > 0 else SUMMARY_CAP].rstrip() + "..."
    return text


def write_summary_to_file(path: str, summary: str, body_hash: str) -> None:
    p = Path(path)
    post = frontmatter.load(p)
    post["summary"] = summary
    post["summary_hash"] = body_hash
    post["summary_generated_at"] = _now_iso()
    p.write_text(frontmatter.dumps(post), encoding="utf-8")


def custom_id_for(reg_id: str) -> str:
    """Map a record id to a valid Anthropic Batch API custom_id (^[A-Za-z0-9_-]{1,64}$)."""
    if len(reg_id) <= 64:
        return reg_id
    digest = hashlib.sha1(reg_id.encode("utf-8")).hexdigest()[:12]
    return f"{reg_id[:50]}-{digest}"  # 50 + 1 + 12 = 63 chars


def _require_client():
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def run_batch(regulations: list[dict], dry_run: bool) -> str | None:
    requests = []
    for reg in regulations:
        prompt = build_prompt(reg)
        if dry_run:
            print(f"\n{'='*60}\n[DRY RUN] {reg['citation']} ({reg['id']})")
            print(prompt[:300] + "...")
            continue
        requests.append({
            "custom_id": custom_id_for(reg["id"]),
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": "You summarize regulations from only the text provided. Be precise and grounded.",
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    if dry_run:
        print(f"\n[DRY RUN] Would send {len(regulations)} regulation(s) to Anthropic Batch API.")
        return None

    client = _require_client()
    print(f"Submitting {len(requests)} request(s) to Anthropic Batch API ...")
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")
    return batch.id


def poll_and_import(batch_id: str, regulations: list[dict]) -> None:
    client = _require_client()
    reg_by_cid = {custom_id_for(reg["id"]): reg for reg in regulations}

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
        cid = result.custom_id
        if result.result.type != "succeeded":
            print(f"  SKIP {cid}: result type={result.result.type}")
            skip += 1
            continue
        reg = reg_by_cid.get(cid)
        if not reg:
            print(f"  WARN {cid}: no matching regulation found")
            skip += 1
            continue
        summary = parse_summary(result.result.message.content[0].text)
        if not summary:
            print(f"  SKIP {cid}: empty summary")
            skip += 1
            continue
        try:
            write_summary_to_file(reg["path"], summary, reg["body_hash"])
            ok += 1
        except Exception as exc:
            print(f"  ERROR {cid}: {exc}")
            err += 1

    print(f"\nImport complete: {ok} summarized, {skip} skipped, {err} errors.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI summaries via the Anthropic Batch API.")
    parser.add_argument("--region", help="Summarize only this region (e.g. AU, US).")
    parser.add_argument("--regen", action="store_true", help="Re-summarize all regulations.")
    parser.add_argument("--stale-only", action="store_true", help="Re-summarize only regulations whose body changed.")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling the API.")
    parser.add_argument("--poll", metavar="BATCH_ID", help="Resume polling for an existing batch ID.")
    args = parser.parse_args()

    if args.poll:
        # Rebuild the path/hash lookup across all regulations for import.
        regulations = load_regulations(args.region, regen=True, stale_only=False)
        poll_and_import(args.poll, regulations)
        return 0

    regulations = load_regulations(args.region, args.regen, args.stale_only)
    if not regulations:
        print("Nothing to summarize. Use --regen to redo all, or --stale-only for changed bodies.")
        return 0

    print(f"Found {len(regulations)} regulation(s) to summarize.")
    batch_id = run_batch(regulations, args.dry_run)

    if batch_id and not args.dry_run:
        print(f"\nTo resume later: python scripts/gen_summaries.py --poll {batch_id}")
        print("\nPolling now ...")
        poll_and_import(batch_id, regulations)

    return 0


if __name__ == "__main__":
    sys.exit(main())
