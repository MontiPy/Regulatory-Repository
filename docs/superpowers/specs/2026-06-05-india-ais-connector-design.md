# India/AIS Connector — Design

**Status:** Approved (brainstorming, 2026-06-05). Third sub-project of API-3 (after China GB and GCC/GSO). Vietnam/QCVN remains deferred (unreachable from this environment).

## Goal

Give the 3 India `in-*` regulation stubs current source links and a consistent framework-reference body, preserving the LLM tags and UN cross-references from API-2. Deliberately **thin and network-free**, proportionate to the tiny record count.

## Why thin (feasibility findings, 2026-06-05)

- There are only **3 India records**, and they are **framework aggregates** (e.g. "AIS-038/AIS-156 EV battery safety", "BS-VI / CAFE", "CMVR / AIS type-approval framework"), not individual standards.
- The Ministry migrated domains: **`morth.nic.in` now redirects to `morth.gov.in`** (the `AIS-156.pdf` URL returns HTML, not a PDF), and `morth.gov.in` is **slow / times out** from this environment.
- The ARAI certification page is reachable but generic; there is no clean per-standard metadata source.
- **API-2 already populated** the UN cross-references (record 1 → `UN R100`; record 2 → `UN R101`, `UN R83`).

So the realistic value is a **link refresh** (fix the stale `morth.nic.in` domain) plus a consistent framework body — no full-text capture (the PDFs moved / time out, and these are aggregates anyway).

## Architecture

Mirrors `connectors/gulf.py` (and `connectors/china.py`) and `scripts/pull.py` registration. **No network calls** — the connector is a deterministic transform (the slow/timeout-prone host makes liveness checks unreliable and pointless here; the domain rewrite is a strict improvement over a known-redirecting link regardless).

- **`manifests/in.yaml`** (create) — `records:` list of `{id, citation, source_url}` for the 3 `in-*` stubs.
- **`connectors/india.py`** (create) — `pull(manifest_path, dest_dir) -> list[Path]`, plus small helpers:
  - `canonical_url(url) -> str` — rewrite `morth.nic.in` → `morth.gov.in`; leave other hosts unchanged.
  - `build_body(citation, title, url) -> str` — framework-reference markdown.
  - `_load_existing(path) -> dict` — existing frontmatter (mirrors gulf.py).
  - `pull()` — per-record assemble + `write_md`.
- **`scripts/pull.py`** (modify) — add `"IN": ("connectors.india", "manifests/in.yaml")` to `REGION_CONNECTOR`.
- Reuses `connectors._common`: `RateLimitedSession` (constructed but unused for network here — kept for signature parity / future use is **not** needed, so the connector simply does not call it), `write_md`.
  - Decision: to stay honest about "network-free", `pull()` does **not** construct a session at all. It reads the manifest, transforms each record, and writes. No `RateLimitedSession` import is required.

## Field precedence (merge rules)

`write_md` already preserves `commodities`, `systems`, `vehicle_categories`, `tagging_status`, `tagged_at`. The connector handles the rest:

| Field | Rule |
|---|---|
| `source_url` | → `canonical_url(existing or manifest source_url)` (fixes the `morth.nic.in` domain). |
| `source_api` | → `ais`. |
| `body` | → framework-reference stub (see below). |
| `title` | **preserve** existing. |
| `status` | **preserve** existing; default `in-force` if absent. |
| `citation` | from manifest. |
| `paywall` | **preserve** existing. |
| `un_equivalent`, `un_equivalent_ai` | **preserve** unchanged (read existing, re-pass). |
| `aliases`, `translation_status` | **preserve** (read existing, re-pass). |
| `commodities`,`systems`,`vehicle_categories`,`tagging_status`,`tagged_at` | preserve (automatic via `write_md`). |

The connector reads the existing `.md` (`_load_existing`) to carry the non-tag preserved fields through, because `write_md` does not preserve those.

## Body format

```markdown
# AIS-038 Rev.2 / AIS-156 — <existing title>

**Citation:** AIS-038 Rev.2 / AIS-156

India vehicle type approval is governed by the **Central Motor Vehicles Rules (CMVR)**;
technical requirements are set by **Automotive Industry Standards (AIS)**, administered by
ARAI for the Ministry of Road Transport & Highways (MoRTH). Many AIS standards are aligned
with UN/ECE Regulations.

[Official source](https://morth.gov.in/...)
```

## Error handling

- Per-record `try/except` around assembly/write; a single record failure is logged and skipped, not fatal.
- No network, so no network error paths; `canonical_url` is a pure string transform.

## Testing

Pure unit tests — **no network, no fixtures**:
- `test_canonical_url_rewrites_morth_domain` — `canonical_url("https://morth.nic.in/x")` → `https://morth.gov.in/x`; a non-morth URL (e.g. `araiindia.com`) is returned unchanged.
- `test_build_body_has_citation_and_link` — body contains the citation, the CMVR/AIS framework note, and the URL.
- `test_pull_repoints_and_preserves` — given a pre-existing tagged `in-*` stub with `un_equivalent`/`un_equivalent_ai` and a `morth.nic.in` source, `pull` sets `source_api=ais`, rewrites the URL to `morth.gov.in`, and **keeps** the tags + both equivalent fields + title unchanged.

## Out of scope

- Full standard text (PDFs moved / time out; records are framework aggregates).
- Per-standard metadata parsing (no clean source).
- Verifying `morth.gov.in` exact paths (host slow/timeout-prone from this environment; the rewrite targets the canonical current ministry domain, a strict improvement over the redirecting `morth.nic.in`).
- Vietnam/QCVN connector (unreachable from this environment — remains an enriched stub).
