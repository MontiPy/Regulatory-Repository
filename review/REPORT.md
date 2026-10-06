# Content & accuracy review — 728 regulation records + knowledge layer

**Run:** 2026-10-06 · **Method:** 47 Sonnet reviewer agents (one shard each, fixed item lists, shared
[brief](REVIEWER_BRIEF.md)) orchestrated by Opus; deterministic pre-checks
([precheck.json](precheck.json)); orchestrator re-verification of every high-severity external claim it
could check ([ADJUDICATION.md](ADJUDICATION.md), [high_decisions.json](high_decisions.json)).
**Nothing in `regulations/` or `knowledge/` has been changed by this review.**

**Limits:** government websites were blocked from the review environment. Reviewers had web *search*
(snippets) but could not open primary sources, so external facts are confirmed against secondary
sources and the "unverifiable" verdict was used where evidence was missing. Many UN-equivalent
judgements rest on reviewer domain knowledge (marked medium/low confidence in the findings).

## Coverage
- **47/47 shards complete, 0 coverage gaps** — every record (728), market profile (48), crosswalk
  topic (69) and glossary term was reviewed exactly once.
- **929 findings** after collapsing the per-record "no regulation text" finding:
  **85 high · 346 medium · 498 low**.

| Area | High / Medium / Low |
|---|---|
| Regulation records | 64 / 289 / 409 |
| Market profiles | 9 / 27 / 32 |
| Crosswalk | 12 / 29 / 53 |
| Glossary | 0 / 1 / 4 |

## Adjudication of high-severity findings (85)
{'ACCEPT': 77, 'REJECT': 2, 'HOLD': 5, 'ACCEPT (modified)': 1}

Spot-checking showed the reviewers to be reliable: of 13 external claims the orchestrator re-checked by
search, 11 were confirmed, 1 confirmed with a correction (Canada EVAS repeal is still a *draft*), and
1 rejected (GB 11551-2014 is the full-width test — the reviewer had it backwards).

## Systemic problems (fix these first — they explain most findings)

1. **387 of 728 records contain no regulation text.** UNECE (all), Australia (page
   navigation/TOC only), Korea and Brazil (link-only), China/GCC/India and every workbook record
   (AI-written template text). The UI's "Full text" availability filter only excludes
   `source_api: spreadsheet`, so most of these are shown as **full text**. → Fix the availability
   classification (detect thin/template bodies) and label them "Summary only — see official source".
2. **AI-suggested UN equivalents are unreliable (214 findings).** Recurrent
   wrong mappings: wipers→R45 (headlamp cleaners), hood latch→R11 (door latches), accelerator→R161
   (anti-theft), LDW/ELKS→R157 (ALKS), CNG/LPG→R34/R153, hydrogen→R100, ESC heavy→R140,
   AVAS→R159. Even grounded `un_equivalent` has 34 findings (e.g. GSO 13H→R13
   instead of R13-H, GB 14166→R14 instead of R16, GB 11551→R94 instead of R137). → Hide
   `un_equivalent_ai` in the UI until regenerated with a stricter prompt + validation, and correct the
   grounded ones listed here.
3. **Records bound to the wrong instrument or filled from the wrong template.** Brazil CONTRAN
   numbers (37, 215, 498, 764, 827, 924), Japan `jp-srrv-*` category templates (accelerator control
   and horns carry fuel/EV text), GCC GSO-ECE 43/46/125 (lighting boilerplate), China GB 34660 (EMC
   described as cybersecurity), GB 13057 (bus seats described as car seats), KR resource-circulation
   (crash-safety text), UNECE R149/R153/R161 titles. These also propagated into crosswalk cells.
4. **Stale status (41 findings).** Repealed/superseded shown as in-force (EU 78/2009,
   661/2009, 2006/66/EC; ADR 00/00 Amdt 6, ADR 28/01; CMVSS 108.1; FMVSS 202), not-yet-applicable
   shown as in-force (GB 34660-2026, GB 26572-2025, GB 11562-2025, FMVSS 213b), drafts shown as
   in-force (GCC EV regulation).
