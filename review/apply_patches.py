"""Validate and apply patch-writer output (review/patches/<group>.json) to regulations/*.md.

Every proposed value is validated before anything is written:
  * only whitelisted fields;
  * systems / commodities / vehicle_categories / status must be taxonomy values;
  * un_equivalent(_ai) items must match ^UN R\\d+[A-Z]?$;
  * effective_date must be YYYY-MM-DD; strings must be non-empty and free of "..." truncation.
Invalid fields are rejected (reported, not applied); the rest of the record's patch still applies.

Usage (repo root): python review/apply_patches.py [--dry-run] [--skip ID ...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "review"))
sys.path.insert(0, str(ROOT))
from apply_record_fixes import apply  # noqa: E402

TAX = yaml.safe_load((ROOT / "taxonomy.yaml").read_text(encoding="utf-8"))
UN_RE = re.compile(r"^UN R\d+[A-Z]?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LIST_TAX = {"systems": "systems", "commodities": "commodities", "vehicle_categories": "vehicle_categories"}
STRING_FIELDS = {"title", "summary", "status_note", "citation"}
ALLOWED = set(LIST_TAX) | STRING_FIELDS | {"status", "un_equivalent", "un_equivalent_ai", "effective_date", "_stub_body", "_confirmed"}


def validate(field: str, value) -> str | None:
    if field not in ALLOWED:
        return "field not allowed"
    if field in LIST_TAX:
        if not isinstance(value, list):
            return "must be a list"
        bad = [v for v in value if v not in TAX[LIST_TAX[field]]]
        return f"not in taxonomy: {bad}" if bad else None
    if field in ("un_equivalent", "un_equivalent_ai"):
        if not isinstance(value, list):
            return "must be a list"
        bad = [v for v in value if not (isinstance(v, str) and UN_RE.match(v))]
        return f"bad UN refs: {bad}" if bad else None
    if field == "status":
        return None if value in TAX["statuses"] else f"status '{value}' not allowed"
    if field == "effective_date":
        return None if isinstance(value, str) and DATE_RE.match(value) else "bad date"
    if field in ("_stub_body", "_confirmed"):
        return None if value is True else "must be true"
    if field in STRING_FIELDS:
        if not isinstance(value, str) or not value.strip():
            return "empty string"
        if value.rstrip().endswith("...") or value.rstrip().endswith("…"):
            return "truncated text"
        if field == "summary" and len(value) > 700:
            return "summary too long"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[], help="record ids to leave untouched (orchestrator veto)")
    ap.add_argument("--dir", default="patches", help="sub-directory of review/ holding <group>.json patch files")
    ap.add_argument("--label", default="Phase 3 — medium/high findings via patch writers (validated)")
    args = ap.parse_args()
    fixes: dict[str, dict] = {}
    rejected: list[str] = []
    for path in sorted((ROOT / "review" / args.dir).glob("*.json")):
        if path.name.endswith(".input.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for rid, patch in (data.get("patches") or {}).items():
            if rid in args.skip:
                rejected.append(f"{rid}: vetoed by orchestrator")
                continue
            if not (ROOT / "regulations" / f"{rid}.md").exists():
                rejected.append(f"{rid}: record does not exist")
                continue
            clean = {}
            for field, value in patch.items():
                if field.startswith("_why"):
                    continue
                err = validate(field, value)
                if err:
                    rejected.append(f"{rid}.{field}: {err}")
                else:
                    clean[field] = value
            if clean.get("_stub_body") and "summary" not in clean:
                rejected.append(f"{rid}._stub_body: needs a corrected summary — skipped")
                clean.pop("_stub_body")
            if clean:
                fixes.setdefault(rid, {}).update(clean)
    print(f"{len(fixes)} records, {sum(len(v) for v in fixes.values())} fields valid; {len(rejected)} rejected")
    for r in rejected:
        print("  REJECTED", r)
    if args.dry_run:
        return 0
    lines = apply(fixes, args.label)
    if rejected:
        lines += ["", "Rejected by validator / orchestrator:", *[f"- {r}" for r in rejected]]
    with (ROOT / "review" / "CHANGES.md").open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"applied; {len(lines)} log lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
