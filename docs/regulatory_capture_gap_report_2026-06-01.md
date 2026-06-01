# Regulatory Capture Gap Report

Date: 2026-06-01

Workspace: `C:\Users\v0409324\OneDrive - Honda\Documents\0) Reference\Regulatory Repository`

## Fix Status

Update applied 2026-06-01: workbook-derived fallback rows are now governed by `manifests/spreadsheet.yaml` and generated into Markdown by `scripts/gen_stubs.py`. The spreadsheet manifest currently contains 195 records. The ECE workbook gaps for `UN R0`, `UN R28`, `UN R37`, `UN R39`, `UN R45`, `UN R55`, `UN R144`, and composite `UN R163` have been added to `manifests/ece.yaml`, `UN R168` has been corrected to real driving emissions, and the generated build now contains 728 records with 0 errors and 0 warnings.

The remaining sections preserve the original audit findings that motivated the fix.

## Scope

This audit checked whether regulations from the current local sources have been captured into the repository output. The sources checked were:

- Connector manifests in `manifests/*.yaml`
- Generated regulation Markdown in `regulations/*.md`
- Build output evidence in `.build_report.txt` and `dist/index.html`
- Baseline workbook `reference/passenger_vehicle_regulatory_reference_repository_v3_cleaned.xlsx`
- Current UNECE status materials referenced by the ECE source:
  - https://unece.org/transport/road-transport/status-1958-agreement-and-annexed-regulations
  - https://unece.org/sites/default/files/2025-02/ECE-TRANS-WP.29-343-Rev.33.pdf
  - https://unece.org/transport/documents/2025/07/working-documents/ec-united-kingdom-and-oica-proposal-new-series

This is a capture/governance audit, not a legal applicability opinion.

## Executive Findings

1. No current manifest entries are being dropped by the pull/build pipeline. The eight manifest-backed regions have full manifest-to-Markdown coverage:

| Region | Manifest records | Generated matching records | Missing generated records |
|---|---:|---:|---:|
| US | 135 | 135 | 0 |
| EU | 24 | 24 | 0 |
| KR | 79 | 79 | 0 |
| AU | 90 | 90 | 0 |
| JP | 31 | 31 | 0 |
| CA | 53 | 53 | 0 |
| ECE | 77 | 77 | 0 |
| BR | 32 | 32 | 0 |

2. ECE 26 is now captured. Evidence:
   - `manifests/ece.yaml` contains `regulation: 26`
   - `regulations/ece-r26.md` exists
   - `.build_report.txt` contains `OK ece-r26`
   - `dist/index.html` contains `ece-r26`

3. The gap is upstream of build: the manifests are curated lists and do not fully represent the workbook baseline or current UNECE source scope. Anything absent from a manifest is not pulled by `scripts/pull.py`.

4. The baseline workbook has at least 55 rows not represented as a matching Markdown record. Most are framework, agency, horizontal, or market-entry rows rather than individual component regulations. They still matter because they exist in the current workbook source.

5. ECE has the highest-risk misses:
   - Workbook rows missing as ECE Markdown: `UN R0`, `UN R28`, `UN R37`, `UN R39`, `UN R45`, `UN R55`, `UN R144`
   - Composite workbook row partially missed: `UN R163` is listed with `UN R116 / R161 / R162 / R163`, but `ece-r163.md` is absent
   - Current UNECE status materials show newer UN Regulations outside the manifest: `R163`, `R164`, `R165`, `R166`, `R167`, `R169`, `R170`, `R171`, `R172`, `R173`, `R174`, `R175`, `R176`, `R177`, `R178`
   - `manifests/ece.yaml` labels `R168` as AEB pedestrian/cyclist protection, but UNECE materials identify `UN R168` as real driving emissions (RDE)
   - All 77 current ECE Markdown files are placeholder bodies pointing to the UNECE index, not full regulation text

## Missed Workbook Rows

The following workbook rows are not represented by a matching Markdown record under `regulations/`. `UN R28` is included here because the workbook contains `REG-0436` and no `regulations/ece-r28.md` exists.

