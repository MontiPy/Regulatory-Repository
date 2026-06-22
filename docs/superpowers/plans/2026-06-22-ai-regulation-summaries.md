# AI-generated regulation summaries — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a genuine 1–2 sentence AI summary on each regulation card (full text stays behind "Read"), generated offline into frontmatter, labeled "AI summary", and flagged "may be out of date" when the source body changed after the summary was written.

**Architecture:** A new `scripts/gen_summaries.py` (mirroring `scripts/auto_tag.py`) calls the Anthropic Batch API and writes `summary` / `summary_hash` / `summary_generated_at` into each regulation's `.md` frontmatter. `scripts/build.py` prefers `summary` over today's heuristic excerpt and derives two booleans (`summary_ai`, `summary_stale`) into each record. `assets/app.js` + `assets/styles.css` render the AI / stale markers on the card. The build itself never calls the network.

**Tech Stack:** Python 3.11+, `python-frontmatter`, `anthropic` (optional `tag` extra), `truststore`; vanilla JS + CSS for the front-end.

## Global Constraints

- Build stays fully **offline** — no CDN, no network calls in `build.py`; type uses system-font stacks already in `styles.css`.
- Strip all **visible** Honda brand text (existing CSS color tokens like `--honda-red` are fine; do not add visible "Honda" copy).
- Python `requires-python = ">=3.11"`.
- AI generation mirrors `scripts/auto_tag.py` conventions exactly: Anthropic **Messages Batch API**, `truststore.inject_into_ssl()`, `ANTHROPIC_API_KEY` from env, model **`claude-sonnet-4-6`**.
- Every new frontmatter key (`summary`, `summary_hash`, `summary_generated_at`) MUST be added to `OPTIONAL_KEYS` in `build.py` or all 838 regulation files fail the unknown-key check (`build.py:184`).
- Stale detection uses **SHA-1 of the cleaned body** (`clean_body(...)` output). `gen_summaries.py` and `build.py` must hash the identical string — share the helper, don't reimplement it.

---

### Task 1: build.py — summary fields + stale detection

**Files:**
- Modify: `scripts/build.py` (imports, `OPTIONAL_KEYS`, new `_body_hash`, `build_record`)
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: existing `clean_body(content, source_api)`, `summarize(body_html)`, `render_markdown(body)`.
- Produces:
  - `_body_hash(cleaned_body: str) -> str` — `hashlib.sha1` hexdigest of the UTF-8 cleaned body. (Imported by Task 2.)
  - `clean_body` — already exists; re-exported for Task 2's import.
  - Each record dict gains: `summary_text: str` (AI summary if present else heuristic), `summary_ai: bool`, `summary_stale: bool`. These flow into `index.json` via existing `split_record`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_build.py`. First extend the import block at the top (around line 11) to add `build_record`, `clean_body`, `_body_hash`:

```python
from scripts.build import (
    BuildIssue,
    _body_hash,
    as_list,
    build_record,
    clean_body,
    clean_summary_display_text,
    copy_static_assets,
    load_region_series,
    render_markdown,
    render_shell,
    report_line,
    search_text_for,
    split_record,
    stringify,
    summarize,
    validate_required,
    validate_un_equivalent,
    write_index_json,
    write_record_bodies,
    write_taxonomy_json,
    write_search_text,
)
```

Then append this test class at the end of the file:

```python
import frontmatter


