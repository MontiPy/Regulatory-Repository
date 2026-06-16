# Open-Tag Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a free-form "open tag" layer (industry-standard commodity/part-type labels) emitted by the LLM alongside the controlled facets, folded raw into the search corpus, plus a normalization pass that distills the emitted tags into a canonical discovered vocabulary.

**Architecture:** `auto_tag.py` is extended so one Claude Sonnet Batch API call per record returns both the controlled tags (still validated against `taxonomy.yaml`) and unfiltered `open_tags`. `build.py` folds the **raw** open tags into `search-text.json`. A new `normalize_tags.py` makes one Sonnet call to cluster the unique emitted tags into `tag_aliases.yaml` (raw→canonical) and `discovered_vocabulary.yaml` (the canonical list). Build has no dependency on normalization output.

**Tech Stack:** Python 3.11, `anthropic` SDK (`tag` optional extra), `python-frontmatter`, `PyYAML`, pytest. Reader is vanilla JS (`assets/app.js`) with MiniSearch.

**Reference spec:** `docs/superpowers/specs/2026-06-16-open-tag-enrichment-design.md`

---

## File Structure

- `scripts/auto_tag.py` (modify) — combined controlled + open-tag prompt/parse/write; model → Sonnet.
- `scripts/build.py` (modify) — register `open_tags`, build into record, fold raw into search.
- `scripts/normalize_tags.py` (create) — distill unique open_tags into canonical vocabulary.
- `assets/app.js` (modify) — include `open_tags` in client search corpus.
- `tag_aliases.yaml` (generated) — raw→canonical map, hand-editable.
- `discovered_vocabulary.yaml` (generated) — sorted canonical vocabulary.
- `tests/test_auto_tag.py` (create) — parse/prompt/write tests.
- `tests/test_normalize_tags.py` (create) — collect/normalize/write tests (mocked LLM).
- `tests/test_build.py` (modify) — open_tags in search + accepted frontmatter key.
- `README.md` (modify) — document the open layer and normalize step.

---

### Task 1: `open_tags` passthrough in `auto_tag.parse_tags`

**Files:**
- Modify: `scripts/auto_tag.py`
- Test: `tests/test_auto_tag.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_auto_tag.py`:

```python
"""Tests for scripts/auto_tag.py — open-tag parsing, prompt, and frontmatter write."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.auto_tag import OPEN_TAGS_CAP, parse_tags

TAXONOMY = {
    "commodities": ["Brakes", "Seats"],
    "systems": ["Braking"],
    "vehicle_categories": ["Passenger car"],
}


class TestParseOpenTags:
    def test_controlled_fields_still_filtered_to_taxonomy(self):
        text = '{"commodities": ["Brakes", "Nonsense"], "systems": [], "vehicle_categories": [], "open_tags": []}'
        result = parse_tags(text, TAXONOMY)
        assert result["commodities"] == ["Brakes"]

    def test_open_tags_passed_through_unfiltered(self):
        text = '{"commodities": [], "systems": [], "vehicle_categories": [], "open_tags": ["master cylinder", "brake booster"]}'
        result = parse_tags(text, TAXONOMY)
        assert result["open_tags"] == ["master cylinder", "brake booster"]

    def test_open_tags_deduped_case_insensitively(self):
        text = '{"open_tags": ["ISOFIX anchorage", "isofix anchorage", "ISOFIX Anchorage"]}'
        result = parse_tags(text, TAXONOMY)
        assert result["open_tags"] == ["ISOFIX anchorage"]

    def test_open_tags_capped(self):
        tags = [f"tag {i}" for i in range(OPEN_TAGS_CAP + 5)]
        import json
        text = json.dumps({"open_tags": tags})
        result = parse_tags(text, TAXONOMY)
        assert len(result["open_tags"]) == OPEN_TAGS_CAP

    def test_non_strings_and_blanks_dropped(self):
        text = '{"open_tags": ["valid", "", "   ", 5, null]}'
        result = parse_tags(text, TAXONOMY)
        assert result["open_tags"] == ["valid"]

    def test_invalid_json_returns_empty_open_tags(self):
        result = parse_tags("not json", TAXONOMY)
        assert result["open_tags"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_auto_tag.py -v`
