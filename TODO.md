# Regulatory Repository — TODO

## General TODOs

- [x] Translate Korean-language content (KMVSS) to English — 78 of 79 articles translated (art18-5 skipped: failed connector pull)

---

## UI Redesign — Region → Series Label Mapping

For the Home "Browse by Market" tiles, formatted as `Series (Region)` with long region names.
Mapping to be stored in `taxonomy.yaml` so it is editable without code changes.

Confirmed from existing connectors/manifests:

| Region | Series | Long name |
|--------|--------|-----------|
| US | FMVSS | United States |
| CA | CMVSS | Canada |
| KR | KMVSS | South Korea |
| AU | ADR | Australia |
| ECE | UN R | UNECE |
| JP | JVSR | Japan |
| BR | CONTRAN | Brazil |
| CN | GB | China |
| GCC | GSO | Gulf Cooperation Council |
| IN | AIS | India |

- [x] **DONE — EU series label.** Set to `EU` (covers both EU Regulations and Directives from EUR-Lex).
- [x] **DONE — Long-tail region series labels.** Filled the grounded ones from each region's actual
  citations: MX→`NOM`, EAEU→`TR CU`, ZA→`VC`, AR→`LCM`, NZ→`Land Transport Rule`. Left TW, ASEAN, IL,
  TR, OTHER blank (heterogeneous member states / framework-only citations / cross-cutting standards —
  no single grounded series; the market tile falls back to the region name).

---

## Phase 1 Build Rearchitecture — follow-ups (from final review)

- [x] **DONE — Auto-tag `custom_id` length.** `auto_tag.py` skipped 26 records whose `id` exceeded
  the Batch API's 64-char `custom_id` limit. Added `custom_id_for()` (prefix + sha1 suffix) mapped
  back on import; the final 26 are now classified. Corpus is **728/728 llm-tagged**.
- [ ] **`effective_date` / `last_amended` dropped.** Allowed in frontmatter (`OPTIONAL_KEYS`) but
  `build_record` never copies them into the record dict, so they never reach the UI. Add them to
  the emitted record if/when needed (pre-existing, low priority).
- [ ] **Validate `source_url` scheme at build.** `source_url` is rendered as an `<a href>` in the
  client but only `body_html` links go through bleach's protocol allow-list. Add a build-time check
  that `source_url` starts with `http://`/`https://` to fully close a `javascript:` link vector
  (low risk: source_urls come from controlled frontmatter).

---

## Phase 3 Workspace — polish (non-blocking, from final review)

- [x] **DONE — `avail=none` removable chip.** When all three Availability boxes are unchecked,
  `renderChips` now adds a "Show: nothing" chip (type `avail-none`); removing it restores the default
  (full text only). Round-trips through `?avail=none`. Browser-verified.
- [x] **DONE — Remove dead CSS.** Removed `.view-bar`, `.view-bar-label`, `.avail-option`,
  `.avail-option input`, the responsive `.view-bar` override, and `.reg-card.is-expanded` from
  `assets/styles.css` (all orphaned). Confirmed zero remaining references; page renders unchanged.

---

## UI Redesign — Data Coverage Tracks (enablers for the new front door)

The redesign is coverage-aware and works at any fill level, but these data tracks make it shine:

- [x] **DONE — Tag the backlog.** All **728/728** records are now `llm-tagged` via
  `scripts/auto_tag.py` (Batch API). The "Browse by part/system" directory is fully populated.
- [x] **DONE — Populate `un_equivalent` / `related`.** Two provenance-separated fields:
  `un_equivalent` (grounded, extracted from text by `scripts/extract_un_equivalent.py` — 74 records)
  and `un_equivalent_ai` (LLM-inferred cross-market links via `scripts/infer_un_equivalent.py`
  Batch API — 462 records, e.g. FMVSS 208 → UN R94). `related` is **derived in `build.py`** from
  grounded shared-UN clusters (capped at 12); `un_index` (UN R → ECE id) is emitted to
  `taxonomy.json`. Reader renders grounded as links and AI as a distinct **"AI-suggested — verify
  against source"** block (also linked). AI values are kept out of the search corpus so the verify
  caveat is never bypassed. Unlocks journey C ("find the equivalent in another market").

