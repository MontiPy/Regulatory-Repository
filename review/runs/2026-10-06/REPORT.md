# Content accuracy review — 6 October 2026

> **Full audit artifacts:** URL logs, coverage files, inventories, per-group findings/patches, run logs and helper scripts were left out of `main` to keep the repository lean. They are preserved on branch `review/2026-10-06-content` (commit ae77802). Links below to those files only work on that branch.

**Continuation:** [The external review](../2026-10-06-external/REPORT.md) resumes this run with successful official-source retrieval and additional corrections. The results and network limitations below describe this earlier run.

Branch: `review/2026-10-06-content`. Baseline: `faefa1c5f239f5e2a6bcf28ce54ebd0b0c3c8a92`. Review content is isolated with the `r20261006-` prefix so historical findings/proposals cannot be accidentally applied. No PR was opened and main was not modified.

All 54 fixed shards were completed: 727 regulation records, 48 market profiles, 69 crosswalk topics and 45 glossary terms. This is a metadata and relevant-clause review, not certification that every technical annex, referenced standard, translation or current legal rule is correct.

**Findings and decisions**

| Severity | Findings | Applied | Held / skipped | Rejected |
| --- | ---: | ---: | ---: | ---: |
| High | 92 | 88 | 3 | 1 |
| Medium | 282 | 205 | 77 | 0 |
| Low | 9 | 9 | 0 | 0 |
| Total | 383 | 302 | 80 | 1 |

The final adjudication labels are 354 accepted, 28 modified and 1 rejected. Labels include accepted verification limitations; the application disposition above determines whether a patch was authorized. Reviewers also recorded 2,722 skipped field/reference groups and 172 already-fixed observations; those are separate from the 383 findings. Patch writers skipped no authorized findings after root amendments. Post-body verifiers held other metadata for all eight stubs while verifying every changed-body summary.

Changes affect **229 regulation records**: 287 initial field/body updates, including 121 summaries, 50 cleared unsupported UN-equivalence lists and eight honest reference stubs. Four knowledge files changed: 17 crosswalk topics, three market profiles (US/CA/EU) and one glossary term (CSMS), through 21 exact replacements covering 27 findings. Subsequent verification confirmed seven stub summaries and narrowed one; no new UN equivalent, machine-equivalent, source URL, id or record deletion was introduced.

**Ten consequential corrections**

1. Removed unsupported `un_equivalent` claims from 50 records, particularly Chinese/GCC template entries. A related-regulation mention does not establish acceptance or equivalence. Empty lists mean evidence absent, not proven legal non-equivalence.
2. Replaced eight wrong-topic bodies with explicit reference notices: GB11552, GB13057, GSO-ECE125/43/46/51, Japanese wiping/defrosting overview, and US Part575. Matching summaries make no invented requirements.
3. Corrected the US seat-belt-reminder crosswalk from the asserted 2026/2027 front/rear schedule to the stored FMVSS208 S7.5 manufacturing applicability of **1 September 2028**; S7.4 is comfort/convenience, not rear reminders.
4. Restored current FMVSS305 links to rear-impact and post-crash mappings, distinguished FMVSS305a's **September 2027/2028** mandatory milestones and extensions, and separated crash-only electrolyte/retention requirements from normal-operation electric-shock protection.
5. Included hydrogen internal-combustion vehicles alongside FCEVs in the hydrogen filter, as explicitly defined in ADR110's embedded text. US FMVSS307/308 mappings now show **September 2028** manufacturing applicability and the 308 storage exclusions.
6. Corrected ADR28's UNR51 alternative to retain stationary-noise conditions, and ADR58's UNR107 alternative to retain additional clauses58.23/58.24. ADR66 includes specified M2 as well as M3 omnibuses.
7. Added Euro7 trailer scope (O3/O4) and qualified EU market dates for **M1/N1**, including the **July2030 small-volume exception**, rather than applying a passenger/light-commercial date to every vehicle.
8. Corrected 11 EU commencement/application dates with explicit phase/exception notes, preserved existing repeal notes, and set FMVSS217a's manufacturing milestone to **30 October 2027 / upcoming**. Notes distinguish general application from adoption or legal issuance.
9. Broadened Canadian s208's title/summary to occupant crash protection and belt installation, including TSD208/airbag provisions; restored s203's body-block requirement and s111's rear-visibility-system subject. Korean Article56-2 now preserves its exact 8km/h/0.15s trigger and the stored 2025 amendment scope.
10. Corrected roof-crush mapping to **3.0×UVW at GVWR≤2,722kg and 1.5×UVW above**, and bumper mapping to distinguish **1.5mph corner** from **2.5mph longitudinal/barrier** tests. These are stored-clause corrections, not assertions of fresh source currency.