Expected: FAIL — `ImportError: cannot import name 'OPEN_TAGS_CAP'`.

- [ ] **Step 3: Implement the minimal code**

In `scripts/auto_tag.py`, add the constant near the other module constants (after `POLL_INTERVAL = 30`):

```python
OPEN_TAGS_CAP = 12
```

Add this helper above `parse_tags`:

```python
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
```

Replace the body of `parse_tags` so both the error path and the success path include `open_tags`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_auto_tag.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/auto_tag.py tests/test_auto_tag.py
git commit -m "feat: parse unfiltered open_tags in auto_tag (deduped, capped at 12)"
```

---

### Task 2: Prompt, model, and frontmatter write for open tags

**Files:**
- Modify: `scripts/auto_tag.py`
- Test: `tests/test_auto_tag.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auto_tag.py`:

```python
from scripts.auto_tag import MODEL, build_prompt, write_tags_to_file


class TestBuildPrompt:
    def test_prompt_requests_open_tags(self):
        reg = {"title": "T", "citation": "C", "region": "US", "body": "body"}
        prompt = build_prompt(reg, TAXONOMY)
        assert "open_tags" in prompt
        assert "at most 12" in prompt.lower()

    def test_model_is_sonnet(self):
        assert MODEL == "claude-sonnet-4-6"


class TestWriteTags:
    def test_open_tags_written_to_frontmatter(self, tmp_path):
        md = tmp_path / "rec.md"
        md.write_text("---\nid: rec\ntitle: T\n---\nbody\n", encoding="utf-8")
        write_tags_to_file(
            str(md),
            {"commodities": ["Brakes"], "systems": [], "vehicle_categories": [], "open_tags": ["master cylinder"]},
        )
        import frontmatter
        post = frontmatter.load(md)
        assert post["open_tags"] == ["master cylinder"]
        assert post["tagging_status"] == "llm-tagged"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_auto_tag.py::TestBuildPrompt tests/test_auto_tag.py::TestWriteTags -v`
Expected: FAIL — `test_model_is_sonnet` fails (model is Haiku) and `test_prompt_requests_open_tags` fails (no open_tags in prompt).

- [ ] **Step 3: Implement the changes**

In `scripts/auto_tag.py`, change the model and token constants:

```python
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
```

In `build_prompt`, replace the return string with one that adds the open-tags section and updates the output format line:

```python
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