class TestBuildRecordSummary:
    BODY = "# Reversing Lamps\n\nThis Standard specifies requirements for reversing lamps fitted to vehicles.\n"

    def _write_reg(self, path, body, **extra):
        meta = {
            "id": path.stem,
            "title": "Test Reg",
            "region": "US",
            "citation": "49 CFR 571.108",
            "status": "in-force",
            "source_url": "https://example.com",
            "source_api": "ecfr",
            "last_pulled": "2024-01-01T00:00:00+00:00",
            "tagging_status": "untagged",
        }
        meta.update(extra)
        post = frontmatter.Post(body, **meta)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def _current_hash(self, body):
        return _body_hash(clean_body(body, "ecfr"))

    def test_no_summary_falls_back_to_heuristic(self, tmp_path):
        path = tmp_path / "test-id.md"
        self._write_reg(path, self.BODY)
        record, _issues = build_record(path, {}, draft=True)
        assert record["summary_ai"] is False
        assert record["summary_stale"] is False
        assert record["summary_text"]  # non-empty heuristic excerpt
        assert "AI summary" not in record["summary_text"]

    def test_summary_present_is_surfaced_and_flagged_ai(self, tmp_path):
        path = tmp_path / "test-id.md"
        self._write_reg(
            path, self.BODY,
            summary="Sets requirements for reversing lamps on vehicles.",
            summary_hash=self._current_hash(self.BODY),
        )
        record, _issues = build_record(path, {}, draft=True)
        assert record["summary_text"] == "Sets requirements for reversing lamps on vehicles."
        assert record["summary_ai"] is True
        assert record["summary_stale"] is False

    def test_summary_with_mismatched_hash_is_stale(self, tmp_path):
        path = tmp_path / "test-id.md"
        self._write_reg(
            path, self.BODY,
            summary="Sets requirements for reversing lamps on vehicles.",
            summary_hash="deadbeef",  # does not match current body
        )
        record, _issues = build_record(path, {}, draft=True)
        assert record["summary_ai"] is True
        assert record["summary_stale"] is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_build.py::TestBuildRecordSummary -v`
Expected: FAIL — `ImportError: cannot import name '_body_hash'` (and/or `KeyError: 'summary_ai'`).

- [ ] **Step 3: Implement the build.py changes**

In `scripts/build.py`, add the `hashlib` import near the top imports (after `import argparse`):

```python
import hashlib
```

Add the three keys to `OPTIONAL_KEYS` (the set defined around line 49) — insert alongside the others:

```python
    "summary",
    "summary_hash",
    "summary_generated_at",
```

Add the hash helper next to `clean_body` (after the `clean_body` function, ~line 262):

```python
def _body_hash(cleaned_body: str) -> str:
    """SHA-1 of the cleaned body — the stable key for summary staleness."""
    return hashlib.sha1(cleaned_body.encode("utf-8")).hexdigest()
