# China GB Connector — Design

**Status:** Approved (brainstorming, 2026-06-04). First sub-project of API-3 (new data-source connectors); GCC / India / Vietnam deferred to later cycles.

## Goal

Replace the 49 spreadsheet-derived China `cn-gb-*` stubs with records enriched from the **official** Chinese national-standards portal (`openstd.samr.gov.cn`): authoritative title (CN + EN), in-force/abolished status, implementation date, the optional "adopted international standard" cross-reference, and a stable official source link. Full regulatory text is **out of scope** (free GB standards are served as image-tile viewers, not extractable text; the rest are sold) — this connector does *metadata enrichment*, not full-text capture.

## Why metadata-only

A feasibility probe (2026-06-04) confirmed: `openstd.samr.gov.cn` is reachable (HTTP 200); the keyword search returns a server-rendered result table; each standard's detail page (`newGbInfo?hcno=…`) exposes title/status/date as extractable HTML. But the full-text "online reading" is an image-tile viewer with no text layer. Metadata enrichment is therefore the reliable, no-OCR, no-purchase ceiling — and it is a real improvement over the spreadsheet stubs (official titles, live status, dates, and an authoritative UN/ISO cross-reference where declared).

## openstd.samr.gov.cn mechanics (verified)

1. **Search:** `GET /bzgk/gb/std_list?p.p2=<GB number>` returns an HTML table. Each match is a cell:
   `<a href="javascript:void(0)" onclick="showInfo('<HCNO>');">GB 11551-2014</a>`
   where `<HCNO>` is a 32-char hex id (e.g. `290A78A7D1665437A160104DCE7FA380`).
2. **Detail:** `GET /bzgk/gb/newGbInfo?hcno=<HCNO>` is the canonical detail page. Fields appear as `label：value` inside table cells, e.g. `英文标准名称：The protection of the occupants in the event of a frontal collision for motor vehicle`. Status is a coloured span (`class="text-success"` = 现行/in-force, `text-warning`/`text-danger` = 废止/abolished or withdrawn). The `采用国际标准` (adopted international standard) row is **optional** — present only when the standard declares one.

The detail page URL (`newGbInfo?hcno=<HCNO>`) is the stable permalink; the connector records it as `source_url` (more durable than the keyword-search URL the stubs currently use).

### Resolving GB numbers
Manifest entries carry a GB number, optionally versioned (`GB 11551-2014`) or bare (`GB 11552`). The connector searches the **bare** number, then selects the matching row:
- versioned entry → exact `GB <num>-<year>` row;
- bare entry → the most recent **in-force** version (fallback: most recent row).
This subsumes the `cqc.com.cn` links some bare-number stubs currently use — everything resolves through openstd.

## Architecture

Follows the established `connectors/brazil.py` pattern and `scripts/pull.py` registration.

- **`manifests/cn.yaml`** (new) — `records:` list seeded from the 49 existing `cn-gb-*` stubs. Each entry: `id`, `gb_number` (e.g. `GB 11551-2014`), and `source_url` (existing, used only as fallback). Title/citation come from openstd at pull time, not the manifest.
- **`connectors/china.py`** (new) — `pull(manifest_path, dest_dir) -> list[Path]`, plus isolated, unit-testable helpers:
  - `search_hcno(session, gb_number) -> tuple[str, str] | None` — returns `(hcno, matched_gb_label)` or `None`.
  - `fetch_detail(session, hcno) -> str` — detail-page HTML.
  - `parse_detail(html) -> dict` — `{cn_title, en_title, status, impl_date, adopted_standard}` (any field may be empty/None).
  - `build_body(meta, gb_number, source_url) -> str` — structured markdown.
  - `enriched_stub_body(...)` — fallback when search/fetch fails or the number is not found.
- **`scripts/pull.py`** — add `"CN": ("connectors.china", "manifests/cn.yaml")` to `REGION_CONNECTOR`.
- Reuses `connectors._common`: `RateLimitedSession` (rate 0.5/s), `markdownify`, `write_md`.

## Data flow per record

```
manifest entry (id, gb_number)
  -> search_hcno(gb_number)
       found?  -> fetch_detail(hcno) -> parse_detail(html) -> build_body(meta)
       not found / error -> enriched_stub_body (preserves existing frontmatter)
  -> assemble record dict (see field precedence) -> write_md(record, body, dest)
```

## Field precedence (merge rules)