## Open tags (NOT restricted to the lists above)
Also return "open_tags": free-form, industry-standard commodity and part-type
identifiers you judge relevant to this regulation, using recognized industry
terminology (e.g. "master cylinder", "ISOFIX anchorage", "tire pressure
monitoring sensor"). These are NOT limited to the controlled lists above.
Return at most 12. If none clearly apply, return an empty array.

## Required output format (JSON only)
{{"commodities": [...], "systems": [...], "vehicle_categories": [...], "open_tags": [...]}}"""
```

In `write_tags_to_file`, add `"open_tags"` to the field loop:

```python
    for field in ("commodities", "systems", "vehicle_categories", "open_tags"):
        post[field] = tags.get(field, [])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_auto_tag.py -v`
Expected: PASS (all tests, including Task 1's).

- [ ] **Step 5: Commit**

```bash
git add scripts/auto_tag.py tests/test_auto_tag.py
git commit -m "feat: emit open_tags via Sonnet and write them to frontmatter"
```

---

### Task 3: Register and search `open_tags` in `build.py`

**Files:**
- Modify: `scripts/build.py`
- Test: `tests/test_build.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_build.py`:

```python
class TestOpenTagsInBuild:
    def test_search_text_includes_open_tags(self):
        record = {
            "id": "r1",
            "title": "T",
            "open_tags": ["master cylinder", "brake booster"],
        }
        blob = search_text_for(record)
        assert "master cylinder" in blob["text"]
        assert "brake booster" in blob["text"]

    def test_open_tags_is_an_accepted_frontmatter_key(self):
        from scripts.build import ALLOWED_KEYS, LIST_FIELDS
        assert "open_tags" in ALLOWED_KEYS
        assert "open_tags" in LIST_FIELDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_build.py::TestOpenTagsInBuild -v`
Expected: FAIL — `open_tags` not in `ALLOWED_KEYS` and not in search text.

- [ ] **Step 3: Implement the changes**

In `scripts/build.py`, add `"open_tags"` to `OPTIONAL_KEYS` (so it joins `ALLOWED_KEYS`):

```python
OPTIONAL_KEYS = {
    "aliases",
    "commodities",
    "systems",
    "vehicle_categories",
    "un_equivalent",
    "un_equivalent_ai",
    "related",
    "tags",
    "open_tags",
    "tagged_at",
    "effective_date",
    "last_amended",
    "paywall",
    "translation_status",
}
```

Add `"open_tags"` to `LIST_FIELDS`:

```python
LIST_FIELDS = {
    "aliases",
    "commodities",
    "systems",
    "vehicle_categories",
    "un_equivalent",
    "un_equivalent_ai",
    "related",
    "tags",
    "open_tags",
}
```

In `search_text_for`, add the open_tags join (after the `tags` line):

```python
        " ".join(record.get("tags", [])),
        " ".join(record.get("open_tags", [])),
```

In `build_record`, add the field to the record dict (after the `"tags"` line):

```python
        "tags": as_list(metadata.get("tags"), "tags", []),
        "open_tags": as_list(metadata.get("open_tags"), "open_tags", []),
```

Note: do **not** add `open_tags` to `TAXONOMY_FIELDS` — it is free-form and must not be validated against the taxonomy.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_build.py -v`
Expected: PASS (new tests plus all existing build tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/build.py tests/test_build.py
git commit -m "feat: fold raw open_tags into the build search corpus"
```

---

### Task 4: Include `open_tags` in the client-side search corpus

**Files:**
- Modify: `assets/app.js`

- [ ] **Step 1: Locate the search-text assembly**

Run: `grep -n "r.tags" assets/app.js`
Expected: one line like `(r.tags || []).join(" "),` (around line 129).

- [ ] **Step 2: Add the open_tags line**

Immediately after the `(r.tags || []).join(" "),` line, add:

```javascript
        (r.open_tags || []).join(" "),
```

- [ ] **Step 3: Verify it is present**

Run: `grep -n "open_tags" assets/app.js`
Expected: the new line is shown.

- [ ] **Step 4: Commit**

```bash
git add assets/app.js
git commit -m "feat: index open_tags in the client search corpus"
```

---

### Task 5: `normalize_tags.py` core logic (no API)

**Files:**
- Create: `scripts/normalize_tags.py`
- Test: `tests/test_normalize_tags.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_normalize_tags.py`:

```python
"""Tests for scripts/normalize_tags.py — collection, normalization, and writing."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.normalize_tags import (
    collect_open_tags,
    load_aliases,
    normalize,
    parse_grouping,
    write_aliases,
    write_vocabulary,
)


def _write_md(path: Path, open_tags: list[str]) -> None:
    body = "---\nid: " + path.stem + "\n"
    body += "open_tags:\n" + "".join(f"- {t}\n" for t in open_tags)
    body += "---\ncontent\n"
    path.write_text(body, encoding="utf-8")


class TestCollectOpenTags:
    def test_unique_and_sorted(self, tmp_path):
        _write_md(tmp_path / "a.md", ["Brake hose", "ISOFIX anchorage"])
        _write_md(tmp_path / "b.md", ["ISOFIX anchorage", "Wheel hub"])
        assert collect_open_tags(tmp_path) == ["Brake hose", "ISOFIX anchorage", "Wheel hub"]


