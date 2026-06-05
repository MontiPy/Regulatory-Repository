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
