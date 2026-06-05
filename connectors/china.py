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


# Detail-page field labels, in roughly the order they appear. _field() captures
# the text between a label and whichever of these labels comes next.
_LABELS = [
    "标准号", "中文标准名称", "英文标准名称", "标准状态", "在线预览", "下载",
    "实施信息", "中国标准分类", "国际标准分类", "发布日期", "实施日期",
    "主管部门", "归口部门", "发布单位", "备注", "采用国际标准",
]


def _field(html: str, label: str) -> str | None:
    """Text between the first occurrence of *label* and the next known label."""
    i = html.find(label)
    if i < 0:
        return None
    rest = html[i + len(label):]
    cut = len(rest)
    for other in _LABELS:
        j = rest.find(other)
        if 0 <= j < cut:
            cut = j
    text = re.sub(r"<[^>]+>", " ", rest[:cut])
    text = text.replace("：", " ").replace(":", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _status(html: str) -> str | None:
    raw = _field(html, "标准状态") or ""
    if "现行" in raw:
        return "in-force"
    if any(tok in raw for tok in ("废止", "被代替", "作废", "已作废")):
        return "abolished"
    return None


def _impl_date(html: str) -> str | None:
    raw = _field(html, "实施日期") or ""
    m = re.search(r"\d{4}-\d{2}-\d{2}", raw)
    return m.group(0) if m else None


def _adopted(html: str) -> str | None:
    """Best-effort adopted-standard token; None when the row is absent/empty."""
    raw = _field(html, "采用国际标准") or ""
    m = re.search(r"(?:ECE|UN|ISO|IEC)\s?R?\s?\d+[A-Za-z]?", raw)
    return m.group(0).replace("  ", " ").strip() if m else None


def parse_detail(html: str) -> dict[str, Any]:
    return {
        "cn_title": _field(html, "中文标准名称"),
        "en_title": _field(html, "英文标准名称"),
        "status": _status(html),
        "impl_date": _impl_date(html),
        "adopted_standard": _adopted(html),
    }