class TestNormalize:
    def test_new_tags_grouped_existing_preserved(self):
        existing = {"old tag": "Old Canonical"}
        grouper = lambda tags: {t: "Brakes" for t in tags}  # noqa: E731
        result = normalize(["old tag", "brake", "brakes"], existing, grouper)
        assert result["old tag"] == "Old Canonical"   # untouched
        assert result["brake"] == "Brakes"
        assert result["brakes"] == "Brakes"

    def test_grouper_only_sees_new_tags(self):
        seen = {}
        def grouper(tags):
            seen["tags"] = list(tags)
            return {t: t for t in tags}
        normalize(["a", "b"], {"a": "A"}, grouper)
        assert seen["tags"] == ["b"]


class TestParseGrouping:
    def test_maps_each_tag(self):
        text = '{"brake": "Brakes", "brakes": "Brakes"}'
        assert parse_grouping(text, ["brake", "brakes"]) == {"brake": "Brakes", "brakes": "Brakes"}

    def test_missing_tag_falls_back_to_self(self):
        assert parse_grouping('{"brake": "Brakes"}', ["brake", "seat"])["seat"] == "seat"

    def test_invalid_json_falls_back_to_identity(self):
        assert parse_grouping("garbage", ["a", "b"]) == {"a": "a", "b": "b"}


class TestWrite:
    def test_aliases_round_trip(self, tmp_path):
        path = tmp_path / "tag_aliases.yaml"
        write_aliases(path, {"b": "B", "a": "A"})
        assert load_aliases(path) == {"a": "A", "b": "B"}

    def test_vocabulary_is_sorted_unique_canonicals(self, tmp_path):
        path = tmp_path / "discovered_vocabulary.yaml"
        write_vocabulary(path, {"x": "Brakes", "y": "Brakes", "z": "Seats"})
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == ["Brakes", "Seats"]

    def test_load_aliases_missing_file_is_empty(self, tmp_path):
        assert load_aliases(tmp_path / "nope.yaml") == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_normalize_tags.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.normalize_tags'`.

- [ ] **Step 3: Create the script**

Create `scripts/normalize_tags.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_normalize_tags.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/normalize_tags.py tests/test_normalize_tags.py
git commit -m "feat: add normalize_tags.py to distill open_tags into a canonical vocabulary"
```

---

### Task 6: Verify the full suite and dry-run wiring

**Files:** none (verification only)

- [ ] **Step 1: Run the whole test suite**

Run: `python -m pytest -q`
Expected: all tests pass (new auto_tag, normalize_tags, build additions, plus all pre-existing tests).

- [ ] **Step 2: Dry-run the tagging prompt (no API call)**

Run: `python scripts/auto_tag.py --region US --dry-run`
Expected: prints prompts that include an `## Open tags` section and the JSON format line ending with `"open_tags": [...]`.

- [ ] **Step 3: Dry-run normalization (no API call)**

This maps each existing open_tag to itself and writes both YAML files. Only meaningful after a real tag run, but confirms the script runs end to end:

Run: `python scripts/normalize_tags.py --dry-run`
Expected: either "No open_tags found..." (if not yet tagged) or a summary line plus `tag_aliases.yaml` / `discovered_vocabulary.yaml` written.

- [ ] **Step 4: No commit** (verification task).

---

### Task 7: Document the open layer in the README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the Stage 2 description**

In `README.md`, find the "### Stage 2 — Tag" section. After the paragraph that begins "Classify untagged records...", add:

```markdown
Alongside the controlled facets, the same call also emits **`open_tags`** — free-form,
industry-standard commodity/part-type labels (e.g. "master cylinder", "ISOFIX
anchorage") that are *not* restricted to the taxonomy. These raw tags are folded
into the search corpus to improve recall; they are not facets.
```