---

## Manifest Expansion Follow-ups (from 99 → 329 entry expansion)

### EU — UNECE/UN Regulations (~67 entries missing)
The EU manifest (`manifests/eu.yaml`) covers EU Regulations and Directives via EUR-Lex CELEX
numbers, but the spreadsheet lists 91 EU/UNECE entries. The ~67 UN Regulations (R10–R168) are
adopted by the EU via OJ decisions and have non-standard CELEX IDs (prefix `4`, e.g.
`42019X0224(01)`). These require per-regulation lookup.

- [x] **DONE** — Built dedicated UNECE connector (`connectors/unece.py`) pulling directly from
  `https://unece.org/transport/vehicle-regulations-wp29`. All major UN Regulations are now in
  `manifests/ece.yaml` under the `ECE` region. This supersedes the EUR-Lex CELEX approach.
- [ ] Optional: Research CELEX IDs for UNECE regulations adopted by EU if EUR-Lex versions are
  needed in addition to the UNECE originals (lower priority given ECE coverage exists).

### AU — Remaining ADR Instrument IDs
- [x] **DONE** — `manifests/au.yaml` expanded from 13 to **90 entries** covering all in-force
  ADRs found via the Federal Register of Legislation OData API. The API uses OData filter syntax
  (`$filter=contains(name,'Design Rule')`) — `scripts/lookup_au_instruments.py` has been updated
  accordingly. ADRs 1–114 (where in-force versions exist) are now included. 94 `.md` files pulled.

### US — EPA Emissions Regulations
- [x] **DONE** — `connectors/ecfr.py` supports an optional `title` field (default `49`).
  `manifests/us.yaml` includes and all entries have been pulled:
  - `{ title: 40, part: 82 }` — Protection of stratospheric ozone (SNAP / refrigerant requirements)
  - `{ title: 40, part: 85 }` — Control of air pollution from mobile sources — emission controls
  - `{ title: 40, part: 86 }` — Control of air pollution from mobile sources (Tier 3)
  - `{ title: 40, part: 600 }` — Fuel economy and GHG exhaust emissions
  - `{ title: 40, part: 1066 }` — Vehicle-testing procedures (emission and fuel economy lab testing)
  - `{ title: 47, part: 15 }` — FCC Radio Frequency Devices (Part 15)

### Brazil — CONTRAN / DENATRAN Resolutions
- [x] **DONE** — Built `connectors/brazil.py` pulling from LexML Brazil. `manifests/br.yaml`
  covers 32 CONTRAN resolutions. 32 `.md` files pulled.

---

## Covered

| Framework | Region | Connector | Source API |
|-----------|--------|-----------|------------|
| FMVSS | United States | `connectors/ecfr.py` | eCFR (ecfr.gov) |
| CMVSS | Canada | `connectors/justice_ca.py` | Justice Laws XML (laws-lois.justice.gc.ca) |
| KMVSS | Korea | `connectors/law_go_kr.py` | law.go.kr public HTML (API key optional) |
| ECE/EU | European Union | `connectors/eurlex.py` | EUR-Lex HTML (eur-lex.europa.eu) |
| UN Regulations | ECE/UNECE | `connectors/unece.py` | UNECE WP.29 (unece.org) |
| JVSR | Japan | `connectors/egov_jp.py` | e-Gov Law API v1 (laws.e-gov.go.jp) |
| ADR | Australia | `connectors/au_legislation.py` | Federal Register of Legislation API (legislation.gov.au) |
| CONTRAN | Brazil | `connectors/brazil.py` | LexML Brazil (lexml.gov.br) |

---

## Gap Analysis — vs. `reference/passenger_vehicle_regulatory_reference_repository_v3_cleaned.xlsx`

The reference spreadsheet contains **652 regulations** across 19 market families.
The repository currently contains **671 regulations** across 12 markets (dist/index.html).
Counts below are from the *Regulation Index* sheet.

### Fully covered (connector exists)

