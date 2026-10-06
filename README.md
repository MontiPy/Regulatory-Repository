# OEM-Agnostic Regulatory Repository

A global vehicle-regulation lookup and certification reference for automotive certification,
homologation and quality engineers working on consumer passenger vehicles (Honda, Toyota, Ford
and similar). It combines **full regulation text pulled from official government sources** with a
**curated certification knowledge layer** covering every vehicle market in the world.

**Live site:** https://montipy.github.io/Regulatory-Repository/ (auto-deployed from `main`).

To run it locally, serve the built bundle over HTTP — the reader loads data with `fetch`, so it must be served, not opened from `file://`:

```
python scripts/build.py
python -m http.server -d dist 8000      # then open http://localhost:8000/
```

---

## What can I do with it?

| Question | Where | What you get |
|---|---|---|
| "What governs this part/system?" | **Regulations** (search + facets) | 726 regulations (FMVSS, CMVSS, UN R, EU, JVSR, KMVSS, GB, ADR, CONTRAN, GSO, AIS…) with full text where public, classified by system / commodity / vehicle category. |
| "How do I get a vehicle approved in country X?" | **Markets** (`?view=markets`, `?view=market&code=JP`) | 48 market profiles covering 155 countries and territories, grouped by world region (plus sanctioned/restricted markets flagged as such): certification regime (self-certification, type approval, hybrid, recognition, registration/inspection), authorities with links, UN 1958/1998 Agreement status, accepted foreign approvals, mandatory marks/labels/certificates, emissions level, language, step-by-step approval process, upcoming changes, and a per-market requirement map. |
| "What is this requirement called in every other market?" | **Crosswalk** (`?view=crosswalk`, `?view=topic&t=side-pole`) | 69 requirement topics (frontal/side/pole impact, belts, ISOFIX, ESC, AEB, lighting, glazing, TPMS, EV safety, REESS, emissions, CO2, EMC, cybersecurity, OTA, VIN, recalls…) × 11 regimes (US, CA, UN R, EU, JP, KR, CN, IN, AU, BR, GCC). Each cell carries the citation, status (mandatory / phase-in / proposed / voluntary / none), engineering notes and one-click links to the regulation text. |
| "What's my compliance checklist for this launch?" | **Launch planner** (`?view=planner&m=US,EU,CN&pt=BEV`) | Pick target markets + powertrain (ICE/HEV/PHEV/BEV/FCEV) → per-market approval routes and a requirement checklist mapped to each market's governing regulation (UN R basis inferred for 1958-Agreement markets). **Export CSV** for a compliance matrix / DVP&R, or print. Every plan is a shareable URL. |
| "What does CoP / IWVTA / RAV / OTTS / SABER mean?" | **Glossary** (`?view=glossary`) | 45 certification and homologation terms linked to the markets and instruments that use them. |

Searching in the header also surfaces matching **market profiles, crosswalk topics and glossary
terms** above the regulation results (e.g. "Saudi", "ISOFIX", "R94").

> **Reference aid, not legal advice.** The knowledge layer is curated by hand. Every market
> profile carries a confidence level (high / medium / low), and un-verified UN-agreement
> memberships are shown as "?" rather than guessed. Confirm the current instrument, series and
> transitional dates with the authority before any certification decision.

## Data quality — what to trust

A full content-and-accuracy review was run in October 2026 (47 reviewer agents + orchestrator
adjudication; see [`review/REPORT.md`](review/REPORT.md) and the change log
[`review/CHANGES.md`](review/CHANGES.md)). Its key conclusions are built into the site:

