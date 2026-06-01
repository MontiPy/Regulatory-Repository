# Continuation Point — 2026-05-22

## What was being done

Investigating why the UI showed only ~110 regulations when the reference spreadsheet
(`reference/passenger_vehicle_regulatory_reference_repository_v3_cleaned.xlsx`) lists 472
regulations in connector-covered regions. The goal was to pull all missing files and
rebuild the HTML.

---

## What was completed this session

### 1. Full coverage analysis

| Region | In Spreadsheet | Manifest | Pulled before | Now pulled |
|---|---|---|---|---|
| United States | 141 | 135 | 92 | 135 |
| Canada | 51 | 53 | 15 | 53 |
| South Korea | 69 | 79 | 10 | 79 |
| Europe / UNECE | 95 | 100 (EU 24 + ECE 76) | 13 | 100 |
| Japan | 52 | 31 | 15 | 31 |
| Australia | 64 | 90 | 13 | 90 |
| **TOTAL** | **472** | **488** | **158** | **488** |

### 2. Both pulls completed successfully

- `python scripts/pull.py --region AU` → 90/90 records OK
- `python scripts/pull.py --all` → **488/488 records OK, 0 failures**
  - ECE (76 entries): UNECE site returned 403 Forbidden, so all 76 files were written as
    **placeholder stubs** pointing to the canonical UNECE URL. Content will be empty but the
    entries exist and are browseable in the UI.

---

## What still needs to be done — IMMEDIATE

### Run the build

```
python scripts/build.py
```

This has NOT been run yet. `dist/index.html` still reflects the old 158-file state.
Running the build is the single step needed to surface all 488 regulations in the UI.

---

## Known permanent gaps (not fixable without new work)

### US — 6 regulations not reachable via eCFR

These appear in the reference spreadsheet under "United States" but cannot be pulled
by the existing eCFR connector:

| Regulation ID | Reason |
|---|---|
| Title 13 CCR 1961.4 / 1962.4-1962.8 | California state law — different source (CARB) |
| California Proposition 65 | State law, HTML-only source |
| MA General Laws Ch. 93K / Acts 2020 Ch. 386 | State law, no public API |
| Dodd-Frank §1502 / EU 2017/821 | Cross-jurisdictional, no single source |
| NOM-042-SEMARNAT-2003 | Mexican standard, misclassified in US family |

→ US manifest (135 entries) vs. spreadsheet (141) = 6 uncoverable this way.

### ECE — placeholder stubs only

The UNECE WP.29 website (`unece.org`) returned HTTP 403 during the pull, so all 76
ECE regulation files contain placeholder text (title + link) rather than actual
regulatory content. To get real content:

1. Try re-running `python scripts/pull.py --region ECE` from a different network
   (the 403 may be IP-rate-limiting or geo-blocking).
2. If the block persists, investigate whether UNECE provides a public download API or
   PDF bulk access.

### Japan — 21 spreadsheet rows not in manifest

The JP manifest covers the 31 main articles of 道路運送車両の保安基準 (JVSR) via e-Gov.
The spreadsheet also includes 21 additional Japan entries the current connector cannot
reach:

- SRRV / TRIAS entries (Art. 8 and UN R adoption refs: R28, R136, R139, R145, R157,
  R6/R7/R23/R38) — these are ministerial notices (告示), different law from JVSR
- Road Transport Vehicle Act (道路運送車両法)
- Act on Recycling of End-of-Life Automobiles
- FY2030 Fuel Economy Standards
- Japan Motor Vehicle Exhaust Emission Standards
- Japan Vehicle Recall System
- Noise Regulation Law
- Radio Act / MIC-TELEC Technical Conformity

These need separate e-Gov law IDs and possibly extended connector logic. The notation
difference (Article 11-2 in spreadsheet vs. 11_2 in manifest) is NOT a real gap —
the connector handles both forms.

---

## TODO.md update needed

The `TODO.md` "Pending: Pull + Rebuild Required" section is now stale. It should be
updated to:
- Remove the AU / US EPA pending items (done)
- Add: "Run `python scripts/build.py` to rebuild dist/index.html"
- Add permanent gap notes for ECE (403 stubs), US 6 entries, JP 21 SRRV/Acts entries