5. **Regulatory changes since authoring** (all verified): EPA rescinded all vehicle GHG standards
   (Feb 2026); NHTSA reset CAFE MY2022–2031 (FR 30 Sep 2026); California ACC II waiver revoked by CRA
   (Jun 2025, in litigation); Canada EVAS repeal proposed; US Syria sanctions lifted; Vietnam,
   Nigeria, Pakistan are 1958 Agreement parties; China mandatory light-vehicle AEB GB 39901-2025 from
   2028.
6. **Weak titles (90 findings)** — "MVSR s. 102", bare CELEX numbers; and
   **effective_date semantics** mix adoption, entry-into-force and application dates (EU).
7. **Summaries truncated** with "..." on many eCFR records, and several summaries describe content of a
   different instrument.

## Proposed fix plan
| Phase | Scope | Effort |
|---|---|---|
| 1 | Apply the 78 accepted high-severity fixes (data edits in `regulations/` and `knowledge/`) | small, one PR |
| 2 | UI: correct "Full text" classification; hide or badge `un_equivalent_ai`; show status nuance (upcoming / superseded) | small code change |
| 3 | Medium findings: titles, tags, summaries, crosswalk cells, market notes | medium, batched by region |
| 4 | Re-pull from an environment that can reach the official sites (eCFR CAFE parts, EU repealed acts, AU/KR/BR/UNECE full text); regenerate summaries/equivalents with validation | needs network access |
| 5 | Low findings (cosmetic) | optional |

