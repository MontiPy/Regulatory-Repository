"""GCC/GSO connector — link + framework-reference enrichment.

GCC member states adopt UN/ECE regulations; individual GSO standards are sold,
so full text is not captured. This connector gives each gcc-* record a live
public source link (the consolidated GSO Technical Regulations PDF) and a
framework-reference body, preserving the LLM tags and UN cross-references built
in API-2. No per-standard parsing (the master PDF's table is column-wise and
unreliable to reconstruct).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import frontmatter
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, write_md

MASTER_URL = (
    "https://static.gso.org.sa/gso-public-docs/conformity/mutabiq/"
    "GSO_TechnicalRegulations_MV_2027_MY-D2.pdf"
)


def master_pdf_live(session: Any) -> bool:
    """True iff the consolidated GSO PDF responds 200 with a PDF content type."""
    try:
        resp = session.get(MASTER_URL, stream=True)
    except Exception:
        return False
    if getattr(resp, "status_code", 200) != 200:
        return False
    return "pdf" in resp.headers.get("Content-Type", "").lower()


def build_body(citation: str, title: str | None, url: str, reachable: bool) -> str:
    head = f"{citation} — {title}" if title else citation
    lines = [f"# {head}", "", f"**Citation:** {citation}", ""]
    if reachable:
        lines += [
            "This Gulf (GSO) standard is part of the **GCC Technical Regulation for Motor "
            "Vehicles**. Individual GSO standards are published and sold by the GCC "
            "Standardization Organization; their full text is not freely available. The "
            "consolidated list of GSO motor-vehicle technical regulations (number, model "
            "year, subject) is published by GSO:",
            "",
            f"[GSO Technical Regulations for Motor Vehicles (consolidated list)]({url})",
        ]
    else:
        lines += [
            "This Gulf (GSO) standard is part of the GCC Technical Regulation for Motor "
            "Vehicles. Individual GSO standards are sold by the GCC Standardization "
            "Organization. The consolidated GSO regulation list could not be reached "
            "automatically at build time; see the source link for the official record.",
            "",
            f"[Official source]({url})",
        ]
    return "\n".join(lines)


def _load_existing(path: Path) -> tuple[dict[str, Any], str]:
    """Return (frontmatter metadata, body content) for an existing record."""
    if not path.exists():
        return {}, ""
    post = frontmatter.load(path)
    return dict(post.metadata), (post.content or "")


def is_gso_record(citation: str, source_url: str) -> bool:
    """True if this GCC record is a GSO standard (belongs to the GSO master
    regulation), vs a member-state / third-party record (e.g. Saudi SASO, UAE
    MOIAT, TÜV) that has its own accurate source and must not be repointed."""
    return citation.strip().upper().startswith("GSO") or "gso.org.sa" in (source_url or "")


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}

    session = RateLimitedSession(rate=0.5)
    reachable = master_pdf_live(session)
    print(f"  GSO master PDF reachable: {reachable}")

    pulled: list[Path] = []
    failed: list[str] = []
    for entry in manifest.get("records", []):
        file_id = str(entry.get("id", "")).strip()
        citation = str(entry.get("citation", "")).strip()
        fallback_url = str(entry.get("source_url", "")).strip()
        if not file_id or not citation:
            continue

        # Leave member-state / third-party GCC records (SASO, MOIAT, TÜV, UAE.S)
        # untouched — they are not GSO standards and have their own accurate source.
        if not is_gso_record(citation, fallback_url):
            print(f"  Skipping GCC {citation} (non-GSO member-state/third-party record)")
            continue

        existing, existing_body = _load_existing(dest_dir / f"{file_id}.md")
        print(f"  Enriching GCC {citation} ...", end=" ", flush=True)
        try:
            url = MASTER_URL if reachable else (fallback_url or existing.get("source_url") or MASTER_URL)
            title = existing.get("title") or citation
            # Preserve the existing curated body; the framework stub is only a
            # fallback for records that have none. The master-PDF link lives in
            # frontmatter source_url.
            body = existing_body if existing_body.strip() else build_body(
                citation, existing.get("title"), url, reachable)

            record: dict[str, Any] = {
                "id": file_id, "title": title, "region": "GCC", "citation": citation,
                "status": existing.get("status") or "in-force",
                "source_url": url, "source_api": "gso",
                "tagging_status": existing.get("tagging_status", "untagged"),
            }
            for field in ("un_equivalent", "un_equivalent_ai", "aliases",
                          "translation_status", "paywall", "tagged_at"):
                if existing.get(field) not in (None, [], ""):
                    record[field] = existing[field]

            pulled.append(write_md(record, body, dest_dir))
            print("OK")
        except Exception as exc:
            failed.append(f"{citation}: {exc}")
            print(f"FAILED: {exc}")

    session.close()
    if failed:
        print(f"\n{len(failed)} failure(s):")
        for msg in failed:
            print(f"  {msg}")
    return pulled