The 49 stubs are already `llm-tagged` and carry the `un_equivalent` / `un_equivalent_ai` built in API-2. `write_md` already preserves `commodities`, `systems`, `vehicle_categories`, `tagging_status`, `tagged_at` when the target file exists. The connector is responsible for the rest:

| Field | Source of truth | Rule |
|---|---|---|
| `title` | openstd | EN title if present, else CN title, else keep existing. Demote a *differing* prior title into `aliases`. |
| `status` | openstd | `in-force` / `abolished` from the status span; if unresolved, keep existing. |
| `citation` | openstd | Canonical `GB <num>-<year>` from the matched row. |
| `source_url` | openstd | `newGbInfo?hcno=…` permalink. |
| `source_api` | connector | Set to `china`. |
| `un_equivalent` | **merge** | Union of (existing grounded values) ∪ (adopted-standard ref, normalized to `UN R…` when it names a UN/ECE reg). Deduped, validated against `^UN R\d+[A-Za-z]?$`. ISO/other adopted standards that are **not** UN regs are recorded in the body, not in `un_equivalent`. |
| `un_equivalent_ai` | **preserve** | Carried through unchanged (connector reads existing and re-passes it). |
| `commodities`,`systems`,`vehicle_categories`,`tagging_status`,`tagged_at` | preserve | Handled automatically by `write_md`. |
| `aliases`,`translation_status`,`paywall` | preserve | Connector reads existing and re-passes; `paywall` left as-is (openstd viewing is free but individual downloads may be sold — don't assert false). |
| `effective_date` | openstd | Implementation date when parsed (frontmatter only; not yet surfaced by `build.py`). |

Because `write_md` overwrites record fields with existing values **only** for its preserve-set (tags), the connector must read the existing `.md` itself to compute the `un_equivalent` union and to carry `un_equivalent_ai`/`aliases`/`translation_status` through. This keeps the equivalents-merge logic in `china.py` (domain owner) and leaves `write_md` unchanged.

## Body format

```markdown
# GB 11551-2014 — The protection of the occupants in the event of a frontal collision for motor vehicle

**Standard No.:** GB 11551-2014
**Chinese title:** 汽车正面碰撞的乘员保护
**Status:** In-force  **Implementation date:** 2014-05-01
**Adopted international standard:** ECE R94 (modified)

Full standard text is published by SAC and viewed through the official portal's
online reader (image-based; not reproduced here).

[Official record — openstd.samr.gov.cn](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=…)
```
When openstd resolution fails, `enriched_stub_body` emits the same header from manifest data with a "could not be resolved on the official portal; visit the source" note — and `write_md` still preserves all existing frontmatter.

## Error handling

- Per-record `try/except` (as in `brazil.py`): any network/parse failure logs `FAILED` and falls back to the enriched stub; the run continues. No record is left worse than its current stub.
- `search_hcno` returns `None` (not an exception) when the GB number has no match → enriched-stub path.
- Encoding: force `resp.encoding = "utf-8"` before parsing (openstd serves UTF-8; `requests` may mis-detect). Bodies are written UTF-8 by `write_md`.
- Rate limit: `RateLimitedSession(rate=0.5)` (≤1 request / 2 s) to be a polite client of a government portal.

## Testing

Mirrors `tests/test_ecfr.py` / `tests/test_justice_ca.py` — **no live network in tests**:
- Save two fixtures under `tests/fixtures/china/`: a real `std_list` search-result page and a real `newGbInfo` detail page (captured during development).
- `test_search_hcno_extracts_id` — `search_hcno` pulls the right hcno + GB label from the fixture, and returns `None` for a miss.
- `test_parse_detail_fields` — `parse_detail` returns the EN title, in-force status, implementation date, and (for a fixture that has it) the adopted-standard string; tolerates the optional field being absent.
- `test_build_body_includes_official_link_and_status` — body contains the GB number, title, status, and the `newGbInfo` permalink.
- `test_pull_preserves_existing_tags_and_equivalents` — given a pre-existing `.md` with `commodities`/`un_equivalent`/`un_equivalent_ai`, a fixture-backed `pull` keeps the tags, **unions** the adopted-standard into `un_equivalent`, and carries `un_equivalent_ai` through unchanged.

## Out of scope (this cycle)

- Full regulatory text (image-tile viewers / paywalled downloads).
- GCC, India, Vietnam connectors (separate later cycles; Vietnam is unreachable from this environment and will remain an enriched stub).
- Surfacing `effective_date` in the built bundle (pre-existing `build.py` gap, tracked in `TODO.md`).
