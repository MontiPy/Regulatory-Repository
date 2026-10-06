"""Aggregate swarm review findings (review/findings/*.json) into one table.

Checks coverage against review/shards/*.json, normalises verdict/severity,
collapses the per-record "no regulation text" boilerplate into one systemic
line, and writes review/findings_all.json plus a console summary.

Usage: python scripts/review_aggregate.py
"""
from __future__ import annotations

import json
import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review"
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


def _is_stub_body(f: dict) -> bool:
    return f.get("field") == "body" and "text" in " ".join(str(f.get(key, "")) for key in ("evidence", "current", "proposed")).lower()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prefix", default="", help="Select one review run without importing older findings")
    parser.add_argument("--coverage-dir", type=Path, help="Coverage sidecars for JSON-list findings")
    parser.add_argument("--out", type=Path, default=REVIEW / "findings_all.json")
    args = parser.parse_args()
    shards = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((REVIEW / "shards").glob(f"{args.prefix}*.json"))}
    rows: list[dict] = []
    missing_shards, coverage_gaps, bad_files = [], {}, []
    stub_bodies: set[str] = set()
    for name, shard in shards.items():
        path = REVIEW / "findings" / f"{name}.json"
        if not path.exists():
            missing_shards.append(name)
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            bad_files.append(f"{name}: {exc}")
            continue
        if isinstance(data, list):
            coverage_path = args.coverage_dir / f"{name}.json" if args.coverage_dir else None
            try:
                coverage = json.loads(coverage_path.read_text(encoding="utf-8")) if coverage_path else {}
            except (OSError, json.JSONDecodeError) as exc:
                bad_files.append(f"{name} coverage: {exc}")
                coverage = {}
            data = {"findings": data, "reviewed": coverage.get("reviewed", [])}
        gap = sorted(set(map(str, shard["items"])) - set(map(str, data.get("reviewed", []))))
        if gap:
            coverage_gaps[name] = gap
        for f in data.get("findings", []):
            required = {"id", "field", "verdict", "severity", "current", "proposed", "evidence", "evidence_url", "confidence"}
            if not isinstance(f, dict) or required - f.keys():
                bad_files.append(f"{name}: invalid finding schema")
                continue
            if str(f["id"]) not in set(map(str, shard["items"])):
                bad_files.append(f"{name}: finding id outside fixed shard: {f['id']}")
                continue
            f = {**f, "shard": name, "kind": shard["kind"]}
            f["severity"] = str(f.get("severity", "low")).lower()
            f["verdict"] = str(f.get("verdict", "questionable")).lower()
            if not args.prefix and shard["kind"] == "records" and _is_stub_body(f):
                stub_bodies.add(str(f.get("id")))
                continue
            rows.append(f)
    rows.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 3), f["kind"], str(f.get("id"))))
    out = {
        "shards_total": len(shards),
        "shards_missing": missing_shards,
        "unparseable": bad_files,
        "coverage_gaps": coverage_gaps,
        "stub_body_records": sorted(stub_bodies),
        "counts": {
            "severity": dict(Counter(f["severity"] for f in rows)),
            "verdict": dict(Counter(f["verdict"] for f in rows)),
            "kind": dict(Counter(f["kind"] for f in rows)),
        },
        "findings": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"shards {len(shards) - len(missing_shards)}/{len(shards)} done; missing: {missing_shards}")
    print("unparseable:", bad_files or "none")
    print("coverage gaps:", coverage_gaps or "none")
    print(f"stub-body records (collapsed): {len(stub_bodies)}")
    print("findings:", out["counts"])
    return 1 if missing_shards or coverage_gaps or bad_files else 0


if __name__ == "__main__":
    sys.exit(main())
