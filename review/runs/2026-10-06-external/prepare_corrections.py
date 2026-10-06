"""Stage exact, reviewable corrections from this run's retained official sources."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path

import frontmatter
import yaml

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
EVIDENCE = RUN / "evidence"
SOURCES = EVIDENCE / "sources"


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


source_rows = {}
for p in EVIDENCE.glob("*-sources.json"):
    for row in json.loads(p.read_text()):
        if row.get("name") and row.get("retrieved_at", "") >= source_rows.get(row["name"], {}).get("retrieved_at", ""):
            source_rows[row["name"]] = row


def source(name):
    row = source_rows[name]
    assert row["availability"] == "response_retrieved" and not row["truncated"], name
    raw = gzip.decompress((ROOT / row["raw_path"]).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == row["sha256"], name
    return row


def text(name):
    return (ROOT / source(name)["text_path"]).read_text()


patches = {}
knowledge = []
bodies = []


def record(rid, why, **changes):
    patches[rid] = {**patches.get(rid, {}), **changes, "_why": why}


def edit(file, old, new, why):
    assert old != new
    knowledge.append({"file": file, "old": old, "new": new, "_why": why})


def body(rid, new, names, note):
    post = frontmatter.load(ROOT / "regulations" / (rid + ".md"))
    path = RUN / "proposed-bodies" / (rid + ".md")
    path.parent.mkdir(exist_ok=True)
    path.write_text(new.strip() + "\n")
    bodies.append({
        "id": rid,
        "expected_body_sha256": hashlib.sha256(post.content.encode()).hexdigest(),
        "proposed_body": str(path.relative_to(ROOT)),
        "sources": [{k: source(n)[k] for k in ("url", "sha256", "retrieved_at")} for n in names],
        "note": note,
    })


removal = source("fmvss216-removal-final")
assert "Effective date: July 6, 2026." in text("fmvss216-removal-final")
record(
    "us-fmvss-216", "FR 2026-11068 removes §571.216 effective 6 July 2026; API now returns 404.",
    status="withdrawn",
    title="FMVSS 216 — Roof crush resistance (historic; removed 6 July 2026)",
    source_url=removal["url"],
    status_note="Removed from 49 CFR effective 6 July 2026 by FR 2026-11068 (3 June 2026). The retained body is historic; use current FMVSS 216a for roof-crush requirements.",
    summary="Historic FMVSS 216 set strength requirements for the passenger compartment roof to reduce rollover roof-crush injuries. NHTSA removed this obsolete standard effective 6 July 2026 (FR 2026-11068); FMVSS 216a supplies the current roof-crush requirements.",
)
post = frontmatter.load(ROOT / "regulations/us-fmvss-216.md")
body("us-fmvss-216",
     "**Historic text:** NHTSA removed §571.216 effective 6 July 2026. "
     "[Removal final rule](" + removal["url"] + "). Use [FMVSS 216a](https://www.ecfr.gov/current/title-49/part-571/section-571.216a) for current requirements.\n\n" + post.content,
     ["fmvss216-removal-final"], "Retain the old text as history, with an explicit withdrawal notice.")
cafe = text("cafe-2026-final")
assert "effective November 30, 2026" in cafe and "beginning with credits earned in MY 2028" in cafe
for rid in ("us-cfr-part-531", "us-cfr-part-533"):
    record(rid, "FR 2026-19964 effective date; retained body matches current eCFR API as of 1 Oct 2026.",
           status_note="SAFE Vehicles Rule III (FR 2026-19964, published 30 September 2026) amends the standards effective 30 November 2026. The retained body matches current eCFR text as of 1 October 2026; it does not incorporate the future-effective amendments.")
record("us-cfr-part-536", "FR 2026-19964 limits the elimination to inter-manufacturer trading of credits earned MY2028 onward.",
       status_note="SAFE Vehicles Rule III (FR 2026-19964) is effective 30 November 2026 and eliminates inter-manufacturer trading for credits earned in MY2028 onward. Earlier earned credits retain their applicable trading rules; distinguish trading from intra-manufacturer transfers.")

elv = text("eu-publication-32026R1738")
assert "1\u00a0September 2028" in elv or "1 September 2028" in elv
record("eu-32000l0053", "Regulation (EU) 2026/1738 Articles 57 and 59: phased application and repeal, not immediate wholesale repeal.",
       status_note="Entered into force on publication, 21 October 2000. Regulation (EU) 2026/1738 entered into force 13 August 2026 and generally applies from 1 September 2028; Article 57 repeals this Directive from that date with specified provisions retained until later dates. Specified Annex II points ceased to apply on 13 August 2026.")

for rid, name in (
    ("br-contran-215", "br-contran215-original"),
    ("br-contran-37", "br-contran37-official"),
    ("br-contran-498", "br-contran498-original"),
    ("br-contran-764", "br-contran764-original"),
    ("br-contran-924", "br-contran924-official"),
    ("br-senatran-990", "br-senatran990-republication"),
):
    record(rid, "Exact instrument located and retrieved from the Ministry of Transport archive; replace generic ATIC source.",
           source_url=source(name)["url"])
record("br-contran-37", "Official Article 2 covers continuous and intermittent sounds; Resolution 988/2022 updates its noise cross-reference.",
       summary="CONTRAN Resolution 37/1998 regulates anti-theft sound alarms and security accessories under CTB Art. 229. Accessories must not compromise vehicle safety; alarms must not imitate emergency-vehicle sounds or emit continuous or intermittent warnings longer than one minute. Resolution 988/2022 updates the maximum-noise cross-reference from 2 January 2023.",
       status_note="In force in the official CONTRAN catalogue; Article 2's maximum-noise cross-reference was amended by Resolution 988/2022 effective 2 January 2023.")
record("br-contran-498", "Official Articles 1–2 explicitly include fabricated, transformed and adapted vehicles regardless of seating capacity.",
       summary="CONTRAN Resolution 498/2014 requires interior lining materials of national and imported vehicles manufactured, transformed or adapted from 1 January 2015, regardless of seating capacity, to have flame propagation no greater than 100 mm/min under its annex test method. Certificates from international bodies recognised by the EU or USA are accepted.")
record("br-contran-764", "Official Articles 1–4 and 9 provide limits, exceptions, UN R28 alternative and applicability date.",
       summary="CONTRAN Resolution 764/2018 sets the vehicle horn test method and limits of 87–112 dB(A), or 83–112 dB(A) for category L vehicles up to 7 kW. It excludes competition vehicles, agricultural traction machines, industrial work machines and tractors. Article 4 permits applicable UN R28 performance test results as an alternative; Article 8 gives effect to the requirements from 1 January 2022.",
       un_equivalent=["UN R28"])
record("br-contran-924", "Official Article 3 includes utilitário and camioneta as well as buses; 27 May 2022 correction changes first-registration cutoff to 2024.",
       vehicle_categories=["Passenger car", "Light truck", "Bus"],
       summary="CONTRAN Resolution 924/2022 regulates mirrors, camera-monitor equipment and equivalent indirect-vision devices on school-transport utilitário, camioneta, bus and microbus vehicles. Annexes IV–VI apply from 1 January 2024 to new projects first registered in RENAVAM from that date (as corrected 27 May 2022), and from 1 January 2026 to the other vehicles specified in Article 4.",
       status_note="In force from 1 April 2022. Read Article 4(I) with the official correction of 27 May 2022: the first brand/model/version registration cutoff is 1 January 2024, not 2019. Brazilian national vehicle definitions govern scope.")
record("br-contran-245-330", "Official Resolution 559/2015 Article 1 and the current catalogue confirm suspended effects.",
       status_note="Resolution 559/2015 suspends the effects of Resolution 245/2007 and Article 4 of Resolution 330/2009. The official catalogue still records that suspension on 6 October 2026. This record is not evidence of a current mandatory factory-installation schedule.")

# Correct the isolated safety-law applicability sentences in emissions overviews.
for rid, name, new_app in (
    ("us-stub-us-epa-40-cfr-part-86-tier-3", "official-us-stub-us-epa-40-cfr-part-86-tier-3",
     "**Applicability:** EPA Tier 3 emission standards under the Clean Air Act cover light-duty vehicles, light-duty trucks, medium-duty passenger vehicles and specified heavy-duty vehicles, with phase-ins beginning in model year 2017. Its gasoline sulfur provisions are fuel requirements; consult 40 CFR Parts 80 and 86 for exact category, model-year and phase-in provisions."),
    ("ca-workbook-reg-0145-eccc-sor-2003-2", "ca-mvsr-sor-2003-2",
     "**Applicability:** SOR/2003-2 under the Canadian Environmental Protection Act, 1999 regulates emissions from prescribed classes of on-road vehicles and engines, including light-duty vehicles, heavy-duty vehicles and engines, and motorcycles. Consult its category definitions, model-year provisions and evidence-of-conformity requirements."),
):
    post = frontmatter.load(ROOT / "regulations" / (rid + ".md"))
    old_app = next(line for line in post.content.splitlines() if line.startswith("**Applicability:**"))
    body(rid, post.content.replace(old_app, new_app, 1), [name],
         "Source-backed correction to one copied applicability sentence; remaining body is an engineering overview.")

# Preserve source text as separate original/amending documents, never as invented consolidations.
def pdf_text(name):
    # Normalize blank lines/form feeds only; preserve extracted wording and reading order.
    return re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text(name).replace("\f", "\n\n")).strip()

def extracted(rid, sections, notice):
    post = frontmatter.load(ROOT / "regulations" / (rid + ".md"))
    result = "# " + post["title"] + "\n\n" + notice + "\n\n"
    for label, name in sections:
        result += "## " + label + "\n\n[Official document](" + source(name)["url"] + ")\n\n" + pdf_text(name) + "\n\n"
    body(rid, result, [n for _, n in sections], notice)

pdf_notice = "**Source text in Portuguese:** Text extracted from the official publication and annexes. PDF reading order, tables and diagrams may not survive extraction; use the linked original documents for technical interpretation. This is not a current consolidated edition."
original37 = text("br-contran37-official")
original37 = original37[original37.index("Fixa normas"):original37.index("Este texto não substitui")]
original37 = original37.strip()
body("br-contran-37", "# Anti-theft sound alarms and security accessories\n\n"
     "**Version note:** Original Resolution 37/1998 followed by the separate amendment 988/2022, effective 2 January 2023. Read the original noise cross-reference with that amendment; this is not an official consolidation.\n\n"
     "## Resolution 37/1998 — original text\n\n[Official source](" + source("br-contran37-official")["url"] + ")\n\n"
     + original37 + "\n\n## Amendment 988/2022\n\n[Official amendment](" + source("br-contran988-original")["url"] + ")\n\n"
     + pdf_text("br-contran988-original"),
     ["br-contran37-official", "br-contran988-original"], "Original and dated amendment retained separately; summary rechecked against both.")
extracted("br-contran-498", [("Resolution 498/2014 and annex", "br-contran498-original")], pdf_notice)
extracted("br-contran-764", [("Resolution 764/2018 and annex", "br-contran764-original")], pdf_notice)
extracted("br-contran-924", [
    ("Correction published 27 May 2022", "br-contran924-correction"),
    ("Resolution 924/2022 — original publication", "br-contran924-official"),
    ("Annexes I–VI", "br-contran924-annexes")],
    pdf_notice + " **Article 4(I) correction:** the original 2019 registration cutoff must be read as 2024, as corrected on 27 May 2022.")
extracted("br-senatran-990", [("Ordinance 990/2022 — republication, 19 August 2022", "br-senatran990-republication")],
          pdf_notice + " The republication includes Articles 1–28 and Annexes I–VII; Article 28 sets entry into force on 1 September 2022.")
eu_body = (EVIDENCE / "eu1151-body.md").read_text()
assert len(eu_body) > 1_000_000 and "[Figure: see official source]" in eu_body
body("eu-32017r1151", "**Version and extraction note:** Original 2017 publication of Regulation (EU) 2017/1151, retrieved from the EU Publications Office on 6 October 2026. Later amendments are not consolidated here. Embedded figures are marked explicitly; consult the [official document](https://publications.europa.eu/resource/celex/32017R1151) for diagrams and mathematical notation.\n\n" + eu_body,
     ["eu-publication-32017R1151"], "Replace the EUR-Lex large-document notice with actual original legal text; later amendment currency remains unverified.")

# Treaty values apply to the named state/entity, not to automatic UN Regulation recognition.
t58 = json.loads((EVIDENCE / "un-1958-treaty-participants.json").read_text())
t98 = json.loads((EVIDENCE / "un-1998-treaty-participants.json").read_text())
single = {
    "US": "United States of America", "CA": "Canada", "MX": "Mexico", "BR": "Brazil",
    "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "CN": "China", "JP": "Japan",
    "KR": "Republic of Korea", "IN": "India", "TH": "Thailand", "MY": "Malaysia",
    "ID": "Indonesia", "PH": "Philippines", "VN": "Viet Nam", "SG": "Singapore",
    "AU": "Australia", "NZ": "New Zealand", "EU": "European Union",
    "GB": "United Kingdom of Great Britain and Northern Ireland", "TR": "Türkiye",
    "UA": "Ukraine", "SA": "Saudi Arabia", "AE": "United Arab Emirates", "IL": "Israel",
    "ZA": "South Africa", "EG": "Egypt", "NG": "Nigeria",
}
groups = {
    "CENTAM": ["Guatemala", "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama", "Belize"],
    "ANDEAN": ["Peru", "Ecuador", "Bolivia", "Venezuela"],
    "UY-PY": ["Uruguay", "Paraguay"],
    "SOUTH-ASIA": ["Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Bhutan", "Maldives"],
    "ASEAN-OTHER": ["Cambodia", "Lao People's Democratic Republic", "Myanmar", "Brunei Darussalam", "Timor-Leste"],
    "EFTA": ["Norway", "Iceland", "Liechtenstein", "Switzerland"],
    "BALKANS": ["Serbia", "Bosnia and Herzegovina", "Montenegro", "North Macedonia", "Albania", "Kosovo", "Republic of Moldova", "Georgia", "Azerbaijan"],
    "EAEU": ["Russian Federation", "Kazakhstan", "Belarus", "Armenia", "Kyrgyzstan"],
    "CENTRAL-ASIA": ["Uzbekistan", "Tajikistan", "Turkmenistan", "Mongolia"],
    "GCC-OTHER": ["Kuwait", "Qatar", "Bahrain", "Oman"],
    "LEVANT": ["Jordan", "Lebanon", "Iraq", "Syrian Arab Republic"],
    "SANCTIONED": ["Iran", "Democratic People's Republic of Korea", "Cuba", "Yemen"],
    "MAGHREB": ["Morocco", "Algeria", "Tunisia", "Libya"],
    "EAST-AFRICA": ["Kenya", "United Republic of Tanzania", "Uganda", "Rwanda", "Ethiopia"],
}
notes = {
    "EFTA": 'UN Treaty Collection checked 6 October 2026: Norway and Switzerland are 1958 parties; only Norway is a 1998 party. Null denotes mixed membership in this group, not a group-wide commitment.',
    "BALKANS": 'UN Treaty Collection checked 6 October 2026: all named states except Kosovo are listed under the 1958 Agreement; Albania, Azerbaijan and Moldova are listed under the 1998 Agreement. Both group flags are null because membership is mixed. National approval procedures require separate verification.',
    "EAEU": 'UN Treaty Collection checked 6 October 2026: all five states are 1958 parties. Kyrgyzstan acceded on 1 September 2023 (1958) and 26 June 2026 (1998). Armenia is not listed under the 1998 Agreement, so that group flag is null.',
    "CENTRAL-ASIA": 'UN Treaty Collection checked 6 October 2026: Uzbekistan (20 October 2025) and Mongolia (29 April 2026) acceded to the 1958 Agreement; Uzbekistan and Tajikistan are 1998 parties. Turkmenistan is not listed under either; mixed membership is represented by null.',
    "SOUTH-ASIA": 'UN Treaty Collection checked 6 October 2026: Pakistan acceded to the 1958 Agreement on 24 February 2020; the other five named states are not listed. None of the six is listed under the 1998 Agreement. Treaty membership does not itself establish national approval acceptance.',
    "ASEAN-OTHER": 'UN Treaty Collection checked 6 October 2026: Cambodia acceded to the 1958 Agreement on 3 February 2026; the other four named states are not listed. Cambodia declared it would not be bound by annexed UN Regulations until further notification. None of the five is listed under the 1998 Agreement.',
    "MAGHREB": 'UN Treaty Collection checked 6 October 2026: Tunisia is listed under both Agreements; Morocco, Algeria and Libya are not. Both group flags are null because membership is mixed.',
    "EAST-AFRICA": 'UN Treaty Collection checked 6 October 2026: Uganda acceded to both Agreements on 23 August 2022; the other four named states are not listed. Both group flags are null because membership is mixed.',
    "HK-MO": 'The UN Treaty Collection 1998 Agreement entry for China expressly extends the Agreement to Hong Kong and Macao. The true flag records territorial application through China, not separate contracting-party status (checked 6 October 2026).',
}
replace_notes = {
    "EFTA": "un_1958 true reflects Norway",
    "BALKANS": "Kosovo is not a UN member",
    "EAEU": "Kyrgyzstan is reported",
    "CENTRAL-ASIA": "Uzbekistan acceded",
    "SOUTH-ASIA": "Pakistan acceded",
    "MAGHREB": "Tunisia is a 1958",
}
coverage = []
for path in sorted((ROOT / "knowledge/markets").glob("*.yaml")):
    raw = path.read_text()
    blocks = re.findall(r"(?ms)^- code: .*?(?=^- code: |\Z)", raw)
    for block in blocks:
        row = yaml.safe_load(block)[0]
        code = row["code"]
        new = block
        before = {k: row.get(k) for k in ("un_1958", "un_1998")}
        after = before.copy()
        members = [single[code]] if code in single else groups.get(code)
        detail = {}
        if members:
            for k, table in (("un_1958", t58), ("un_1998", t98)):
                detail[k] = {member: table.get(member) for member in members}
                flags = [member in table for member in members]
                after[k] = flags[0] if all(f == flags[0] for f in flags) else None
        if code == "HK-MO":
            # Source footnote 2, rather than absence of separate participant names.
            assert "Special Administrative Regions of Hong Kong and Macao" in text("un-1998-treaty")
            after["un_1998"] = True
        for k, value in after.items():
            token = "null" if value is None else str(value).lower()
            new = re.sub(r"(?m)^  " + k + r": (?:true|false|null)$", "  " + k + ": " + token, new)
        if code in notes:
            note = json.dumps(notes[code], ensure_ascii=False)
            if code in replace_notes:
                marker = replace_notes[code]
                matches = [line for line in new.splitlines() if marker in line]
                assert len(matches) == 1, code
                old = matches[0]
                indent = '  notes: [' if old.startswith('  notes: [') else '    - '
                replacement = indent + note + (']' if indent.endswith('[') else '')
                # Pakistan's import-policy note is separate from treaty membership.
                if code == "SOUTH-ASIA":
                    replacement = '  notes: [' + note + ', "Sri Lanka has had periodic vehicle-import suspensions; check current import policy."]'
                new = new.replace(old, replacement, 1)
            elif "  notes:\n" in new:
                new = new.replace("  notes:\n", "  notes:\n    - " + note + "\n", 1)
            elif "  notes: [" in new:
                new = new.replace("  notes: [", "  notes: [" + note + ", ", 1)
            else:
                new = new.replace("  records:", "  notes: [" + note + "]\n  records:", 1)
        if new != block:
            edit("markets/" + path.name, block, new,
                 "UN Treaty Collection XI-B-16 and XI-B-32, complete party tables and relevant territorial/declaration notes, checked 6 October 2026.")
        coverage.append({"code": code, "before": before, "after": after,
                         "named_entity_checks": detail,
                         "scope": "Named state/entity or closed list; membership is separate from national UN Regulation application." if members else
                                  ("China's express territorial declaration authenticated for 1998 only." if code == "HK-MO" else
                                   "Open-ended or territorial profile: flags retained; no group-wide determination made."),
                         "changed": new != block})
dump(EVIDENCE / "treaty-profile-decisions.json", coverage)

# Knowledge policy corrections preserve YAML formatting using exact replacements.
americas = (ROOT / "knowledge/markets/americas.yaml").read_text()
edit("markets/americas.yaml",
     '# `un_1958` / `un_1998`: true / false, or null when not verified.',
     '# `un_1958` / `un_1998`: true / false for the named entity or all named group members;\n# null when unverified or mixed (see country-specific notes). Treaty membership\n# does not itself establish application or acceptance of particular UN Regulations.',
     'Clarify mixed-group and territorial flags after official party-table checks.')
def replace_line(file, raw, needle, new, why):
    lines = [line for line in raw.splitlines() if needle in line]
    assert len(lines) == 1, needle
    edit(file, lines[0], new, why)

replace_line("markets/americas.yaml", americas, '  emissions: "EPA Tier 3',
 '  emissions: "EPA Tier 3 → 2027+ criteria-pollutant standards. EPA rescinded the GHG endangerment finding and federal vehicle GHG standards (final rule published 18 February 2026). Public Law 119-16 disapproved the ACC II waiver on 12 June 2025; CARB adopted permanent emergency vehicle emissions regulations on 26 March 2026 allowing earlier standards while litigation over newer rules is resolved. NHTSA published the CAFE reset for MY2022–2031 on 30 September 2026 (SAFE Vehicles Rule III), effective 30 November 2026; inter-manufacturer trading ends for credits earned in MY2028 onward."',
 "Official EPA final rule, Public Law 119-16, CARB 26 March release and FR 2026-19964; future-effective CAFE change and limited credit scope.")
replace_line("markets/americas.yaml", americas, '  emissions: "ECCC On-Road',
 '  emissions: "ECCC On-Road Vehicle and Engine Emission Regulations cover criteria pollutants. Canada retains separate passenger-automobile/light-truck GHG regulations. The consolidated SOR/2010-201 still contains EVAS targets, including MY2026; the 15 August 2026 Canada Gazette Part I proposal would repeal EVAS and update US references to preserve existing Canadian GHG requirements. Enhanced future GHG standards are being developed; that proposal does not establish tighter MY2027–2032 targets."',
 "Current SOR/2010-201 and Gazette I 15 August 2026 reg2: proposed repeal/reference continuity, not new MY2027–2032 targets.")
replace_line("markets/americas.yaml", americas, '    - "EVAS repeal and replacement',
 '    - "Proposed EVAS repeal and US-reference updates (Canada Gazette Part I, 15 August 2026; comments close 29 October 2026). Separate enhanced future GHG standards remain under development; verify any final registration before treating repeal as effective."',
 "Gazette I reg2, 75-day comment period and entry into force on registration; no authenticated final repeal.")
europe = (ROOT / "knowledge/markets/europe.yaml").read_text()
replace_line("markets/europe.yaml", europe, '    - "End-of-Life Vehicles Regulation',
 '    - "ELV Regulation (EU) 2026/1738 is in force from 13 August 2026 and generally applies from 1 September 2028. Directive 2000/53/EC is repealed from that application date with staged exceptions in Article 57; check each circularity/recycled-content milestone separately."',
 "Official Regulation 2026/1738 Articles 57 and 59; distinguish entry into force, general application and staged repeal.")
cw = (ROOT / "knowledge/crosswalk.yaml").read_text()
replace_line("crosswalk.yaml", cw, '      US: { cite: "NHTSA CAFE',
 '      US: { cite: "NHTSA CAFE 49 CFR 531/533; SAFE Vehicles Rule III reset for MY2022–2031 effective 30 November 2026; test & label 40 CFR 600", records: [us-cfr-part-531, us-cfr-part-533, us-40cfr-part-600], note: "FR 2026-19964 was published 30 September 2026; its amendments are future-effective as of 6 October. Federal EPA vehicle GHG standards were rescinded in February 2026." }',
 "FR 2026-19964 effective date verified; do not present published future amendment as currently incorporated text.")
replace_line("crosswalk.yaml", cw, '      EU: { cite: "ELV Directive',
 '      EU: { cite: "ELV Directive 2000/53/EC; ELV Regulation (EU) 2026/1738; REACH (EC) 1907/2006; Batteries Regulation (EU) 2023/1542", records: [eu-32000l0053, eu-32023r1542], note: "ELV 2026/1738 is in force from 13 August 2026, generally applies from 1 September 2028, and repeals the Directive then with Article 57 exceptions. Batteries Regulation replaced Directive 2006/66/EC from 18 August 2025 with transitional exceptions." }',
 "Official ELV Articles 57/59 support staged dates, without claiming wholesale immediate Directive repeal.")
replace_line("crosswalk.yaml", cw, '      BR: {"cite": "CONTRAN 245',
 '      BR: { cite: "Mandatory factory anti-theft installation schedule suspended by CONTRAN 559/2015", records: [br-contran-245-330, br-contran-37], status: none, note: "This none status applies only to the suspended 245/2007 and 330/2009 installation schedule. Anti-theft sound alarms and fitted security accessories remain regulated by 37/1998, amended by 988/2022; other requirements must be checked separately." }',
 "Official Resolution 559 Article 1 and current catalogue confirm suspension; scoped none does not erase accessory regulation.")
un118 = (EVIDENCE / "browser-un118-body.txt").read_text()
assert "vehicles of categories M3, Classes II and III" in un118
replace_line("crosswalk.yaml", cw, '      UN: { cite: "UN R118 (buses only)"',
 '      UN: { cite: "UN R118 — M3 Classes II and III (02-series scope)", note: "Requirements apply when R118 approval is required by the jurisdiction or sought by the applicant. The 2015 publication covers vehicle and component approvals; check the applied amendment series and national scope. This is not a universal bus-fitment mandate." }\n      EU: { cite: "UN R118 via (EU) 2019/2144 Annex I and Annex II F16", records: [eu-32019r2144], note: "The original GSR publication lists M3 and the 02 series. That series covers Classes II and III; check later GSR amendments, the applied approval series and category before relying on this mapping." }',
 "Authenticated EUR-Lex 2015 R118 02-series §1.1 and GSR Annexes I/II F16; remove false no-requirement claim with explicit conditional scope.")

dump(RUN / "patches" / "external.json",
     {"group": "external", "patches": patches, "knowledge_patches": knowledge, "skipped": []})
dump(RUN / "body-proposals.json", bodies)
print(f"Staged {len(patches)} record metadata proposals, {len(knowledge)} knowledge replacements and {len(bodies)} body proposals.")
