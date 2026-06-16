# OEM-Agnostic Regulatory Repository

An HTML reference tool for vehicle regulations across 21 regions. Regulation text is pulled directly from official government sources; classification and cross-references are added on top.

**Live site:** https://montipy.github.io/Regulatory-Repository/ (auto-deployed from `main`).

To run it locally, serve the built bundle over HTTP — the reader loads data with `fetch`, so it must be served, not opened from `file://`:

```
python scripts/build.py
python -m http.server -d dist 8000      # then open http://localhost:8000/
```

---

## What is this?

Vehicle engineers need to know which regulations apply to a given commodity (e.g., Seats) or system (e.g., Braking) in each market. Today this requires hunting across agency websites, internal spreadsheets, and second-hand summaries.

This repository pulls regulation text from official APIs, classifies each record against a controlled taxonomy (commodity / vehicle system / vehicle category), and renders everything into a static web bundle with faceted search.

Current coverage: **728 records** across **21 regions** — 697 from live connectors plus 31 reference stubs for markets without a public source.

| Region | Code | Source connector | Records |
|--------|------|-----------|---------|
| United States | US | eCFR (49 CFR Part 571 FMVSS; 40/47 CFR) | 142 |
| Australia | AU | Federal Register of Legislation (ADR) | 99 |
| UNECE | ECE | UNECE WP.29 (UN Regulations) | 86 |
| South Korea | KR | law.go.kr (KMVSS) | 83 |
| Gulf Cooperation Council | GCC | GSO Technical Regulations (metadata) | 63 |
| Canada | CA | Justice Laws XML (CMVSS) | 59 |
| Japan | JP | e-Gov Law API (JVSR) | 56 |
| China | CN | openstd.samr.gov.cn (GB; metadata) | 49 |
| Brazil | BR | LexML Brazil (CONTRAN) | 32 |
| European Union | EU | EUR-Lex (Regulations & Directives) | 25 |
| India | IN | MoRTH / ARAI (AIS; metadata) | 3 |

The remaining 31 records are reference stubs (`source_api: spreadsheet`) for markets without a public connector — ASEAN, EAEU, Mexico, New Zealand, South Africa, Argentina, Israel, Türkiye, Taiwan, and cross-cutting standards (ISO/IEC/SAE). All records are classified against the taxonomy and many carry UN-equivalent cross-references regardless of source.

---

## Prerequisites

- Python 3.10+
- `pip install -r requirements.txt`

---

## Three-stage pipeline

```
Stage 1: PULL        Stage 2: TAG              Stage 3: BUILD
Python, no LLM  →    auto_tag.py        →      Python, no LLM
API → .md            Anthropic Batch API        .md → HTML
```

### Stage 1 — Pull

Fetch regulation text from official APIs into `regulations/*.md`:

```
python scripts/pull.py --region US      # pull one region
python scripts/pull.py --all            # pull all regions
```

Each `.md` file has YAML frontmatter (id, title, citation, source URL, etc.) and a Markdown body containing the regulation text verbatim from the API.

Re-running is safe and idempotent — it overwrites existing files with fresh content.

### Stage 2 — Tag

Classify untagged records against the controlled taxonomy with `scripts/auto_tag.py`. It sends each untagged record to the Anthropic Messages **Batch API** (Claude Sonnet 4.6), then writes the returned `commodities` / `systems` / `vehicle_categories` back into the `.md` frontmatter and marks the record `tagging_status: llm-tagged`.

