# AI-generated regulation summaries — design

**Date:** 2026-06-22
**Branch:** feat/ui-ux-improvements
**Status:** Approved, ready for implementation plan

## Problem

Each regulation card shows `summary_text`, which today is a naive truncation of
the first ~250 characters of the rendered body (`summarize()` in `build.py`).
For most regulations this surfaces administrative lead-text rather than a
description of the regulation — e.g. the ADR 1/00 card reads "Vehicle Standard
(Australian Design Rule 1/00 – Reversing Lamps) 2005 In force Administered by
Department of Infrastructure…" instead of saying what the rule requires.

The full text is already reachable via the "Read" reader pane; that part works.
The gap is the card-level summary.

## Goal

Replace the raw lead-text excerpt with a genuine 1–2 sentence, plain-language
summary of what each regulation covers and requires. Summaries are
AI-generated, visibly labeled as such, and stored in each regulation's
frontmatter so they are reviewable in git.

## Decisions (from brainstorming)

- **Source:** AI-generated at build-time-adjacent step (not heuristic, not manual).
- **Storage:** Written into each regulation's `.md` frontmatter (part of source content, git-reviewable).
- **Labeling:** Visibly labeled "AI summary" on the card, consistent with the existing `un_equivalent_ai` "AI-Suggested" precedent. The official source remains authoritative.
- **Style:** 1–2 sentences — what the regulation covers and what it requires/mandates. Scannable on a card.
- **Staleness:** Generate once; manual regeneration only (no auto-refresh in the generator). The **build** detects when a summary's underlying body text has changed since the summary was made and the card flags it as possibly out of date.

## Architecture

Three touch points, mirroring existing conventions.

### 1. Generation script — `scripts/gen_summaries.py`

Mirrors `scripts/auto_tag.py` closely (proven scaffolding):

- Anthropic **Messages Batch API**; `truststore.inject_into_ssl()` for corporate TLS interception; `ANTHROPIC_API_KEY` from env.
- Model: `claude-sonnet-4-6` (same as `auto_tag.py`), `max_tokens` small (~256).
- Loads regulations via `list_md_files(REGULATIONS_DIR)`.
- Prompt input is `clean_body(post.content, source_api)` — the **chrome-stripped**
  cleaned body, reusing `build.py`'s `clean_body`, so summaries never open with
  nav/breadcrumb boilerplate (the current excerpt's failure mode). Truncate to a
  body cap (~5000 chars) as `auto_tag` does.
- Prompt is hard-grounded: summarize **only** what the provided text states; do
  not add outside knowledge; 1–2 sentences; describe what the regulation covers
  and what it requires. A confidently-wrong summary under an AI label is the
  worst failure mode, so the prompt enforces the same discipline as `auto_tag`'s
  "do not guess."
- Writes back to frontmatter via `frontmatter.dumps`:
  - `summary` — the generated text.
  - `summary_hash` — SHA-1 of the exact cleaned body string that was summarized.
  - `summary_generated_at` — UTC ISO timestamp.
- Flags:
  - default: skip any regulation that already has a `summary`.
  - `--region <R>`: limit to one region.
  - `--dry-run`: print prompts without calling the API.
  - `--poll <BATCH_ID>`: resume polling an existing batch.
  - `--regen`: regenerate all (ignore existing `summary`).
  - `--stale-only`: regenerate only regulations whose stored `summary_hash` no
    longer matches the current cleaned-body hash.

### 2. Build — `scripts/build.py`

- Add `summary`, `summary_hash`, `summary_generated_at` to `OPTIONAL_KEYS`.
  **All three** must be registered or `validate_required` (build.py:184) fails
  every one of the 838 files on the unknown-key check.
- In `build_record`, after computing `body_html` and the cleaned body:
  - `summary_text = stringify(metadata.get("summary")) or summarize(body_html)`
    — AI summary when present, today's heuristic excerpt as fallback.
  - `summary_ai = bool(metadata.get("summary"))` — presence of the field is the
    AI signal.
  - `summary_stale = summary_ai and metadata.get("summary_hash") != sha1(cleaned_body)`
    — true when the body has changed since the summary was generated. (Compute
    `cleaned_body` once and reuse for both `render_markdown` input and the hash.)
- Add `summary_ai` and `summary_stale` to the record dict. `summary_text`
  already flows into `index.json` and `search_text_for`, so AI summaries become
  searchable with no extra work.

### 3. Front-end — `assets/app.js` + `assets/styles.css`

- `cardSummaryHtml` (app.js:409) already renders `record.summary_text`; plumbing
  is unchanged. Add markers:
  - When `record.summary_ai`, render a small **"AI summary"** label on the card
    (visual treatment consistent with the existing `un_equivalent_ai` chips).
  - When `record.summary_stale`, render a **"may be out of date"** marker beside
    it.
- The body-match search snippet path (`summary-snippet`) is unaffected — markers
  apply to the plain summary line.
- Add minimal CSS for the marker(s).

## Data flow

```
.md frontmatter (summary, summary_hash, summary_generated_at)
  -> build_record: summary_text = summary or summarize(); summary_ai; summary_stale
  -> index.json (light record)
  -> app.js cardSummaryHtml -> card render with AI / stale markers
```

Generation is an offline, occasional operation. The build remains fast and fully
offline (no CDN, no network), reading only what the generator already wrote.

## Out of scope

- Changing the Read / full-text reader view (already works).
- Auto-calling the LLM during `build.py` (build stays offline/deterministic).
- Actually backfilling summaries for all 838 regulations in this task. The script
  enables it; running it against the API is a separate operational step. The
  fallback excerpt covers any regulation without a summary.

## Testing

- `build.py` unit coverage: a record with `summary` set surfaces it as
  `summary_text` with `summary_ai=True`; a matching `summary_hash` yields
  `summary_stale=False`; a mismatched hash yields `summary_stale=True`; a record
  with no `summary` falls back to `summarize()` with `summary_ai=False`.
- `gen_summaries.py`: `--dry-run` prints prompts and makes no API call / no file
  writes; skip-if-present and `--stale-only` selection logic select the right
  records (testable without the API).
- Front-end: manual check that the AI and stale markers render and that a
  fallback (no-summary) card shows no AI marker.
