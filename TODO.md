# Regulatory Repository — TODO

## General TODOs

- [ ] Translate Korean-language content (KMVSS) to English — all regulatory text must be in English for this tool to function correctly

---

## Manifest Expansion Follow-ups (from 99 → 329 entry expansion)

### EU — UNECE/UN Regulations (~67 entries missing)
The EU manifest (`manifests/eu.yaml`) covers EU Regulations and Directives via EUR-Lex CELEX
numbers, but the spreadsheet lists 91 EU/UNECE entries. The ~67 UN Regulations (R10–R168) are
adopted by the EU via OJ decisions and have non-standard CELEX IDs (prefix `4`, e.g.
`42019X0224(01)`). These require per-regulation lookup.

- [ ] Research CELEX IDs for the following UNECE/UN Regulations adopted by EU and add to `manifests/eu.yaml`:
  - UNECE R3, R4, R6, R7, R10, R11, R12, R13-H, R14, R16, R17, R19, R21, R23, R25, R27
  - UNECE R30, R34, R37, R38, R39, R43, R44, R45, R46, R48, R51, R55, R64, R77, R79
  - UNECE R83, R85, R87, R91, R94, R95, R98, R99, R100, R101, R112, R114, R116, R117
  - UNECE R119, R121, R123, R125, R127, R128, R129, R135, R137, R138, R139, R140, R141
  - UNECE R142, R144, R145, R148, R149, R150, R152, R153, R154, R155, R156, R157, R158
  - UNECE R159, R160, R161, R162, R163, R168
- [ ] Alternatively, build a dedicated UNECE connector (`connectors/unece.py`) that fetches
  directly from `https://unece.org/transport/vehicle-regulations-wp29` — this avoids the
  EUR-Lex CELEX lookup entirely and gives first-class UNECE coverage (see *Regions Not Yet
  Implemented → ECE* section below)

### AU — Remaining ADR Instrument IDs (~51 entries missing)
The AU manifest (`manifests/au.yaml`) has 13 verified instrument IDs. The spreadsheet lists
64 ADRs, but the Federal Register of Legislation API (`api.prod.legislation.gov.au`) was
inaccessible from the build environment (403 Forbidden). Once network access is available:

- [ ] Write `scripts/lookup_au_instruments.py` — queries
  `https://api.prod.legislation.gov.au/v1/Titles?text=Design+Rule` to retrieve all ADR
  instrument IDs in bulk, then patches `manifests/au.yaml` with the results
- [ ] Alternatively, look up instrument IDs manually from
  `https://www.legislation.gov.au/Browse/ByTitle/LegislativeInstruments/InForce/0/0/Principal`
  filtered to "Design Rule" and add entries for:
  ADR 1, 2, 5, 6, 10, 18, 21, 22, 25, 29, 31, 42 (newer version), 43, 46, 47, 48, 49,
  50, 52, 60, 61, 69, 72, 73, 81, 82, 83, 85, 88, 89, 90, 92, 93, 94, 95, 98, 107, 108,
  109, 110, 111, 112, 113 and the Road Vehicle Standards framework instruments

### US — EPA Emissions Regulations (excluded from current pull)
The eCFR connector is hardcoded to Title 49. The spreadsheet includes 40 CFR regulations
(EPA) which were intentionally excluded because the connector can't reach them.

- [ ] Extend `connectors/ecfr.py` to accept an optional `title` field (default `49`) so
  40 CFR entries can be pulled alongside 49 CFR entries
- [ ] Add to `manifests/us.yaml` once connector supports it:
  - `{ title: 40, part: 86 }` — Light-duty vehicle emission standards (Tier 3)
  - `{ title: 40, part: 86, section: "1811-27" }` — Tier 4 criteria exhaust emission standards
  - `{ title: 40, part: 600 }` — Fuel economy and GHG exhaust emissions
- [ ] FCC entry: `{ title: 47, part: 15 }` — Radio Frequency Devices (Part 15) — same fix needed

---

## Covered

| Framework | Region | Connector | Source API |
|-----------|--------|-----------|------------|
| FMVSS | United States | `connectors/ecfr.py` | eCFR (ecfr.gov) |
| CMVSS | Canada | `connectors/justice_ca.py` | Justice Laws XML (laws-lois.justice.gc.ca) |
| KMVSS | Korea | `connectors/law_go_kr.py` | law.go.kr public HTML (API key optional) |
| ECE/EU | European Union | `connectors/eurlex.py` | EUR-Lex HTML (eur-lex.europa.eu) |
| JVSR | Japan | `connectors/egov_jp.py` | e-Gov Law API v1 (laws.e-gov.go.jp) |
| ADR | Australia | `connectors/au_legislation.py` | Federal Register of Legislation API (legislation.gov.au) |

---

## Gap Analysis — vs. `reference/passenger_vehicle_regulatory_reference_repository_v3_cleaned.xlsx`

The reference spreadsheet contains **652 regulations** across 19 market families.
Counts below are from the *Regulation Index* sheet.

### Fully covered (connector exists)

