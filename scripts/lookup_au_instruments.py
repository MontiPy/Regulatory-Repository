"""Look up Australian Design Rule instrument IDs from the Federal Register of Legislation.

Usage (run locally — requires outbound internet access):
    python scripts/lookup_au_instruments.py [--patch]

Without --patch: prints a YAML block of found entries to stdout.
With    --patch: updates manifests/au.yaml in place, appending newly found entries.

The legislation.gov.au Titles API returns all legislative instruments; we filter
for titles matching "Design Rule" or "ADR" and extract their instrument IDs.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifests" / "au.yaml"

API_BASE = "https://api.prod.legislation.gov.au/v1"
BROWSE_BASE = "https://www.legislation.gov.au"

# ADR numbers we want to find, mapped to a hint title for the manifest
ADR_TARGETS = {
    "ADR 1":   "ADR 1 - Reversing Lamps",
    "ADR 2":   "ADR 2 - Side Door Latches and Hinges",
    "ADR 5":   "ADR 5 - Anchorages for Seatbelts",
    "ADR 6":   "ADR 6 - Direction Indicators",
    "ADR 10":  "ADR 10 - Steering Column",
    "ADR 11":  "ADR 11 - Internal Sun Visors",
    "ADR 18":  "ADR 18 - Instrumentation",
    "ADR 21":  "ADR 21 - Instrument Panel",
    "ADR 22":  "ADR 22 - Head Restraints",
    "ADR 25":  "ADR 25 - Anti-theft Lock",
    "ADR 29":  "ADR 29 - Side Door Strength",
    "ADR 31":  "ADR 31 - Brake Systems for Passenger Cars",
    "ADR 43":  "ADR 43 - Vehicle Configuration and Dimensions",
    "ADR 46":  "ADR 46 - Headlamps",
    "ADR 47":  "ADR 47 - Retroreflectors",
    "ADR 48":  "ADR 48 - Rear Registration Plate Illumination",
    "ADR 49":  "ADR 49 - Front and Rear Position Lamps and Stop Lamps",
    "ADR 50":  "ADR 50 - Front Fog Lamps",
    "ADR 52":  "ADR 52 - Rear Fog Lamps",
    "ADR 60":  "ADR 60 - Centre High-mounted Stop Lamp",
    "ADR 61":  "ADR 61 - Vehicle Marking",
    "ADR 69":  "ADR 69 - Full Frontal Impact Occupant Protection",
    "ADR 72":  "ADR 72 - Dynamic Side Impact Occupant Protection",
    "ADR 73":  "ADR 73 - Offset Frontal Impact Occupant Protection",
    "ADR 81":  "ADR 81 - Fuel Consumption Labelling for Light Vehicles",
    "ADR 82":  "ADR 82 - Engine Immobilisers",
    "ADR 83":  "ADR 83 - External Noise",
    "ADR 85":  "ADR 85 - Pole Side Impact Performance",
    "ADR 88":  "ADR 88 - Electronic Stability Control",
    "ADR 89":  "ADR 89 - Brake Assist Systems",
    "ADR 90":  "ADR 90 - Steering System",
    "ADR 92":  "ADR 92 - External Projections",
    "ADR 93":  "ADR 93 - Forward Field of View",
    "ADR 94":  "ADR 94 - Audible Warning",
    "ADR 95":  "ADR 95 - Installation of Tyres",
    "ADR 98":  "ADR 98 - Advanced Emergency Braking",
    "ADR 107": "ADR 107 - Lane Keep Assist and Emergency Lane Keeping",
    "ADR 108": "ADR 108 - Reversing Technologies",
    "ADR 109": "ADR 109 - Electric Power Train Safety Requirements",
    "ADR 110": "ADR 110 - Hydrogen-Fuelled Vehicles Safety",
    "ADR 111": "ADR 111 - Advanced Emission Control for Light Vehicles",
    "ADR 112": "ADR 112 - Real Driving Emissions",
    "ADR 113": "ADR 113 - Acoustic Vehicle Alerting Systems",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "regulatory-repository/1.0 (+contact@example.com)"
    s.headers["Accept"] = "application/json"
    return s


def _fetch_page(sess: requests.Session, offset: int, page_size: int = 100) -> dict:
    url = f"{API_BASE}/Titles"
    params = {
        "text": "Design Rule",
        "pageSize": page_size,
        "pageNumber": offset // page_size + 1,
    }
    resp = sess.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _extract_adr_number(title_str: str) -> str | None:
    """Return 'ADR N' or 'ADR NN' from a title string, or None if not an ADR."""
    m = re.search(r"\bADR\s+(\d+)", title_str, re.IGNORECASE)
    if m:
        return f"ADR {m.group(1)}"
    return None


def fetch_all_adr_instruments(sess: requests.Session) -> dict[str, tuple[str, str]]:
    """Return {adr_key: (instrument_id, full_title)} for all found ADRs."""
    found: dict[str, tuple[str, str]] = {}
    page_size = 100
    offset = 0

    print("Querying legislation.gov.au for ADR instruments...", file=sys.stderr)
    while True:
        data = _fetch_page(sess, offset, page_size)
        items = data.get("titles", data.get("items", data.get("results", [])))
        if not items:
            # Try alternate response shape
            if isinstance(data, list):
                items = data
            else:
                break

        for item in items:
            title_str = item.get("title", "") or item.get("name", "") or str(item)
            instrument_id = item.get("id", "") or item.get("registerId", "")
            adr_key = _extract_adr_number(title_str)
            if adr_key and instrument_id:
                # Keep the most recent version (highest F-number or latest date)
                if adr_key not in found or instrument_id > found[adr_key][0]:
                    found[adr_key] = (instrument_id, title_str)
                    print(f"  Found {adr_key}: {instrument_id} — {title_str[:60]}", file=sys.stderr)

        total = data.get("total", data.get("count", len(items)))
        offset += page_size
        if offset >= total or not items:
            break
        time.sleep(0.5)

    return found


def load_existing_ids(manifest_path: Path) -> set[str]:
    """Return instrument IDs already in the manifest."""
    with manifest_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {r.get("instrument_id", "") for r in data.get("records", [])}


def build_new_entries(
    found: dict[str, tuple[str, str]],
    targets: dict[str, str],
    existing_ids: set[str],
) -> list[dict[str, str]]:
    new_entries = []
    for adr_key, hint_title in sorted(targets.items(), key=lambda kv: int(re.search(r"\d+", kv[0]).group())):
        if adr_key in found:
            instrument_id, full_title = found[adr_key]
            if instrument_id not in existing_ids:
                new_entries.append({
                    "instrument_id": instrument_id,
                    "title": hint_title,
                })
        else:
            print(f"  NOT FOUND: {adr_key} ({hint_title})", file=sys.stderr)
    return new_entries


def patch_manifest(manifest_path: Path, new_entries: list[dict[str, str]]) -> None:
    with manifest_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["records"].extend(new_entries)
    with manifest_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Patched {manifest_path} with {len(new_entries)} new entries.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Look up AU ADR instrument IDs and update manifests/au.yaml.")
    parser.add_argument("--patch", action="store_true", help="Write results into manifests/au.yaml (default: print only).")
    args = parser.parse_args()

    sess = _session()
    try:
        found = fetch_all_adr_instruments(sess)
    except requests.HTTPError as exc:
        print(f"ERROR: API returned {exc.response.status_code}. "
              f"Check network access to {API_BASE}.", file=sys.stderr)
        return 1
    finally:
        sess.close()

    existing_ids = load_existing_ids(MANIFEST_PATH)
    new_entries = build_new_entries(found, ADR_TARGETS, existing_ids)

    if not new_entries:
        print("No new entries found (all targets already in manifest or not matched).", file=sys.stderr)
        return 0

    if args.patch:
        patch_manifest(MANIFEST_PATH, new_entries)
    else:
        print("\n# New entries to add to manifests/au.yaml:")
        for entry in new_entries:
            print(f"  - {{ instrument_id: \"{entry['instrument_id']}\", title: \"{entry['title']}\" }}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
