"""Brazil vehicle regulation connector — CONTRAN, CONAMA, IBAMA, SENATRAN, ANATEL, MOVER.

Handles four URL types (declared per-entry in the manifest):
  pdf   — download and extract text via pdfminer (.pdf, .pdf/view, .pdf/@@download/file, direct download)
  html  — fetch HTML page and convert to markdown
  stub  — index/archive URL with no specific document; write a structured placeholder body
  atic  — third-party ATIC URL; write a structured placeholder body (no scraping)
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, markdownify, write_md

try:
    from pdfminer.high_level import extract_text as _pdf_extract
    _HAS_PDFMINER = True
except ImportError:
    _HAS_PDFMINER = False


def _extract_pdf_bytes(data: bytes) -> str:
    if not _HAS_PDFMINER:
        return ""
    try:
        return _pdf_extract(io.BytesIO(data)).strip()
    except Exception:
        return ""


def _download_pdf(session: RateLimitedSession, url: str) -> str:
    """Download a PDF from *url* and return extracted text, or empty string on failure."""
    download_url = url
    if download_url.endswith("/view"):
        download_url = download_url[:-5]
    try:
        resp = session.get(download_url)
        ct = resp.headers.get("Content-Type", "")
        if "pdf" in ct or ".pdf" in download_url.lower():
            return _extract_pdf_bytes(resp.content)
    except Exception:
        pass
    return ""


def _fetch_html_text(session: RateLimitedSession, url: str) -> str:
    """Fetch an HTML page and return markdown body, or empty string on failure."""
    try:
        resp = session.get(url)
        text = markdownify(resp.text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text
    except Exception:
        return ""


def _stub_body(title: str, citation: str, source_url: str, note: str) -> str:
    return (
        f"# {title}\n\n"
        f"**Citation:** {citation}\n\n"
        f"**Source:** [{source_url}]({source_url})\n\n"
        f"{note}"
    )


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    records_conf: list[dict[str, Any]] = manifest.get("records", [])
    session = RateLimitedSession(rate=0.5)
    pulled: list[Path] = []
    failed: list[str] = []

    for entry in records_conf:
        file_id: str = entry.get("id", "").strip()
        title: str = entry.get("title", "").strip()
        citation: str = entry.get("citation", "").strip()
        source_url: str = entry.get("source_url", "").strip()
        url_type: str = entry.get("url_type", "stub")

        if not file_id or not source_url:
            continue

        label = f"BR {citation}"
        try:
            print(f"  Pulling {label} [{url_type}] ...", end=" ", flush=True)

            if url_type == "pdf":
                text = _download_pdf(session, source_url)
                if text and len(text) > 100:
                    body = f"# {title}\n\n{text}"
                else:
                    body = _stub_body(title, citation, source_url,
                                      "Full text could not be extracted automatically. "
                                      "Visit the source URL to download the official document.")

            elif url_type == "html":
                text = _fetch_html_text(session, source_url)
                if text and len(text) > 300:
                    body = text if text.startswith("#") else f"# {title}\n\n{text}"
                else:
                    body = _stub_body(title, citation, source_url,
                                      "Full text not available from this page. "
                                      "Visit the source URL for the official document.")

            elif url_type == "atic":
                body = _stub_body(title, citation, source_url,
                                  "This regulation is administered through Brazil's vehicle "
                                  "type-approval process. Full text is accessible via the "
                                  "official certification body (ATIC) or SENATRAN resolution archive.")

            else:  # stub
                body = _stub_body(title, citation, source_url,
                                  "Full text requires visiting the official CONTRAN resolution archive. "
                                  "The source URL links to the archive index where this resolution can be found.")

            record: dict[str, Any] = {
                "id": file_id,
                "title": title,
                "region": "BR",
                "citation": citation,
                "status": "in-force",
                "source_url": source_url,
                "source_api": "brazil",
                "tagging_status": "untagged",
                "translation_status": "untranslated",
            }
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
