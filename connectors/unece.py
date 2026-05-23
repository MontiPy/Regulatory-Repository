"""UNECE WP.29 connector — pulls UN Regulation texts from the UNECE transport portal.

Manifest entries:
  - { regulation: 10, title: "Electromagnetic Compatibility (EMC)" }
  - { regulation: "13-H", title: "Braking of Passenger Cars" }

The connector fetches the UNECE WP.29 regulations index page once, discovers
individual regulation page URLs, then fetches each page for content. When a
page cannot be reached (network unavailable) it writes a structured placeholder
pointing to the canonical UNECE source URL.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, markdownify, write_md

ECE_BASE = "https://unece.org"
ECE_INDEX_URL = f"{ECE_BASE}/transport/vehicle-regulations-wp29/Regulations"


def _ece_slug(reg_num: int | str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]", "-", str(reg_num)).strip("-").lower()
    return f"ece-r{clean}"


def _citation(reg_num: int | str) -> str:
    return f"UN R{reg_num}"


def _discover_reg_url(index_html: str, reg_num: int | str) -> str | None:
    """Find a specific regulation page URL from the WP.29 index HTML."""
    num_str = str(reg_num)
    patterns = [
        rf'href="([^"]+)"[^>]*>[^<]*[Rr]egulation[^<]*[Nn]o\.?\s*{re.escape(num_str)}\b',
        rf'href="([^"]+regulation-no-{re.escape(num_str.lower())}[^"]*)"',
    ]
    for pattern in patterns:
        m = re.search(pattern, index_html)
        if m:
            href = m.group(1)
            if href.startswith("/"):
                return ECE_BASE + href
            if href.startswith("http"):
                return href
    return None


def _parse_title_from_page(html: str, reg_num: int | str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL | re.IGNORECASE)
    if m:
        raw = re.sub(r"<[^>]+>", " ", m.group(1))
        title = " ".join(raw.split()).strip()
        if title and len(title) > 5:
            return title
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if m:
        raw = re.sub(r"<[^>]+>", " ", m.group(1))
        title = " ".join(raw.split()).strip()
        if title and "unece" not in title.lower():
            return title
    return ""


def _extract_page_body(html: str) -> str:
    for tag in ("nav", "header", "footer", "script", "style", "aside"):
        html = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.DOTALL | re.IGNORECASE)
    m = re.search(
        r'<(?:main|article|div[^>]*(?:id|class)="[^"]*content[^"]*"[^>]*)>(.*?)</(?:main|article|div)>',
        html, re.DOTALL | re.IGNORECASE,
    )
    body = m.group(1) if m else html
    md = markdownify(body)
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def _fetch_regulation(
    session: RateLimitedSession,
    reg_num: int | str,
    title_hint: str,
    index_html: str | None,
) -> tuple[dict[str, Any], str]:
    reg_url = ECE_INDEX_URL
    title = f"UN Regulation No. {reg_num}"
    if title_hint:
        title = f"UN Regulation No. {reg_num} — {title_hint}"

    md_body = ""

    if index_html:
        found_url = _discover_reg_url(index_html, reg_num)
        if found_url:
            try:
                resp = session.get(found_url)
                page_html = resp.content.decode("utf-8", errors="replace")
                found_title = _parse_title_from_page(page_html, reg_num)
                if found_title and not title_hint:
                    title = found_title
                md_body = _extract_page_body(page_html)
                reg_url = found_url
            except Exception:
                pass

    if not md_body:
        md_body = (
            f"# {title}\n\n"
            f"See the [UNECE WP.29 Regulations index]({ECE_INDEX_URL}) "
            f"for the full text of UN Regulation No. {reg_num}."
        )

    record: dict[str, Any] = {
        "id": _ece_slug(reg_num),
        "title": title,
        "region": "ECE",
        "citation": _citation(reg_num),
        "status": "in-force",
        "source_url": reg_url,
        "source_api": "unece",
        "tagging_status": "untagged",
    }
    return record, md_body


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    records_conf: list[dict[str, Any]] = manifest.get("records", [])
    session = RateLimitedSession(rate=0.5)
    pulled: list[Path] = []
    failed: list[str] = []

    index_html: str | None = None
    print("  Fetching UNECE WP.29 regulation index ...", end=" ", flush=True)
    try:
        resp = session.get(ECE_INDEX_URL)
        index_html = resp.content.decode("utf-8", errors="replace")
        print("OK")
    except Exception as exc:
        print(f"WARN ({exc}); will use placeholder bodies")

    for entry in records_conf:
        reg_num = entry.get("regulation")
        if reg_num is None:
            continue
        title_hint = str(entry.get("title", "")).strip()
        label = f"UN R{reg_num}"
        try:
            print(f"  Pulling {label} ...", end=" ", flush=True)
            record, body = _fetch_regulation(session, reg_num, title_hint, index_html)
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