**Evidence, adjudication and rejected proposals**

Every HIGH finding was independently re-checked against retained bodies. Thirty randomly selected MEDIUM findings (10.6%, seed20261006), all date proposals, all knowledge changes and additional patch-stage concerns were checked. [Root evidence checks](root-evidence-checks.json) preserve body excerpts and file hashes. [Final decisions](adjudication.json) and [ADJUDICATION](../../ADJUDICATION.md) identify every accepted, modified, rejected and held finding.

The GB27887 child-restraint body-stub proposal was rejected: anchor/installation material overlaps the CRS subject, so missing legal text does not establish a different topic. CA emissions' copied safety-applicability sentence is held because a whole-body stub would exceed the strict different-topic rule. The R118 flammability cell remains held: its `none` status is misleading for buses, but an unqualified implicit mandatory mapping could also mislead. Korean Article26's proposed Bus tag is held until its national-category bridge is established. A reviewer's nonexistent §563.6a citation was rejected in favor of actual §§563.3/563.4(a)/563.6/563.12.

**What was and was not verified externally**

The environment still enforced a restricted network policy after the settings update. All **602 distinct regulation/authority URLs** checked with `curl -sIL` returned policy403/curl56: [complete URL log](evidence/url-checks.json). These outcomes do not establish that the links are dead or working, or authenticate the instrument at the URL. The user instructed **finish with body evidence**. No official-source content was successfully fetched in this run; no correction rests on model knowledge or search snippets, and no well-established-knowledge exception was used.

`check_kr_translations.py` could not reach the Korean source: translation staleness, renumbering and latest Korean amendments remain unverified. `pull_staged.py EU /tmp/regulatory-review-stage` yielded zero staged records; `merge_staged.py` dry-run had zero candidates. No body refresh was applied, and `pull.py` was never run. [Logs](logs/) and [staged dry run](staged-dry-run.md) record the limitations.

Current treaty membership (1958/1998), authority competence, national acceptance, repeal/supersession, unlinked citations and categorical no-requirement assertions were not independently authenticated. Market claims on 2026 EPA/GHG changes, SAFE Vehicles RuleIII, CARB waivers/litigation, Canadian ZEV repeal proposals and the ELV replacement remain unverified. Reading them or preserving unrelated text is not endorsement. Large technical annexes were searched for metadata assertions, not audited line by line. Absent tables and incorporated TSD/SAE/ISO/UN documents were not reconstructed.

**Non-official or non-regulatory evidence**

No external third-party source was fetched or used to establish a new legal requirement. Stored limited bodies and headings were used to withdraw unsupported claims and describe their advertised subject. **79 changed records lack full regulation text**, listed below; their legal subject/version/scope is not independently certified. The MOVER announcement is official government news, but not the decree itself. No new mandate was derived from generic template prose.

Known non-government source URLs remain in the repository and were not used to verify law: GAIKINDO (Indonesia overview), Thuviennhadat (Vietnam overview), and ATIC for `br-abnt-nbr-15145`, `br-contran-215`, `br-contran-37`, `br-contran-498`, `br-contran-764`, `br-contran-924`, `br-contran-safety-labeling` and `br-senatran-990`. Their official replacements were not reachable. Paywall and publisher-access assertions were not revalidated, including Chinese GB records labelled paywalled.

**Needs a human**