Alongside the controlled facets, the same call also emits **`open_tags`** — free-form,
industry-standard commodity/part-type labels (e.g. "master cylinder", "ISOFIX
anchorage") that are *not* restricted to the taxonomy. These raw tags are folded
into the search corpus to improve recall and shown as read-only chips on each
record's detail view; they are not filter facets.

```
# Tag all untagged regulations (requires an Anthropic API key)
ANTHROPIC_API_KEY=sk-ant-... python scripts/auto_tag.py

python scripts/auto_tag.py --region US            # tag only one region
python scripts/auto_tag.py --dry-run              # print prompts without calling the API
python scripts/auto_tag.py --retag                # re-tag already-tagged records
python scripts/auto_tag.py --poll msgbatch_xxxxx  # resume polling a submitted batch
```

The taxonomy is defined in `taxonomy.yaml`. The model may only select values that appear verbatim in the taxonomy, and results are re-validated against it on import, so tagging stays within the controlled vocabulary. Tagging is the only stage that uses an LLM — pull and build are deterministic.

> The earlier manual batch workflow (`tag_export.py` → classify JSONL in `tagging_batches/` → `tag_import.py`) still exists for offline/no-API-key use, but `auto_tag.py` is the standard path.

#### Normalizing open tags

After tagging, distill the emitted `open_tags` into a canonical vocabulary:

```
ANTHROPIC_API_KEY=sk-ant-... python scripts/normalize_tags.py
python scripts/normalize_tags.py --dry-run   # no API; map each tag to itself
```

This makes one or more Claude Sonnet calls (the unique new tags are batched in
chunks) and writes
`tag_aliases.yaml` (raw → canonical, hand-editable — existing entries are never
overwritten) and `discovered_vocabulary.yaml` (the canonical list). Search uses
the **raw** tags directly, so normalization is optional and never narrows recall.

### Stage 3 — Build

Render everything to a static web bundle:

```
python scripts/build.py
```

Output in `dist/`: `index.html` + `assets/` (CSS, JS, vendored MiniSearch) + `data/` (`index.json` light metadata, `records/<id>.json` lazy bodies, `taxonomy.json`, `search-text.json` search corpus). Serve it over HTTP (see top of this README) or let the Pages workflow host it.

---

## Hosting (GitHub Pages)

The site auto-deploys to GitHub Pages on every push to `main` via `.github/workflows/deploy.yml`, which builds the bundle and publishes `dist/` (kept gitignored — always built fresh). All asset/data paths are relative, so it works under the project sub-path `…github.io/Regulatory-Repository/`.

One-time setup: in **Settings → Pages → Build and deployment**, set **Source = GitHub Actions**. After that, every push to `main` redeploys automatically; `workflow_dispatch` allows a manual rebuild from the Actions tab.

---

## Updating a region

```
python scripts/pull.py --region AU                      # re-pull Australia
ANTHROPIC_API_KEY=sk-ant-... python scripts/auto_tag.py --region AU   # tag new records
python scripts/build.py
```

---

## File layout

```
Regulatory Repository/
├── README.md
├── taxonomy.yaml                    controlled vocabularies for tagging
├── requirements.txt
├── regulations/                     generated .md files, one per regulation
├── connectors/                      per-region API clients
│   ├── _common.py                   shared HTTP, rate limiting, schema
│   ├── ecfr.py                      US (eCFR)
│   ├── eurlex.py                    EU (EUR-Lex)
│   ├── law_go_kr.py                 KR (law.go.kr)
│   ├── au_legislation.py            AU (legislation.gov.au)
│   ├── egov_jp.py                   JP (e-Gov)
│   └── justice_ca.py                CA (laws-lois.justice.gc.ca)
├── manifests/                       per-region pull lists
│   ├── us.yaml, eu.yaml, kr.yaml, au.yaml, jp.yaml, ca.yaml
├── scripts/
│   ├── pull.py                      Stage 1 orchestrator
│   ├── auto_tag.py                  Stage 2: LLM tagging via Anthropic Batch API
│   ├── build.py                     Stage 3 HTML builder
│   ├── tag_export.py / tag_import.py  legacy manual-batch tagging (optional)
│   └── ...                          extract_un_equivalent.py, infer_un_equivalent.py, gen_stubs.py, etc.
├── tagging_batches/                 staging for the legacy manual tagging workflow
├── templates/
│   └── index.html.j2                Jinja2 template
└── dist/
    └── index.html                   shareable output
```

---

## Taxonomy

Four search facets, controlled vocabularies, AND across facets / OR within:

**Commodities** (Tier 1/2 supplier perspective): Seats, Glass, Lighting modules, Tires, Brakes, Airbags, Seatbelts, Mirrors, Wheels, Wiring, ECUs, ADAS sensors, Batteries, Electric motors, Fuel system, Exhaust, HVAC, Infotainment, Body structure, Bumpers, Door latches & hinges, Steering column, Suspension, Fuel tanks, Hoses & lines, Connectors, Charging inlet, Power electronics, Horn, Wipers & washers, Pedals

**Systems**: Lighting & signaling, Braking, Steering, Tires & wheels, Crashworthiness, Restraints, Visibility, Emissions, Fuel safety, EMC, EV charging, Battery safety, ADAS, Cybersecurity, Noise, Glazing, HVAC, Vehicle identification, Pedestrian protection, Theft prevention, Tell-tales & controls, On-board diagnostics, Software updates

**Vehicle categories**: Passenger car, Light truck, Heavy truck, Motorcycle, Bus, Trailer, Off-road

**Status**: in-force, proposed, withdrawn, superseded

---

## Adding a new region

1. Write a connector in `connectors/your_region.py` implementing `pull(manifest_path, dest_dir) -> list[Path]`.
2. Create `manifests/your_region.yaml` listing the records to pull.
3. Register the region in `scripts/pull.py` under `REGION_CONNECTOR`.
4. Run `python scripts/pull.py --region YOUR_REGION`.
5. Tag the new records and rebuild.

See `connectors/_common.py` for shared utilities (rate limiting, frontmatter writing, markdownify).

---

## Notes on Korean (KR) records

The law.go.kr website renders article content via JavaScript. Without a free API key from [open.law.go.kr](https://open.law.go.kr), the KR connector captures the page structure but not the full article body text. Set the `KR_LAW_API_KEY` environment variable to enable full text retrieval.

## Notes on Japanese (JP) records

Article text is in Japanese (法令 XML from e-Gov). Titles include the Japanese article name where the API provides it.

## Notes on EU records

Two EU regulations (REACH 1907/2006 and Commission Regulation 2017/1151) require authenticated EUR-Lex access for their full text and may show CELEX-style titles rather than the full regulation name.

---

## Deferred to v2

- Vietnam (QCVN) — `vbpl.vn` is unreachable from the build environment
- Full text for paywalled standards (GCC/GSO sold standards, image-based GB standards) — connectors capture official metadata and cross-references instead
- Change-detection pipeline (alert when upstream regulations are amended)
- Human tag-review workflow
- Multi-user editing or hosted deployment
