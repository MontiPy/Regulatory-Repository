# Open-Tag Enrichment Layer — Design

**Date:** 2026-06-16
**Status:** Approved (pending spec review)

## Problem

The repository already classifies regulations via an LLM (Stage 2), but it is
deliberately locked to the controlled vocabulary in `taxonomy.yaml`: the model
may only select values that appear verbatim in the taxonomy, and `parse_tags()`
discards anything outside it. There is no way for an engineer to search by
richer, more specific industry terminology (e.g. "master cylinder", "ISOFIX
anchorage", "TPMS sensor") unless that exact phrase happens to appear in the
regulation body.

Additionally, the existing controlled tags on ~697 of 728 records were produced
by the **legacy manual batch workflow** (`tag_export.py` → hand-classified JSONL
→ `tag_import.py`), not by the Batch API. The user wants a genuine API retag of
the whole corpus.

## Goal

Add an **open (free-form) tagging layer** alongside the controlled facets,
without disturbing the controlled-vocabulary faceted search:

1. The LLM emits free-form, industry-standard commodity / part-type tags per
   record (not limited to the taxonomy).
2. **Raw** open tags are folded into the search corpus to improve recall.
3. A separate normalization pass clusters the emitted tags into a canonical,
   more expansive vocabulary — a standalone deliverable and the seed for a
   future facet/review pass.

This is **search-only enrichment** (no new facets, no reader UI changes) for
this iteration.

## Key design decisions

### Raw tags feed search; the canonical list is a separate deliverable

Search is a recall-maximizing consumer. Normalization *collapses* surface forms
("ISOFIX anchor point" → "ISOFIX anchorage"), which is the opposite of what
search wants. Therefore:

- **Raw** open tags go into `search-text.json` (every surface form searchable).
- **Normalization** produces `discovered_vocabulary.yaml` as a standalone
  artifact — the "more expansive list" — and does **not** feed search.

Build has **no dependency** on the normalization output, so search works even if
normalization has never run.

### Expectation: bounded search win

The full regulation body (up to 20,000 chars) is already in the search index.
Open tags therefore only add search value for terms the body does **not**
literally contain — industry jargon, abstractions, synonyms. A real but bounded
benefit. This is also the second reason raw (not canonical) tags feed search:
the synonyms that add value are exactly what canonicalization would discard.

### One combined Batch API pass (not a separate emission script)

Because the user wants every record's controlled tags **redone via the API
anyway** (the originals were manual), there is no reason to pay for two
per-record passes. `auto_tag.py` is extended so a single Batch API call per
record returns both the controlled tags (validated against the taxonomy) and the
open tags (unfiltered). The "controlled path stays pristine" guarantee is upheld
by the parse/validation logic, not by a separate API call.

### Model: Claude Sonnet 4.6

`claude-haiku-4-5-20251001` → `claude-sonnet-4-6`. The open-tag layer is a
world-knowledge + judgment task where Sonnet is materially better, and Sonnet is
more likely to match/beat the hand-reviewed manual tags being overwritten. At
728 records the whole-corpus retag costs ≈ $4.90 via Batch API vs ≈ $1.60 for
Haiku — a ~$3 difference, so cost is not a deciding factor at this scale.

### Field name: dedicated `open_tags`

A dedicated, self-documenting frontmatter field rather than reusing the
vestigial generic `tags` field (populated on 0 records but already wired into
search on both `build.py` and `app.js`). Clarity over zero-plumbing.

## Architecture

```
auto_tag.py --retag (extended)        normalize_tags.py            build.py
Batch API, per record (Sonnet):  →    1 Sonnet call over unique →  folds RAW open_tags
  • controlled tags (validated)        new raw open_tags →          into search-text.json
  • open_tags (unfiltered, ≤12)        discovered_vocabulary.yaml   (no dependency on
→ written to frontmatter               + tag_aliases.yaml            normalization output)
```

## Components

### 1. `scripts/auto_tag.py` (extended)

- `MODEL`: `claude-haiku-4-5-20251001` → `claude-sonnet-4-6`.
- `MAX_TOKENS`: 512 → 1024 (room for the additional array).
- `build_prompt()`: add an open-tags section after the controlled facets,
  instructing the model to also return `open_tags` — free-form, industry-standard
  commodity / part-type identifiers it judges relevant, **not** limited to the
  controlled lists, using recognized terminology, **at most 12**.
- `parse_tags()`:
  - Controlled facets (`commodities`, `systems`, `vehicle_categories`) still
    filtered against `taxonomy.yaml` — unchanged.
  - `open_tags` passed through **unfiltered**, but defensively normalized:
    strings only, trimmed, deduped case-insensitively, empties dropped, **capped
    at 12**.
- `write_tags_to_file()`: also write the `open_tags` field.
- Run path: `python scripts/auto_tag.py --retag` retags all 728 records in
  place (the `--retag` flag and batch flow already exist; only the prompt/parse/
  write and model constant change).

### 2. `scripts/normalize_tags.py` (new)

- Load every record's `open_tags`; collect the unique set.
- Load existing `tag_aliases.yaml` if present; **skip** any raw tag already keyed
  (preserves prior runs and manual edits — never re-decided).
- Send only the *new* unique raw tags to **one** Sonnet call (single message via
  the Messages API, not the Batch API) requesting canonical groupings
  (`raw → canonical`).
- Extend `tag_aliases.yaml` with the new mappings (generated, hand-editable;
  existing entries never overwritten).
- Write `discovered_vocabulary.yaml`: the sorted, unique set of canonical tags —
  the deliverable "expansive list".
- Volume: 728 × ≤12 = ≤~8,700 raw tags, far fewer unique; fits one Sonnet
  request comfortably. Chunk only if the corpus grows by orders of magnitude.
- Requires `ANTHROPIC_API_KEY`; fails clearly if unset (mirrors `auto_tag.py`).

### 3. `scripts/build.py` (extended)

- Register `open_tags` in `OPTIONAL_KEYS` and `LIST_FIELDS`. **No**
  `TAXONOMY_FIELDS` entry (free-form — no taxonomy validation).
- `build_record()`: add `"open_tags": as_list(metadata.get("open_tags"),
  "open_tags", [])`.
- `search_text_for()`: add `" ".join(record.get("open_tags", []))` to the parts
  list (raw tags into the search corpus).
- `discovered_vocabulary.yaml` is a repo artifact only — not shipped to `dist/`
  (nothing consumes it yet; shipping is deferred to the future facet pass).

### 4. `assets/app.js`

- Add `(r.open_tags || []).join(" ")` to the client-side search-text assembly
  (mirrors the existing `r.tags` line), so the browser MiniSearch corpus
  includes open tags too.

### 5. New files

- `tag_aliases.yaml` — `raw → canonical` map (generated by `normalize_tags.py`,
  hand-editable).
- `discovered_vocabulary.yaml` — sorted unique canonical vocabulary (deliverable).

## Data flow

1. `auto_tag.py --retag` → each record's frontmatter gains `open_tags: [...]`
   (raw) and refreshed controlled tags; `tagging_status: llm-tagged`.
2. `normalize_tags.py` → reads all `open_tags`, writes/extends
   `tag_aliases.yaml` and `discovered_vocabulary.yaml`.
3. `build.py` → folds raw `open_tags` into `search-text.json`; reader searches
   them via MiniSearch.

## Error handling

- Missing `ANTHROPIC_API_KEY`: both scripts exit with a clear error (existing
  pattern in `auto_tag.py`).
- Malformed model output: `parse_tags()` already returns empty arrays on JSON
  decode failure; `open_tags` defaults to `[]`.
- Tag-count bloat: capped at 12 per record in `parse_tags()`.
- Normalization not run yet: build uses raw tags directly — search still works.
- `tag_aliases.yaml` hand edits: never overwritten; only new keys appended.

## Testing

- `parse_tags`: `open_tags` passthrough is unfiltered, deduped, capped at 12,
  non-strings dropped; controlled facets still filtered against taxonomy
  (regression).
- `normalize_tags`: merge/grouping logic with a **mocked** LLM response (no live
  API); "skip already-keyed raw tags" behavior; `discovered_vocabulary.yaml`
  contains the sorted canonical set.
- `build`: `search_text_for()` includes `open_tags`; frontmatter carrying
  `open_tags` does not raise an "unknown frontmatter keys" error; existing
  controlled-tag and build tests still pass.

## Out of scope (deferred)

- Promoting discovered tags into reader **facets** (future "mode A/C" pass).
- Shipping `discovered_vocabulary.yaml` into the `dist/` bundle.
- Embedding-based clustering for normalization (LLM grouping is sufficient at
  this scale).
- Human review queue for promoting open tags into `taxonomy.yaml`.