| Repo ID | Market | Regulation ID | Title | Note |
|---|---|---|---|---|
| REG-0145 | Canada | ECCC SOR/2003-2 | On-Road Vehicle and Engine Emission Regulations | Framework/agency regulation |
| REG-0358 | Canada | Motor Vehicle Safety Regulations (C.R.C., c. 1038) | Motor Vehicle Safety Regulations - Certification, Records, Importation and Defect/Non-compliance Provisions | Umbrella/framework |
| REG-0359 | Canada | Motor Vehicle Tire Safety Regulations (SOR/2013-198) | Motor Vehicle Tire Safety Regulations | Umbrella/framework |
| REG-0360 | Canada | Passenger Automobile and Light Truck Greenhouse Gas Emission Regulations (SOR/2010-201) | Passenger Automobile and Light Truck Greenhouse Gas Emission Regulations | Framework/agency regulation |
| REG-0370 | Australia | Road Vehicle Standards Act 2018 / Road Vehicle Standards Rules 2019 | Road Vehicle Standards - Supply, Type Approval and Compliance Framework | Umbrella/framework |
| REG-0371 | Australia | Register of Approved Vehicles (RAV) | Register of Approved Vehicles Entry Requirements | Framework/admin row |
| REG-0372 | Australia | Australian Road Vehicle Recall Framework | Vehicle Recalls Under Road Vehicle Standards and Consumer Product Safety Framework | Umbrella/framework |
| REG-0434 | Europe / UNECE | UN R0 | International Whole Vehicle Type Approval (IWVTA) | Umbrella/framework |
| REG-0436 | Europe / UNECE | UN R28 | Audible Warning Devices | Missing ECE Markdown |
| REG-0437 | Europe / UNECE | UN R39 | Speedometer Equipment | Missing ECE Markdown |
| REG-0438 | Europe / UNECE | UN R55 | Mechanical Coupling Components | Missing ECE Markdown |
| REG-0444 | Europe / UNECE | UN R144 | Accident Emergency Call Systems | Missing ECE Markdown |
| REG-0451 | United States | 49 CFR Part 575 | Consumer Information / Labels and Ratings | Umbrella row; specific 575 subparts exist |
| REG-0546 | Other / Cross-Market | Directive 2011/65/EU / RoHS | Materials / Electronics - RoHS | Horizontal/supporting |
| REG-0568 | Canada | SOR/2010-90 | Motor Vehicle Restraint Systems and Booster Seats Safety Regulations | Framework/agency regulation |
| REG-0569 | Canada | ISED Radio Equipment Certification / RSS-Gen / ICES | Canada Radiofrequency and EMC Equipment Approval | Framework/admin row |
| REG-0577 | Europe / UNECE | UNECE R37 | Filament Light Sources | Missing ECE Markdown |
| REG-0580 | Europe / UNECE | UNECE R45 | Headlamp Cleaners | Missing ECE Markdown |
| REG-0596 | South Korea | Clean Air Conservation Act / Motor Vehicle Emissions Certification | Korea Motor Vehicle Emissions Certification and Permissible Emission Standards | Framework/agency regulation |
| REG-0597 | South Korea | Noise and Vibration Control Act / Vehicle Noise | Korea Motor Vehicle Noise Authentication and Standards | Framework/agency regulation |
| REG-0598 | South Korea | Radio Waves Act / RRA-KC Conformity Assessment | Korea RF and EMC Conformity Assessment for Radio Equipment | Framework/admin row |
| REG-0599 | South Korea | Act on Resource Circulation of Electrical and Electronic Equipment and Vehicles | Korea Vehicle Resource Circulation / Recycling Requirements | Framework/agency regulation |
| REG-0604 | Australia | New Vehicle Efficiency Standard Act 2024 | New Vehicle Efficiency Standard (NVES) | Framework/agency regulation |
| REG-0605 | Australia | Radiocommunications Equipment (General) Rules 2021 / ACMA | Australia RF Equipment Compliance for In-vehicle Radio Devices | Framework/admin row |
| REG-0610 | Mexico | NOM-194-SE-2021 | Safety devices for new light vehicles - requirements and specifications | Missing market row |
| REG-0612 | Mexico | NOM-163-SEMARNAT-SCFI-2023 | CO2 emissions from new vehicles up to 3,857 kg GVWR | Missing market row |
| REG-0613 | Europe / UNECE | TR CU 018/2011 | Technical Regulation on Safety of Wheeled Vehicles | Missing EAEU row |
| REG-0614 | Europe / UNECE | ERA-GLONASS emergency call requirements | Automatic emergency call equipment requirements linked to EAEU/Russia vehicle approval | Framework/admin row |
| REG-0615 | ASEAN | ASEAN Automotive Products Mutual Recognition Arrangement (APMRA) | ASEAN framework for mutual recognition of automotive product approvals | Umbrella/framework |
| REG-0616 | ASEAN | Thailand TIS / DLT vehicle type approval framework | Thailand national vehicle and component conformity framework | Umbrella/framework |
| REG-0617 | ASEAN | Indonesia SNI / Vehicle Type Approval Framework | Indonesia national vehicle type approval and SNI conformity framework | Umbrella/framework |
| REG-0618 | ASEAN | JPJ Vehicle Type Approval / Malaysia emissions approval | Malaysia vehicle type approval and environmental approval framework | Umbrella/framework |
| REG-0619 | ASEAN | QCVN 09:2024/BGTVT / Circular 48/2024/TT-BGTVT | Vietnam technical and environmental safety requirements for vehicles | Framework/regulatory package |
| REG-0620 | ASEAN | Philippines motor vehicle/component conformity and emissions approval framework | Philippines vehicle and component certification, COC and emissions/environmental framework | Umbrella/framework |
| REG-0622 | South Africa | NRCS Compulsory Specifications / VC Series | South Africa compulsory specifications for motor vehicles and components | Umbrella/framework |
| REG-0623 | South Africa | VC 8056 | Pneumatic tyres for passenger cars and trailers | Missing market row |
| REG-0624 | Argentina / Mercosur | LCM / LCA | Argentina model configuration and environmental configuration licenses | Framework/admin row |
| REG-0627 | Israel | Israel vehicle import/type approval framework | Israel import, registration and standards-recognition framework | Umbrella/framework |
| REG-0628 | New Zealand | Land Transport Rules / Approved Standards | New Zealand vehicle standards and recognized standards framework | Umbrella/framework |
| REG-0629 | New Zealand | Land Transport (Clean Vehicle Standard) Regulations 2022 | New Zealand Clean Car Standard / Clean Vehicle Standard | Framework/agency regulation |
| REG-0630 | Turkey | Turkey motor vehicle type approval framework | Turkey vehicle type approval aligned with EU framework | Umbrella/framework |
| REG-0637 | Europe / UNECE | Directive (EU) 2022/2464 / Directive (EU) 2024/1760 / Regulation (EU) 2023/956 | CSRD, CSDDD and CBAM sustainability/due-diligence overlays | Horizontal/framework |
| REG-0639 | Europe / UNECE | UNECE 1958 Agreement / Schedule 1 CoP principles | UNECE type approval and conformity-of-production framework | Umbrella/framework |
| REG-0641 | Other / Cross-Market | IATF 16949 | Automotive quality management system | Horizontal/supporting |
| REG-0642 | Other / Cross-Market | ISO 9001 | Quality management systems - Requirements | Horizontal/supporting |
| REG-0643 | Other / Cross-Market | ISO 26262 | Road vehicles - Functional safety | Horizontal/supporting |
| REG-0644 | Other / Cross-Market | ISO 21448 | Road vehicles - Safety of the intended functionality | Horizontal/supporting |
| REG-0645 | Other / Cross-Market | ISO/SAE 21434 | Road vehicles - Cybersecurity engineering | Horizontal/supporting |
| REG-0646 | Other / Cross-Market | ISO 24089 | Road vehicles - Software update engineering | Horizontal/supporting |
| REG-0647 | Other / Cross-Market | Automotive SPICE (ASPICE) | Automotive software process assessment model | Horizontal/supporting |
| REG-0648 | Other / Cross-Market | ISO 6469 series | Electrically propelled road vehicles - Safety specifications | Horizontal/supporting |
| REG-0649 | Other / Cross-Market | UN Manual of Tests and Criteria, Section 38.3 | Lithium battery transport tests | Horizontal/supporting |
| REG-0650 | Other / Cross-Market | ISO 22628 | Road vehicles - Recyclability and recoverability calculation method | Horizontal/supporting |
| REG-0651 | Other / Cross-Market | AIAG-VDA FMEA / MSA / SPC / PPAP / APQP | Automotive core quality tools | Horizontal/supporting |
| REG-0652 | Other / Cross-Market | ISO 34502 / ISO/TR 4804 / ISO/PAS 8800 | Automated-driving scenario, safety and AI guidance standards | Horizontal/supporting |

