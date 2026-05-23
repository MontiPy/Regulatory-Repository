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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPREADSHEET = ROOT / "reference" / "passenger_vehicle_regulatory_reference_repository_v3_cleaned.xlsx"
REGULATIONS_DIR = ROOT / "regulations"


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
    df = load_spreadsheet()
    written: list[Path] = []

    # --- GCC ---
    print("\nGenerating GCC stubs ...")
    for _, row in df[df["Market Family"] == "GCC / Middle East"].iterrows():
        reg_id = _safe(row["Regulation ID"])
        title = _safe(row["Regulation Title"]) or reg_id
        file_id = _gcc_id(row)
        source_url = _safe(row["Source URL(s)"]).split(";")[0].strip()
        body = _build_body(row, title)
        path = _write_stub(file_id, title, "GCC", reg_id, source_url, True,
                           _GCC_TRANSLATION, body, REGULATIONS_DIR, dry_run)
        written.append(path)
        print(f"  {'[dry-run] ' if dry_run else ''}OK -> {path.name}")

    # --- China ---
    print("\nGenerating China (CN) stubs ...")
    for _, row in df[df["Market Family"] == "China"].iterrows():
        reg_id = _safe(row["Regulation ID"])
        title = _safe(row["Regulation Title"]) or reg_id
        file_id = _cn_id(row)
        source_url = _safe(row["Source URL(s)"]).split(";")[0].strip()
        body = _build_body(row, title)
        path = _write_stub(file_id, title, "CN", reg_id, source_url, True,
                           _CN_TRANSLATION, body, REGULATIONS_DIR, dry_run)
        written.append(path)
        print(f"  {'[dry-run] ' if dry_run else ''}OK -> {path.name}")

    # --- Taiwan ---
    print("\nGenerating Taiwan (TW) stubs ...")
    for _, row in df[df["Market Family"] == "Taiwan"].iterrows():
        reg_id = _safe(row["Regulation ID"])
        title = _safe(row["Regulation Title"]) or reg_id
        file_id = _tw_id(row)
        source_url = _safe(row["Source URL(s)"]).split(";")[0].strip()
        body = _build_body(row, title)
        path = _write_stub(file_id, title, "TW", reg_id, source_url, False,
                           _TW_TRANSLATION, body, REGULATIONS_DIR, dry_run)
        written.append(path)
        print(f"  {'[dry-run] ' if dry_run else ''}OK -> {path.name}")

    # --- India ---
    print("\nGenerating India (IN) stubs ...")
    for _, row in df[df["Market Family"] == "India"].iterrows():
        reg_id = _safe(row["Regulation ID"])
        title = _safe(row["Regulation Title"]) or reg_id
        file_id = _in_id(row)
        source_url = _safe(row["Source URL(s)"]).split(";")[0].strip()
        paywall = _IN_PAYWALL.get(reg_id, False)
        body = _build_body(row, title)
        path = _write_stub(file_id, title, "IN", reg_id, source_url, paywall,
                           _IN_TRANSLATION, body, REGULATIONS_DIR, dry_run)
        written.append(path)
        print(f"  {'[dry-run] ' if dry_run else ''}OK -> {path.name}")

    # --- US state laws / cross-market (missing from eCFR manifest) ---
    print("\nGenerating US stub entries ...")
    # Filter to only entries not reachable via eCFR (don't start with standard CFR prefixes)
    us_all = df[df["Market Family"] == "United States"]
    cfr_prefixes = ("FMVSS", "49 CFR", "40 CFR", "47 CFR")
    us_stubs = us_all[~us_all["Regulation ID"].astype(str).apply(
        lambda x: any(x.startswith(p) for p in cfr_prefixes)
    )]
    # Also skip entries already on disk (e.g. us-40cfr-part-86 covers EPA Tier 3)
    for _, row in us_stubs.iterrows():
        reg_id = _safe(row["Regulation ID"])
        title = _safe(row["Regulation Title"]) or reg_id
        file_id = _us_stub_id(row)
        if (REGULATIONS_DIR / f"{file_id}.md").exists() and not dry_run:
            print(f"  skip (exists) {file_id}.md")
            continue
        source_url = _safe(row["Source URL(s)"]).split(";")[0].strip()
        body = _build_body(row, title)
        path = _write_stub(file_id, title, "US", reg_id, source_url, False,
                           _US_TRANSLATION, body, REGULATIONS_DIR, dry_run)
        written.append(path)
        print(f"  {'[dry-run] ' if dry_run else ''}OK -> {path.name}")

    # --- Japan non-JVSR (SRRV/TRIAS, Emissions, Noise, Fuel Economy, Recall, Radio, ELV) ---
    print("\nGenerating Japan non-JVSR stubs ...")
    jp_all = df[df["Market Family"] == "Japan"]
    jp_non_jvsr = jp_all[~jp_all["Regulation ID"].astype(str).str.startswith("Article")]
    for _, row in jp_non_jvsr.iterrows():
        reg_id = _safe(row["Regulation ID"])
        title = _safe(row["Regulation Title"]) or reg_id
        file_id = _jp_srrv_id(row)
        # Deduplicate: if same file_id already written, append index
        base_id = file_id
        counter = 2
        while (REGULATIONS_DIR / f"{file_id}.md").exists() or file_id in {p.stem for p in written}:
            file_id = f"{base_id}-{counter}"
            counter += 1
        source_url = _safe(row["Source URL(s)"]).split(";")[0].strip()
        body = _build_body(row, title)
        path = _write_stub(file_id, title, "JP", reg_id, source_url, False,
                           _JP_TRANSLATION, body, REGULATIONS_DIR, dry_run)
        written.append(path)
        print(f"  {'[dry-run] ' if dry_run else ''}OK -> {path.name}")

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
