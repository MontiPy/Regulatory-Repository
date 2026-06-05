"""India/AIS connector — thin, network-free link refresh + framework body.

The 3 India records are framework aggregates (AIS standards under the CMVR,
administered by ARAI/MoRTH). The Ministry migrated morth.nic.in -> morth.gov.in;
this connector canonicalizes the stale domain, writes a CMVR/AIS framework body,
and preserves the LLM tags and UN cross-references from API-2. No network calls
(morth.gov.in is slow/timeout-prone; the domain rewrite is a strict improvement
over the redirecting morth.nic.in link regardless).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import frontmatter
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import write_md


def canonical_url(url: str) -> str:
    """Rewrite the migrated ministry domain; leave other hosts unchanged."""
    return (url or "").replace("morth.nic.in", "morth.gov.in")


def build_body(citation: str, title: str | None, url: str) -> str:
    head = f"{citation} — {title}" if title else citation
    return "\n".join([
        f"# {head}",
        "",
        f"**Citation:** {citation}",
        "",
        "India vehicle type approval is governed by the **Central Motor Vehicles Rules "
        "(CMVR)**; technical requirements are set by **Automotive Industry Standards "
        "(AIS)**, administered by ARAI for the Ministry of Road Transport & Highways "
        "(MoRTH). Many AIS standards are aligned with UN/ECE Regulations.",
        "",
        f"[Official source]({url})",
    ])


def _load_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return dict(frontmatter.load(path).metadata)


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}

    pulled: list[Path] = []
    failed: list[str] = []
    for entry in manifest.get("records", []):
        file_id = str(entry.get("id", "")).strip()
        citation = str(entry.get("citation", "")).strip()
        manifest_url = str(entry.get("source_url", "")).strip()
        if not file_id or not citation:
            continue

        existing = _load_existing(dest_dir / f"{file_id}.md")
        print(f"  Enriching IN {citation} ...", end=" ", flush=True)
        try:
            url = canonical_url(existing.get("source_url") or manifest_url)
            title = existing.get("title") or citation
            body = build_body(citation, existing.get("title"), url)

            record: dict[str, Any] = {
                "id": file_id, "title": title, "region": "IN", "citation": citation,
                "status": existing.get("status") or "in-force",
                "source_url": url, "source_api": "ais",
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

    if failed:
        print(f"\n{len(failed)} failure(s):")
        for msg in failed:
            print(f"  {msg}")
    return pulled