## Additional ECE Regulation-Level Gaps

These do not all correspond to one missing workbook row, but they are missing regulation records when comparing `manifests/ece.yaml` to current UNECE status materials and composite workbook IDs.

| Regulation | Issue |
|---|---|
| UN R163 | Listed in workbook row `REG-0061` as part of `UNECE R116 / R161 / R162 / R163`, but `ece-r163.md` is absent |
| UN R164 | Not in `manifests/ece.yaml` |
| UN R165 | Not in `manifests/ece.yaml` |
| UN R166 | Not in `manifests/ece.yaml` |
| UN R167 | Not in `manifests/ece.yaml` |
| UN R169 | Not in `manifests/ece.yaml` |
| UN R170 | Not in `manifests/ece.yaml` |
| UN R171 | Not in `manifests/ece.yaml` |
| UN R172 | Not in `manifests/ece.yaml` |
| UN R173 | Not in `manifests/ece.yaml` |
| UN R174 | Not in `manifests/ece.yaml` |
| UN R175 | Not in `manifests/ece.yaml` |
| UN R176 | Not in `manifests/ece.yaml` |
| UN R177 | Not in `manifests/ece.yaml` |
| UN R178 | Not in `manifests/ece.yaml` |
| UN R168 | Present, but manifest title appears wrong; current UNECE material identifies R168 with real driving emissions (RDE), not AEB pedestrian/cyclist protection |

