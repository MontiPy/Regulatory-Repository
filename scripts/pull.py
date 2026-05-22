"""Stage 1 orchestrator — pulls regulations from official APIs into regulations/*.md."""
from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure stdout/stderr handle Unicode on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REGULATIONS_DIR = ROOT / "regulations"
MANIFESTS_DIR = ROOT / "manifests"
CONNECTORS_DIR = ROOT / "connectors"
REPORT_PATH = ROOT / ".pull_report.txt"

sys.path.insert(0, str(ROOT))

REGION_CONNECTOR = {
    "US": ("connectors.ecfr", "manifests/us.yaml"),
    "EU": ("connectors.eurlex", "manifests/eu.yaml"),
    "KR": ("connectors.law_go_kr", "manifests/kr.yaml"),
    "AU": ("connectors.au_legislation", "manifests/au.yaml"),
    "JP": ("connectors.egov_jp", "manifests/jp.yaml"),
    "CA": ("connectors.justice_ca", "manifests/ca.yaml"),
}


def pull_region(region: str, only: str | None = None) -> list[tuple[str, str]]:
    if region not in REGION_CONNECTOR:
        print(f"Unknown region: {region}")
        return []

    module_name, manifest_rel = REGION_CONNECTOR[region]
    manifest_path = ROOT / manifest_rel

    if not manifest_path.exists():
        print(f"  Manifest not found: {manifest_path}")
        return []

    import importlib
    try:
        mod = importlib.import_module(module_name)
    except ImportError as exc:
        print(f"  Connector not available for {region}: {exc}")
        return []

    print(f"\nPulling {region} from {manifest_path.name} ...")
    pulled = mod.pull(manifest_path, REGULATIONS_DIR)
    return [(str(p), "OK") for p in pulled]


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull regulations from official APIs.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--region", choices=list(REGION_CONNECTOR), help="Pull one region.")
    group.add_argument("--all", action="store_true", help="Pull all regions.")
    parser.add_argument("--only", help="Filter: e.g. section=108 or celex=32019R2144")
    args = parser.parse_args()

    regions = list(REGION_CONNECTOR) if args.all else [args.region]
    report_lines: list[str] = [f"Pull run: {datetime.now(timezone.utc).isoformat(timespec='seconds')}"]
    total = 0

    for region in regions:
        results = pull_region(region, only=args.only)
        for path, status in results:
            report_lines.append(f"{status} {path}")
            total += 1

    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"\nDone. {total} record(s) written. See .pull_report.txt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