Then add a new subsection after the Stage 2 command block:

```markdown
#### Normalizing open tags

After tagging, distill the emitted `open_tags` into a canonical vocabulary:

```
ANTHROPIC_API_KEY=sk-ant-... python scripts/normalize_tags.py
python scripts/normalize_tags.py --dry-run   # no API; map each tag to itself
```

This makes one Claude Sonnet call over the unique new tags and writes
`tag_aliases.yaml` (raw → canonical, hand-editable — existing entries are never
overwritten) and `discovered_vocabulary.yaml` (the canonical list). Search uses
the **raw** tags directly, so normalization is optional and never narrows recall.
```
```

(Note: the model used for tagging is now Claude Sonnet 4.6, not Haiku — update the "Claude Haiku" mention in the Stage 2 paragraph to "Claude Sonnet".)

- [ ] **Step 2: Update the model mention**

In the Stage 2 paragraph, change "(Claude Haiku)" to "(Claude Sonnet 4.6)".

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document open_tags and the normalize_tags step"
```

---

### Task 8: Run the live retag, normalize, and build (operational — requires API key)

**Files:** writes to `regulations/*.md`, `tag_aliases.yaml`, `discovered_vocabulary.yaml`, `dist/`

> This task spends money (~$5 for the full 728-record Sonnet Batch retag). It requires `ANTHROPIC_API_KEY` and `pip install -e ".[tag]"` (or `pip install anthropic`). Run it deliberately, review the git diff before committing the regenerated frontmatter.

- [ ] **Step 1: Spot-check one region first**

Run: `ANTHROPIC_API_KEY=sk-ant-... python scripts/auto_tag.py --region US --retag`
Then review: `git diff --stat regulations/` and open one US file to confirm `open_tags` looks sensible and controlled tags are still valid.

- [ ] **Step 2: Retag the whole corpus in place**

Run: `ANTHROPIC_API_KEY=sk-ant-... python scripts/auto_tag.py --retag`
Expected: a batch is submitted, polled to completion, and frontmatter is updated for all records.

- [ ] **Step 3: Normalize the emitted tags**

Run: `ANTHROPIC_API_KEY=sk-ant-... python scripts/normalize_tags.py`
Expected: `tag_aliases.yaml` and `discovered_vocabulary.yaml` are written. Open `discovered_vocabulary.yaml` and skim the canonical list; hand-edit `tag_aliases.yaml` if any grouping is wrong.

- [ ] **Step 4: Rebuild and verify search**

Run:
```
python scripts/build.py
python -m http.server -d dist 8000
```
Open http://localhost:8000/ and search for an open-tag term that does not appear verbatim in a regulation body (e.g. "master cylinder"); confirm the expected record surfaces.

- [ ] **Step 5: Commit the regenerated data**

```bash
git add regulations/ tag_aliases.yaml discovered_vocabulary.yaml
git commit -m "data: retag corpus via Sonnet with open_tags + canonical vocabulary"
```

---

## Self-Review Notes

- **Spec coverage:** open-tag emission (Tasks 1–2), raw-into-search build wiring (Task 3) + client (Task 4), normalization → `tag_aliases.yaml` + `discovered_vocabulary.yaml` (Task 5), Sonnet model (Task 2), dedicated `open_tags` field (Tasks 1–3), cap-at-12 (Task 1), no taxonomy validation of open_tags (Task 3 note), README (Task 7), operational retag-in-place (Task 8). All spec sections map to a task.
- **No `dist/` shipping of the discovered vocabulary** — matches the spec's "deferred" scope.
- **Type consistency:** `parse_tags`/`write_tags_to_file` return/consume the same dict keys (`commodities`, `systems`, `vehicle_categories`, `open_tags`); `normalize(all_tags, existing, grouper)` and the `grouper(tags) -> dict[str,str]` contract are consistent across the script and tests.