## Present But Not Manifest-Governed

These are already built into `dist/index.html`, but they are not reproducible through the current manifest pull pipeline.

| Group | Count | Notes |
|---|---:|---|
| CN | 49 | Spreadsheet-derived stubs; no `manifests/cn.yaml` |
| GCC | 63 | Spreadsheet-derived stubs; no `manifests/gcc.yaml` |
| IN | 3 | Spreadsheet-derived stubs; no `manifests/in.yaml` |
| TW | 1 | Spreadsheet-derived stub; no `manifests/tw.yaml` |
| US stubs | 6 | `source_api: spreadsheet`, not represented in `manifests/us.yaml` |
| JP SRRV stubs | 25 | `source_api: spreadsheet`, not represented in `manifests/jp.yaml` |
| AU extras | 4 | Existing official-source Markdown not represented in `manifests/au.yaml` |

AU extras not represented in `manifests/au.yaml`:

- `au-f2005l03996.md` - ADR 42/04 General Safety Requirements
- `au-f2006l02663.md` - ADR 14/02 Rear Vision Mirrors
- `au-f2011l02016.md` - ADR 79/04 Emission Control for Light Vehicles
- `au-f2012l00703.md` - ADR 34/02 Child Restraint Anchorages

## Likely Root Cause

The build path is working, but the source governance model is incomplete.

- `scripts/pull.py` only pulls entries declared in the region manifests.
- `connectors/unece.py` iterates `manifest.get("records", [])`; it does not discover all current UNECE regulations.
- The repository mixes manifest-pulled records with workbook-derived spreadsheet stubs.
- Stub regions are present in output but have no manifest source of truth.
- `README.md` is stale: it still describes 98 records across 6 regions and says Brazil/GCC/China are deferred, while the current build has 672 records across 12 regions.

## Recommended Next Steps

1. Treat the workbook as a source manifest candidate and add a reconciliation test that fails when a workbook `Regulation ID` has no corresponding Markdown record or explicit exclusion.
2. Add missing ECE manifest records first: `R0`, `R28`, `R37`, `R39`, `R45`, `R55`, `R144`, `R163`, and then review `R164` through `R178`.
3. Correct the `R168` title in `manifests/ece.yaml`.
4. Decide whether framework/horizontal rows should become Markdown stubs or be explicitly excluded with rationale.
5. Create manifest/governance files for stub-only regions: CN, GCC, IN, TW, and the JP/US spreadsheet stubs.
6. Update `README.md` after the source-of-truth decision so record/region counts and deferred-region notes match the current repository.
