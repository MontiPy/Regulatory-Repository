# Orchestrator adjudication log

Claims from reviewers that depend on external facts were re-checked by the orchestrator
(WebSearch; government sites blocked for direct fetch). Decision key:
**ACCEPT** = confirmed, will be applied · **ACCEPT (modified)** = confirmed with correction ·
**REJECT** = reviewer was wrong · **HOLD** = could not confirm; not applied.

| # | Claim (shard) | Decision | Evidence |
|---|---|---|---|
| 1 | EPA rescinded the GHG endangerment finding and ALL vehicle GHG standards (mk-01, cw-06) | **ACCEPT** | Final rule signed 12 Feb 2026, published 18 Feb 2026, effective late Apr 2026 — [Holland & Knight](https://www.hklaw.com/en/insights/publications/2026/02/epa-repeals-vehicle-all-greenhouse-gas-standards-for-vehicles), [DLA Piper](https://www.dlapiper.com/en-us/insights/publications/2026/02/epa-rescinds-endangerment-finding-and-eliminates-mobile-source-ghg-emissions-standards) |
| 2 | Canada EV Availability Standard "repealed" (mk-01) | **ACCEPT (modified)** | Repeal announced Feb 2026; repeal regulations are a **draft** (Canada Gazette I, 15 Aug 2026, comments to 29 Oct 2026) with tighter GHG standards for MY2027–2032 proposed — [Canada Gazette](https://gazette.gc.ca/rp-pr/p1/2026/2026-08-15/html/reg2-eng.html), [Electric Autonomy](https://electricautonomy.ca/policy-regulations/2026-02-05/canada-repeals-ev-availability-standard-restores-5000-vehicle-incentives-with-new-automotive-policy/). Profile should say "repeal proposed", not "repealed". |
| 3 | Vietnam is a 1958 Agreement CP since 24 Sep 2023 (mk-04) | **ACCEPT** | [Vietnam Law Magazine](https://vietnamlawmagazine.vn/vietnam-approves-plan-to-implement-unece-1958-agreement-on-road-vehicles-76408.html); implementation plan Decision 77/QD-TTg (Jan 2026). E-number not confirmed — not applied. |
| 4 | US Syria sanctions programme revoked (mk-07) | **ACCEPT** | EO 14312, 30 Jun 2025, effective 1 Jul 2025 — [OFAC](https://ofac.treasury.gov/recent-actions/20250630). Assad-related/terrorism sanctions remain. |
| 5 | China light-vehicle AEB mandatory GB 39901-2025, effective 1 Jan 2028 (cw-03) | **ACCEPT** | [CnEVPost](https://cnevpost.com/2026/01/28/china-issues-1st-mandatory-standard-driver-assist-aeb-as-standard/) |
| 6 | GB 11551-2014 is the 40 % offset test, so CN frontal-full/offset cells are swapped (cw-01) | **REJECT** | GB 11551-2014 specifies the **100 % overlap rigid barrier at 50 km/h** — [hnsaf](https://www.hnsaf.com/NewsDetail/4748819.html), [Zhihu](https://zhuanlan.zhihu.com/p/378379927). Crosswalk is correct. Real defect: record `cn-gb-11551-2014` maps `un_equivalent` UN R94 (offset) — should be UN R137 (full width). |
| 7 | Nigeria 1958 CP (E63), Pakistan 1958 CP (E64) (mk-08, mk-03) | **ACCEPT** | Search results list E63 Nigeria, E64 Pakistan (secondary sources; UNECE status doc blocked). |
| 8 | Congress revoked California ACC II waiver via CRA, 12 Jun 2025 (cw-06, rec-us-parts-05) | **ACCEPT** | [H.J.Res.88](https://www.congress.gov/bill/119th-congress/house-joint-resolution/88); California + 10 states sued the same day — status "federally revoked, in litigation". |
| 9 | NHTSA reset CAFE MY2022–2031 ("SAFE III"), FR 30 Sep 2026 (rec-us-parts-01) | **ACCEPT** | [Federal Register 2026-19964](https://www.federalregister.gov/documents/2026/09/30/2026-19964/the-safer-affordable-fuel-efficient-safe-vehicles-rule-iii-for-model-years-2022-to-2031-passenger), effective 30 Nov 2026; eliminates credit trading. Records us-cfr-part-531/533/536 need re-pull. |
