"""EUR-Lex connector — pulls EU regulations via the EUR-Lex REST API."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectors._common import RateLimitedSession, markdownify, write_md

EURLEX_REST = "https://eur-lex.europa.eu/legal-content/{celex}/TXT/HTML/"
EURLEX_API = "https://eur-lex.europa.eu/oj/direct-access.html"

# EUR-Lex data service (returns XML metadata)
EURLEX_WEBSERVICE = "https://eur-lex.europa.eu/legal-content/{celex}/TXT/HTML/?uri=CELEX:{celex}"
EURLEX_META_API = "https://eur-lex.europa.eu/legal-content/{celex}/ALL/?uri=CELEX:{celex}"

# EUR-Lex REST API for metadata
EURLEX_API_BASE = "https://eur-lex.europa.eu/oj/collection.html"
EURLEX_DATA_SERVICE = "https://eur-lex.europa.eu/legal-content/{celex}/TXT/HTML/?uri=CELEX:{celex}&from=EN"

CELEX_META_URL = "https://eur-lex.europa.eu/legal-content/{celex}/ALL/?uri=CELEX:{celex}"
CELEX_HTML_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{celex}"


def _celex_to_slug(celex: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]", "-", celex.lower()).strip("-")
    return f"eu-{clean}"


def _fetch_html_content(session: RateLimitedSession, celex: str) -> str:
    url = CELEX_HTML_URL.format(celex=celex)
    try:
        resp = session.get(url)
        return resp.text
    except Exception:
        return ""


def _parse_title_from_html(html: str) -> str:
    # Priority 1: oj-doc-ti / doc-ti class paragraphs (always preferred)
    match = re.search(r"<p[^>]*class=['\"][^'\"]*doc-ti[^'\"]*['\"][^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
    if match:
        raw = re.sub(r"<[^>]+>", " ", match.group(1))
        title = " ".join(raw.split())
        if title:
            return title

    # Priority 2: older pages — first <strong> inside a <p> that looks like a legal title
    match = re.search(r"<p[^>]*>\s*<strong>((?:Regulation|Directive|Decision|Commission)[^<]{10,})</strong>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = " ".join(match.group(1).split())
        if title:
            return title[:300]

    # Priority 3: <title> tag, filtering XML/HTML filenames and EUR-Lex boilerplate
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if match:
        raw = re.sub(r"<[^>]+>", " ", match.group(1))
        title = " ".join(raw.split())
        if title and not title.lower().startswith("eur-lex") and not re.search(r"\.(xml|html?|pdf)$", title, re.IGNORECASE):
            return title

    return ""


def _title_from_md_body(md_body: str) -> str:
    for line in md_body.splitlines():
        line = line.strip()
        if re.match(r"^(REGULATION|DIRECTIVE|DECISION|IMPLEMENTING|DELEGATED)\s+\(EU", line, re.IGNORECASE):
            return line[:200]
        if re.match(r"^(REGULATION|DIRECTIVE|DECISION)\s+\(EC|EEC|EURATOM", line, re.IGNORECASE):
            return line[:200]
        if re.match(r"^(Regulation|Directive|Decision)\s+\d{4}/\d+", line):
            return line[:200]
    return ""


def _parse_date_from_html(html: str) -> str:
    match = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", html)
    if match:
        months = {"January": "01", "February": "02", "March": "03", "April": "04",
                  "May": "05", "June": "06", "July": "07", "August": "08",
                  "September": "09", "October": "10", "November": "11", "December": "12"}
        day, month_name, year = match.group(1), match.group(2), match.group(3)
        return f"{year}-{months[month_name]}-{int(day):02d}"
    return ""


def _extract_body_html(full_html: str) -> str:
    match = re.search(r"<body[^>]*>(.*?)</body>", full_html, re.DOTALL | re.IGNORECASE)
    if match:
        body = match.group(1)
        body = re.sub(r"<nav[^>]*>.*?</nav>", "", body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r"<header[^>]*>.*?</header>", "", body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r"<footer[^>]*>.*?</footer>", "", body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
        return body
    return full_html


def pull(manifest_path: Path, dest_dir: Path) -> list[Path]:
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    records_conf: list[dict[str, Any]] = manifest.get("records", [])

    seen_celex: set[str] = set()
    unique_records: list[dict[str, Any]] = []
    for entry in records_conf:
        celex = entry.get("celex", "").strip()
        if celex and celex not in seen_celex:
            seen_celex.add(celex)
            unique_records.append(entry)

    session = RateLimitedSession(rate=1.0)
    pulled: list[Path] = []
    failed: list[str] = []

    for entry in unique_records:
        celex = entry.get("celex", "").strip()
        if not celex:
            continue

        label = f"EUR-Lex CELEX {celex}"
        try:
            print(f"  Pulling {label} ...", end=" ", flush=True)

            html = _fetch_html_content(session, celex)
            if not html:
                raise RuntimeError("Empty response from EUR-Lex")

            title_text = _parse_title_from_html(html)
            effective_date = _parse_date_from_html(html)

            body_html = _extract_body_html(html)
            md_body = markdownify(body_html)
            md_body = re.sub(r"\n{3,}", "\n\n", md_body).strip()

            if not title_text:
                title_text = _title_from_md_body(md_body)
            if not title_text:
                title_text = celex

            slug = _celex_to_slug(celex)
            citation = f"CELEX {celex}"
            src_url = CELEX_HTML_URL.format(celex=celex)

            record: dict[str, Any] = {
                "id": slug,
                "title": title_text,
                "region": "EU",
                "citation": citation,
                "status": "in-force",
                "source_url": src_url,
                "source_api": "eurlex",
                "tagging_status": "untagged",
            }
            if effective_date:
                record["effective_date"] = effective_date

            path = write_md(record, md_body, dest_dir)
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
