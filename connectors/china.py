"""China GB standards connector — metadata enrichment from openstd.samr.gov.cn.

Resolves each GB number to its official record on the national standards portal
and writes title / status / implementation date / adopted-standard cross-reference.
Full text is image-based on the portal and is not captured. Existing LLM tags and
UN-equivalent cross-references on the target file are preserved.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import frontmatter
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, write_md

try:
    from scripts.un_refs import normalize_un
except ImportError:  # when run as a script from repo root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from un_refs import normalize_un

BASE = "https://openstd.samr.gov.cn/bzgk/gb"

# A search-result row: showInfo('<HCNO>'); ... > GB 11551-2014 </a>
_ROW_RE = re.compile(r"showInfo\('([0-9A-Fa-f]{32})'\)[^>]*>\s*(GB[^<]+?)\s*</a>")


def search_hcno(session: Any, gb_number: str) -> tuple[str, str] | None:
    """Return (hcno, matched_label) for a GB number, or None if not found.

    Searches the bare GB number; for a versioned query returns the exact-version
    row, otherwise the most recent version (by trailing year).
    """
    bare = gb_number.split("-")[0].strip()
    resp = session.get(f"{BASE}/std_list?p.p2={quote(bare)}")
    resp.encoding = "utf-8"
    pairs = [(h.upper(), lbl.strip()) for h, lbl in _ROW_RE.findall(resp.text)]
    if not pairs:
        return None
    target = gb_number.strip()
    for hcno, label in pairs:
        if label == target:
            return (hcno, label)

    def year(label: str) -> int:
        m = re.search(r"-(\d{4})$", label)
        return int(m.group(1)) if m else 0

    return max(pairs, key=lambda p: year(p[1]))
