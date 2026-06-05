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


def _merge_un_equivalent(existing: list[str], adopted_standard: str | None) -> list[str]:
    """Union existing grounded UN refs with the adopted-standard ref when it is a
    UN/ECE regulation. ISO/IEC standards are not UN regs and are excluded."""
    out = list(existing or [])
    if adopted_standard:
        canon = normalize_un(adopted_standard.replace("ECE", "UN"))
        if canon and canon not in out:
            out.append(canon)
    return out


def build_body(meta: dict[str, Any], gb_number: str, source_url: str) -> str:
    en = (meta.get("en_title") or "").strip()
    cn = (meta.get("cn_title") or "").strip()
    head = f"{gb_number} — {en}" if en else gb_number
    status = meta.get("status") or "unknown"
    status_disp = {"in-force": "In-force", "abolished": "Abolished"}.get(status, status)

    lines = [f"# {head}", "", f"**Standard No.:** {gb_number}"]
    if cn:
        lines.append(f"**Chinese title:** {cn}")
    status_line = f"**Status:** {status_disp}"
    if meta.get("impl_date"):
        status_line += f"  **Implementation date:** {meta['impl_date']}"
    lines.append(status_line)
    if meta.get("adopted_standard"):
        lines.append(f"**Adopted international standard:** {meta['adopted_standard']}")
    lines += [
        "",
        "Full standard text is published by SAC and viewed through the official "
        "portal's online reader (image-based; not reproduced here).",
        "",
        f"[Official record — openstd.samr.gov.cn]({source_url})",
    ]
    return "\n".join(lines)


def enriched_stub_body(gb_number: str, source_url: str) -> str:
    link = f"[{source_url}]({source_url})" if source_url else "the official portal"
    return (
        f"# {gb_number}\n\n"
        f"**Standard No.:** {gb_number}\n\n"
        f"This standard could not be resolved on the official portal "
        f"(openstd.samr.gov.cn) automatically. Visit {link} for the official record."
    )


def fetch_detail(session: Any, hcno: str) -> str:
    resp = session.get(f"{BASE}/newGbInfo?hcno={hcno}")
    resp.encoding = "utf-8"
    return resp.text


def _load_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return dict(frontmatter.load(path).metadata)


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}

    session = RateLimitedSession(rate=0.5)
    pulled: list[Path] = []
    failed: list[str] = []

    for entry in manifest.get("records", []):
        file_id = str(entry.get("id", "")).strip()
        gb = str(entry.get("gb_number", "")).strip()
        fallback_url = str(entry.get("source_url", "")).strip()
        if not file_id or not gb:
            continue

        existing = _load_existing(dest_dir / f"{file_id}.md")
        meta: dict[str, Any] = {}
        print(f"  Pulling CN {gb} ...", end=" ", flush=True)
        try:
            found = search_hcno(session, gb)
            if not found:
                raise LookupError("not found on openstd")
            hcno, label = found
            source_url = f"{BASE}/newGbInfo?hcno={hcno}"
            meta = parse_detail(fetch_detail(session, hcno))
            citation = label
            title = meta.get("en_title") or meta.get("cn_title") or existing.get("title") or label
            status = meta.get("status") or existing.get("status") or "in-force"
            body = build_body(meta, citation, source_url)
            print(f"OK ({'in-force' if status=='in-force' else status})")
        except Exception as exc:
            citation = existing.get("citation") or gb
            source_url = fallback_url or existing.get("source_url") or ""
            title = existing.get("title") or gb
            status = existing.get("status") or "in-force"
            body = enriched_stub_body(gb, source_url)
            failed.append(f"{gb}: {exc}")
            print(f"STUB ({exc})")

        record: dict[str, Any] = {
            "id": file_id, "title": title, "region": "CN", "citation": citation,
            "status": status, "source_url": source_url or fallback_url or f"{BASE}/std/index",
            "source_api": "china",
            "tagging_status": existing.get("tagging_status", "untagged"),
        }
        un_eq = _merge_un_equivalent(existing.get("un_equivalent", []), meta.get("adopted_standard"))
        if un_eq:
            record["un_equivalent"] = un_eq
        for field in ("un_equivalent_ai", "translation_status", "paywall", "tagged_at"):
            if existing.get(field) not in (None, [], ""):
                record[field] = existing[field]
        aliases = list(existing.get("aliases", []) or [])
        prev_title = existing.get("title")
        if prev_title and prev_title != title and prev_title not in aliases:
            aliases.append(prev_title)
        if aliases:
            record["aliases"] = sorted(set(aliases))
        if meta.get("impl_date"):
            record["effective_date"] = meta["impl_date"]

        pulled.append(write_md(record, body, dest_dir))

    session.close()
    if failed:
        print(f"\n{len(failed)} fell back to stub:")
        for msg in failed:
            print(f"  {msg}")
    return pulled
