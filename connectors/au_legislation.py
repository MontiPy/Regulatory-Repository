"""Australian Federal Register of Legislation connector — pulls ADR instruments."""
from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, markdownify, write_md

API_BASE = "https://api.prod.legislation.gov.au/v1"
BROWSE_BASE = "https://www.legislation.gov.au"


def _instrument_url(instrument_id: str) -> str:
    return f"https://www.legislation.gov.au/Details/{instrument_id}"


def _fetch_epub_text(session: RateLimitedSession, instrument_id: str) -> str:
    """Latest compiled text, from the FRL API's EPUB rendition (zipped XHTML, in spine order)."""
    url = (
        f"{API_BASE}/documents/find(titleId='{instrument_id}',asAtSpecification='Latest',type='Primary',"
        "format='Epub',uniqueTypeNumber=0,volumeNumber=0,rectificationVersionNumber=0)"
    )
    try:
        data = session.get(url).content
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        return ""
    opf_name = next((n for n in zf.namelist() if n.endswith(".opf")), None)
    if opf_name:
        opf = zf.read(opf_name).decode("utf-8", errors="replace")
        base = opf_name.rsplit("/", 1)[0] + "/" if "/" in opf_name else ""
        hrefs = dict(re.findall(r'<item[^>]*id="([^"]+)"[^>]*href="([^"]+)"', opf))
        hrefs.update({k: v for v, k in re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"', opf)})
        order = [base + hrefs[i] for i in re.findall(r'<itemref[^>]*idref="([^"]+)"', opf) if i in hrefs]
    else:
        order = sorted(n for n in zf.namelist() if n.endswith((".xhtml", ".html", ".htm")))
    parts = []
    for name in order:
        try:
            html = zf.read(name).decode("utf-8", errors="replace")
        except KeyError:
            continue
        m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        parts.append(markdownify(m.group(1) if m else html))
    return re.sub(r"\n{3,}", "\n\n", "\n\n".join(parts)).strip()


def _fetch_instrument(session: RateLimitedSession, instrument_id: str, hint_title: str) -> tuple[dict[str, Any], str]:
    detail_url = f"{API_BASE}/legislation/{instrument_id}"
    try:
        resp = session.get(detail_url, headers={"Accept": "application/json"})
        data = resp.json() if hasattr(resp, "json") else {}
    except Exception:
        data = {}

    title = data.get("title") or hint_title or instrument_id
    if not isinstance(title, str):
        title = str(title)

    clean_id = re.sub(r"[^a-zA-Z0-9]", "-", instrument_id.lower()).strip("-")
    slug = f"au-{clean_id}"

    citation_match = re.search(r"ADR\s+(\d+[\w/]*)", hint_title, re.IGNORECASE)
    if citation_match:
        citation = f"ADR {citation_match.group(1)}"
    else:
        citation = instrument_id

    md_body = _fetch_epub_text(session, instrument_id)
    if not md_body:
        md_body = f"# {title}\n\nSee {_instrument_url(instrument_id)} for full text."

    record: dict[str, Any] = {
        "id": slug,
        "title": title,
        "region": "AU",
        "citation": citation,
        "status": "in-force",
        "source_url": _instrument_url(instrument_id),
        "source_api": "au_legislation",
        "tagging_status": "untagged",
    }
    return record, md_body


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    records_conf: list[dict[str, Any]] = manifest.get("records", [])
    session = RateLimitedSession(rate=1.0)
    pulled: list[Path] = []
    failed: list[str] = []

    for entry in records_conf:
        instrument_id = entry.get("instrument_id", "").strip()
        hint_title = entry.get("title", "")
        if not instrument_id:
            continue

        label = f"AU {instrument_id} ({hint_title})"
        try:
            print(f"  Pulling {label} ...", end=" ", flush=True)
            record, body = _fetch_instrument(session, instrument_id, hint_title)
            path = write_md(record, body, dest_dir)
            pulled.append(path)
            print(f"OK -> {path.name}")
        except Exception as exc:
            print(f"FAILED: {exc}")
            failed.append(f"{label}: {exc}")

    session.close()

    if failed:
        print(f"\n{len(failed)} failure(s):")
        for msg in failed:
            print(f"  {msg}")

    return pulled
