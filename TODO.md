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

- [ ] **EU series label — DECIDE.** EUR-Lex pulls a mix of EU Regulations and Directives; no single
  acronym. Candidate labels: `EU` / `EC` / `EU Reg`. Pick one.
- [ ] **Long-tail region series labels — TBD.** Provide `Series (Region)` for: OTHER, ASEAN, ZA
  (South Africa), NZ (New Zealand), MX (Mexico), EAEU (Eurasian Economic Union), TW (Taiwan),
  TR (Türkiye), IL (Israel), AR (Argentina). Many are stubs today; label as the standards body
  where known (e.g. ZA → NRCS, IN already AIS).

---

## UI Redesign — Data Coverage Tracks (enablers for the new front door)

The redesign is coverage-aware and works at any fill level, but these data tracks make it shine:

- [ ] **Tag the backlog.** 630 of 728 records are `tagging_status: untagged` (only 98 classified
  by commodity/system). Run the backlog through `scripts/auto_tag.py` so the "Browse by part/system"
  directory is well-populated. Parallel track — gets its own spec/plan. (Path 1 of the agreed
  "Path 1 + Path 2 together" approach.)
- [ ] **Populate `un_equivalent` / `related`.** Currently EMPTY across all 728 records, so the
  reading pane's "Equivalents & Related" panel renders only when data exists. Building cross-market
  equivalence mappings (e.g. FMVSS 208 ↔ UN R94 ↔ CMVSS 208) would unlock journey C ("find the
  equivalent in another market"). Schema + validation already exist in `build.py`. Future data track.

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
- Standards body: Gulf Standards Organization (GSO)
- Relevant standard: GSSO Technical Regulation for Motor Vehicles
- Public access: https://www.gso.org.sa — limited free access; some standards require purchase
- Notes: GCC member states (SA, AE, KW, QA, BH, OM) largely adopt UN/ECE regulations by reference; a thin connector pointing to GSO Circular references may be feasible
- Current state: 63 stub `.md` files exist in `regulations/`

### CCC — China Compulsory Certification (GB Standards)
- Standards body: CNCA / SAC
- Relevant standards: GB 7258 (motor vehicles), GB/T series
- Public access: https://openstd.samr.gov.cn — free for some GB standards; many require purchase
- Notes: Machine-readable API not publicly known; HTML scraping of samr.gov.cn may be needed
- Current state: 49 stub `.md` files exist in `regulations/`

### VSTD — Vietnam (QCVN Standards)
- Standards body: Vietnam Register (VR) / Ministry of Transport
- Relevant standards: QCVN 09 (emissions), QCVN 30 (braking), QCVN 35 (lighting), etc.
- Public access: https://vbpl.vn or https://vanbanphapluat.co
- Notes: Official XML/JSON API not available; HTML scraping required; Vietnamese-language only

### AIS — India (Automotive Industry Standard)
- Standards body: ARAI / Ministry of Road Transport and Highways
- Relevant standards: AIS-001 through AIS-153 series; CMVR (Central Motor Vehicles Rules)
- Public access: https://morth.nic.in; https://www.araiindia.com
- Notes: No public machine-readable API; PDFs available for purchase; CMVR text available
  at https://legislative.gov.in
- Current state: 3 stub `.md` files exist in `regulations/`

### Radio Wave / EMC
- This is a cross-cutting topic, not a single regional framework
- Key regulations by region:
  - US: FCC Part 15 (47 CFR §15) — ✅ pulled via `connectors/ecfr.py`
  - EU: Directive 2014/30/EU (EMC) + UN R10 (vehicle-level EMC)
  - Japan: Radio Law (電波法) via e-Gov — same connector as JVSR
  - KR: Radio Waves Act (전파법) — same connector as KMVSS
- Notes: US FCC entries already covered; EU/JP/KR EMC entries can be added to existing manifests
