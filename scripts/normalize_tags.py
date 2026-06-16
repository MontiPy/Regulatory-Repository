"""Normalize free-form open_tags into a canonical discovered vocabulary.

Reads every regulation's `open_tags`, sends the unique tags not yet mapped to
one Anthropic Messages call (Claude Sonnet) for canonical grouping, then writes:

  - tag_aliases.yaml            raw tag -> canonical tag (generated, hand-editable)
  - discovered_vocabulary.yaml  sorted unique canonical tags (the expansive list)

Existing tag_aliases.yaml entries (including hand edits) are never overwritten;
only new raw tags are sent to the model. Build does not depend on these files —
search uses the raw tags directly — so normalization can run any time after
tagging.

Usage:
    ANTHROPIC_API_KEY=sk-ant-... python scripts/normalize_tags.py
    python scripts/normalize_tags.py --dry-run   # no API; map each tag to itself
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import frontmatter
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"
ALIASES_PATH = ROOT / "tag_aliases.yaml"
VOCAB_PATH = ROOT / "discovered_vocabulary.yaml"

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 16000


def collect_open_tags(regulations_dir: Path) -> list[str]:
    """Return the sorted unique set of open_tags across all records."""
    unique: set[str] = set()
    for path in sorted(regulations_dir.glob("*.md")):
        post = frontmatter.load(path)
        for tag in post.metadata.get("open_tags", []) or []:
            if isinstance(tag, str) and tag.strip():
                unique.add(tag.strip())
    return sorted(unique)


def load_aliases(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return dict(yaml.safe_load(fh) or {})


def build_grouping_prompt(tags: list[str]) -> str:
    listing = "\n".join(f"- {t}" for t in tags)
    return f"""\
You are normalizing a list of free-form automotive part/commodity tags into a
canonical vocabulary. Group tags that mean the same thing (synonyms, plural and
singular forms, spelling variants, abbreviations) under ONE canonical label.

Choose the clearest, most industry-standard phrasing as the canonical label.
Every input tag must appear exactly once as a key in the output.

Return ONLY a JSON object mapping each input tag to its canonical label:
{{"<input tag>": "<canonical label>", ...}}

Tags to normalize:
{listing}"""


def parse_grouping(text: str, tags: list[str]) -> dict[str, str]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {t: t for t in tags}
    result: dict[str, str] = {}
    for tag in tags:
        canon = data.get(tag) if isinstance(data, dict) else None
        result[tag] = canon.strip() if isinstance(canon, str) and canon.strip() else tag
    return result


def normalize(all_tags: list[str], existing: dict[str, str], grouper) -> dict[str, str]:
    """Merge groupings for new tags into existing aliases; existing keys preserved."""
    new_tags = [t for t in all_tags if t not in existing]
    merged = dict(existing)
    if new_tags:
        groupings = grouper(new_tags)
        for tag in new_tags:
            merged[tag] = groupings.get(tag, tag)
    return merged


def write_aliases(path: Path, aliases: dict[str, str]) -> None:
    ordered = {k: aliases[k] for k in sorted(aliases)}
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(ordered, fh, allow_unicode=True, sort_keys=False)


def write_vocabulary(path: Path, aliases: dict[str, str]) -> None:
    vocab = sorted({v for v in aliases.values()})
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(vocab, fh, allow_unicode=True)


def make_grouper(dry_run: bool):
    if dry_run:
        return lambda tags: {t: t for t in tags}

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

    def grouper(tags: list[str]) -> dict[str, str]:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system="You are a precise vocabulary normalizer. Return only valid JSON.",
            messages=[{"role": "user", "content": build_grouping_prompt(tags)}],
        )
        return parse_grouping(message.content[0].text, tags)

    return grouper


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize open_tags into a canonical vocabulary.")
    parser.add_argument("--dry-run", action="store_true", help="Skip the API; map each tag to itself.")
    args = parser.parse_args()

    all_tags = collect_open_tags(REGULATIONS_DIR)
    if not all_tags:
        print("No open_tags found. Run scripts/auto_tag.py first.")
        return 0
    existing = load_aliases(ALIASES_PATH)
    new_count = len([t for t in all_tags if t not in existing])
    print(f"{len(all_tags)} unique open_tags ({new_count} new, {len(existing)} already mapped).")

    grouper = make_grouper(args.dry_run)
    aliases = normalize(all_tags, existing, grouper)

    write_aliases(ALIASES_PATH, aliases)
    write_vocabulary(VOCAB_PATH, aliases)
    canonical_count = len({v for v in aliases.values()})
    print(
        f"Wrote {ALIASES_PATH.name} ({len(aliases)} tags) and "
        f"{VOCAB_PATH.name} ({canonical_count} canonical labels)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
