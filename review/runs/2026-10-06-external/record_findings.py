"""Retain adjudication separately from HTTP retrieval outcomes."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
E = RUN / "evidence"
rows = {}
for p in E.glob("*-sources.json"):
    for row in json.loads(p.read_text()):
        name = row.get("name")
        if name and row.get("retrieved_at", "") >= rows.get(name, {}).get("retrieved_at", ""):
            rows[name] = row

def evidence(name, phrase):
    row = rows[name]
    assert row["availability"] == "response_retrieved" and not row["truncated"], name
    text = re.sub(r"\s+", " ", (ROOT / row["text_path"]).read_text())
    normalized = re.sub(r"\s+", " ", phrase)
    index = text.lower().find(normalized.lower())
    assert index >= 0, (name, phrase)
    return {"source": name, "url": row["url"], "sha256": row["sha256"],
            "retrieved_at": row["retrieved_at"], "text_path": row["text_path"],
            "quote": text[max(0, index - 100):index + len(normalized) + 200]}

findings = []
def add(id, severity, decision, claim, references=(), limitation=None):
    findings.append({"id": id, "severity": severity, "decision": decision, "claim": claim,
                     "evidence": [evidence(*ref) for ref in references], "limitation": limitation})

add("EXT-001", "high", "applied",
    "FMVSS 216 is withdrawn effective 6 July 2026; retain its body only as history and link current 216a.",
    [("fmvss216-removal-final", "Effective date: July 6, 2026.")])
add("EXT-002", "medium", "applied",
    "SAFE Vehicles Rule III is published but future-effective on 30 November 2026. Inter-manufacturer trading ends for credits earned in MY2028 onward.",
    [("cafe-2026-final", "effective November 30, 2026"), ("cafe-2026-final", "beginning with credits earned in MY 2028")])
add("EXT-003", "high", "applied",
    "The 15 August Canadian proposal repeals EVAS and updates references; it is not a proposal establishing tighter MY2027–2032 GHG targets.",
    [("ca-2026-evas-proposal", "works to develop enhanced greenhouse gas emission standards")],
    "A proposal/announcement does not amend the consolidated regulation before final registration.")
add("EXT-004", "medium", "confirmed",
    "Consolidated Canadian SOR/2010-201 still includes MY2026-onward ZEV provisions.",
    [("ca-mvsr-sor-2010-201", "30.11")], "No authenticated final EVAS repeal retrieved.")
add("EXT-005", "medium", "applied",
    "ELV Regulation 2026/1738 is in force from 13 August 2026, generally applies 1 September 2028, and contains phased Directive repeals.",
    [("eu-publication-32026R1738", "Directive 2000/53/EC is repealed with effect from 1 September 2028"),
     ("eu-publication-32026R1738", "It shall apply from 1 September 2028.")])
add("EXT-006", "medium", "applied",
    "Official treaty party lists support state/entity flags, mixed-group notes and recent accessions; China expressly extends 1998 to Hong Kong/Macao.",
    [("un-1958-treaty", "Cambodia"), ("un-1998-treaty", "Special Administrative Regions of Hong Kong and Macao")],
    "See treaty-profile-decisions.json for all 48 profiles. Treaty membership alone does not establish regulation adoption or E-mark recognition.")
add("EXT-007", "medium", "applied",
    "Replace six generic Brazilian third-party links with exact official instruments; import source text for five Brazilian records.",
    [("br-senatran990-republication", "PORTARIA Nº 990")],
    "The DOC for 215 was downloaded but not text-extracted. Paid ABNT and the generic safety-label record remain unresolved.")
add("EXT-008", "medium", "applied",
    "Resolution 924 covers school-transport utilitário/camioneta as well as buses; the correction changes Article 4(I)'s first-registration cutoff from 2019 to 2024.",
    [("br-contran924-official", "veículos do tipo utilitário, camioneta, ônibus e micro-ônibus"),
     ("br-contran924-correction", "a partir de 1º de janeiro de 2024")],
    "Coarse repository categories are browsing aids; Brazilian national definitions govern applicability.")
add("EXT-009", "medium", "applied",
    "Anti-theft factory-installation effects are suspended by Resolution 559/2015; accessory and sound-alarm rules remain distinct.",
    [("br-contran559-original", "Art. 1º"), ("br-contran37-official", "sons contínuos ou intermitentes")])
add("EXT-010", "medium", "applied",
    "Repair copied FMVSS/MVSR applicability sentences in the Tier 3 and Canadian emissions overviews.",
    [("official-us-stub-us-epa-40-cfr-part-86-tier-3", "some heavy-duty vehicles"),
     ("ca-mvsr-sor-2003-2", "Canadian Environmental Protection Act, 1999")],
    "The remaining bodies are engineering overviews, not authentic regulation text.")
add("EXT-011", "medium", "applied",
    "Replace the EUR-Lex large-document notice in 2017/1151 with its actual original 2017 legal text.",
    [("eu-publication-32017R1151", "2017/1151")],
    "Later amendments are not consolidated; 783 embedded images were replaced by explicit figure pointers. The official source remains necessary for mathematical notation and diagrams.")
add("EXT-012", "medium", "confirmed_source_ambiguity",
    "The FMVSS224 4,356/4,536 discrepancy and Part561 exactly-4,536 boundary ambiguity are present in the official source.",
    [("us-fmvss-224", "4,356"), ("us-cfr-part-561", "4,536")],
    "Preserve legal wording; obtain authoritative clarification before treating the apparent errors as corrected.")
add("EXT-013", "low", "confirmed_source_artifact",
    "Part588 'se-mail', CA116 'of a every', and FMVSS120 punctuation reproduce official source text.",
    [("us-cfr-part-588", "se-mail"), ("ca-mvsr-c-r-c---c--1038-s116", "of a every")],
    "FMVSS120 also matches the current official XML under whitespace normalization; no silent copy edit applied.")
add("EXT-014", "high", "held",
    "UN R83's 09-series placeholder is also present in official EU publication; authentic commencement remains unresolved.",
    [("eu-publication-42026X1086", "XX September 2026 (TBC)")],
    "CN214–217/2026 relate to older amendment submissions and do not supply an authenticated 09-series commencement date.")
add("EXT-015", "medium", "held",
    "ADR60's instrument-table name conflict, ADR99's 00/01 conflict, and ADR45's absent applicability table are source artifacts.",
    [("au-adr60-text-original", "Reversing"),
     ("au-adr99-text-original", "99/01"),
     ("au-adr45-text-original", "table")],
    "No guessed table reconstruction or silent operative-clause repair.")
add("EXT-016", "high", "held",
    "The Korean checker is pinned to lsiSeq270023, a March 2025 version; that cannot establish current translation currency.",
    [("kmvss-history-page", "2025. 3. 15.")],
    "Current name/ID/body routes timed out or failed. The checker itself failed with HTTP502. No stale/clean translation verdict is supported.")
add("EXT-017", "medium", "held",
    "Korean Article26 bus-category bridge and omitted attached technical tables remain unauthenticated.",
    [], "Do not substitute broad repository categories for unverified national definitions.")
add("EXT-018", "medium", "confirmed",
    "Euro7 M1/N1 new-type/new-vehicle dates and the small-volume exception are supported by the official original publication.",
    [("eu-publication-32024R1257", "29 November 2026")],
    "The original publication is not a complete review of later amendments or technical annexes.")
add("EXT-019", "medium", "confirmed_with_limit",
    "COM(2025)995 contains the proposed 90% 2035 target; retain proposal status.",
    [("eu-co2-proposal-parliament", "fleet-wide CO2 emission target for cars and vans from 100% to 90%")],
    "An adopted replacement and the latest legislative-procedure status were not independently authenticated.")
add("EXT-020", "medium", "confirmed_with_limit",
    "EPA's February 2026 federal vehicle GHG rescission and June2025 ACCII waiver disapproval are authenticated; CARB's March2026 response is documented.",
    [("epa-2026-ghg-final", "rescinding"),
     ("acc-ii-public-law", "June 12, 2025"),
     ("carb-emergency-2026", "March 26, 2026")],
    "CARB's press release documents its action; it is not a fresh court-docket review or the full adopted regulatory text.")
un118_text = (E / "browser-un118-body.txt").read_text()
un118_quote = next(line for line in un118_text.splitlines() if 'vehicles of categories M3, Classes II and III' in line)
import hashlib
findings.append({"id": "EXT-021", "severity": "medium", "decision": "applied",
                 "claim": "UN R118 is not a no-requirement mapping for buses. The retrieved 02-series scope covers M3 Classes II/III; the GSR original references that series.",
                 "evidence": [{"url": "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:42015X0421(01)",
                               "text_path": str((E / "browser-un118-body.txt").relative_to(ROOT)),
                               "text_sha256": hashlib.sha256(un118_text.encode()).hexdigest(),
                               "retrieval": "Chromium browser with verified proxy CA", "quote": un118_quote},
                              evidence("eu-publication-32019R2144", "F16 Flammability in buses")],
                 "limitation": "Conditional approval scope is stated explicitly. Original publication does not establish latest series or every national mandate."})
(E / "findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2) + "\n")
print(f"Retained {len(findings)} priority adjudications.")