| Market Family | Standard Body | Regs in spreadsheet | Connector |
|---|---|---|---|
| United States (FMVSS) | FMVSS / United States | 132 | `connectors/ecfr.py` |
| Canada | CMVSS / Canada | 51 | `connectors/justice_ca.py` |
| South Korea | KMVSS / South Korea | 69 | `connectors/law_go_kr.py` |
| Europe / UNECE | ECE / UNECE and EU | 94 | `connectors/eurlex.py` + `connectors/unece.py` |
| Japan | Japan MLIT / Safety Regulations | 52 | `connectors/egov_jp.py` |
| Australia | ADR / Australia | 64 | `connectors/au_legislation.py` |
| Brazil | CONTRAN / Brazil | 32 | `connectors/brazil.py` |

**Subtotal covered: ~494 of 652 regulations (~76%)**

---

### Partial gaps within covered regions

These regulations fall under a covered Market Family but are **not reachable** by the existing connector:

| Regulation ID | Standard Body | Title | Action |
|---|---|---|---|
| Title 13 CCR 1961.4+ | US / California CARB | Advanced Clean Cars II / LEV IV / ZEV | California Code of Regulations — separate source, no connector |
| California Prop 65 | United States / California | Toxic enforcement warnings | HTML source; no connector |
| MA Ch. 93K / Acts 2020 | United States / Massachusetts | Right-to-repair telematics | State law; no connector |
| Dodd-Frank §1502 / EU 2017/821 | United States / EU / Global supply chain | Conflict minerals due-diligence | Cross-jurisdictional; no connector |
| TR CU 018/2011 | EAEU / Eurasian Economic Commission | Safety of Wheeled Vehicles (Russia/EAEU) | No connector |
| ERA-GLONASS requirements | EAEU / Russia / Customs Union | Emergency call requirements | No connector |
| EU 2022/2464 / CBAM | ECE / UNECE and EU / Global supply chain | CSRD / CSDDD / CBAM sustainability | Cross-cutting; no connector |
| UNECE 1958 Agreement | UNECE / 1958 Agreement | Type approval and CoP framework | No connector |

---

### Fully uncovered regions (no connector, ~158 regulations)

| Market Family | Standard Body | Count | Notes |
|---|---|---|---|
| GCC / Middle East | GCC / GSO | 61 | See implementation note below |
| GCC / Middle East | GCC member overlay / Saudi Arabia SASO | 1 | |
| GCC / Middle East | GCC member overlay / UAE MOIAT | 1 | |
| China | GB / China | 49 | See implementation note below |
| ASEAN | Vietnam / VR / BGTVT | 1 | See VSTD note below |
| ASEAN | Thailand / TISI / DLT | 1 | |
| ASEAN | Malaysia / JPJ / DOE | 1 | |
| ASEAN | Philippines / LTO / DTI-BPS / DENR-EMB | 1 | |
| ASEAN | Indonesia / Ministry of Industry / Ministry of Transportation | 1 | |
| ASEAN | ASEAN / Member State Authorities | 1 | |
| India | India / MoRTH / ARAI | 1 | See AIS note below |
| India | India / MoRTH / ARAI / BIS | 1 | |
| India | India / MoRTH / CPCB / BEE | 1 | |
| Mexico | Mexico / Secretaria de Economia / SICT | 1 | |
| Mexico | Mexico / SEMARNAT / Secretaria de Economia | 1 | |
| New Zealand | New Zealand / Waka Kotahi NZTA | 2 | |
| South Africa | South Africa / NRCS / SABS | 1 | |
| South Africa | South Africa / NRCS | 1 | |
| Argentina / Mercosur | Argentina / INTI / Transport Authorities | 1 | |
| Taiwan | Taiwan / VSCC / MOTC | 1 | |
| Israel | Israel / Ministry of Transport and Road Safety | 1 | |
| Turkey | Turkey / Ministry of Industry and Technology | 1 | |

### Cross-market / Supporting Standards (16 regulations — no connector planned)

These are horizontal standards (ISO 26262, UN R155 cybersecurity, SOTIF, etc.) that are
referenced across regions rather than belonging to a single jurisdiction. No standalone
connector is planned; they should be tracked as cross-references in regional manifests.

| Standard Body | Count |
|---|---|
| Supporting Standards (Functional Safety, Cybersecurity, SOTIF, AV, EV, Software, Quality, Recyclability, Dangerous Goods) | 13 |
| Materials / Recycling Horizontal | 3 |

---

## Regions Not Yet Implemented

