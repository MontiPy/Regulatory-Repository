"""Generate stub .md regulation files from the reference spreadsheet.

Used for regions where no live connector exists (paywalled standards, scattered
sources with no public API). Content is sourced from the Comprehensive Guide
sheet; stubs carry source_api=spreadsheet so the UI shows the appropriate banner.

Usage:
    python scripts/gen_stubs.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPREADSHEET = ROOT / "reference" / "passenger_vehicle_regulatory_reference_repository_v3_cleaned.xlsx"
REGULATIONS_DIR = ROOT / "regulations"
SPREADSHEET_MANIFEST = ROOT / "manifests" / "spreadsheet.yaml"


@dataclass(frozen=True)
class StubTarget:
    file_id: str
    workbook_id: str
    market_family: str
    region_body: str
    title: str
    region: str
    citation: str
    source_url: str
    paywall: bool
    translation_status: str
    body: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slugify(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def _safe(val: Any) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()


def _build_body(row: pd.Series, title: str) -> str:
    parts = [f"# {title}\n"]

    regulated_area = _safe(row.get("Regulated Area", ""))
    applicability = _safe(row.get("Applicability", ""))
    intent = _safe(row.get("Key Compliance Intent", ""))
    systems = _safe(row.get("Primary Vehicle Systems / CBUs Impacted", ""))
    failure_modes = _safe(row.get("Failure Modes / Symptoms by CBU Impact", ""))
    related = _safe(row.get("Related Regulations", ""))
    notes = _safe(row.get("Notes / Engineering Considerations", ""))

    if regulated_area:
        parts.append(f"**Regulated Area:** {regulated_area}\n")
    if applicability:
        parts.append(f"**Applicability:** {applicability}\n")
    if intent:
        parts.append(f"\n## Key Compliance Intent\n\n{intent}")
    if systems:
        parts.append(f"\n## Primary Vehicle Systems and Components\n\n{systems}")
    if failure_modes:
        parts.append(f"\n## Failure Modes and Symptoms\n\n{failure_modes}")
    if related:
        parts.append(f"\n## Related Regulations\n\n{related}")
    if notes:
        parts.append(f"\n## Engineering Considerations\n\n{notes}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Stub target definitions
# Each entry: (market_family filter, id_prefix, region_code, paywall, translation_status, id_override_fn)
# id_override_fn(row) -> str | None  (return None to use auto-slug)
# ---------------------------------------------------------------------------

def _gcc_id(row: pd.Series) -> str:
    return "gcc-" + _slugify(str(row["Regulation ID"]))


def _cn_id(row: pd.Series) -> str:
    return "cn-" + _slugify(str(row["Regulation ID"]))


def _tw_id(row: pd.Series) -> str:
    return "tw-" + _slugify(str(row["Regulation ID"]))


def _in_id(row: pd.Series) -> str:
    return "in-" + _slugify(str(row["Regulation ID"]))


def _us_stub_id(row: pd.Series) -> str:
    return "us-stub-" + _slugify(str(row["Regulation ID"]))


def _jp_srrv_id(row: pd.Series) -> str:
    title = _safe(row.get("Regulation Title", str(row["Regulation ID"])))
    return "jp-srrv-" + _slugify(title)


def _workbook_id(row: pd.Series, region: str) -> str:
    repo_id = _safe(row.get("Repo ID", "workbook")).lower()
    return f"{region.lower()}-workbook-{repo_id}-{_slugify(str(row['Regulation ID']))}"


# Paywall overrides per India entry
_IN_PAYWALL = {
    "AIS-038 Rev.2 / AIS-156": True,
}

# Translation status overrides
_TW_TRANSLATION = ""   # law.moj.gov.tw has English
_IN_TRANSLATION = ""   # English
_US_TRANSLATION = ""   # English
_JP_TRANSLATION = "untranslated"   # Japanese
_GCC_TRANSLATION = "untranslated"  # Arabic/English bilingual but paywalled
_CN_TRANSLATION = "untranslated"   # Chinese

_EXTRA_WORKBOOK_STUB_IDS = {
    # Workbook rows that are not covered as row-level Markdown by live connectors.
    "REG-0145",
    "REG-0358",
    "REG-0359",
    "REG-0360",
    "REG-0370",
    "REG-0371",
    "REG-0372",
    "REG-0451",
    "REG-0546",
    "REG-0568",
    "REG-0569",
    "REG-0596",
    "REG-0597",
    "REG-0598",
    "REG-0599",
    "REG-0604",
    "REG-0605",
    "REG-0610",
    "REG-0612",
    "REG-0613",
    "REG-0614",
    "REG-0615",
    "REG-0616",
    "REG-0617",
    "REG-0618",
    "REG-0619",
    "REG-0620",
    "REG-0622",
    "REG-0623",
    "REG-0624",
    "REG-0627",
    "REG-0628",
    "REG-0629",
    "REG-0630",
    "REG-0637",
    "REG-0639",
    "REG-0641",
    "REG-0642",
    "REG-0643",
    "REG-0644",
    "REG-0645",
    "REG-0646",
    "REG-0647",
    "REG-0648",
    "REG-0649",
    "REG-0650",
    "REG-0651",
    "REG-0652",
}

_REGION_BY_MARKET = {
    "Argentina / Mercosur": "AR",
    "ASEAN": "ASEAN",
    "Australia": "AU",
    "Brazil": "BR",
    "Canada": "CA",
    "China": "CN",
    "GCC / Middle East": "GCC",
    "India": "IN",
    "Israel": "IL",
    "Japan": "JP",
    "Mexico": "MX",
    "New Zealand": "NZ",
    "Other / Cross-Market": "OTHER",
    "South Africa": "ZA",
    "South Korea": "KR",
    "Taiwan": "TW",
    "Turkey": "TR",
    "United States": "US",
}

_TRANSLATION_BY_REGION = {
    "AR": "untranslated",
    "ASEAN": "untranslated",
    "CN": _CN_TRANSLATION,
    "EAEU": "untranslated",
    "GCC": _GCC_TRANSLATION,
    "IL": "untranslated",
    "JP": _JP_TRANSLATION,
    "KR": "untranslated",
    "MX": "untranslated",
    "TR": "untranslated",
}


def load_spreadsheet() -> pd.DataFrame:
    df_idx = pd.read_excel(SPREADSHEET, sheet_name="Regulation Index")
    df_guide = pd.read_excel(SPREADSHEET, sheet_name="Comprehensive Guide")
    # Both sheets have 652 rows in the same order — join by position
    guide_cols = ["Key Compliance Intent", "Primary Vehicle Systems / CBUs Impacted",
                  "Failure Modes / Symptoms by CBU Impact", "Related Regulations",
                  "Notes / Engineering Considerations", "Applicability", "Regulated Area"]
    for col in guide_cols:
        if col in df_guide.columns and col not in df_idx.columns:
            df_idx[col] = df_guide[col].values
    return df_idx


def _region_for_row(row: pd.Series) -> str:
    market_family = _safe(row.get("Market Family", ""))
    region_body = _safe(row.get("Region / Standard Body", ""))

    if market_family == "Europe / UNECE":
        if any(token in region_body for token in ("EAEU", "Russia", "Customs Union")):
            return "EAEU"
        if "EU" in region_body and "UNECE / 1958" not in region_body:
            return "EU"
        return "ECE"

    return _REGION_BY_MARKET.get(market_family, "OTHER")


def _is_legacy_stub_row(row: pd.Series) -> bool:
    market_family = _safe(row.get("Market Family", ""))
    reg_id = _safe(row.get("Regulation ID", ""))

    if market_family in {"GCC / Middle East", "China", "Taiwan", "India"}:
        return True

    if market_family == "United States":
        cfr_prefixes = ("FMVSS", "49 CFR", "40 CFR", "47 CFR")
        return not any(reg_id.startswith(prefix) for prefix in cfr_prefixes)

    if market_family == "Japan":
        return not reg_id.startswith("Article")

    return False


def _should_generate_stub(row: pd.Series) -> bool:
    return _is_legacy_stub_row(row) or _safe(row.get("Repo ID", "")) in _EXTRA_WORKBOOK_STUB_IDS


def _base_file_id(row: pd.Series, region: str) -> str:
    market_family = _safe(row.get("Market Family", ""))
    repo_id = _safe(row.get("Repo ID", ""))

    if _is_legacy_stub_row(row) and repo_id not in _EXTRA_WORKBOOK_STUB_IDS:
        if market_family == "GCC / Middle East":
            return _gcc_id(row)
        if market_family == "China":
            return _cn_id(row)
        if market_family == "Taiwan":
            return _tw_id(row)
        if market_family == "India":
            return _in_id(row)
        if market_family == "United States":
            return _us_stub_id(row)
        if market_family == "Japan":
            return _jp_srrv_id(row)

    return _workbook_id(row, region)


def _paywall_for_row(row: pd.Series, region: str) -> bool:
    reg_id = _safe(row.get("Regulation ID", ""))
    if region in {"CN", "GCC", "OTHER"}:
        return True
    if region == "IN":
        return _IN_PAYWALL.get(reg_id, False)
    return False


def _translation_for_row(region: str) -> str:
    return _TRANSLATION_BY_REGION.get(region, "")


def _source_url_for_row(row: pd.Series) -> str:
    return _safe(row.get("Source URL(s)", "")).split(";")[0].strip()


def plan_stub_targets(df: pd.DataFrame | None = None) -> list[StubTarget]:
    df = load_spreadsheet() if df is None else df
    targets: list[StubTarget] = []
    assigned_ids: set[str] = set()

    for _, row in df.iterrows():
        if not _should_generate_stub(row):
            continue

        region = _region_for_row(row)
        reg_id = _safe(row.get("Regulation ID", ""))
        title = _safe(row.get("Regulation Title", "")) or reg_id
        base_id = _base_file_id(row, region)
        file_id = base_id
        counter = 2
        while file_id in assigned_ids:
            file_id = f"{base_id}-{counter}"
            counter += 1
        assigned_ids.add(file_id)

        targets.append(
            StubTarget(
                file_id=file_id,
                workbook_id=_safe(row.get("Repo ID", "")),
                market_family=_safe(row.get("Market Family", "")),
                region_body=_safe(row.get("Region / Standard Body", "")),
                title=title,
                region=region,
                citation=reg_id,
                source_url=_source_url_for_row(row),
                paywall=_paywall_for_row(row, region),
                translation_status=_translation_for_row(region),
                body=_build_body(row, title),
            )
        )

    return targets


def _manifest_record(target: StubTarget) -> dict[str, Any]:
    return {
        "id": target.file_id,
        "workbook_id": target.workbook_id,
        "market_family": target.market_family,
        "region_body": target.region_body,
        "region": target.region,
        "citation": target.citation,
        "title": target.title,
        "source_url": target.source_url,
    }


def _write_spreadsheet_manifest(targets: list[StubTarget], dry_run: bool) -> None:
    manifest = {
        "region": "SPREADSHEET",
        "connector": "gen_stubs",
        "description": (
            "Workbook-derived fallback records generated from the regulatory reference "
            "spreadsheet."
        ),
        "source": str(SPREADSHEET.relative_to(ROOT)).replace("\\", "/"),
        "records": [_manifest_record(target) for target in targets],
    }

    if dry_run:
        print(f"  [dry-run] would write {SPREADSHEET_MANIFEST.relative_to(ROOT)}")
        return

    SPREADSHEET_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    SPREADSHEET_MANIFEST.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_stub(
    file_id: str,
    title: str,
    region: str,
    citation: str,
    source_url: str,
    paywall: bool,
    translation_status: str,
    body: str,
    dest_dir: Path,
    dry_run: bool,
) -> Path:
    path = dest_dir / f"{file_id}.md"

    # Preserve existing tagging fields if file already exists
    existing_meta: dict[str, Any] = {}
    if path.exists():
        try:
            post = frontmatter.load(path)
            for field in ("commodities", "systems", "vehicle_categories", "tagging_status", "tagged_at"):
                if field in post.metadata:
                    existing_meta[field] = post.metadata[field]
        except Exception:
            pass

    meta: dict[str, Any] = {
        "id": file_id,
        "title": title,
        "region": region,
        "citation": citation,
        "status": "in-force",
        "source_url": source_url,
        "source_api": "spreadsheet",
        "last_pulled": _now_iso(),
        "tagging_status": existing_meta.get("tagging_status", "untagged"),
    }
    if paywall:
        meta["paywall"] = True
    if translation_status:
        meta["translation_status"] = translation_status
    meta.update({k: v for k, v in existing_meta.items() if k not in meta})

    if dry_run:
        print(f"  [dry-run] would write {path.name}")
        return path

    post = frontmatter.Post(body, **meta)
    dest_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return path


def generate_stubs(dry_run: bool = False) -> list[Path]:
    targets = plan_stub_targets()
    written: list[Path] = []

    print("\nGenerating spreadsheet-backed stubs ...")
    for target in targets:
        path = _write_stub(
            target.file_id,
            target.title,
            target.region,
            target.citation,
            target.source_url,
            target.paywall,
            target.translation_status,
            target.body,
            REGULATIONS_DIR,
            dry_run,
        )
        written.append(path)
        print(f"  {'[dry-run] ' if dry_run else ''}OK -> {path.name}")

    _write_spreadsheet_manifest(targets, dry_run)

    print(f"\nDone. {len(written)} stub(s) {'would be ' if dry_run else ''}written.")
    return written


def main() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Generate stub regulation .md files from reference spreadsheet.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be written without writing files.")
    args = parser.parse_args()
    generate_stubs(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