- Resolve the UNR83 09-series body placeholder **“XX September2026 (TBC)”**, authentic commencement and compilation currency; do not invent a date.
- Obtain official clarification for FMVSS224's **4,356 versus4,536kg** body discrepancy and Part561's exactly-4,536kg extension boundary. Part588 “se-mail addresses,” FMVSS120 malformed parentheses and CA116 “of a every” need source-versus-extraction checks.
- Repair isolated copied body sentences in EPA Tier3 and Canadian SOR2003-2; inspect mixed emissions/OBD template remnants in NVES, Chinese fuel-consumption and TPMS entries. The permitted stub mechanism does not authorize arbitrary clause edits.
- Decide whether to split/rename combined AIS038/AIS156 records and their inconsistent source link, and resolve Canadian workbook record1106's instrument identity. No ids were renamed automatically.
- Define a precise bus-class mapping for UNR118; decide how CONAMA492's narrow UNR83 method reference should be represented without claiming whole-instrument equivalence.
- Add or link a standalone UNR178 record if appropriate; its existence is explicit in ADR107, but current authentic UN text/series must be obtained.
- Resolve ADR60's conflicting Table-of-Instruments name, ADR99 00/01 heading discrepancies, and missing ADR45/application and other extracted tables. These cannot be corrected through summary guesses.
- Confirm the Korean translation/category bridge and omitted attached tables. Taxonomy lacks precise national three-wheel/ultra-compact/LSV and platform-lift categories; no substitute categories were invented.
- Verify the detailed current-policy claims in US/CA/EU profiles and CAFE records531/533 from current government sources. All other treaty/authority/acceptance/no-requirement claims remain subject to official confirmation.
- Resolve duplicate citation groups: SOR2010-90 full/overview entries, and ten SRRV/TRIAS topic overviews sharing a generic citation. Duplicate citation is not proof of a duplicate instrument; merges or id changes need a decision.
- Obtain real technical text for the limited records and paid standards; confirm official source replacements for the third-party URLs, and correct the MOVER full-text classification. Its summary now identifies the news article accurately, but the build heuristic still classifies that body as full.

**Deterministic results and remaining coverage**

| Check | Before | After |
| --- | ---: | ---: |
| Summary/index/link bodies | 240 | 240 |
| Summary | 182 | 174 |
| Index | 15 | 15 |
| Link | 43 | 51 |
| Full by build heuristic | 487 | 487 |
| Summaries ending in ... or … | 0 | 0 |
| Empty systems | 42 | 41 |
| Empty commodities | 83 | 86 |
| Empty vehicle categories | 23 | 23 |
| In-force with future effective_date | 0 | 0 |
| Prefix/region mismatch | 0 | 0 |
| Title-word/body heuristic flags | 123 | 122 |
| Duplicate citation groups | 2 | 2 |
| summary_stale | 0 | 0 |

The 240 limited bodies plus MOVER mean **at least241 records lack the actual regulation text**, despite the heuristic's487 full classifications. Other extraction omissions may remain in full-labelled bodies. Empty filters can be correct for administrative/component-only rules; the three emptied commodity lists were individually checked against label/test-device scopes and taxonomy. Title-word, thin-body and status-keyword flags are review hints, not automatic legal findings. `review_precheck` still reports69 body-thin,12 per-record duplicate-citation,14 status-text and1 weak-title flags; no speculative fix was applied to clear a detector.

[PRECHECK](PRECHECK.md) lists every initial required flag; [final inventory](inventory-after.json) lists all remaining limited records, empty filters, title flags and duplicate groups. [Coverage sidecars](coverage/) disclose every reviewed and skipped group, including missing tables and specific unlinked claims.

**Validation and branch work**

Both patch directories and the post-body verification passed `review/apply_patches.py --dry-run` with **zero rejections**; only this orchestrator applied content via that validator. The knowledge extension validates full YAML schema and every record reference before any write. Suspicious empty lists, all dates/status changes and stubs were individually checked. [Proposal audit](proposal-audit.json) records zero unauthorized changes; [final diff](record-changes.json) confirms exactly229 records and eight authorized body changes.

Final `scripts/build.py`: **727 records, zero errors, zero warnings**. Final pytest: **228 passed** (baseline212;16 safeguards tests). Eleven browser samples passed against the locally served dist bundle: seven records plus two crosswalk topics, US profile and CSMS glossary; [browser checks](browser-checks.json) and screenshots in [evidence](evidence/) preserve the results. This is a sample, not a browser review of every changed record. No record is summary_stale.

The validators were hardened in a separate logical commit: calendar-date and URL validation, conflicting-proposal veto, fixed-shard coverage checking, isolated run aggregation, and schema-checked knowledge proposals. Historical patch directories were never applied. The complete applied log is in [CHANGES](../../CHANGES.md); all held/rejected findings are listed there and in adjudication.

**Changed records with limited/non-regulatory bodies**