## High-severity findings and decisions
| Decision | Area | Item | Field | Current | Proposed | Basis |
|---|---|---|---|---|---|---|
| ACCEPT | crosswalk | `accelerator-control` | cells.JP.records | jp-srrv-accelerator-control (cite 'Safety Regs / TRIAS') | Remove or re-point to a record that actually contains the Japanese accelerator-control requirement; no article cited | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | crosswalk | `aeb` | cells.CN | cite: 'Mandatory GB for light-vehicle AEB under development'; status: proposed | GB 39901-2025 (Light-duty vehicle AEBS requirements and test methods), mandatory, published 2026-01-29, effective 2028-01-01 for new M1 type | confirmed (GB 39901-2025) — orchestrator web check |
| ACCEPT | crosswalk | `anti-theft` | cells.UN.records / cells.EU.records (ece | ece-r161 linked as UN R161 (unauthorized use), but record is titled 'UN Regulation No. 161 | Keep cite 'UN R161 (unauthorized use)' but fix record ece-r161 title/summary/systems/tags to 'Protection of motor vehicles against unauthori | confirmed — orchestrator web check |
| ACCEPT | crosswalk | `br-contran-37` | title | Identification and Lighting of Controls (CONTRAN 37/1998) | Record describes the wrong instrument; CONTRAN 37/1998 concerns anti-theft sound alarms/security accessories. Identification of controls is  | confirmed — orchestrator web check |
| ACCEPT | crosswalk | `co2-fuel-economy` | cells.US.cite | NHTSA CAFE 49 CFR 531/533; EPA GHG 40 CFR 86/600; fuel economy label 40 CFR 600 | Remove EPA GHG fleet standards (rescinded, effective 20 Apr 2026); keep NHTSA CAFE (49 CFR 531/533) and the 40 CFR 600 fuel-economy test/lab | confirmed (EPA rule Feb 2026) — orchestrator web check |
| ACCEPT | crosswalk | `controls-telltales` | cells.BR.cite | CONTRAN 758/2018; 37/1998 (records br-contran-758, br-contran-37) | CONTRAN 758/2018 only (controls/tell-tales: revokes Res. 225/07, allows UN R121 or FMVSS 101 as alternative); drop br-contran-37 from record | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | crosswalk | `emc` | cells.CN.records (cn-gb-34660) / cells.C | cite 'GB 34660 (vehicle EMC)', record cn-gb-34660 (GB 34660-2026, effective 2027-07-01) wh | Cite 'GB 34660-2017 (in force); GB 34660-2026 replaces it from 1 Jul 2027'. Fix record body/summary/systems (EMC) and un_equivalent_ai to UN | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | crosswalk | `end-of-life` | cells.EU.cite / cells.EU.records (eu-320 | 'Battery Dir./Reg.' linked to Directive 2006/66/EC (record status in-force); no record for | Cite Regulation (EU) 2023/1542 (Battery Regulation); mark eu-32006l0066 as repealed (with effect from 18 Aug 2025, limited transitional prov | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | crosswalk | `exhaust-emissions` | cells.US.cite | CARB LEV IV (13 CCR 1961.4) presented as current; record us-stub-title-13-ccr... status in | State that the EPA waiver for ACC II (LEV IV/ZEV) was revoked under the CRA (signed 12 Jun 2025); LEV III still applies, LEV IV only optiona | confirmed (H.J.Res.88) — orchestrator web check |
| REJECT | crosswalk | `frontal-full` | cells.CN | GB 11551-2014 listed as the China full-width rigid barrier standard | Remove GB 11551-2014 from the full-width row (no verified Chinese mandatory full-width rigid-barrier regulation; leave cell empty or mark no | GB 11551-2014 is the 100% full-width rigid-barrier test (50 km/h) — crosswalk is correct. Instead fix record cn-gb-11551 |
| REJECT | crosswalk | `frontal-offset` | cells.CN | GB/T 20913-2007 (recommended), status voluntary; 'offset now via C-NCAP; check GB 11551 sc | GB 11551-2014 (mandatory 40% ODB, R94-equivalent); keep GB/T 20913 only as a secondary voluntary note; drop status: voluntary | Same as above: GB 11551-2014 is full-width, not the 40% offset test. |
| HOLD | crosswalk | `hood-latch` | cells.BR.cite / cells.BR.records | CONTRAN 498/2014 -> br-contran-498 (hood latch) | Replace with CONTRAN 426/2012 (hood two-stage lock / secondary latch); CONTRAN 498/2014 is the interior-material flammability resolution (se | Removal of CONTRAN 498/2014 from hood-latch confirmed (498 = interior flammability); replacement CONTRAN 426/2012 not ye |
| ACCEPT (modified) | markets | `CA` | watch[1] / emissions / notes | Electric Vehicle Availability Standard — 2026 model-year target status; emissions: 'EV Ava | State that the EVAS was paused (Sept 2025) and then repealed (announced Feb 2026), to be replaced by tightened GHG standards (Canada Gazette | Repeal announced Feb 2026; repeal regulations are a DRAFT (Canada Gazette I, 15 Aug 2026; comments to 29 Oct 2026). Say  |
| ACCEPT | markets | `CENTRAL-ASIA` | notes[0] | Uzbekistan's 1958 Agreement accession was reported in 2025; Tajikistan is a 1958 Agreement | Uzbekistan acceded to the 1958 Agreement on 20 Oct 2025 (and also to the 1998 Agreement); Mongolia acceded to the 1958 Agreement on 29 Apr 2 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | markets | `CO` | un_1958 | false | null (unverified) until deposit of the instrument of accession / entry into force is confirmed on the UNECE 1958 status list (TRANS/WP.29/34 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| HOLD | markets | `IL` | un_1958 | false |  | Israel 1958 Agreement status not determinable from available sources. |
| ACCEPT | markets | `NG` | un_1958 | null (note: 'accession status should be checked at UNECE') | true (E63) | confirmed (E63) — orchestrator web check |
| ACCEPT | markets | `SA` | emissions | GSO Euro-level limits (MY2027 step to Euro 6-equivalent per GSO plan — verify) | GSO MY2027: Euro 5 limits for Saudi Arabia (Euro 6b applies to UAE); do not claim a Euro 6 step for SA without evidence | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | markets | `SANCTIONED` | basis / members (Syria) | Syria grouped under 'Comprehensive or sectoral sanctions (US OFAC, EU, UK, UN) restrict ve | Remove or separate Syria: US revoked the Syria sanctions programme (EO 14312, 30 Jun 2025) and EU lifted economic sanctions (27 May 2025); r | confirmed (EO 14312) — orchestrator web check |
| ACCEPT | markets | `SOUTH-ASIA` | un_1958 | null (unverified) | Pakistan: true (E64, notified 24 Apr 2020); other members unverified. Consider splitting Pakistan into its own profile or adding a per-count | confirmed (E64) — orchestrator web check |
| ACCEPT | markets | `VN` | un_1958 | false | true (Vietnam is a 1958 Agreement contracting party since 24 Sep 2023; E-mark reported as E67) | confirmed (24 Sep 2023) — orchestrator web check |
| ACCEPT | records | `au-f2011l02016` | status | in-force (no qualifier) | in-force but being superseded by ADR 79/05 (new models from 1 Dec 2025; all vehicles from 1 Jul 2028) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `au-f2012l01123` | status | in-force | superseded (historic compilation; ceased 18 March 2014) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `au-f2012l01123` | title | ADR 00/00 - Approval Procedures and Administrative Requirements / Definitions and Vehicle  | Vehicle Standard (Australian Design Rule - Definitions and Vehicle Categories) 2005 Amendment 6 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `au-f2023l01530` | un_equivalent_ai | UN R100 | UN R134 (hydrogen vehicle safety) / UN GTR 13; R100 is electric power train safety | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `au-f2024l00161` | un_equivalent_ai | UN R157 | UN R130 (LDWS) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `au-workbook-reg-0604-new-vehicle-efficiency-standard-act-202` | summary | ...requiring them to meet fleet average CO2, fuel economy, certified emissions, and OBD re | NVES sets fleet-average CO2 (g/km) targets for suppliers with credits/penalties (from 1 July 2025); it does not itself impose OBD, certified | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `br-contran-215` | title | Burglar Alarm / Anti-theft Equipment | "Quebra-mato" (bull bar / front protection) devices on vehicles up to 3,500 kg GVW | confirmed (CONTRAN 215 = quebra-mato) — orchestrator web check |
| HOLD | records | `br-contran-245-330` | status | in-force | suspended (CONTRAN 559/2015); verify later repeal | Suspension by CONTRAN 559/2015 not independently confirmed. |
| ACCEPT | records | `br-contran-37` | title | Identification and Lighting of Controls | Anti-theft Alarms and Security Accessories (sound alarms, blocking devices) | confirmed (CONTRAN 37 = alarms) — orchestrator web check |
| ACCEPT | records | `br-contran-498` | title | Cover / Hood Latch | Flammability of Vehicle Interior Materials | confirmed (CONTRAN 498 = flammability) — orchestrator web check |
| ACCEPT | records | `br-contran-498` | un_equivalent_ai | UN R11 (door latches) | UN R118 (burning behaviour of interior materials) / FMVSS 302 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `br-contran-764` | title | Multimedia and Navigation Device | Horn / Audible Warning Device sound pressure test method | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `br-contran-827` | citation | CONTRAN 827/1998 (Horn / Audible Warning Device) | Citation does not exist as a horn instrument; horn test method is CONTRAN 764/2018, mandatory equipment CONTRAN 912/2022 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `br-contran-827` | title | Horn / Audible Warning Device | Delete or merge into br-contran-764 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `br-contran-924` | title | Interior and Exterior Mirrors | Mirrors / camera-monitor devices for school transport vehicles | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| HOLD | records | `br-mover-rota-2030` | citation | MOVER / Rota 2030 | Decree 12.435/2025 (regulating Law 14.902/2024, MOVER) | Decree 12.435/2025 number not independently confirmed. |
| ACCEPT | records | `ca-mvsr-c-r-c---c--1038-s108-1` | status | in-force | repealed | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-cnca-c11-01-2020` | summary | ...for passenger vehicles and light trucks ... supplier regulatory flowdown | Implementation rules for compulsory product certification - Motor vehicles; applies to M, N and O category vehicles (complete and incomplete | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-11552` | summary | Regulates interior fittings of passenger cars, covering structural areas including body-in | GB 11552-2009 (Interior fittings/protrusions of passenger cars; modified adoption of ECE R21): requirements for interior protrusions, contro | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-13057` | title | Strength of seats and their anchorages of passenger vehicles (vehicle_categories: Passenge | Strength of seats and their anchorages of buses (客车座椅及其车辆固定件的强度); vehicle_categories Bus; un_equivalent UN R80 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-14166-2024` | un_equivalent | UN R14 | UN R16 (safety belts and restraint systems) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-19578` | summary | sets maximum allowable fuel consumption... requires vehicles meet certified fuel economy,  | Sets passenger-car fuel consumption limits (18% tighter than GB 19578-2021; mass-based limits, inflection 1090 kg); new type approvals from  | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-26572-2025` | status | in-force (effective_date 2027-08-01) | upcoming / published, not yet in force | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-27887-2024` | summary | Covers design and installation requirements for ISOFIX/LATCH lower anchors, top tether anc | GB 27887-2024 sets requirements and tests for child restraint systems (the CRS itself, dynamic testing, i-Size/ISOFIX CRS); vehicle anchorag | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-34660` | status | in-force | upcoming: GB 34660-2026 effective 2027-07-01; GB 34660-2017 remains in force until then | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-34660` | summary | EMC ... "mandates that these systems be resilient to cyber and software risks" | Road vehicle EMC: radiated/conducted emissions and immunity of vehicle and ESAs (RF, transients, ESD) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-34660` | un_equivalent_ai | UN R155, UN R156 | UN R10 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-4599-2024` | summary | Covers headlamps, daytime running lights, stop, tail, turn, reverse lamps, reflectors ...  | Road illumination devices and systems: dipped/main-beam headlamps, front fog, cornering lamps (M and N) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `cn-gb-9743-2024` | summary | Covers tyres, wheels/rims, valve stems, TPMS, spare tyres, load/speed ratings ... warned o | Passenger car pneumatic tyre safety performance requirements (strength, endurance, high speed, load index/speed symbol, markings) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `ece-r149` | title | UN Regulation No. 149 — Road Illumination Devices (except headlamps) | UN Regulation No. 149 — Road Illumination Devices (RID) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `ece-r149` | summary | Road illumination devices (excluding headlamps) are regulated under UN R149... | R149 (RID) is the consolidated headlamp regulation: driving/passing-beam headlamps and AFS, replacing R112/R113/R123 etc. for new approvals. | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `ece-r153` | title | UN Regulation No. 153 — Fuel System Integrity in a Frontal Collision | UN Regulation No. 153 — Fuel System Integrity and Safety of Electric Power Train in the Event of a Rear-End Collision | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `ece-r153` | summary | ...addresses fuel system integrity in passenger vehicles during a frontal collision... | Fuel system integrity and high-voltage electric power train safety after a rear-end collision (M1/N1). | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `ece-r161` | title | UN Regulation No. 161 — Pedal Misapplication Mitigation Systems | UN Regulation No. 161 — Devices against Unauthorized Use | confirmed (R161 = unauthorized use; pedal error = R175) — orchestrator web check |
| ACCEPT | records | `ece-r161` | summary | Pedal misapplication mitigation systems are the subject of this regulation... | UN R161 covers devices against unauthorized use (locking systems) for vehicles; not pedal misapplication. | confirmed — orchestrator web check |
| ACCEPT | records | `eu-32006l0066` | status | in-force | superseded (repealed by Regulation (EU) 2023/1542 with effect from 18 August 2025, with limited transitional exceptions) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `eu-32009r0078` | status | in-force | superseded (repealed by Regulation (EU) 2019/2144 with effect from 6 July 2022) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `eu-32009r0661` | status | in-force | superseded (repealed by Regulation (EU) 2019/2144 with effect from 6 July 2022; tyre requirements moved to Reg (EU) 2019/2144 / Reg (EU) 202 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `eu-32017r1151` | effective_date | 2018-05-30 | 2017-06-01 (adoption) / in force 2017-07-27 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `eu-32023r2590` | un_equivalent | UN R167 | empty (no UN equivalent for ADDW) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `gcc-gcc-ev-technical-regulation-draft` | status | in-force | draft / proposed (not in force) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `gcc-gso-ece-125` | summary | Summary: lamp/illumination/glare/driver-intent signalling requirements | UN R125 is Forward Field of Vision of motor vehicle drivers (M1 only): driver's forward visibility/obstruction angles, not lighting. Rewrite | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `gcc-gso-ece-13h-2012` | un_equivalent | UN R13 | UN R13-H (passenger cars/M1); UN R13 covers heavy vehicles M2/M3/N/O | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `gcc-gso-ece-43-gso-3538` | summary | Summary: road illumination, signalling driver intent, lighting/HMI | UN R43: safety glazing materials and their installation (windscreen, windows, impact/optical/light transmission) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `gcc-gso-ece-46` | summary | Summary: mirrors ... light color, intensity, aim and tell-tale logic | UN R46: devices for indirect vision (mirrors, camera-monitor systems): fields of view, installation, performance | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `gcc-uae-fuel-economy-standard-number-to-verify-gemini-cited-` | citation | UAE Fuel Economy Standard (number to verify; Gemini cited UAE.S 5011) | Replace with verified instrument or remove record | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `gcc-uae-fuel-economy-standard-number-to-verify-gemini-cited-` | status | in-force | unverified | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `in-ais-038-rev-2-ais-156` | summary / vehicle_categories / citation | Summary and applicability treat AIS-038 Rev.2 and AIS-156 as one set for M/N passenger-car | AIS-038 Rev.2 = electric power train + REESS safety for M and N categories (UN R100 counterpart). AIS-156 = L-category (2W/3W/quadricycle) p | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `jp-jvsregs-art43-7` | un_equivalent_ai | ["UN R159"] | ["UN R138"] | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `jp-srrv-accelerator-control` | summary | Accelerator Control ... regulates fuel systems, high-voltage energy storage ... to prevent | Rewrite for accelerator control (accelerator pedal/control behaviour); summary and body are the generic fuel/EV-safety template, not acceler | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `jp-srrv-accelerator-control` | un_equivalent_ai | UN R34, UN R100 | empty | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `jp-srrv-audible-warning-devices` | summary | ... compliance intent focuses on preventing fire, explosion, electric shock, and... | Horn/audible warning performance (sound level, tone); AVAS where applicable | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `jp-srrv-electric-vehicle-rechargeable-energy-storage-system` | citation | SRRV / TRIAS / UN R136 | SRRV / TRIAS / UN R100 (passenger cars, M1/N1) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `jp-srrv-engine-power-train-and-pedal-lever` | summary | Fuel systems, EV energy storage ... are regulated under SRRV Article 8 to prevent fire, ex | SRRV Art. 8 covers engine and power transmission; rewrite. Fuel devices are Art. 15 (as the record itself says) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `jp-srrv-engine-power-train-and-pedal-lever` | un_equivalent_ai | UN R34, UN R100 | empty (R85 engine power measurement possible, unverified) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `other-workbook-reg-0643-iso-26262` | un_equivalent | un_equivalent: UN R157; un_equivalent_ai: UN R155, UN R156 | Remove R157 as an equivalent (R157 is ALKS, a regulation not a functional-safety process standard). ISO 26262 has no single UN counterpart;  | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `other-workbook-reg-0644-iso-21448` | un_equivalent | UN R157; un_equivalent_ai: UN R155 | No direct UN equivalent. R157 (ALKS) is a legal regulation; ISO 21448 SOTIF is a voluntary engineering standard that may support ADAS approv | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| HOLD | records | `other-workbook-reg-0652-iso-34502-iso-tr-4804-iso-pas-8800` | status | in-force (for all three documents) | Split: ISO/TR 4804:2020 withdrawn 29 Apr 2025, replaced by ISO/TS 5083:2025; ISO 34502:2022 and ISO/PAS 8800:2024 current | ISO/TR 4804 withdrawal date not independently confirmed (plausible). |
| ACCEPT | records | `us-cfr-part-531` | status | status in-force; body pulled 2026-06-01 shows the 2022/2024 standards (MY 2012-2031 table, | keep in-force but flag that standards were reset by the NHTSA SAFE Vehicles Rule III final rule (FR 2026-19964, published 2026-09-30); re-pu | confirmed (FR 2026-19964) — orchestrator web check |
| ACCEPT | records | `us-cfr-part-533` | status | status in-force; body pulled 2026-06-01 shows the 2022/2024 standards (MY 2012-2031 table, | keep in-force but flag that standards were reset by the NHTSA SAFE Vehicles Rule III final rule (FR 2026-19964, published 2026-09-30); re-pu | confirmed (FR 2026-19964) — orchestrator web check |
| ACCEPT | records | `us-fmvss-124` | un_equivalent_ai | UN R161 | No direct UN equivalent (remove) | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `us-stub-dodd-frank-section-1502-regulation-eu-2017-821` | title | Conflict minerals and responsible sourcing due-diligence frameworks (citation joins Dodd-F | Split into two records: Dodd-Frank s1502 (SEC Rule 13p-1, 17 CFR 240.13p-1/Form SD) and Regulation (EU) 2017/821 | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |
| ACCEPT | records | `us-stub-title-13-ccr-1961-4-1962-4-1962-8` | status | in-force | Flag as federally contested: EPA's ACC II waiver was revoked via CRA (Pub. L. 119-16, 12 Jun 2025); CARB enforcement is disputed/in litigati | confirmed (CRA, litigation pending) — orchestrator web check |
| ACCEPT | records | `us-stub-us-epa-40-cfr-part-86-tier-3` | summary | Compliance applies to passenger cars as listed in 49 CFR Part 571 | Tier 3 (40 CFR Part 86, Subpart S etc.) applies to light-duty vehicles, light-duty trucks and medium-duty passenger vehicles (and sets 10 pp | internal evidence (record title/body/citation contradict the field) or reviewer web evidence; consistent with orchestrat |

## Reproduce / extend
```
python scripts/review_precheck.py          # deterministic checks → review/precheck.json
# run reviewers per review/shards/*.json following review/REVIEWER_BRIEF.md
python scripts/review_aggregate.py         # → review/findings_all.json (coverage + counts)
```
All findings (including medium/low) with evidence are in `review/findings/<shard>.json` and the merged
`review/findings_all.json`.

## Fix status (applied on branch `review/content-accuracy`)

| Phase | What | Status |
|---|---|---|
| 1 | Accepted high-severity record and knowledge fixes | Applied (see `CHANGES.md`) |
| 2 | Labels in the UI: what kind of text each record holds (`content_kind`: full, summary, index or link), AI-suggested UN equivalents marked unverified, `upcoming` status plus `status_note` | Applied |
| 3 | Medium and high findings turned into structured patches by 11 patch writers, then checked by `apply_patches.py` (taxonomy, UN-ref format, dates, truncation) | Applied: 199 records, 304 fields, 0 rejected |
| 3+ | Orchestrator follow-up: 5 record bodies copied from a wrong-topic template replaced with reference stubs; stale template `open_tags` cleared (18 records) | Applied |
| 4 | Re-pull from official sources into a staging folder, then merge body text only (`scripts/pull_staged.py`, `scripts/merge_staged.py`) | Done 2026-10-06: 161 records upgraded to full text, 22 refreshed; log in `REPULL_2026-10.md` |
| 5 | Low-severity findings | Not done |

Held for human verification (not applied):
- `au-f2006l01279` (ADR 28/01): the supersession by ADR 83/00 is unconfirmed.
- `eu-workbook-reg-0637`: Omnibus I (Directive (EU) 2026/470) could not be verified.
- `gcc-gso-ece-26` `un_equivalent_ai`, `cn-gb-20072-2024` `un_equivalent` (low confidence), `br-contran-749` categories, and a 2026 ISO 9001 edition.
- Knowledge items: Macau authority and Euro 6c, JP IWVTA wording, Canada certification label, India cybersecurity status, and AE/IL/SA `un_1958` notes.

Judgement calls worth checking (taken from the patch writers' notes):
- ADR 19/02→R53; ADR 105/00 set to Heavy truck only.
- JVSR Art. 26→R107; the ALKS and controls records in jp-srrv still carry template tags.
- `eu-32014r0540`: R51 and R59 kept as machine-suggested equivalents, not stated ones.
- `eu-32024r1257` (Euro 7) and FMVSS 213b set to `upcoming`; FMVSS 202 set to `superseded` by 202a.
- `br-contran-245-330` suspension note and the Massachusetts 93K litigation note come only from search snippets and are worded with hedges.
- India BS-VI citation and Brazil MOVER citation (Law 14.902/2024) come from the patch writers' own knowledge.
- ERA-GLONASS, `br-contran-498` and `cn-gb-26572-2025`/`8410` have `systems` set to [], because the taxonomy has no eCall, flammability or substances value.
- 0652 bundles ISO 34502, ISO/TR 4804 and PAS 8800, so it may need splitting into separate records.

### Phase 4 re-pull (2026-10-06)

- Records now holding **full regulation text: 486 of 726** (was 325).
- **UN Regulations:** unece.org blocks automated access (403, PDFs included). 81 of 85 now carry the text the EU republished in the Official Journal (new connector `connectors/unece_oj.py`). Each body names its CELEX number and warns that later UNECE supplements may exist. R27, R114, R144 and R154 have no usable OJ copy.
- **Australia:** the connector previously saved the register's landing page. It now pulls the compiled text as EPUB from the FRL API (90 records). The register lists every AU record as in force except F2012L01123 (an amending instrument), so the held ADR 28/01 "superseded" finding is rejected.
- **US:** 22 eCFR texts refreshed with real amendments, e.g. obsolete phase-in subparts removed from Part 585 and FMVSS 301.
- **Japan and Korea:** the bodies are kept as their English translations. The original-language re-pull matched them.
- **China:** openstd.samr.gov.cn shows the standard text only as images, so the pull returns metadata only. That metadata matched every record except GB 1589, whose successor GB 1589-2026 now has a status note.
- **GCC and India:** the standards are sold or have no free text, so these stay as summaries.
- Embedded base64 figures were replaced with "Figure omitted" markers, keeping `regulations/` at about 36 MB.
- 183 summaries are flagged stale because their body changed. They need re-checking against the new text.

### Phase 4b: metadata checked against the re-pulled text (2026-10-06)

Ten verifier agents (`review/VERIFY_BRIEF.md`) checked every record whose body changed in the re-pull, using the regulation's own scope, applicability and dates. Results:
- 183 records checked: 54 summaries confirmed and 129 rewritten. Most of the old summaries were template text that claimed the record had no text.
- Vehicle categories corrected to match each scope clause on about 40 records (UN categories L/M/N/O/T mapped to the taxonomy).
- `un_equivalent` for Australian ADRs now comes from each ADR's own "alternative standards" clause. Machine-suggested duplicates were removed on 33 records.
- FMVSS 305a, 307 and 308 set to `upcoming`, because their mandatory dates fall in 2027–2028.
- `br-anatel-cert` was excluded: the re-pull returned a generic landing page, so its previous body was restored.
- No summaries are flagged stale any more.

Worth a human look:
- ADR 72/01 and ADR 68/01 first apply on 2026-11-01 but are marked `in-force` (the instrument is made; application is phased).
- UN R83 (09 series) and R160 (01 series) say "entry into force TBC" in the OJ text.
- The ADR 30/01 compilation header refers to ADR 79/05, which looks like an error in the source.
- Some loose commodity and system tags remain where the taxonomy has no better value.