| Market Family | Standard Body | Regs in spreadsheet | Connector |
|---|---|---|---|
| United States (FMVSS) | FMVSS / United States | 132 | `connectors/ecfr.py` |
| Canada | CMVSS / Canada | 51 | `connectors/justice_ca.py` |
| South Korea | KMVSS / South Korea | 69 | `connectors/law_go_kr.py` |
| Europe / UNECE | ECE / UNECE and EU | 94 | `connectors/eurlex.py` |
| Japan | Japan MLIT / Safety Regulations | 52 | `connectors/egov_jp.py` |
| Australia | ADR / Australia | 64 | `connectors/au_legislation.py` |

**Subtotal covered: ~462 of 652 regulations (~71%)**

---

### Partial gaps within covered regions

These regulations fall under a covered Market Family but are **not reachable** by the existing connector:

| Regulation ID | Standard Body | Title | Action |
|---|---|---|---|
| 47 CFR Part 15 | United States / FCC | FCC Part 15 — Radio Frequency Devices | Add to `manifests/us.yaml`; eCFR connector can pull this |
| 40 CFR Part 85 | US EPA | Control of Air Pollution from Mobile Sources | New manifest entry; eCFR connector can pull this |
| 40 CFR Part 1066 | US EPA | Vehicle-Testing Procedures | New manifest entry; eCFR connector can pull this |
| 40 CFR Part 82 | FMVSS / United States / EPA | SNAP Program / Ozone Protection | New manifest entry; eCFR connector can pull this |
| Title 13 CCR 1961.4+ | US / California CARB | Advanced Clean Cars II / LEV IV / ZEV | California Code of Regulations — separate source, no connector |
| California Prop 65 | United States / California | Toxic enforcement warnings | HTML source; no connector |
| MA Ch. 93K / Acts 2020 | United States / Massachusetts | Right-to-repair telematics | State law; no connector |
| Dodd-Frank §1502 / EU 2017/821 | United States / EU / Global supply chain | Conflict minerals due-diligence | Cross-jurisdictional; no connector |
| TR CU 018/2011 | EAEU / Eurasian Economic Commission | Safety of Wheeled Vehicles (Russia/EAEU) | No connector |
| ERA-GLONASS requirements | EAEU / Russia / Customs Union | Emergency call requirements | No connector |
| EU 2022/2464 / CBAM | ECE / UNECE and EU / Global supply chain | CSRD / CSDDD / CBAM sustainability | Cross-cutting; no connector |
| UNECE 1958 Agreement | UNECE / 1958 Agreement | Type approval and CoP framework | No connector |

---

### Fully uncovered regions (no connector, ~190 regulations)

| Market Family | Standard Body | Count | Notes |
|---|---|---|---|
| GCC / Middle East | GCC / GSO | 61 | See implementation note below |
| GCC / Middle East | GCC member overlay / Saudi Arabia SASO | 1 | |
| GCC / Middle East | GCC member overlay / UAE MOIAT | 1 | |
| China | GB / China | 49 | See implementation note below |
| Brazil | CONTRAN / Brazil | 32 | See implementation note below |
| Brazil | CONTRAN / Brazil / MOVER | 1 | |
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

### ECE — UNECE World Forum (UN Regulations)
- Standards body: United Nations Economic Commission for Europe
- Source: https://unece.org/transport/vehicle-regulations-wp29
- Public access: Full regulation texts available as HTML/PDF on UNECE site
- Notes: EU connector pulls EU regulations that *cite* UN Rs, but a dedicated connector
  targeting UNECE directly (e.g., UN R48, UN R13, UN R94, UN R100) would give proper
  first-class ECE coverage independent of the EU implementation

### CCC — China Compulsory Certification (GB Standards)
- Standards body: CNCA / SAC
- Relevant standards: GB 7258 (motor vehicles), GB/T series
- Public access: https://openstd.samr.gov.cn — free for some GB standards; many require purchase
- Notes: Machine-readable API not publicly known; HTML scraping of samr.gov.cn may be needed

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

### INMETRO — Brazil (CONTRAN / DENATRAN)
- Standards body: DENATRAN / SENATRAN; INMETRO for certification
- Relevant standards: CONTRAN resolutions (e.g., Resolução 792 on tires, 886 on lighting)
- Public access: https://www.gov.br/senatran or https://www.lexml.gov.br
- Notes: LexML Brazil provides structured legal XML; CONTRAN resolutions are accessible
  at https://www.denatran.gov.br/resolucoes

### Radio Wave / EMC
- This is a cross-cutting topic, not a single regional framework
- Key regulations by region:
  - US: FCC Part 15 (47 CFR §15) — https://www.ecfr.gov (same connector as FMVSS)
  - EU: Directive 2014/30/EU (EMC) + UN R10 (vehicle-level EMC)
  - Japan: Radio Law (電波法) via e-Gov — same connector as JVSR
  - KR: Radio Waves Act (전파법) — same connector as KMVSS
- Notes: US FCC entries can be added to `manifests/us.yaml` using the existing eCFR
  connector (47 CFR §15); no new connector needed for US EMC