Each item below requires a new manifest (`manifests/<region>.yaml`), a connector
(`connectors/<name>.py`), and registration in `scripts/pull.py`.

---

### GCC — Gulf Cooperation Council (GSO)
- [x] **DONE (conservative) — `connectors/gulf.py` + `manifests/gcc.yaml`.** Verifies the public GSO
  master *Technical Regulations for Motor Vehicles* PDF is live, then repoints 58 GSO records'
  `source_url` to it (fixing the dead `wp-content` links) with a framework-reference body and
  `source_api: gso`, preserving the API-2 tags + `un_equivalent`/`un_equivalent_ai` (verified zero
  drops). 5 non-GSO member-state/third-party records (SASO, MOIAT, UAE.S, TÜV) are deliberately
  left untouched. Full text NOT captured (sold); per-standard title parsing intentionally avoided
  (the master PDF's table is column-wise / unreliable). Spec/plan: `docs/superpowers/{specs,plans}/2026-06-05-gcc-gso-connector*`.
- Standards body: Gulf Standardization Organization (GSO). GCC members largely adopt UN/ECE by reference.

### CCC — China Compulsory Certification (GB Standards)
- [x] **DONE — `connectors/china.py` + `manifests/cn.yaml` (47 records).** Metadata enrichment from
  `openstd.samr.gov.cn`: resolves each GB number → `hcno` → `newGbInfo` detail page, extracting the
  official CN/EN title, in-force/superseded status, implementation date (frontmatter `effective_date`,
  not yet surfaced in the UI), the optional adopted-standard cross-reference, and a stable permalink.
  Frontmatter-preserving merge keeps the LLM tags and `un_equivalent`/`un_equivalent_ai` from API-2
  (verified zero drops). Full text NOT captured (image-tile viewer / paywalled). All 47 resolved on
  the portal; 0 stub fallbacks. Spec/plan: `docs/superpowers/{specs,plans}/2026-06-04-china-gb-connector*`.
- Standards body: CNCA / SAC. Public access: https://openstd.samr.gov.cn (free metadata; full text image-based).

### VSTD — Vietnam (QCVN Standards)
- Standards body: Vietnam Register (VR) / Ministry of Transport
- Relevant standards: QCVN 09 (emissions), QCVN 30 (braking), QCVN 35 (lighting), etc.
- Public access: https://vbpl.vn or https://vanbanphapluat.co
- Notes: Official XML/JSON API not available; HTML scraping required; Vietnamese-language only

### AIS — India (Automotive Industry Standard)
- [x] **DONE (thin) — `connectors/india.py` + `manifests/in.yaml` (3 records).** Network-free: rewrites
  the stale `morth.nic.in` → `morth.gov.in` domain, sets `source_api: ais`, preserves the curated
  body + API-2 tags/cross-refs. The 3 records are framework aggregates; no full text (PDFs moved /
  morth.gov.in times out from this env). Spec/plan: `docs/superpowers/{specs,plans}/2026-06-05-india-ais-connector*`.
- Standards body: ARAI / MoRTH. CMVR text at https://legislative.gov.in.

### Connector regression (found + fixed 2026-06-05)
- [x] **DONE — Preserve curated bodies in metadata-enrichment connectors.** The china/gcc connectors
  initially overwrote rich curated workbook bodies with generated stubs (105 records regressed).
  Fixed: china/gcc/india now preserve the existing body (generated body = fallback only); restored
  the 105 bodies from the API-2 baseline; `effective_date` now surfaced in build + reader. Full-text
  connectors (ecfr/brazil/justice_ca/egov_jp/eurlex/unece/au) correctly still overwrite bodies.

### Radio Wave / EMC
- This is a cross-cutting topic, not a single regional framework
- Key regulations by region:
  - US: FCC Part 15 (47 CFR §15) — ✅ pulled via `connectors/ecfr.py`
  - EU: Directive 2014/30/EU (EMC) + UN R10 (vehicle-level EMC)
  - Japan: Radio Law (電波法) via e-Gov — same connector as JVSR
  - KR: Radio Waves Act (전파법) — same connector as KMVSS
- Notes: US FCC entries already covered; EU/JP/KR EMC entries can be added to existing manifests