| Record | Fields changed | Evidence limitation |
| --- | --- | --- |
| [ar-workbook-reg-0624-lcm-lca](../../../regulations/ar-workbook-reg-0624-lcm-lca.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [asean-workbook-reg-0615-asean-automotive-products-mutual-recognition-arrangement-apmra](../../../regulations/asean-workbook-reg-0615-asean-automotive-products-mutual-recognition-arrangement-apmra.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [asean-workbook-reg-0617-indonesia-sni-vehicle-type-approval-framework](../../../regulations/asean-workbook-reg-0617-indonesia-sni-vehicle-type-approval-framework.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [asean-workbook-reg-0618-jpj-vehicle-type-approval-malaysia-emissions-approval](../../../regulations/asean-workbook-reg-0618-jpj-vehicle-type-approval-malaysia-emissions-approval.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [asean-workbook-reg-0619-qcvn-09-2024-bgtvt-circular-48-2024-tt-bgtvt](../../../regulations/asean-workbook-reg-0619-qcvn-09-2024-bgtvt-circular-48-2024-tt-bgtvt.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [asean-workbook-reg-0620-philippines-motor-vehicle-component-conformity-and-emissions-approval-framework](../../../regulations/asean-workbook-reg-0620-philippines-motor-vehicle-component-conformity-and-emissions-approval-framework.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [au-f2009l03609](../../../regulations/au-f2009l03609.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [au-f2018l01520](../../../regulations/au-f2018l01520.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [au-f2022l00213](../../../regulations/au-f2022l00213.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [au-f2023l01317](../../../regulations/au-f2023l01317.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [au-workbook-reg-0370-road-vehicle-standards-act-2018-road-vehicle-standards-rules-2019](../../../regulations/au-workbook-reg-0370-road-vehicle-standards-act-2018-road-vehicle-standards-rules-2019.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [au-workbook-reg-0371-register-of-approved-vehicles-rav](../../../regulations/au-workbook-reg-0371-register-of-approved-vehicles-rav.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [au-workbook-reg-0605-radiocommunications-equipment-general-rules-2021-acma](../../../regulations/au-workbook-reg-0605-radiocommunications-equipment-general-rules-2021-acma.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [ca-workbook-reg-0145-eccc-sor-2003-2](../../../regulations/ca-workbook-reg-0145-eccc-sor-2003-2.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [ca-workbook-reg-0359-motor-vehicle-tire-safety-regulations-sor-2013-198](../../../regulations/ca-workbook-reg-0359-motor-vehicle-tire-safety-regulations-sor-2013-198.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-11551-2014](../../../regulations/cn-gb-11551-2014.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-11552](../../../regulations/cn-gb-11552.md) | body → reference stub, summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-13057](../../../regulations/cn-gb-13057.md) | body → reference stub, summary | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-14166-2024](../../../regulations/cn-gb-14166-2024.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-14167-2024](../../../regulations/cn-gb-14167-2024.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-1495-2002](../../../regulations/cn-gb-1495-2002.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-15083-2019](../../../regulations/cn-gb-15083-2019.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-15084-2022](../../../regulations/cn-gb-15084-2022.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-15086-2013](../../../regulations/cn-gb-15086-2013.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-18296-2019](../../../regulations/cn-gb-18296-2019.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-18352-6-2016](../../../regulations/cn-gb-18352-6-2016.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-18384-2020-gb-18384-2025](../../../regulations/cn-gb-18384-2020-gb-18384-2025.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-20071-2025](../../../regulations/cn-gb-20071-2025.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-21670-2025](../../../regulations/cn-gb-21670-2025.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-24550-2024](../../../regulations/cn-gb-24550-2024.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-27887-2024](../../../regulations/cn-gb-27887-2024.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-38031-2025](../../../regulations/cn-gb-38031-2025.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-44495-2024](../../../regulations/cn-gb-44495-2024.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-44496-2024](../../../regulations/cn-gb-44496-2024.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-4599-2024](../../../regulations/cn-gb-4599-2024.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-4785-2019](../../../regulations/cn-gb-4785-2019.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-8410](../../../regulations/cn-gb-8410.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-9656-2021](../../../regulations/cn-gb-9656-2021.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-9743-2024](../../../regulations/cn-gb-9743-2024.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-t-18411-2018](../../../regulations/cn-gb-t-18411-2018.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-t-20913-2007](../../../regulations/cn-gb-t-20913-2007.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-t-30512-2014](../../../regulations/cn-gb-t-30512-2014.md) | systems | Own limited body/heading; legal text and currency unverified. |
| [cn-gb-t-30677-2014](../../../regulations/cn-gb-t-30677-2014.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1040-1041-1042](../../../regulations/gcc-gso-1040-1041-1042.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1053-2002](../../../regulations/gcc-gso-1053-2002.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1503-2002](../../../regulations/gcc-gso-1503-2002.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1598-2002](../../../regulations/gcc-gso-1598-2002.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1624-2002](../../../regulations/gcc-gso-1624-2002.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1677-2002](../../../regulations/gcc-gso-1677-2002.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1680-1685-2003](../../../regulations/gcc-gso-1680-1685-2003.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1707-2005](../../../regulations/gcc-gso-1707-2005.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1708-2005](../../../regulations/gcc-gso-1708-2005.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-1709-2005](../../../regulations/gcc-gso-1709-2005.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-36-2005](../../../regulations/gcc-gso-36-2005.md) | summary, un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-37-2012](../../../regulations/gcc-gso-37-2012.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-38-2005](../../../regulations/gcc-gso-38-2005.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-39-2005](../../../regulations/gcc-gso-39-2005.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-40-2011](../../../regulations/gcc-gso-40-2011.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-41-2007](../../../regulations/gcc-gso-41-2007.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-42-2015](../../../regulations/gcc-gso-42-2015.md) | summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-51-2007](../../../regulations/gcc-gso-51-2007.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-52-2007](../../../regulations/gcc-gso-52-2007.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-53-2007](../../../regulations/gcc-gso-53-2007.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-ece-125](../../../regulations/gcc-gso-ece-125.md) | body → reference stub, summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-ece-13h-2012](../../../regulations/gcc-gso-ece-13h-2012.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-ece-43-gso-3538](../../../regulations/gcc-gso-ece-43-gso-3538.md) | body → reference stub, summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-ece-46](../../../regulations/gcc-gso-ece-46.md) | body → reference stub, summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-ece-51](../../../regulations/gcc-gso-ece-51.md) | body → reference stub, summary | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-ece-83-gso-ece-154](../../../regulations/gcc-gso-ece-83-gso-ece-154.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-gso-my2027-emission-limit-implementation](../../../regulations/gcc-gso-my2027-emission-limit-implementation.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [gcc-mc-250905-2025](../../../regulations/gcc-mc-250905-2025.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [in-ais-038-rev-2-ais-156](../../../regulations/in-ais-038-rev-2-ais-156.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [jp-srrv-japan-motor-vehicle-noise-requirements](../../../regulations/jp-srrv-japan-motor-vehicle-noise-requirements.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [jp-srrv-windshield-wiping-washing-defrosting-and-defogging](../../../regulations/jp-srrv-windshield-wiping-washing-defrosting-and-defogging.md) | body → reference stub, summary | Own limited body/heading; legal text and currency unverified. |
| [kr-workbook-reg-0597-noise-and-vibration-control-act-vehicle-noise](../../../regulations/kr-workbook-reg-0597-noise-and-vibration-control-act-vehicle-noise.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [other-workbook-reg-0648-iso-6469-series](../../../regulations/other-workbook-reg-0648-iso-6469-series.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [us-stub-us-epa-40-cfr-part-86-tier-3](../../../regulations/us-stub-us-epa-40-cfr-part-86-tier-3.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |
| [us-workbook-reg-0451-49-cfr-part-575](../../../regulations/us-workbook-reg-0451-49-cfr-part-575.md) | body → reference stub, summary | Own limited body/heading; legal text and currency unverified. |
| [za-workbook-reg-0623-vc-8056](../../../regulations/za-workbook-reg-0623-vc-8056.md) | un_equivalent | Own limited body/heading; legal text and currency unverified. |

All remaining summary/index/link record IDs are in [inventory-after.json](inventory-after.json). No record review coverage gap remains; external legal authentication and complete technical text coverage remain open.

Branch publication: [review/2026-10-06-content](https://github.com/MontiPy/Regulatory-Repository/tree/review/2026-10-06-content) was pushed successfully. Logical commits: `b59fa82` validators/inventory, `6e43f84` content, `4e006f0` evidence/adjudication/report; final documentation polish follows on the same branch. No PR opened and main untouched.