- **Only about 45 % of records hold the regulation text itself.** The build classifies every body
  (`content_kind`): `full` (regulation text), `summary` (curated/AI-written description), `index`
  (the source site's landing page only) or `link` (a pointer only). After the 2026-10 re-pull,
  486 records hold full text (UN Regulations via the EU Official Journal, Australian ADRs via the
  FRL API). Cards are labelled ("Summary only", "Link only", "Index page only"), the
  reader shows a "Not the regulation text" banner, and the **Availability** filter can narrow
  results to full regulation text.
- **UN equivalents are only those the regulation itself states** (`un_equivalent`, e.g. an ADR's
  "alternative standards" clause, or a GSO/GB standard that adopts a UN Regulation). Machine-suggested
  equivalents were removed in 2026-10 after the review found hundreds of wrong mappings; the removed
  values are kept in `review/removed_un_equivalent_ai.json` for anyone re-checking them.
- **Status** now distinguishes `upcoming` (adopted, not yet applicable) and carries an optional
  `status_note` for nuance (e.g. "being superseded by ADR 79/05", "federal waiver revoked, in
  litigation").
- Reproduce or extend the review with `scripts/review_precheck.py`, the shard/brief files in
  `review/`, and `scripts/review_aggregate.py`.

---

## Regulation corpus

Vehicle engineers need to know which regulations apply to a given commodity (e.g., Seats) or system (e.g., Braking) in each market. Today this requires hunting across agency websites, internal spreadsheets, and second-hand summaries.

This repository pulls regulation text from official APIs, classifies each record against a controlled taxonomy (commodity / vehicle system / vehicle category), and renders everything into a static web bundle with faceted search.

Current coverage: **726 records** across **21 regions** — 697 from live connectors plus 31 reference stubs for markets without a public source.

| Region | Code | Source connector | Records |
|--------|------|-----------|---------|
| United States | US | eCFR (49 CFR Part 571 FMVSS; 40/47 CFR) | 141 |
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

## Certification knowledge layer (`knowledge/`)

Hand-curated YAML, validated and compiled by `scripts/knowledge.py` during `scripts/build.py`
into `dist/data/markets.json`, `crosswalk.json` and `glossary.json`:

```
knowledge/
├── markets/                 one file per world region (americas, europe, asia_pacific, mea)
│   └── *.yaml               market profiles — see the header of americas.yaml for field semantics
├── crosswalk.yaml           columns (regimes) × topics (requirements) with cited cells
└── glossary.yaml            certification terms
```

Validation is strict — any of these **fail the build**:

- a `records:` id that does not exist in `regulations/` (so links can never silently rot);
- unknown or missing keys, duplicate market codes / topic ids;
- enum violations (`regime`, `drive`, `confidence`, cell `status`, `powertrains`, world-region `group`);
- a `regions:` value not in `taxonomy.yaml`, or a non-http(s) authority URL;
- a crosswalk column pointing at an unknown market, or a glossary term at an unknown market.

**Adding a market:** append an entry to the relevant `knowledge/markets/<region>.yaml`
(`code`, `name`, `group`, `regions`, `drive`, `regime`, `basis`, `un_1958`/`un_1998` — use `null`
when not verified — `authorities`, `accepts`, `marks`, `emissions`, `language`, `process`,
`records`, `confidence`; optional `aliases`, `members`, `watch`, `notes`). Quote any value that
contains a comma inside `{ … }` flow mappings.

**Adding a crosswalk topic:** add an item under `topics:` with an `id`, a declared `group`,
`title`, `description`, `powertrains` (`[all]` or a subset of ICE/HEV/PHEV/BEV/FCEV), optional
`gtr`, and `cells` keyed by column (`cite` required; `records`, `status`, `note` optional). An
absent cell means *not mapped yet*; use `status: none` to state that a market has no requirement.

Update `reviewed:` in `crosswalk.yaml` whenever citations are re-checked.

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
├── knowledge/                       curated markets / crosswalk / glossary (see above)
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
│   ├── knowledge.py                 validates + compiles knowledge/ (called by build.py)
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

**Commodities** (Tier 1/2 supplier perspective): Seats, Glass, Lighting modules, Tires, Brakes, Airbags, Seatbelts, Mirrors, Wheels, Wiring, ECUs, ADAS sensors, Batteries, Electric motors, Fuel system, Exhaust, HVAC, Infotainment, Body structure, Bumpers, Door latches & hinges, Steering column, Suspension, Fuel tanks, Hoses & lines, Connectors, Charging inlet, Power electronics, Horn, Wipers & washers, Pedals, Couplings & towing, Interior trim, Telematics unit

**Systems**: Lighting & signaling, Braking, Steering, Tires & wheels, Crashworthiness, Restraints, Visibility, Emissions, Fuel safety, EMC, EV charging, Battery safety, ADAS, Cybersecurity, Noise, Glazing, HVAC, Vehicle identification, Pedestrian protection, Theft prevention, Tell-tales & controls, On-board diagnostics, Software updates, Emergency call (eCall), Fire safety & flammability, Hazardous substances & recycling, Radio & telecom, Event & data recording, Dimensions & weights

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

The KR connector works without an API key: its public HTML fallback returns the full Korean article text (verified in the 2026-10 re-pull, where it matched the stored English translations). The optional `KR_LAW_API_KEY` for [open.law.go.kr](https://open.law.go.kr) switches to the JSON API, but registration requires Korean identity verification, so most users cannot get one and do not need it.

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
