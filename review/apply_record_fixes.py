"""Apply adjudicated review fixes to regulations/*.md and log every change.

Each entry in FIXES maps a record id to field updates. Special keys:
  _body_replace: [(old, new), ...]  literal replacements in the Markdown body
  _delete: True                      remove the record file (instrument does not exist / unverified)
Summaries written here are re-hashed against the current body so they are not flagged stale.

Run from the repo root: python review/apply_record_fixes.py <phase-label>
Appends a section to review/CHANGES.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build import _body_hash, clean_body  # noqa: E402

REG = ROOT / "regulations"
NOW = "2026-10-06T00:00:00+00:00"

STUB_BODY = (
    "# {title}\n\n"
    "**Reference stub — this repository does not hold the regulation text.** "
    "See the official source linked on this record.\n"
)

FIXES: dict[str, dict] = {
    # ── Australia ────────────────────────────────────────────────────────
    "au-f2011l02016": {
        "status_note": "Being superseded by ADR 79/05: applies to new models from 1 Dec 2025 and all new vehicles from 1 Jul 2028.",
        "un_equivalent_ai": ["UN R83"],
    },
    "au-f2012l01123": {
        "title": "ADR Definitions and Vehicle Categories 2005 — Amendment 6 (historic compilation)",
        "status": "superseded",
        "status_note": "No longer in force since 18 Mar 2014; use the current ADR Definitions and Vehicle Categories compilation.",
    },
    "au-f2023l01530": {"un_equivalent_ai": ["UN R134"]},
    "au-f2024l00161": {"un_equivalent_ai": ["UN R130"], "vehicle_categories": ["Heavy truck", "Bus"]},
    "au-workbook-reg-0604-new-vehicle-efficiency-standard-act-2024": {
        "summary": "The New Vehicle Efficiency Standard Act 2024 sets fleet-average CO2 (g/km) targets for suppliers of new "
                   "light vehicles in Australia, with credits and penalties from 1 July 2025. It does not itself set "
                   "pollutant-emission, OBD or fuel-consumption-label requirements (those are ADR 79, 111, 112 and 81).",
        "systems": ["Emissions"],
        "commodities": [],
        "un_equivalent_ai": [],
    },
    # ── Brazil (CONTRAN numbers bound to the wrong subject) ───────────────
    "br-contran-215": {
        "title": "Bull bars (quebra-mato) on vehicles up to 3,500 kg GVW",
        "summary": "CONTRAN Resolution 215/2006 regulates the manufacture, installation and use of bull bars (quebra-mato) "
                   "on motor vehicles up to 3,500 kg GVW, including an identification plate and INMETRO-registered "
                   "manufacturers, because they can affect frontal airbag performance and pedestrian injury risk.",
        "systems": ["Pedestrian protection", "Crashworthiness"],
        "commodities": ["Bumpers"],
        "vehicle_categories": ["Passenger car", "Light truck"],
        "un_equivalent_ai": [],
    },
    "br-contran-37": {
        "title": "Anti-theft sound alarms and security accessories",
        "summary": "CONTRAN Resolution 37/1998 sets rules for anti-theft sound alarms and other security accessories under "
                   "Art. 229 of the Brazilian Traffic Code: alarms must not imitate emergency-vehicle sounds, must not "
                   "sound continuously for more than one minute, and must not compromise vehicle safety.",
        "systems": ["Theft prevention", "Noise"],
        "commodities": [],
        "un_equivalent_ai": ["UN R116"],
    },
    "br-contran-498": {
        "title": "Flammability of vehicle interior lining materials",
        "summary": "CONTRAN Resolution 498/2014 requires interior lining materials of national and imported vehicles "
                   "manufactured from 1 Jan 2015 to have a flame propagation rate of no more than 100 mm/min; test "
                   "certificates recognised in the EU or USA are accepted.",
        "systems": ["Crashworthiness"],
        "commodities": ["Seats", "Body structure"],
        "un_equivalent_ai": ["UN R118"],
    },
    "br-contran-764": {
        "title": "Horn (audible warning device) sound-pressure test method",
        "summary": "CONTRAN Resolution 764/2018 sets the sound-pressure-level test method for vehicle horns (audible "
                   "warning devices).",
        "systems": ["Noise"],
        "commodities": ["Horn"],
        "un_equivalent_ai": ["UN R28"],
    },
    "br-contran-827": {"_delete": True},
    "br-contran-924": {
        "title": "Mirrors and indirect-vision devices for school-transport vehicles",
        "vehicle_categories": ["Bus"],
    },
    # ── Canada ───────────────────────────────────────────────────────────
    "ca-mvsr-c-r-c---c--1038-s108-1": {"status": "withdrawn", "status_note": "Repealed by SOR/2018-43, s. 4."},
    # ── China ────────────────────────────────────────────────────────────
    "cn-cnca-c11-01-2020": {
        "summary": "CNCA-C11-01:2020 is the China Compulsory Certification (CCC) implementation rule for motor vehicles. "
                   "It applies to M, N and O category vehicles (complete and incomplete), excluding low-speed vehicles, "
                   "and defines type testing, factory inspection and certificate maintenance.",
        "vehicle_categories": ["Passenger car", "Light truck", "Heavy truck", "Bus", "Trailer"],
    },
    "cn-gb-11551-2014": {"un_equivalent": ["UN R137"], "un_equivalent_ai": []},
    "cn-gb-11552": {
        "summary": "GB 11552-2009 covers the interior fittings of passenger cars (modified adoption of UN R21): energy "
                   "absorption and radii of interior surfaces, protrusions, controls, seat backs and power-operated "
                   "windows and sunroofs.",
        "un_equivalent_ai": ["UN R21"],
    },
    "cn-gb-13057": {
        "title": "Strength of seats and their anchorages of buses",
        "vehicle_categories": ["Bus"],
        "un_equivalent_ai": ["UN R80"],
        "commodities": ["Seats"],
    },
    "cn-gb-14166-2024": {"un_equivalent": ["UN R16"], "un_equivalent_ai": []},
    "cn-gb-14167-2024": {"un_equivalent_ai": ["UN R145"]},
    "cn-gb-19578": {
        "summary": "GB 19578-2024 sets mass-based fuel-consumption limits for passenger cars (about 18% tighter than the "
                   "2021 edition), applying to new type approvals from 1 Jan 2026 and to approved types by 1 Jan 2028. "
                   "It is a fuel-consumption standard, not an emissions or OBD standard.",
        "systems": ["Emissions"],
    },
    "cn-gb-26572-2025": {
        "status": "upcoming",
        "status_note": "Published; applies from 1 Aug 2027.",
    },
    "cn-gb-27887-2024": {
        "summary": "GB 27887-2024 sets requirements and dynamic tests for child restraint systems themselves (including "
                   "ISOFIX/i-Size CRS). Vehicle anchorages are covered by GB 14167-2024.",
    },
    "cn-gb-34660": {
        "status": "upcoming",
        "status_note": "GB 34660-2026 applies from 1 Jul 2027; GB 34660-2017 remains in force until then.",
        "summary": "GB 34660 sets road-vehicle electromagnetic compatibility requirements: radiated and conducted emissions "
                   "and immunity of the vehicle and its electrical/electronic sub-assemblies (RF fields, transients, ESD).",
        "systems": ["EMC"],
        "commodities": ["ECUs", "Wiring"],
        "un_equivalent_ai": ["UN R10"],
    },
    "cn-gb-4599-2024": {
        "summary": "GB 4599-2024 covers road illumination devices and systems: passing- and driving-beam headlamps, front "
                   "fog lamps and cornering lamps for M and N vehicles.",
        "systems": ["Lighting & signaling"],
        "un_equivalent": ["UN R149"],
        "un_equivalent_ai": [],
    },
    "cn-gb-5920-2024": {"un_equivalent": ["UN R148"], "un_equivalent_ai": []},
    "cn-gb-9743-2024": {
        "summary": "GB 9743-2024 sets safety performance requirements for passenger-car pneumatic tyres: strength, "
                   "endurance, high-speed performance, load index / speed symbol and markings.",
        "commodities": ["Tires"],
        "un_equivalent_ai": [],
    },
    # ── UNECE ────────────────────────────────────────────────────────────
    "ece-r149": {
        "title": "UN Regulation No. 149 — Road Illumination Devices (RID)",
        "summary": "UN R149 is the consolidated road-illumination regulation: passing- and driving-beam headlamps, "
                   "adaptive front-lighting systems (AFS), front fog and cornering lamps. It replaces R98, R112, R113, "
                   "R119 and R123 for new approvals.",
        "_body_replace": [("Road Illumination Devices (except headlamps)", "Road Illumination Devices (RID)")],
    },
    "ece-r153": {
        "title": "UN Regulation No. 153 — Fuel System Integrity and Electric Power Train Safety in a Rear-End Collision",
        "summary": "UN R153 covers the integrity of the fuel system and the safety of the high-voltage electric power "
                   "train of M1 and N1 vehicles after a rear-end collision.",
        "_body_replace": [("Fuel System Integrity in a Frontal Collision",
                           "Fuel System Integrity and Electric Power Train Safety in a Rear-End Collision")],
    },
    "ece-r161": {
        "title": "UN Regulation No. 161 — Devices against Unauthorized Use",
        "summary": "UN R161 sets uniform provisions for protecting motor vehicles against unauthorized use and for "
                   "approving the locking device used for this purpose. (Pedal-misapplication control is UN R175.)",
        "systems": ["Theft prevention"],
        "commodities": ["Steering column", "ECUs"],
        "_body_replace": [("Pedal Misapplication Mitigation Systems", "Devices against Unauthorized Use")],
    },
    # ── EU ───────────────────────────────────────────────────────────────
    "eu-32006l0066": {
        "status": "superseded",
        "status_note": "Repealed by Regulation (EU) 2023/1542 (Batteries Regulation) with effect from 18 Aug 2025, with limited transitional exceptions.",
    },
    "eu-32009r0078": {
        "status": "superseded",
        "status_note": "Repealed by Regulation (EU) 2019/2144 with effect from 6 Jul 2022.",
    },
    "eu-32009r0661": {
        "status": "superseded",
        "status_note": "Repealed by Regulation (EU) 2019/2144 with effect from 6 Jul 2022.",
    },
    "eu-32017r1151": {"effective_date": "2017-07-27"},
    "eu-32023r2590": {"un_equivalent": []},
    # ── GCC ──────────────────────────────────────────────────────────────
    "gcc-gcc-ev-technical-regulation-draft": {"status": "proposed", "status_note": "Draft technical regulation — not yet in force."},
    "gcc-gso-ece-125": {
        "summary": "GSO-ECE 125 adopts UN R125 on the forward field of vision of motor-vehicle drivers (M1): limits on "
                   "A-pillar obscuration and required forward visibility. It is not a lighting regulation.",
        "systems": ["Visibility"],
        "commodities": ["Glass", "Body structure"],
        "un_equivalent_ai": ["UN R125"],
    },
    "gcc-gso-ece-13h-2012": {"un_equivalent": ["UN R13H"]},
    "gcc-gso-ece-43-gso-3538": {
        "summary": "GSO-ECE 43 / GSO 3538 adopt UN R43 on safety glazing materials and their installation: windscreens "
                   "and windows, impact, optical and light-transmission tests.",
        "systems": ["Glazing", "Visibility"],
        "commodities": ["Glass"],
        "un_equivalent_ai": ["UN R43"],
    },
    "gcc-gso-ece-46": {
        "summary": "GSO-ECE 46 adopts UN R46 on devices for indirect vision (mirrors and camera-monitor systems): fields of "
                   "view, installation and performance.",
        "systems": ["Visibility"],
        "commodities": ["Mirrors"],
        "un_equivalent_ai": ["UN R46"],
    },
    "gcc-uae-fuel-economy-standard-number-to-verify-gemini-cited-uae-s-5011": {"_delete": True},
    # ── India ────────────────────────────────────────────────────────────
    "in-ais-038-rev-2-ais-156": {
        "title": "India electric power train and REESS safety — AIS-038 Rev. 2 (M & N categories)",
        "summary": "AIS-038 Rev. 2 sets electric power train and traction-battery (REESS) safety requirements for M and N "
                   "category vehicles (UN R100 counterpart). AIS-156 is the equivalent standard for L-category two- and "
                   "three-wheelers and does not apply to passenger cars or light trucks.",
        "citation": "AIS-038 (Rev. 2); AIS-156 applies to L-category only",
    },
    # ── Japan ────────────────────────────────────────────────────────────
    "jp-jvsregs-art43-7": {"un_equivalent_ai": ["UN R138"]},
    "jp-srrv-accelerator-control": {
        "summary": "Japan's accelerator-control requirements (return-to-idle and control behaviour) under the Safety "
                   "Regulations for Road Vehicles and TRIAS test procedures. This record is a reference stub without "
                   "regulation text.",
        "systems": ["Tell-tales & controls"],
        "commodities": ["Pedals"],
        "un_equivalent_ai": [],
        "_stub_body": True,
    },
    "jp-srrv-audible-warning-devices": {
        "summary": "Japan's audible warning device (horn) requirements — sound level and tone — under the Safety "
                   "Regulations for Road Vehicles (UN R28 applied). This record is a reference stub without regulation text.",
        "systems": ["Noise"],
        "commodities": ["Horn"],
        "_stub_body": True,
    },
    "jp-srrv-electric-vehicle-rechargeable-energy-storage-system": {"citation": "SRRV / TRIAS / UN R100"},
    "jp-srrv-engine-power-train-and-pedal-lever": {
        "summary": "Japan's requirements for the engine, power transmission and pedal/lever arrangement (Safety "
                   "Regulations for Road Vehicles Art. 8; fuel devices are Art. 15). This record is a reference stub "
                   "without regulation text.",
        "systems": [],
        "commodities": ["Pedals"],
        "un_equivalent_ai": [],
        "_stub_body": True,
    },
    # ── Cross-cutting standards ──────────────────────────────────────────
    "other-workbook-reg-0643-iso-26262": {"un_equivalent": [], "un_equivalent_ai": []},
    "other-workbook-reg-0644-iso-21448": {"un_equivalent": [], "un_equivalent_ai": []},
    # ── United States ────────────────────────────────────────────────────
    "us-cfr-part-531": {"status_note": "Standards reset by NHTSA SAFE Vehicles Rule III (FR 2026-19964, 30 Sep 2026, effective 30 Nov 2026); text here predates it — re-pull."},
    "us-cfr-part-533": {"status_note": "Standards reset by NHTSA SAFE Vehicles Rule III (FR 2026-19964, 30 Sep 2026, effective 30 Nov 2026); text here predates it — re-pull."},
    "us-fmvss-124": {"un_equivalent_ai": []},
    "us-stub-dodd-frank-section-1502-regulation-eu-2017-821": {
        "title": "Conflict-minerals due diligence — US Dodd-Frank §1502 (SEC Rule 13p-1) and EU Regulation 2017/821 (two separate instruments)",
        "systems": [],
    },
    "us-stub-title-13-ccr-1961-4-1962-4-1962-8": {
        "status_note": "Federal waiver for ACC II revoked by Congress under the CRA (12 Jun 2025); enforcement in litigation.",
    },
    "us-stub-us-epa-40-cfr-part-86-tier-3": {
        "summary": "EPA Tier 3 (40 CFR Part 86, Subpart S) sets exhaust and evaporative emission standards for light-duty "
                   "vehicles, light-duty trucks and medium-duty passenger vehicles, plus a 10 ppm gasoline sulfur limit. "
                   "It is a Clean Air Act rule, separate from the FMVSS in 49 CFR Part 571.",
        "vehicle_categories": ["Passenger car", "Light truck"],
        "un_equivalent_ai": [],
    },
}


def fmt(v) -> str:
    return "∅" if v in (None, "", []) else str(v)[:160]


def apply(fixes: dict[str, dict], label: str) -> list[str]:
    log = [f"\n## {label}\n", "| Record | Field | Before | After |", "|---|---|---|---|"]
    for rid, changes in fixes.items():
        path = REG / f"{rid}.md"
        if not path.exists():
            raise SystemExit(f"missing record {rid}")
        if changes.get("_delete"):
            path.unlink()
            log.append(f"| `{rid}` | (record) | exists | **deleted** |")
            continue
        raw = path.read_text(encoding="utf-8")
        post = frontmatter.loads(raw)
        meta = post.metadata
        for old, new in changes.get("_body_replace", []):
            if old not in post.content:
                raise SystemExit(f"{rid}: body text not found: {old!r}")
            post.content = post.content.replace(old, new)
            log.append(f"| `{rid}` | body | {fmt(old)} | {fmt(new)} |")
        if changes.get("_stub_body"):
            post.content = STUB_BODY.format(title=meta.get("title"))
            log.append(f"| `{rid}` | body | wrong-topic template text | honest reference stub |")
        for field, value in changes.items():
            if field.startswith("_"):
                continue
            before = meta.get(field)
            if value in ([], "") :
                meta.pop(field, None) if field in ("status_note",) else meta.__setitem__(field, value)
            else:
                meta[field] = value
            log.append(f"| `{rid}` | {field} | {fmt(before)} | {fmt(value)} |")
        if changes.get("_confirmed") and "summary" not in changes:
            log.append(f"| `{rid}` | summary | (checked against current text) | confirmed |")
        if "summary" in changes or changes.get("_confirmed") or changes.get("_body_replace") or changes.get("_stub_body"):
            meta["summary_hash"] = _body_hash(clean_body(post.content, str(meta.get("source_api", ""))))
            meta["summary_generated_at"] = NOW
        out = frontmatter.dumps(post)
        if raw.endswith("\n") and not out.endswith("\n"):
            out += "\n"
        path.write_text(out, encoding="utf-8")
    return log


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "Phase 1 — accepted high-severity record fixes"
    lines = apply(FIXES, label)
    changes = ROOT / "review" / "CHANGES.md"
    if not changes.exists():
        changes.write_text("# Changes applied from the content-accuracy review\n", encoding="utf-8")
    with changes.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"applied {len(FIXES)} record fix sets; {len(lines) - 3} changes logged")
