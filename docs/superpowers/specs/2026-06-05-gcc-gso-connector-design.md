# GCC/GSO Connector — Design

**Status:** Approved (brainstorming, 2026-06-05). Second sub-project of API-3 (after the China GB connector). India/AIS and Vietnam/QCVN remain for later cycles.

## Goal

Give the 63 GCC `gcc-*` regulation stubs a clean, live public source link and a consistent framework-reference body, sourced from the **public** GSO consolidated *Technical Regulations for Motor Vehicles* PDF — while preserving the LLM tags and UN cross-references built in API-2. This is deliberately a **conservative** connector: it does **not** attempt per-standard title parsing (the master PDF's table extracts column-wise with wrapped titles, so reconstructing `{GSO number → title}` is fragile and would risk attaching the wrong title to a regulation).

## Why conservative (feasibility findings, 2026-06-05)

- **All 63 GCC records are `paywall: true`.** GSO sells individual standards; there is **no free per-standard portal** (unlike China's openstd).
- The **master PDF is public and extracts to clean English** (`https://static.gso.org.sa/gso-public-docs/conformity/mutabiq/GSO_TechnicalRegulations_MV_2027_MY-D2.pdf`, 412 KB, ~17.9 K chars) — but it is a 12-page **list** (columns: GSO number, year, title), **not** the standard texts.
- The table extracts **column-wise** (126 number-lines vs 48 year-lines, multi-line-wrapped titles) → reliable per-standard row reconstruction is **fragile**; mis-alignment would mislabel a regulation. Excluded from scope.
- The master PDF contains **no GSO→UN/ECE adoption mapping** that a Latin-text scan could find — but **API-2 already populated `un_equivalent`/`un_equivalent_ai`** for the GCC records, so cross-references are already covered.
- **Data defect to fix:** 27 stubs point at `https://www.gso.org.sa/wp-content/...` which now **404s**; the `static.gso.org.sa` master PDF is live.

## Architecture

Follows the established `connectors/china.py` merge pattern and `scripts/pull.py` registration.

- **`manifests/gcc.yaml`** (create) — `records:` list of `{id, citation, source_url}`, one per existing `gcc-*` stub (63), seeded from the stubs.
- **`connectors/gulf.py`** (create) — `pull(manifest_path, dest_dir) -> list[Path]`, plus small isolated helpers:
  - `master_pdf_live(session) -> bool` — GET `MASTER_URL`, return True iff `200` and `application/pdf` content type.
  - `build_body(citation, title, master_url, reachable) -> str` — framework-reference markdown.
  - `_load_existing(path) -> dict` — existing frontmatter (mirrors china.py).
  - `pull()` — per-record assemble + `write_md`.
- **`scripts/pull.py`** (modify) — add `"GCC": ("connectors.gulf", "manifests/gcc.yaml")` to `REGION_CONNECTOR`.
- Reuses `connectors._common`: `RateLimitedSession`, `write_md` (already preserves the 5 tag fields).

**Constant:** `MASTER_URL = "https://static.gso.org.sa/gso-public-docs/conformity/mutabiq/GSO_TechnicalRegulations_MV_2027_MY-D2.pdf"`.

## Data flow

```
manifest entry (id, citation, source_url)
  -> (once per run) master_pdf_live(session) -> reachable: bool, canonical MASTER_URL
  -> per record: load existing frontmatter
       reachable  -> source_url = MASTER_URL ; body = build_body(..., reachable=True)
       unreachable-> source_url = existing source_url (fallback) ; body notes the master is
                     temporarily unavailable
  -> assemble record (preserving fields below) -> write_md(record, body, dest)
```

The master-PDF reachability is checked **once** at the start of the run (not per record) and the result reused — a single network request, polite to the host.

## Field precedence (merge rules)

`write_md` already preserves `commodities`, `systems`, `vehicle_categories`, `tagging_status`, `tagged_at` when the target file exists. The connector handles the rest:

| Field | Rule |
|---|---|
| `source_url` | → `MASTER_URL` when the master PDF is reachable; else keep existing `source_url`. |
| `source_api` | → `gso`. |
| `body` | → framework-reference stub (see below). |
| `title` | **preserve** existing (no reliable parsing source). |
| `status` | **preserve** existing (no reliable source); default `in-force` only if absent. |
| `citation` | from manifest (the existing GSO citation). |
| `paywall` | **preserve** (`true` — GSO sells the standards). |
| `un_equivalent`, `un_equivalent_ai` | **preserve** unchanged (read existing, re-pass). No new source contributes here. |
| `aliases`, `translation_status` | **preserve** (read existing, re-pass). |
| `commodities`,`systems`,`vehicle_categories`,`tagging_status`,`tagged_at` | preserve (automatic via `write_md`). |

The connector reads the existing `.md` itself (`_load_existing`) to carry `un_equivalent`/`un_equivalent_ai`/`aliases`/`translation_status`/`paywall`/`status`/`title` through, because `write_md` does not preserve those.

## Body format

```markdown
# GSO 1053:2002 — <existing title>

**Citation:** GSO 1053:2002

This Gulf (GSO) standard is part of the **GCC Technical Regulation for Motor Vehicles**.
Individual GSO standards are published and sold by the GCC Standardization Organization;
their full text is not freely available. The consolidated list of GSO motor-vehicle
technical regulations (number, model year, subject) is published by GSO:

[GSO Technical Regulations for Motor Vehicles (consolidated list)](https://static.gso.org.sa/gso-public-docs/conformity/mutabiq/GSO_TechnicalRegulations_MV_2027_MY-D2.pdf)
```
When the master PDF is unreachable at pull time, the body instead notes that the consolidated list could not be reached and links the record's existing `source_url`.

## Error handling

- Single reachability check wrapped in `try/except`; any failure → `reachable = False`, the run continues using per-record fallbacks (no aborted run, no record left worse than its current stub).
- Per-record `try/except` around assembly/write; a single record failure is logged and skipped, not fatal.
- `RateLimitedSession(rate=0.5)`.

## Testing

Fake-session unit tests — **no live network, no 412 KB binary fixture**:
- `test_master_pdf_live_true` / `_false` — `master_pdf_live` returns True for a fake `200 application/pdf` response and False for a `404`/non-pdf response.
- `test_build_body_links_master_when_reachable` — body contains the citation, the master-PDF URL, and the "sold by GSO" framework note.
- `test_build_body_notes_unavailable_when_unreachable` — unreachable body notes the list could not be reached and uses the fallback URL.
- `test_pull_preserves_tags_and_equivalents` — given a pre-existing tagged `gcc-*` stub with `un_equivalent`/`un_equivalent_ai`, a fake-session `pull` sets `source_api=gso`, repoints `source_url` to `MASTER_URL`, and **keeps** the tags + both equivalent fields unchanged.

## Out of scope (this cycle)

- Per-standard title/status parsing from the master PDF (fragile column-wise table — explicitly excluded).
- Full standard text (sold by GSO).
- Inlining the master list into the 63 bodies (rejected for bloat; referenced by link instead).
- India/AIS and Vietnam/QCVN connectors (later cycles; Vietnam unreachable from this environment).
