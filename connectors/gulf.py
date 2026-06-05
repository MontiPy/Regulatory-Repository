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