```

In `build_record` (~line 404), replace this:

```python
    body_html = render_markdown(clean_body(post.content, stringify(metadata.get("source_api"))))
    record = {
```

with this (compute the cleaned body once, derive flags, prefer the authored summary):

```python
    cleaned_body = clean_body(post.content, stringify(metadata.get("source_api")))
    body_html = render_markdown(cleaned_body)
    authored_summary = stringify(metadata.get("summary"))
    summary_ai = bool(authored_summary)
    summary_stale = summary_ai and stringify(metadata.get("summary_hash")) != _body_hash(cleaned_body)
    record = {
```

Then, in the record dict, replace the existing summary line:

```python
        "summary_text": summarize(body_html),
```

with:

```python
        "summary_text": authored_summary or summarize(body_html),
        "summary_ai": summary_ai,
        "summary_stale": summary_stale,
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_build.py::TestBuildRecordSummary -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full build test module to confirm no regression**

Run: `python -m pytest tests/test_build.py -q`
Expected: PASS (all existing tests still green).

- [ ] **Step 6: Commit**

```bash
git add scripts/build.py tests/test_build.py
git commit -m "feat: surface authored summary + AI/stale flags in build records"
```

---

### Task 2: gen_summaries.py — generation script

**Files:**
- Create: `scripts/gen_summaries.py`
- Test: `tests/test_gen_summaries.py`

**Interfaces:**
- Consumes (from Task 1): `from scripts.build import clean_body, _body_hash`.
- Produces (used by tests + operator):
  - `should_process(meta: dict, current_hash: str, regen: bool, stale_only: bool) -> bool`
  - `parse_summary(text: str) -> str`
  - `write_summary_to_file(path: str, summary: str, body_hash: str) -> None`
  - `build_prompt(reg: dict) -> str`
  - CLI: `python scripts/gen_summaries.py [--region R] [--regen] [--stale-only] [--dry-run] [--poll BATCH_ID]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_gen_summaries.py`:

```python
"""Tests for scripts/gen_summaries.py — selection, parsing, frontmatter write."""
from __future__ import annotations

import sys
from pathlib import Path

import frontmatter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.gen_summaries import (
    parse_summary,
    should_process,
    write_summary_to_file,
)


class TestShouldProcess:
    def test_default_skips_when_summary_present(self):
        meta = {"summary": "x", "summary_hash": "abc"}
        assert should_process(meta, "abc", regen=False, stale_only=False) is False

    def test_default_includes_when_no_summary(self):
        assert should_process({}, "abc", regen=False, stale_only=False) is True

    def test_regen_includes_everything(self):
        meta = {"summary": "x", "summary_hash": "abc"}
        assert should_process(meta, "abc", regen=True, stale_only=False) is True

    def test_stale_only_includes_when_hash_mismatch(self):
        meta = {"summary": "x", "summary_hash": "old"}
        assert should_process(meta, "new", regen=False, stale_only=True) is True

    def test_stale_only_skips_when_hash_matches(self):
        meta = {"summary": "x", "summary_hash": "same"}
        assert should_process(meta, "same", regen=False, stale_only=True) is False

    def test_stale_only_skips_when_no_summary(self):
        assert should_process({}, "new", regen=False, stale_only=True) is False


class TestParseSummary:
    def test_strips_code_fences(self):
        assert parse_summary("```\nHello world.\n```") == "Hello world."

    def test_collapses_whitespace(self):
        assert parse_summary("Hello   \n  world.") == "Hello world."

    def test_strips_wrapping_quotes(self):
        assert parse_summary('"Hello world."') == "Hello world."

    def test_truncates_overlong_text(self):
        long = "word " * 100
        result = parse_summary(long)
        assert len(result) <= 323  # cap + ellipsis
        assert result.endswith("...")


class TestWriteSummaryToFile:
    def test_writes_three_fields(self, tmp_path):
        path = tmp_path / "reg.md"
        post = frontmatter.Post("Body text", id="reg", title="T")
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

        write_summary_to_file(str(path), "A short summary.", "hash123")

        reloaded = frontmatter.load(path)
        assert reloaded["summary"] == "A short summary."
        assert reloaded["summary_hash"] == "hash123"
        assert reloaded["summary_generated_at"]  # timestamp set
        assert reloaded.content.strip() == "Body text"  # body untouched
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_gen_summaries.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.gen_summaries'`.

- [ ] **Step 3: Create the generation script**

Create `scripts/gen_summaries.py`:

```python
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
    text = text.strip('"“”').strip()
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_gen_summaries.py -v`
Expected: PASS (all selection / parse / write tests green).

- [ ] **Step 5: Smoke-test the CLI selection + prompt with --dry-run (no API call)**

Run: `python scripts/gen_summaries.py --region AU --dry-run`
Expected: prints `Found N regulation(s) to summarize.`, several `[DRY RUN]` prompt previews showing real regulation text (not nav boilerplate), and `Would send N regulation(s)`. No file changes, no network call.

- [ ] **Step 6: Commit**

```bash
git add scripts/gen_summaries.py tests/test_gen_summaries.py
git commit -m "feat: add gen_summaries.py AI summary generator"
```

---

### Task 3: Front-end — AI / stale markers on cards

**Files:**
- Modify: `assets/app.js` (`cardSummaryHtml`, ~line 409; add `summaryMetaHtml`)
- Modify: `assets/styles.css` (after `.summary-snippet`, ~line 520)

**Interfaces:**
- Consumes (from Task 1, via `index.json`): `record.summary_text`, `record.summary_ai`, `record.summary_stale`.
- Produces: card DOM with a `.summary-meta` line carrying an "AI summary" tag (and a "may be out of date" tag when stale). No new exported JS.

- [ ] **Step 1: Add the marker helper and wire it into the card summary (app.js)**

In `assets/app.js`, replace the existing `cardSummaryHtml` function (around line 409):

```javascript
    function cardSummaryHtml(record, query) {
      const snippet = bodyMatchSnippet(record, query);
      if (snippet) return `<p class="summary summary-snippet">${highlight(snippet, query)}</p>`;
      return `<p class="summary">${highlight(record.summary_text || "No summary available.", query)}</p>`;
    }
```

with:

```javascript
    function summaryMetaHtml(record) {
      if (!record.summary_ai) return "";
      const tags = [`<span class="summary-tag">AI summary</span>`];
      if (record.summary_stale) {
        tags.push(`<span class="summary-tag summary-stale" title="The source text changed after this summary was written.">may be out of date</span>`);
      }
      return `<p class="summary-meta">${tags.join("")}</p>`;
    }

    function cardSummaryHtml(record, query) {
      const snippet = bodyMatchSnippet(record, query);
      if (snippet) return `<p class="summary summary-snippet">${highlight(snippet, query)}</p>`;
      const summary = `<p class="summary">${highlight(record.summary_text || "No summary available.", query)}</p>`;
      return summary + summaryMetaHtml(record);
    }
```

- [ ] **Step 2: Add the marker styles (styles.css)**

In `assets/styles.css`, immediately after the `.summary-snippet` rule (~line 520), add:

```css
    .summary-meta { margin: 6px 0 0; display: flex; flex-wrap: wrap; gap: 6px; }
    .summary-tag {
      display: inline-flex; align-items: center; min-height: 18px;
      padding: 1px 6px; font-size: var(--text-eyebrow); letter-spacing: 0.03em;
      color: var(--fg-3); border: 1px solid var(--line-1); background: var(--surface);
    }
    .summary-tag.summary-stale {
      color: var(--danger);
      border-color: color-mix(in srgb, var(--danger) 45%, transparent);
    }
```

- [ ] **Step 3: Verify the build still produces a bundle**

Run: `python scripts/build.py --draft`
Expected: `Build complete: 838 records, 0 errors, ... warnings.` and `dist/` written.

- [ ] **Step 4: Manual DOM verification (reversible — touches one real reg, then reverts)**

Pick one regulation file and temporarily give it a matching summary so a labeled card renders, then build and eyeball:

```bash
python - <<'PY'
import frontmatter, sys
from pathlib import Path
sys.path.insert(0, "scripts")
from build import clean_body, _body_hash
p = next(Path("regulations").rglob("*.md"))
post = frontmatter.load(p)
post["summary"] = "TEST: Sets out requirements for this regulation's subject."
post["summary_hash"] = _body_hash(clean_body(post.content or "", str(post.get("source_api") or "")))
post["summary_generated_at"] = "2026-06-22T00:00:00+00:00"
p.write_text(frontmatter.dumps(post), encoding="utf-8")
print("patched", p)
PY
python scripts/build.py --draft
```

Open `dist/index.html` in a browser, find that regulation's card. Confirm:
- the card shows the "TEST: …" summary text, and
- an **"AI summary"** tag appears beneath it.

Then change that file's `summary_hash` to `"stale"` and rebuild to confirm the **"may be out of date"** tag also appears.

Finally revert the throwaway edit:

```bash
git checkout -- regulations/
```

- [ ] **Step 5: Commit**

```bash
git add assets/app.js assets/styles.css
git commit -m "feat: show AI summary + out-of-date markers on cards"
```

---

## Notes for the operator (post-implementation)

Generating real summaries is a separate operational step (needs `ANTHROPIC_API_KEY` and the `anthropic` package: `pip install -e ".[tag]"`):

```bash
ANTHROPIC_API_KEY=sk-ant-... python scripts/gen_summaries.py            # all un-summarized
ANTHROPIC_API_KEY=sk-ant-... python scripts/gen_summaries.py --region AU  # one region first
python scripts/build.py                                                  # rebuild with summaries
```

Until then, every card falls back to today's heuristic excerpt (unlabeled), so the tool stays fully functional with zero summaries present.
