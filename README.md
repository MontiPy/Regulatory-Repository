# OEM-Agnostic Regulatory Repository

A single-file offline HTML reference tool for vehicle regulations across six major markets. All content is pulled directly from official government APIs — no LLM-drafted text.

**Open `dist/index.html` in any browser.** No server, no login, no internet required.

---

## What is this?

Vehicle engineers need to know which regulations apply to a given commodity (e.g., Seats) or system (e.g., Braking) in each market. Today this requires hunting across agency websites, internal spreadsheets, and second-hand summaries.

This repository pulls regulation text from official APIs, classifies each record against a controlled taxonomy (commodity / vehicle system / vehicle category), and renders everything into a single shareable HTML file with faceted search.

Current coverage: **98 records** across **6 regions**.

| Region | Code | Source API | Records |
|--------|------|-----------|---------|
| United States | US | eCFR (49 CFR Part 571, FMVSS) | 32 |
| European Union | EU | EUR-Lex | 13 |
| Japan | JP | e-Gov Law API | 15 |
| Canada | CA | Justice Laws XML | 15 |
| Australia | AU | Federal Register of Legislation | 13 |
| South Korea | KR | law.go.kr (KMVSS) | 10 |

---

## Prerequisites

- Python 3.10+
- `pip install -r requirements.txt`

---

## Three-stage pipeline

```
Stage 1: PULL        Stage 2: TAG              Stage 3: BUILD
Python, no LLM  →    export → classify  →      Python, no LLM
API → .md            → import                  .md → HTML
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

Classify untagged records against the controlled taxonomy:

```
# 2a: export untagged records to batch JSONL files
python scripts/tag_export.py

# 2b: open Claude Code (or Codex) and follow instructions in:
#     tagging_batches/_vocab.md
#     Write results to tagging_batches/batch_NNN_results.jsonl

# 2c: import classifications back into .md frontmatter
python scripts/tag_import.py
```

The taxonomy is defined in `taxonomy.yaml`. Classifying is the only step that requires human/LLM review — all other stages are deterministic.

### Stage 3 — Build

Render everything to a single offline HTML file:

```
python scripts/build.py
```

Output: `dist/index.html` — share via OneDrive, email, or USB. Opens from `file://` with no internet connection.

---

## Updating a region

```
python scripts/pull.py --region AU    # re-pull Australia
python scripts/tag_export.py          # export newly untagged records
# classify new batches in tagging_batches/
python scripts/tag_import.py
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
│   ├── tag_export.py                Stage 2a: export to JSONL batches
│   ├── tag_import.py                Stage 2c: import JSONL results
│   └── build.py                     Stage 3 HTML builder
├── tagging_batches/                 staging for Stage 2 I/O
│   ├── _vocab.md                    vocab + classifier instructions
│   ├── batch_NNN.jsonl              input batches
│   └── batch_NNN_results.jsonl      output from classifier
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

- GCC, China, Brazil (no public APIs; would require scrapers or manual entry)
- Change-detection pipeline (alert when upstream regulations are amended)
- Human tag-review workflow
- Multi-user editing or hosted deployment
